"""Pinned V7 reader for every public watcher-status consumption in this owner."""
import hashlib
import importlib.util
from pathlib import Path

PATH = Path(__file__).resolve().parent.with_name('water-anchor-watcher-v7') / 'status_reader.py'
EXPECTED = 'c9383d0aedfaabdff98a52afcfe1c0d3619291d6d48138495e87f283d958e908'
assert hashlib.sha256(PATH.read_bytes()).hexdigest() == EXPECTED
spec = importlib.util.spec_from_file_location('_r28_t02_v7_public_status_reader', PATH)
reader = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reader)


def read_status(path):
    return reader.read_json(path)
