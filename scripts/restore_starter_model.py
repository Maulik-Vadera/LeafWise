"""Restore only the two known starter-model files, with pinned revision and hashes."""
from pathlib import Path
import hashlib
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
BASE = "https://huggingface.co/imaflower/plantvillage-mobilenetv3/resolve/d76fe187be1c4c3a5474f835a7a70cd08c7ab085/"
FILES = {"model.onnx": "c6a962f699ddc820108231b23454b6a4e242407044c2c2514a0f6294d35428fc",
         "model.onnx.data": "c03d114add89db13d850e5bbe0a7c09040cf6caf1acfbbd489c21234fa6dcb5e"}

def main():
    for name, digest in FILES.items():
        target = ROOT / "models" / name
        if target.exists() and hashlib.sha256(target.read_bytes()).hexdigest() == digest:
            print(f"Verified {name}")
            continue
        print(f"Downloading {name}")
        with urllib.request.urlopen(BASE + name, timeout=120) as response:
            data = response.read(30 * 1024 * 1024)
        if hashlib.sha256(data).hexdigest() != digest:
            raise SystemExit("Checksum mismatch. Nothing was installed.")
        temporary = target.with_suffix(target.suffix + ".part")
        temporary.write_bytes(data)
        temporary.replace(target)
    print("Starter weights verified. Restart Leafwise to load them.")

if __name__ == "__main__":
    main()
