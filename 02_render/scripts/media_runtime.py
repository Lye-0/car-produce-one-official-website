"""Use installed dependencies, with this workstation's existing vendor fallback."""
from pathlib import Path
import sys
try:
 import av
 assert hasattr(av,'open')
except (ImportError,AssertionError):
 for key in list(sys.modules):
  if key=='av' or key.startswith('av.'):del sys.modules[key]
 sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'90_archive/session_work/python_vendor'))
 import av
 if not hasattr(av,'open'):raise RuntimeError('Install scripts/requirements-media.txt in the Python used by render.ps1.')
import numpy as np
from PIL import Image
