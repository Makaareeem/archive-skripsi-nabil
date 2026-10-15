"""Versioned model and knowledge-base downloads."""
import hashlib
import json
from pathlib import Path

MANIFEST_PATH = Path(__file__).resolve().parent.parent / "assets.json"


def read_manifest():
    data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    if data.get("version") != 1:
        raise ValueError("Unsupported asset manifest version.")
    return data


def asset_path(directory, record):
    directory = Path(directory).resolve()
    path = directory / record["filename"]
    if path.parent != directory or not path.name or path.name in {".", ".."}:
        raise ValueError("Asset filename must not contain a directory.")
    return path


def verify_file(path, record):
    marker = path.with_name(path.name + ".verified.json")
    stat = path.stat()
    stamp = {"sha256": record["sha256"], "bytes": stat.st_size, "mtime_ns": stat.st_mtime_ns}
    if stat.st_size != record["bytes"]:
        raise ValueError("Unexpected asset size: " + path.name)
    try:
        if json.loads(marker.read_text(encoding="utf-8")) == stamp:
            return path
    except (OSError, ValueError):
        pass
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            digest.update(block)
    if digest.hexdigest() != record["sha256"]:
        raise ValueError("Asset checksum mismatch: " + path.name)
    temporary = marker.with_suffix(".tmp")
    temporary.write_text(json.dumps(stamp), encoding="utf-8")
    temporary.replace(marker)
    return path


def ensure_asset(directory, repo_id, revision, record, repo_type="model", token=None):
    path = asset_path(directory, record)
    if not path.is_file():
        from huggingface_hub import hf_hub_download
        path.parent.mkdir(parents=True, exist_ok=True)
        hf_hub_download(repo_id=repo_id, filename=record["filename"], revision=revision,
                        repo_type=repo_type, token=token, local_dir=str(path.parent))
    return verify_file(path, record)


def validate_registry(registry, manifest):
    for key, cfg in registry.items():
        asset = manifest["models"].get(key)
        if not asset or (asset["repo_id"], asset["filename"]) != (cfg["gguf_repo"], cfg["gguf_filename"]):
            raise ValueError("Model registry differs from deployment manifest: " + key)
