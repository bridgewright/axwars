#!/usr/bin/env python3
"""Assemble submission-pwc.zip for AX 인재전쟁 · 삼일PwC (both tracks + K-IFRS corpus).

Bundles, at the archive root (exactly README.md + src/ + logs/, no wrapper dir):
  README.md   -- submission Q&A, both tracks (copied from submission/README.md)
  src/        -- Codex plugin root: .codex-plugin/, .claude-plugin/, .mcp.json,
                 skills/{gaap-ifrs-converter,gaap-standards-qa}/SKILL.md,
                 gaap-ifrs/ (track 1 engine), gaap_standards_mcp/ (track 2 server),
                 tools/ (ingest pipeline), corpus/ (kifrs.jsonl.zst + vectors/ + manifest.json),
                 examples/ (track 1), tests/ (track 2), viewer/ (test_viewer.py fixture),
                 pyproject.toml, README.md (technical), README_track2.md (test_readme.py fixture)
  logs/claude-code/*.jsonl -- dev conversation log, as-is

Usage:
    python tools/build_submission.py

Output:
    ~/Desktop/submission-pwc.zip
"""
from __future__ import annotations

import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_ZIP = Path.home() / "Desktop" / "submission-pwc.zip"

# Directory names dropped wherever they appear while copying a tree. "logs" is
# here because gaap-ifrs/ has accidental nested dev-log copies (from the
# Stop-hook logger running with different cwds during development) that are
# NOT the intended package content -- the one real dev log ships separately
# from the top-level logs/claude-code/ (see build() below).
_SKIP_DIR_NAMES = {"__pycache__", ".pytest_cache", ".git", "logs", "downloads"}


def _is_skipped_dir(name: str) -> bool:
    return name in _SKIP_DIR_NAMES or name.endswith(".egg-info") or "scratchpad" in name.lower()


def _is_skipped_file(name: str) -> bool:
    return name == ".DS_Store" or name.endswith(".pyc")


def _ignore(dirpath: str, names: list[str]) -> list[str]:
    skipped = []
    for n in names:
        p = Path(dirpath) / n
        if p.is_dir() and _is_skipped_dir(n):
            skipped.append(n)
        elif p.is_file() and _is_skipped_file(n):
            skipped.append(n)
    return skipped


def copytree(src: Path, dst: Path) -> None:
    shutil.copytree(src, dst, ignore=_ignore, dirs_exist_ok=True)


def build(staging: Path) -> None:
    src = staging / "src"
    src.mkdir(parents=True)

    # -- plugin manifests + local MCP config (Codex + Claude Code parity) --
    for plugin_dir in (".codex-plugin", ".claude-plugin"):
        (src / plugin_dir).mkdir()
        shutil.copy2(REPO_ROOT / plugin_dir / "plugin.json", src / plugin_dir / "plugin.json")
    shutil.copy2(REPO_ROOT / ".mcp.json", src / ".mcp.json")

    # -- skills: track 1 (gaap-ifrs/SKILL.md relocated) + track 2 (already in place) --
    (src / "skills" / "gaap-ifrs-converter").mkdir(parents=True)
    shutil.copy2(REPO_ROOT / "gaap-ifrs" / "SKILL.md",
                 src / "skills" / "gaap-ifrs-converter" / "SKILL.md")
    copytree(REPO_ROOT / "skills" / "gaap-standards-qa", src / "skills" / "gaap-standards-qa")

    # -- whole-directory bundles --
    copytree(REPO_ROOT / "gaap-ifrs", src / "gaap-ifrs")                   # track 1 engine
    copytree(REPO_ROOT / "gaap_standards_mcp", src / "gaap_standards_mcp")  # track 2 MCP server pkg
    copytree(REPO_ROOT / "tools", src / "tools")                           # ingest pipeline
    copytree(REPO_ROOT / "corpus", src / "corpus")                         # kifrs.jsonl.zst + vectors/ + manifest.json
    copytree(REPO_ROOT / "examples", src / "examples")                    # track 1 worked examples
    copytree(REPO_ROOT / "tests", src / "tests")                          # track 2 tests (credibility)
    copytree(REPO_ROOT / "viewer", src / "viewer")                        # fixture for tests/test_viewer.py

    # build_submission.py (this file) is a repo dev tool, not plugin content.
    (src / "tools" / "build_submission.py").unlink(missing_ok=True)

    # -- root project files --
    shutil.copy2(REPO_ROOT / "pyproject.toml", src / "pyproject.toml")
    shutil.copy2(REPO_ROOT / "README_track2.md", src / "README_track2.md")  # fixture for tests/test_readme.py
    shutil.copy2(REPO_ROOT / "README.md", src / "README.md")                # technical readme, both tracks

    # -- archive-root submission Q&A README (both tracks) --
    shutil.copy2(REPO_ROOT / "submission" / "README.md", staging / "README.md")

    # -- dev conversation log, as-is (top-level logs/claude-code/ only) --
    log_dst = staging / "logs" / "claude-code"
    log_dst.mkdir(parents=True)
    for f in sorted((REPO_ROOT / "logs" / "claude-code").glob("*.jsonl")):
        shutil.copy2(f, log_dst / f.name)


REQUIRED = [
    "README.md",
    "src/.codex-plugin/plugin.json",
    "src/.claude-plugin/plugin.json",
    "src/.mcp.json",
    "src/skills/gaap-ifrs-converter/SKILL.md",
    "src/skills/gaap-standards-qa/SKILL.md",
    "src/corpus/kifrs.jsonl.zst",
    "src/corpus/vectors/index.faiss",
    "src/corpus/vectors/id_map.json",
    "src/corpus/manifest.json",
    "src/pyproject.toml",
    "src/README.md",
]


def verify_staging(staging: Path) -> None:
    missing = [p for p in REQUIRED if not (staging / p).exists()]
    if missing:
        sys.exit("ERROR: missing required files before zipping:\n  " + "\n  ".join(missing))
    if not list((staging / "logs" / "claude-code").glob("*.jsonl")):
        sys.exit("ERROR: no dev log .jsonl staged under logs/claude-code/")


def zip_staging(staging: Path, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if out_path.exists():
        out_path.unlink()
    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for path in sorted(staging.rglob("*")):
            if path.is_file():
                zf.write(path, path.relative_to(staging))


def main() -> None:
    if not (REPO_ROOT / "corpus" / "vectors" / "index.faiss").exists():
        sys.exit("ERROR: corpus/vectors/index.faiss missing on disk -- build the corpus before packaging.")

    staging = Path(tempfile.mkdtemp(prefix="submission-pwc-"))
    try:
        build(staging)
        verify_staging(staging)
        zip_staging(staging, OUTPUT_ZIP)
    finally:
        shutil.rmtree(staging, ignore_errors=True)

    size_mb = OUTPUT_ZIP.stat().st_size / (1024 * 1024)
    print(f"Built {OUTPUT_ZIP} ({size_mb:.2f} MB)")
    if size_mb > 100:
        print("WARNING: exceeds the 100MB submission limit!", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
