"""Build the deterministic, double-blind JUDGe supplementary snapshot."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import stat
import tempfile
import zipfile
from pathlib import Path
from typing import Any

ARCHIVE_ROOT = "finmirror-judge2026-supplement"
FIXED_ZIP_TIME = (2026, 8, 12, 0, 0, 0)
TEXT_SUFFIXES = {
    ".cff",
    ".css",
    ".html",
    ".json",
    ".jsonl",
    ".md",
    ".py",
    ".toml",
    ".txt",
    ".yaml",
    ".yml",
}
FORBIDDEN_TESTS = {
    "test_build_anonymous_supplement.py",
    "test_judge_audit.py",
    "test_lineage.py",
    "test_openai_compatible_adapter.py",
    "test_report.py",
    "test_sources.py",
    "test_statcan_pilot.py",
    "test_trace_audit.py",
}
SUPPLEMENT_DOCS = (
    "ADAPTER_GUIDE.md",
    "AGENT_TRACE_AUDIT.md",
    "DATA_CARD.md",
    "EQUIVALENCE_ASSURANCE.md",
    "EVALUATOR_ASSURANCE.md",
    "JUDGE_ASSURANCE.md",
    "METHODOLOGY.md",
    "RERANK_ASSURANCE.md",
    "RESULTS.md",
    "V0.2_PROTOCOL.md",
)
IDENTITY_PATTERNS = (
    r"Mingyang(?:\s+\(Ethan\))?\s+Wang",
    r"Mingyang\s+Wang",
    r"\bEthan\b",
    r"faceWang753",
    r"mingyang233",
    r"[A-Z0-9._%+-]+@(?:gmail|outlook|hotmail)\.com",
    r"linkedin\.com/[^\s<>'\"]+",
)
REMOTE_URL_RE = re.compile(r"https?://(?!127\.0\.0\.1|localhost)[^\s<>'\"`)]+", re.I)
SECRET_RE = re.compile(
    r"(?:api[_-]?key|access[_-]?token|client[_-]?secret|password)\s*[:=]\s*['\"]"
    r"(?!local['\"])[^'\"]+",
    re.I,
)
PHONE_RE = re.compile(r"(?<!\d)(?:\+?1[ .-]?)?\(?[2-9]\d{2}\)?[ .-]?\d{3}[ .-]?\d{4}(?!\d)")
SIN_RE = re.compile(r"(?<!\d)\d{3}[ -]\d{3}[ -]\d{3}(?!\d)")
MODEL_SUFFIXES = {".bin", ".gguf", ".onnx", ".pt", ".pth", ".safetensors"}
SENSITIVE_NAMES = {".env", "credentials", "id_rsa", "id_rsa.pub", "secrets"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def scrub_json(value: Any, *, filename: str) -> Any:
    if isinstance(value, dict):
        cleaned = {key: scrub_json(item, filename=filename) for key, item in value.items()}
        if "finmirror_git_commit" in cleaned:
            cleaned["finmirror_git_commit"] = "anonymous-supplement-0.2.0"
        if "finmirror_code_state_note" in cleaned:
            cleaned["finmirror_code_state_note"] = (
                "The bundled evaluator and adapter are the exact code snapshot used for this "
                "anonymous supplementary release."
            )
        if "$schema" in cleaned:
            cleaned["$schema"] = "urn:anonymous:json-schema"
        if "$id" in cleaned:
            cleaned["$id"] = f"urn:anonymous:{filename}"
        return cleaned
    if isinstance(value, list):
        return [scrub_json(item, filename=filename) for item in value]
    if isinstance(value, str):
        return scrub_text(value)
    return value


def scrub_text(text: str) -> str:
    for pattern in IDENTITY_PATTERNS:
        text = re.sub(pattern, "Anonymous Authors", text, flags=re.I)
    text = REMOTE_URL_RE.sub("urn:anonymous:redacted-url", text)
    text = re.sub(
        r"FinMirror:\s+version `0\.2\.0`, commit `[0-9a-f]{7,40}`",
        "FinMirror: anonymous version `0.2.0` snapshot",
        text,
    )
    text = re.sub(
        r"From a clean FinMirror checkout at the commit above",
        "From the unpacked anonymous supplement",
        text,
    )
    return text


def copy_scrubbed(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if source.suffix.lower() not in TEXT_SUFFIXES:
        shutil.copyfile(source, destination)
        return
    raw = source.read_text(encoding="utf-8")
    if source.suffix.lower() in {".json", ".jsonl"}:
        if source.suffix.lower() == ".json":
            try:
                parsed = json.loads(raw)
            except json.JSONDecodeError:
                cleaned = scrub_text(raw)
            else:
                cleaned = (
                    json.dumps(
                        scrub_json(parsed, filename=source.name),
                        ensure_ascii=False,
                        indent=2,
                        sort_keys=True,
                    )
                    + "\n"
                )
        else:
            lines = []
            for line in raw.splitlines():
                if not line.strip():
                    continue
                parsed = json.loads(line)
                lines.append(
                    json.dumps(
                        scrub_json(parsed, filename=source.name),
                        ensure_ascii=False,
                        sort_keys=True,
                        separators=(",", ":"),
                    )
                )
            cleaned = "\n".join(lines) + "\n"
    else:
        cleaned = scrub_text(raw)
    destination.write_text(cleaned, encoding="utf-8", newline="\n")


def add_tree(
    source: Path, destination: Path, *, excluded_names: set[str] | None = None
) -> None:
    excluded_names = excluded_names or set()
    for path in sorted(source.rglob("*")):
        if not path.is_file() or path.name in excluded_names:
            continue
        if any(part in {".git", "__pycache__", ".pytest_cache"} for part in path.parts):
            continue
        if path.suffix.lower() in MODEL_SUFFIXES:
            continue
        copy_scrubbed(path, destination / path.relative_to(source))


def write_anonymous_metadata(repo: Path, stage: Path) -> None:
    source = (repo / "pyproject.toml").read_text(encoding="utf-8")
    source = re.sub(
        r'authors = \[\{ name = "[^"]+" \}\]',
        'authors = [{ name = "Anonymous Authors" }]',
        source,
    )
    source = re.sub(r"\n\[project\.urls\]\n.*?(?=\n\[)", "\n", source, flags=re.S)
    (stage / "pyproject.toml").write_text(scrub_text(source), encoding="utf-8", newline="\n")


def write_readme(stage: Path, baseline_names: list[str]) -> None:
    baselines = "\n".join(f"- `{name}`" for name in baseline_names) or "- none"
    readme = f"""# Anonymous JUDGe 2026 Supplement: FinMirror

This double-blind snapshot contains the FinMirror 0.2.0 evaluator, the exact synthetic
v0.1 paired-world dataset, machine-readable schemas, a focused offline test suite, and
the archived evidence for the real local open-weight baselines listed below.

{baselines}

The model weights are intentionally excluded. Model identifiers, immutable model and
runtime revisions, quantization, file sizes, and SHA-256 receipts remain in each baseline
directory so a reviewer can supply and verify the same weight file independently.

The snapshot intentionally contains no author identity, project remote, email address,
repository history, credentials, or externally hosted URL. Local loopback endpoints are
retained because they are part of the reproduction contract.

## Quick verification

```text
python verify_manifest.py
python -m pip install -e .
python -m pytest tests/test_dataset.py tests/test_evaluator.py tests/test_assurance.py
python -m finmirror.cli validate benchmark/v0.1
```

See `REPRODUCE.md` for the exact artifact interpretation boundary.
"""
    (stage / "README.md").write_text(readme, encoding="utf-8", newline="\n")

    reproduce = """# Reproduction and interpretation

## Deterministic evaluator

The bundled dataset manifest binds the case JSONL and schema. The validation and focused
test commands in `README.md` require no API key and make no network request.

## Real local-model baselines

Each directory under `artifacts/model-baselines/` contains predictions, a JSON report,
an HTML report, a model/runtime receipt, and a run note. Verify every weight file against
the receipt before starting the loopback inference server. Then use the exact parameters
in the run note. The archived predictions contain no gold label supplied at inference.

These small, quantized, CPU-runnable baselines are diagnostic results on synthetic
evidence worlds. They do not establish production, regulatory, safety, or investment
performance. A valid structured response is not evidence of grounding; the hard gate and
paired reliability must be interpreted separately from contract validity.

## Double-blind boundary

Project remotes, author metadata, repository history, hosted links, and raw model weights
are deliberately absent. Runtime and model revisions are retained only where required to
reproduce the reported result. The manifest binds every included byte.
"""
    (stage / "REPRODUCE.md").write_text(reproduce, encoding="utf-8", newline="\n")


def write_verifier(stage: Path) -> None:
    verifier = '''"""Verify every byte declared by MANIFEST.json."""

import hashlib
import json
from pathlib import Path

root = Path(__file__).resolve().parent
manifest = json.loads((root / "MANIFEST.json").read_text(encoding="utf-8"))
seen = set()
for item in manifest["files"]:
    path = root / item["path"]
    data = path.read_bytes()
    actual = hashlib.sha256(data).hexdigest()
    if len(data) != item["bytes"] or actual != item["sha256"]:
        raise SystemExit(f"integrity failure: {item['path']}")
    seen.add(item["path"])
actual_paths = {
    path.relative_to(root).as_posix()
    for path in root.rglob("*")
    if path.is_file() and path.name not in {"MANIFEST.json", "MANIFEST.sha256"}
}
if actual_paths != seen:
    raise SystemExit("manifest path-set mismatch")
print(f"verified {len(seen)} files")
'''
    (stage / "verify_manifest.py").write_text(verifier, encoding="utf-8", newline="\n")


def write_manifest(stage: Path) -> list[dict[str, object]]:
    items = []
    for path in sorted(stage.rglob("*")):
        if not path.is_file() or path.name in {"MANIFEST.json", "MANIFEST.sha256"}:
            continue
        items.append(
            {
                "path": path.relative_to(stage).as_posix(),
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
            }
        )
    payload = {
        "schema_version": "1.0",
        "artifact": "FinMirror anonymous JUDGe 2026 supplement",
        "release": "0.2.0",
        "files": items,
    }
    manifest_path = stage / "MANIFEST.json"
    manifest_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    (stage / "MANIFEST.sha256").write_text(
        f"{sha256(manifest_path)}  MANIFEST.json\n",
        encoding="utf-8",
        newline="\n",
    )
    return items


def declared_model_byte_tokens(stage: Path) -> dict[Path, set[str]]:
    """Return exact decimal byte counts declared by each baseline receipt."""
    tokens: dict[Path, set[str]] = {}
    baseline_root = stage / "artifacts" / "model-baselines"
    if not baseline_root.exists():
        return tokens
    for receipt_path in sorted(baseline_root.glob("*/model-receipt.json")):
        try:
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            model = receipt["model"]
            byte_count = model["bytes"]
        except (json.JSONDecodeError, KeyError, TypeError):
            continue
        if type(byte_count) is int and byte_count > 0:
            tokens.setdefault(receipt_path.parent, set()).add(str(byte_count))
    return tokens


def is_declared_model_byte_token(
    match: re.Match[str], *, path: Path, declared_tokens: dict[Path, set[str]]
) -> bool:
    """Classify only an unformatted token equal to the sibling receipt's model size."""
    token = match.group(0)
    return (
        token.isascii()
        and token.isdigit()
        and token in declared_tokens.get(path.parent, set())
    )


def scan(stage: Path) -> dict[str, object]:
    failures: list[str] = []
    file_count = 0
    total_bytes = 0
    declared_tokens = declared_model_byte_tokens(stage)
    for path in sorted(stage.rglob("*")):
        if not path.is_file():
            continue
        file_count += 1
        total_bytes += path.stat().st_size
        relative = path.relative_to(stage).as_posix()
        if (
            ".git" in path.parts
            or path.suffix.lower() in MODEL_SUFFIXES
            or path.suffix.lower() in {".key", ".pem"}
            or path.name.lower() in SENSITIVE_NAMES
        ):
            failures.append(f"forbidden path: {relative}")
        if path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        text = path.read_text(encoding="utf-8")
        if REMOTE_URL_RE.search(text):
            failures.append(f"remote URL: {relative}")
        if SECRET_RE.search(text):
            failures.append(f"secret-like assignment: {relative}")
        phone_matches = [
            match
            for match in PHONE_RE.finditer(text)
            if not is_declared_model_byte_token(
                match, path=path, declared_tokens=declared_tokens
            )
        ]
        if path.name not in {"MANIFEST.json", "MANIFEST.sha256"} and (
            phone_matches or SIN_RE.search(text)
        ):
            failures.append(f"phone/SIN-like PII: {relative}")
        for pattern in IDENTITY_PATTERNS:
            if re.search(pattern, text, flags=re.I):
                failures.append(f"identity token: {relative}")
                break
    if failures:
        raise RuntimeError("anonymous snapshot scan failed:\n" + "\n".join(failures))
    return {
        "file_count": file_count,
        "total_bytes": total_bytes,
        "remote_url_hits": 0,
        "identity_hits": 0,
        "secret_hits": 0,
        "phone_or_sin_hits": 0,
        "git_metadata_hits": 0,
        "model_weight_files": 0,
    }


def zip_deterministically(stage: Path, destination: Path) -> None:
    with zipfile.ZipFile(
        destination, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
    ) as archive:
        for path in sorted(stage.rglob("*")):
            if not path.is_file():
                continue
            arcname = f"{ARCHIVE_ROOT}/{path.relative_to(stage).as_posix()}"
            info = zipfile.ZipInfo(arcname, FIXED_ZIP_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = (stat.S_IFREG | 0o644) << 16
            archive.writestr(
                info, path.read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9
            )


def build(repo: Path, output_dir: Path) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)
    archive_path = output_dir / "finmirror_judge2026_anonymous_supplement.zip"
    with tempfile.TemporaryDirectory(prefix="finmirror-judge-supplement-") as temp:
        stage = Path(temp) / ARCHIVE_ROOT
        stage.mkdir()
        add_tree(repo / "src", stage / "src")
        add_tree(repo / "benchmark" / "v0.1", stage / "benchmark" / "v0.1")
        add_tree(repo / "schema", stage / "schema")
        add_tree(repo / "tests", stage / "tests", excluded_names=FORBIDDEN_TESTS)
        for name in (
            "CHANGELOG.md",
            "CITATION.cff",
            "LICENSE",
            "DATA_LICENSE.md",
            "NOTICE",
        ):
            copy_scrubbed(repo / name, stage / name)
        for name in SUPPLEMENT_DOCS:
            copy_scrubbed(repo / "docs" / name, stage / "docs" / name)
        write_anonymous_metadata(repo, stage)
        baseline_root = repo / "artifacts" / "model-baselines"
        baseline_names: list[str] = []
        if baseline_root.exists():
            for baseline in sorted(baseline_root.iterdir()):
                if not baseline.is_dir() or not baseline.name.startswith("qwen"):
                    continue
                baseline_names.append(baseline.name)
                add_tree(
                    baseline,
                    stage / "artifacts" / "model-baselines" / baseline.name,
                )
        write_readme(stage, baseline_names)
        write_verifier(stage)
        write_manifest(stage)
        scan_result = scan(stage)
        zip_deterministically(stage, archive_path)
    archive_hash = sha256(archive_path)
    sidecar = output_dir / "finmirror_judge2026_anonymous_supplement.sha256"
    sidecar.write_text(f"{archive_hash}  {archive_path.name}\n", encoding="utf-8", newline="\n")
    result = {
        "archive": str(archive_path),
        "archive_bytes": archive_path.stat().st_size,
        "archive_sha256": archive_hash,
        "sidecar": str(sidecar),
        "baselines": baseline_names,
        "scan": scan_result,
    }
    (output_dir / "finmirror_judge2026_anonymous_supplement_build.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    result = build(args.repo.resolve(), args.output_dir.resolve())
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
