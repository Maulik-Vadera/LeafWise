"""Evaluate a frozen ONNX model on untouched data. Never changes model thresholds."""
import argparse
import csv
import json
from pathlib import Path
import numpy as np
from PIL import Image, ImageOps
from app.catalog import canonical
from app.inference import LeafModel, softmax
from app.imaging import preprocess, quality

def evaluate(model_dir, csv_path, output, split="test", unknown_root=None):
    model=LeafModel(model_dir)
    if not model.ready:raise ValueError(model.error)
    rows=[r for r in csv.DictReader(Path(csv_path).open(newline="",encoding="utf-8")) if r.get("split",split)==split]
    if not rows:raise ValueError("No images in the selected evaluation split")
    mapping={label:i for i,label in enumerate(model.labels)}
    truth=[];pred=[];scores=[];accepted=[]
    config=model.manifest["preprocess"]
    for row in rows:
        label=canonical(row["label"])
        if label not in mapping:raise ValueError(f"Unsupported evaluation label: {label}")
        with Image.open(row["path"]) as im:
            im=ImageOps.exif_transpose(im).convert("RGB")
            x=preprocess(im,config)
            logits=model.session.run(None,{model.session.get_inputs()[0].name:x})[0]
            p=softmax(logits,model.manifest.get("temperature",1))[0]
            # Evaluate the real application's acceptance policy, including image quality.
            q=quality(im)
            result=model.predict([im],label.split("___")[0],bool(q["warnings"]))
        truth.append(mapping[label]);pred.append(int(p.argmax()));scores.append(p)
        accepted.append(q["usable"] and result["status"]=="possible_match")
    y=np.array(truth);guesses=np.array(pred);probs=np.array(scores);accepted=np.array(accepted)
    correct=y==guesses;matrix=np.zeros((len(mapping),len(mapping)),dtype=int)
    for a,b in zip(y,guesses):matrix[a,b]+=1
    per_class=[]
    for i,label in enumerate(model.labels):
        tp=int(matrix[i,i]);support=int(matrix[i].sum());pp=int(matrix[:,i].sum())
        precision=tp/pp if pp else 0;recall=tp/support if support else 0
        f1=2*precision*recall/(precision+recall) if precision+recall else 0
        per_class.append({"label":label,"support":support,"precision":precision,"recall":recall,"f1":f1})
    confidence=probs.max(1);ece=0.
    for lower,upper in zip(np.linspace(0,1,11)[:-1],np.linspace(0,1,11)[1:]):
        mask=(confidence>=lower)&(confidence<upper if upper<1 else confidence<=upper)
        if mask.any():ece+=mask.mean()*abs(float(confidence[mask].mean())-float(correct[mask].mean()))
    present=[r["f1"] for r in per_class if r["support"]]
    result={"model":model.manifest["revision"],"split":split,"images":len(y),"accuracy":float(correct.mean()),
            "macro_f1_present_classes":float(np.mean(present)),"ece_10_bins":float(ece),
            "decision_coverage":float(accepted.mean()),"accepted_accuracy":float(correct[accepted].mean()) if accepted.any() else None,
            "per_class":per_class,"confusion_matrix":matrix.tolist(),
            "note":"Closed-set lab scores are not field reliability. Compare independent farms, seasons and devices. ECE depends on this evaluation distribution."}
    if unknown_root:
        unknown=list(p for p in Path(unknown_root).rglob('*') if p.suffix.lower() in {'.jpg','.jpeg','.png','.webp'})
        false_accepts=0; usable=0
        for path in unknown:
            with Image.open(path) as im:
                im=ImageOps.exif_transpose(im).convert('RGB');q=quality(im)
                if not q['usable']:continue
                usable+=1
                first=model.predict([im],'auto',bool(q['warnings']))
                # Worst case: user mistakenly confirms the model's own crop guess.
                follow=model.predict([im],first['candidate']['crop_id'],bool(q['warnings']))
                false_accepts+=follow['status']=='possible_match'
        result['unknown_set']={'images':len(unknown),'quality_usable':usable,'false_accepts':false_accepts,
            'false_acceptance_rate_all':false_accepts/len(unknown) if unknown else None,
            'note':'Non-leaves and unsupported crops; assumes user confirms the predicted crop. No learned out-of-distribution detector is included.'}
    Path(output).parent.mkdir(parents=True,exist_ok=True)
    Path(output).write_text(json.dumps(result,indent=2));return result

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--model',required=True);p.add_argument('--manifest',required=True)
    p.add_argument('--out',required=True);p.add_argument('--split',default='test');p.add_argument('--unknown-root')
    a=p.parse_args();r=evaluate(a.model,a.manifest,a.out,a.split,a.unknown_root)
    print(json.dumps({k:v for k,v in r.items() if k not in {'confusion_matrix','per_class'}},indent=2))

if __name__=='__main__':main()
