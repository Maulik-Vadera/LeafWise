"""Fail-closed ONNX loading and selective, multi-view classification."""
import hashlib
import json
from pathlib import Path
import threading
import numpy as np
from .catalog import canonical, entry, generic_guide
from .imaging import preprocess

def softmax(logits, temperature=1.0):
    values = np.asarray(logits, dtype=np.float64) / temperature
    values -= values.max(axis=-1, keepdims=True)
    ex = np.exp(values)
    return ex / ex.sum(axis=-1, keepdims=True)

def decide(probabilities, labels, crop_hint, quality_warnings=False, threshold=.85, margin=.25):
    if crop_hint == "auto":
        return {"status": "needs_identification", "candidate": None, "candidates": [],
                "reasons": ["This disease model cannot identify an unknown plant. Use Identify a plant first."],
                "guide": generic_guide()}
    probabilities = np.asarray(probabilities)
    if probabilities.ndim != 2 or probabilities.shape[1] != len(labels) or not np.isfinite(probabilities).all():
        raise ValueError("Invalid inference output")
    mean = probabilities.mean(axis=0)
    ordered = np.argsort(mean)[::-1]
    top = int(ordered[0]); second = int(ordered[1])
    best = entry(labels[top])
    agreement = len(set(probabilities.argmax(axis=1).tolist())) == 1
    reasons = []
    if crop_hint == "auto":
        reasons.append("Confirm the crop before using disease-specific guidance.")
    if crop_hint not in {"auto", best["crop_id"]}:
        reasons.append("The photo prediction does not agree with the crop you selected.")
    if mean[top] < threshold or mean[top] - mean[second] < margin:
        reasons.append("The model cannot separate the leading possibilities clearly enough.")
    if not agreement:
        reasons.append("The photos disagree. Retake clear views of the same affected leaf.")
    if quality_warnings:
        reasons.append("Photo quality may be limiting this result.")
    accepted = not reasons
    status = "possible_match" if accepted else "uncertain"
    candidates = [{"id": labels[int(i)], "crop": entry(labels[int(i)])["crop"],
                   "name": entry(labels[int(i)])["name"], "score": round(float(mean[i]), 5)}
                  for i in ordered if entry(labels[int(i)])["crop_id"] == crop_hint][:3]
    crop_matches = crop_hint == best["crop_id"]
    return {"status": status, "candidate": best if crop_matches else None, "candidates": candidates if crop_matches else [],
            "score": round(float(mean[top]), 5), "view_agreement": agreement,
            "reasons": reasons, "guide": best if accepted else generic_guide(),
            "score_note": "Model score is a relative match among supported classes, not a probability that the diagnosis is correct.",
            "scope_note": "This classifier cannot reliably reject every unfamiliar plant or non-leaf image. It screens visible patterns only.",
            "variety": {"status": "not_identified", "name": None}}

class LeafModel:
    def __init__(self, directory):
        self.directory = Path(directory)
        self.session = None
        self.error = None
        self.manifest = {}
        self.labels = []
        self.lock = threading.Lock()
        self.load()

    def load(self):
        try:
            import onnxruntime as ort
            self.manifest = json.loads((self.directory / "manifest.json").read_text("utf-8"))
            self.labels = [canonical(s) for s in self.manifest["labels"]]
            if len(set(self.labels)) != len(self.labels) or len(self.labels) < 2:
                raise ValueError("Invalid label mapping")
            for name, digest in self.manifest["sha256"].items():
                path = (self.directory / name).resolve()
                if path.parent != self.directory.resolve():
                    raise ValueError("Invalid model path")
                if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
                    raise ValueError("Model checksum mismatch")
            options = ort.SessionOptions()
            options.intra_op_num_threads = 2
            options.inter_op_num_threads = 1
            options.log_severity_level = 3
            session = ort.InferenceSession(str(self.directory / "model.onnx"), sess_options=options,
                                          providers=["CPUExecutionProvider"])
            size = self.manifest["preprocess"]["size"]
            shape = session.get_inputs()[0].shape
            if shape[1:] != [3, size, size] or session.get_outputs()[0].shape[-1] != len(self.labels):
                raise ValueError("Model shapes and manifest differ")
            self.session = session
        except Exception as exc:
            # Do not expose paths or an internal traceback through the public health route.
            self.error = "Model is unavailable or failed integrity checks. See the terminal and README."
            print(f"Leafwise model unavailable ({type(exc).__name__}): {exc}")

    @property
    def ready(self):
        return self.session is not None

    @property
    def crop_ids(self):
        return sorted({entry(label)["crop_id"] for label in self.labels}) if self.ready else []

    def predict(self, images, crop_hint, warnings=False):
        if not self.ready:
            raise RuntimeError(self.error)
        predictions = []
        # Sequential views also support exports with a fixed batch size of one.
        with self.lock:
            for img in images:
                x = preprocess(img, self.manifest["preprocess"])
                logits = self.session.run(None, {self.session.get_inputs()[0].name: x})[0]
                if np.asarray(logits).shape != (1, len(self.labels)) or not np.isfinite(logits).all():
                    raise RuntimeError("Model returned invalid logits")
                predictions.append(softmax(logits, self.manifest.get("temperature", 1))[0])
        settings = self.manifest.get("decision", {})
        result = decide(predictions, self.labels, crop_hint, warnings,
                        settings.get("threshold", .85), settings.get("margin", .25))
        result["model"] = {"name": self.manifest["name"], "revision": self.manifest["revision"],
                           "field_validated": False, "class_count": len(self.labels)}
        return result
