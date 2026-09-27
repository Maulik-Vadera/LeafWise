"""Small launcher: isolated environment, dependency fingerprint, then the app."""
from pathlib import Path
import hashlib
import os
import subprocess
import sys
import venv

def main():
    if sys.version_info < (3, 11) or sys.version_info >= (3, 14):
        raise SystemExit("Use Python 3.12 (recommended), 3.11 or 3.13. Python 3.14 is not tested for this package.")
    root = Path(__file__).resolve().parents[1]
    os.chdir(root)
    environment = root / ".venv"
    python = environment / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    if not python.exists():
        print("Creating Leafwise's private Python environment…", flush=True)
        venv.EnvBuilder(with_pip=True).create(environment)
    requirements = root / "requirements.txt"
    fingerprint = hashlib.sha256(requirements.read_bytes()).hexdigest()
    marker = environment / "leafwise-requirements.sha256"
    if not marker.exists() or marker.read_text() != fingerprint:
        print("Installing dependencies. This first step needs internet access…", flush=True)
        subprocess.run([str(python), "-m", "pip", "install", "-r", str(requirements)], check=True)
        marker.write_text(fingerprint)
    subprocess.run([str(python), str(root / "run.py")], check=True)

if __name__ == "__main__":
    try:
        main()
    except (OSError, subprocess.CalledProcessError) as exc:
        print(f"Setup could not complete: {exc}\nSee START_HERE.md for the manual commands.", file=sys.stderr)
        sys.exit(1)
