"""Train MobileNetV3 from ImageNet, select on validation, calibrate separately, export ONNX."""
import argparse
import csv
import hashlib
import json
import random
from collections import Counter, defaultdict
from pathlib import Path
import numpy as np
import torch
from torch import nn
from torch.utils.data import Dataset, DataLoader
from torchvision import models, transforms
from PIL import Image, ImageOps
from app.catalog import canonical
from app.imaging import preprocess

PREPROCESS = {"size":224,"resize_short":256,"mean":[.485,.456,.406],"std":[.229,.224,.225]}

def read_splits(path):
    rows = list(csv.DictReader(Path(path).open(newline="", encoding="utf-8")))
    if not rows:
        raise ValueError("Empty split manifest")
    groups, hashes = defaultdict(set), defaultdict(set)
    for row in rows:
        row["label"] = canonical(row["label"])
        if row["split"] not in {"train", "val", "calibration", "test"}:
            raise ValueError("Invalid split")
        groups[row["group"]].add(row["split"])
        hashes[row["pixel_sha256"]].add(row["split"])
    if any(len(s) > 1 for s in [*groups.values(), *hashes.values()]):
        raise ValueError("Leakage: a physical group or duplicate crosses splits")
    labels = sorted({r["label"] for r in rows})
    for split in ("train", "val", "calibration", "test"):
        if {r["label"] for r in rows if r["split"] == split} != set(labels):
            raise ValueError(f"Every class must be represented in {split}")
    return rows, labels

class Leaves(Dataset):
    def __init__(self, rows, labels, split):
        self.rows = [r for r in rows if r["split"] == split]
        self.mapping = {label:i for i,label in enumerate(labels)}
        self.augmentation = transforms.Compose([
            transforms.RandomResizedCrop(224, scale=(.65,1.0)),
            transforms.RandomHorizontalFlip(), transforms.RandomVerticalFlip(),
            transforms.RandomRotation(20), transforms.ColorJitter(.15,.15,.1,.03),
            transforms.ToTensor(), transforms.Normalize(PREPROCESS["mean"], PREPROCESS["std"])
        ]) if split == "train" else None
    def __len__(self):
        return len(self.rows)
    def __getitem__(self, idx):
        row = self.rows[idx]
        with Image.open(row["path"]) as im:
            im = ImageOps.exif_transpose(im).convert("RGB")
            x = self.augmentation(im) if self.augmentation else torch.from_numpy(preprocess(im, PREPROCESS)[0])
        return x, self.mapping[row["label"]]

def make_model(count, pretrained=True):
    model = models.mobilenet_v3_small(weights=models.MobileNet_V3_Small_Weights.DEFAULT if pretrained else None)
    model.classifier[3] = nn.Linear(model.classifier[3].in_features, count)
    return model

@torch.inference_mode()
def gather(model, loader, device):
    model.eval(); logits=[]; labels=[]
    for x,y in loader:
        logits.append(model(x.to(device)).cpu()); labels.append(y)
    return torch.cat(logits), torch.cat(labels)

def calibrate(logits, targets):
    # Search one scalar on calibration-only data. No threshold optimization on test.
    candidates = torch.logspace(-.7, .7, 81)
    loss = [nn.functional.cross_entropy(logits / t, targets).item() for t in candidates]
    return float(candidates[int(np.argmin(loss))])

def train(args):
    torch.manual_seed(args.seed); random.seed(args.seed); np.random.seed(args.seed)
    torch.set_num_threads(args.threads)
    rows, labels = read_splits(args.manifest)
    if len(labels) < 2:
        raise ValueError("At least two classes are required")
    out = Path(args.out)
    if out.exists() and any(out.iterdir()):
        raise ValueError("Choose an empty output directory to preserve prior runs")
    out.mkdir(parents=True, exist_ok=True)
    device = torch.device(args.device if args.device != "auto" else ("cuda" if torch.cuda.is_available() else "cpu"))
    data = {split: Leaves(rows, labels, split) for split in ["train","val","calibration"]}
    loaders = {split:DataLoader(ds,batch_size=args.batch_size,shuffle=split=="train",num_workers=args.workers) for split,ds in data.items()}
    model = make_model(len(labels), not args.no_pretrained).to(device)
    for parameter in model.features.parameters():
        parameter.requires_grad = False
    frequencies=Counter(r["label"] for r in rows if r["split"]=="train")
    class_weights=torch.tensor([1/np.sqrt(frequencies[label]) for label in labels],device=device,dtype=torch.float32)
    class_weights /= class_weights.mean()
    loss_fn=nn.CrossEntropyLoss(weight=class_weights)
    optimizer=torch.optim.AdamW(model.classifier.parameters(),lr=args.lr,weight_decay=.001)
    history=[]; best=float("inf"); stale=0
    for epoch in range(args.epochs):
        if epoch==args.warmup_epochs:
            for parameter in model.features.parameters():parameter.requires_grad=True
            optimizer=torch.optim.AdamW(model.parameters(),lr=args.lr/10,weight_decay=.001)
        model.train()
        if epoch < args.warmup_epochs:model.features.eval()
        running=0.;total=0
        for x,y in loaders["train"]:
            x,y=x.to(device),y.to(device);optimizer.zero_grad(set_to_none=True)
            loss=loss_fn(model(x),y);loss.backward();optimizer.step()
            running+=loss.item()*len(y);total+=len(y)
        logits,targets=gather(model,loaders["val"],device)
        val_loss=nn.functional.cross_entropy(logits,targets).item()
        accuracy=(logits.argmax(1)==targets).float().mean().item()
        record={"epoch":epoch+1,"train_loss":running/total,"val_loss":val_loss,"val_accuracy":accuracy}
        history.append(record);print(json.dumps(record),flush=True)
        if val_loss < best:
            best=val_loss;stale=0
            torch.save({"state_dict":model.state_dict(),"labels":labels},out/"best.pt")
        else:
            stale+=1
        if stale>=args.patience and epoch>=args.warmup_epochs:break
    checkpoint=torch.load(out/"best.pt",map_location=device,weights_only=True)
    model.load_state_dict(checkpoint["state_dict"])
    logits,targets=gather(model,loaders["calibration"],device)
    temperature=calibrate(logits,targets)
    model=model.cpu().eval()
    sample=torch.randn(1,3,224,224)
    torch.onnx.export(model,sample,str(out/"model.onnx"),input_names=["input"],output_names=["logits"],
                      dynamic_axes={"input":{0:"batch"},"logits":{0:"batch"}},opset_version=17,dynamo=False,external_data=False)
    import onnxruntime as ort
    ort_session=ort.InferenceSession(str(out/"model.onnx"),providers=["CPUExecutionProvider"])
    with torch.inference_mode():reference=model(sample).numpy()
    exported=ort_session.run(None,{"input":sample.numpy()})[0]
    error=float(np.max(np.abs(reference-exported)))
    if error > 3e-4:raise RuntimeError(f"ONNX parity failed: {error}")
    digest=hashlib.sha256((out/"model.onnx").read_bytes()).hexdigest()
    manifest={"schema":1,"name":"Leafwise · trained MobileNetV3","revision":digest[:16],"labels":labels,
              "preprocess":PREPROCESS,"temperature":temperature,"sha256":{"model.onnx":digest},
              "decision":{"threshold":.85,"margin":.25,"calibrated":False},
              "source":"Locally trained from supplied dataset manifest", "field_validated":False,
              "notes":"Temperature fitted on calibration split. Decision thresholds are provisional. Independent field evaluation required."}
    (out/"manifest.json").write_text(json.dumps(manifest,indent=2))
    (out/"training.json").write_text(json.dumps({"history":history,"seed":args.seed,"device":str(device),
        "temperature":temperature,"onnx_max_abs_error":error,"pretrained":not args.no_pretrained,
        "manifest_sha256":hashlib.sha256(Path(args.manifest).read_bytes()).hexdigest()},indent=2))
    print(f"Exported {out}. Now evaluate the held-out test split; it has not been used to fit the model.")

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--manifest",required=True);p.add_argument("--out",required=True)
    p.add_argument("--epochs",type=int,default=15);p.add_argument("--warmup-epochs",type=int,default=3)
    p.add_argument("--batch-size",type=int,default=32);p.add_argument("--lr",type=float,default=3e-4)
    p.add_argument("--patience",type=int,default=4);p.add_argument("--workers",type=int,default=0)
    p.add_argument("--threads",type=int,default=4);p.add_argument("--device",default="auto")
    p.add_argument("--seed",type=int,default=42);p.add_argument("--no-pretrained",action="store_true",help="Smoke testing only; real training benefits from ImageNet weights")
    a=p.parse_args()
    if a.epochs<1 or a.batch_size<1 or a.warmup_epochs<0:p.error("Invalid training sizes")
    train(a)

if __name__=="__main__":
    main()
