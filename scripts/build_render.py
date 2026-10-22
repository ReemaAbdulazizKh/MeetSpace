"""Render native Python build: install backend and build the same-origin UI."""
from pathlib import Path
import shutil
import subprocess
import sys

root = Path(__file__).resolve().parents[1]
subprocess.run([sys.executable, '-m', 'pip', 'install', '-r', 'backend/requirements.txt'], cwd=root, check=True)
npm = shutil.which('npm')
if not npm:
    raise SystemExit('Node.js/npm is required in the build environment.')
subprocess.run([npm, 'ci'], cwd=root/'frontend', check=True)
subprocess.run([npm, 'run', 'build'], cwd=root/'frontend', check=True)
