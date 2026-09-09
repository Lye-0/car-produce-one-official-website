"""CPO glTF/GLB compatibility patch: make default texture samplers explicit.

Standard-library-only. Does not regenerate meshes or decode/re-encode textures.
Non-JSON chunks, including the entire geometry/image BIN chunk, are preserved
byte for byte. Input and output must be different files; neither is overwritten.

Usage:
  python fix_texture_samplers.py old.glb repaired.glb
  python fix_texture_samplers.py old.glb repaired.glb --revision v07.1

The glTF standard allows texture.sampler to be omitted. This patch avoids that
optional path in importers, addressing the supplied samplers-None traceback.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import struct
from pathlib import Path
from typing import Any

JSON_CHUNK = 0x4E4F534A
BIN_CHUNK = 0x004E4942
DEFAULT_SAMPLER = {
    "name": "CPO_Explicit_Default_Repeat_Linear",
    "magFilter": 9729,       # LINEAR
    "minFilter": 9987,       # LINEAR_MIPMAP_LINEAR
    "wrapS": 10497,          # REPEAT, the glTF default
    "wrapT": 10497,
}


def decode_glb(raw: bytes) -> tuple[dict[str, Any], list[tuple[int, bytes]]]:
    if len(raw) < 20:
        raise ValueError("Truncated GLB header.")
    magic, version, total = struct.unpack_from("<4sII", raw)
    if magic != b"glTF" or version != 2 or total != len(raw):
        raise ValueError("Expected a complete GLB version 2 file.")
    chunks: list[tuple[int, bytes]] = []
    offset = 12
    while offset < len(raw):
        if offset + 8 > len(raw):
            raise ValueError("Truncated chunk header.")
        length, kind = struct.unpack_from("<II", raw, offset)
        offset += 8
        if length % 4 or offset + length > len(raw):
            raise ValueError("Invalid chunk length or alignment.")
        chunks.append((kind, raw[offset:offset + length]))
        offset += length
    if not chunks or chunks[0][0] != JSON_CHUNK:
        raise ValueError("First GLB chunk must be JSON.")
    if sum(k == JSON_CHUNK for k, _ in chunks) != 1:
        raise ValueError("Expected exactly one JSON chunk.")
    document = json.loads(chunks[0][1].decode("utf-8"))
    if not isinstance(document, dict) or document.get("asset", {}).get("version") != "2.0":
        raise ValueError("Expected a glTF 2.0 document.")
    return document, chunks


def encode_glb(document: dict[str, Any], chunks: list[tuple[int, bytes]]) -> bytes:
    text = json.dumps(document, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8")
    text += b" " * (-len(text) % 4)
    output_chunks = [(JSON_CHUNK, text), *chunks[1:]]
    body = b"".join(struct.pack("<II", len(data), kind) + data for kind, data in output_chunks)
    return struct.pack("<4sII", b"glTF", 2, 12 + len(body)) + body


def ensure_explicit_samplers(document: dict[str, Any]) -> list[int]:
    """Mutate only sampler definitions and missing texture sampler references.

    Existing valid sampler selections and sampler settings are never replaced.
    Reject dangling or non-integer explicit references instead of guessing.
    """
    textures = document.get("textures", [])
    if not isinstance(textures, list):
        raise ValueError("textures must be an array.")
    if not textures:
        return []
    original = document.get("samplers")
    if original is not None and not isinstance(original, list):
        raise ValueError("samplers must be an array when present.")
    samplers = copy.deepcopy(original) if original is not None else []
    for i, sampler in enumerate(samplers):
        if not isinstance(sampler, dict):
            raise ValueError(f"samplers[{i}] must be an object.")
    pending: list[int] = []
    for i, texture in enumerate(textures):
        if not isinstance(texture, dict):
            raise ValueError(f"textures[{i}] must be an object.")
        index = texture.get("sampler")
        if index is None:
            pending.append(i)
        elif type(index) is not int or not 0 <= index < len(samplers):
            raise ValueError(f"textures[{i}].sampler is an invalid explicit reference: {index!r}.")
    if not pending:
        return []
    index = next((i for i, s in enumerate(samplers) if s == DEFAULT_SAMPLER), None)
    if index is None:
        index = len(samplers)
        samplers.append(copy.deepcopy(DEFAULT_SAMPLER))
    document["samplers"] = samplers
    for i in pending:
        textures[i]["sampler"] = index
    return pending


def patch_file(source: Path, destination: Path, revision: str | None = None) -> dict[str, Any]:
    source, destination = Path(source), Path(destination)
    if source.resolve() == destination.resolve():
        raise ValueError("Input and output must be different; keep the original.")
    if destination.exists():
        raise FileExistsError(f"Refusing to overwrite {destination}.")
    raw = source.read_bytes()
    old, chunks = decode_glb(raw)
    new = copy.deepcopy(old)
    changed = ensure_explicit_samplers(new)
    if revision:
        new["asset"]["generator"] = "CAR PRODUCE ONE " + revision + " / explicit texture samplers / geometry unchanged"
        new["asset"].setdefault("extras", {}).update(
            revision=revision,
            compatibility_patch="All textures reference an explicit repeat/linear sampler; geometry and embedded images unchanged",
            compatibility_source_sha256=hashlib.sha256(raw).hexdigest(),
        )
    encoded = encode_glb(new, chunks)
    verified, out_chunks = decode_glb(encoded)
    if chunks[1:] != out_chunks[1:]:
        raise RuntimeError("Safety check failed: a non-JSON chunk changed.")
    for key in old.keys() | verified.keys():
        if key not in {"asset", "samplers", "textures"} and old.get(key) != verified.get(key):
            raise RuntimeError(f"Safety check failed: {key} changed.")
    if [{k:v for k,v in t.items() if k != 'sampler'} for t in old.get('textures', [])] != [
        {k:v for k,v in t.items() if k != 'sampler'} for t in verified.get('textures', [])
    ]:
        raise RuntimeError("A texture property other than sampler changed.")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("xb") as file:
        file.write(encoded)
    return {
        "source_file": source.name,
        "output_file": destination.name,
        "source_sha256": hashlib.sha256(raw).hexdigest(),
        "output_sha256": hashlib.sha256(encoded).hexdigest(),
        "added_sampler_references": changed,
        "samplers": verified.get("samplers", []),
        "non_json_chunks_identical": True,
        "bytes": len(encoded),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--revision", default=None)
    args = parser.parse_args()
    try:
        result = patch_file(args.input, args.output, args.revision)
    except (ValueError, OSError, UnicodeError) as exc:
        parser.exit(1, f"ERROR: {exc}\n")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
