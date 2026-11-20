"""
Secure plugin packager for agentic-discovery.

Builds under ./dist/:
  agentic-discovery/                   Clean plugin directory
  agentic-discovery-1.0.0.zip          Versioned zip bundle ready for Claude Code / Claude Desktop upload
  agentic-discovery.zip                Root-level zip bundle for convenience

Whitelists only required plugin files, scans for credentials/secrets,
and excludes temporary runs, caches, and test artifacts.
"""
from __future__ import annotations

import json
from pathlib import Path
import re
import shutil
import sys
import zipfile


ROOT = Path(__file__).resolve().parent
DIST = ROOT / "dist"
PLUGIN_NAME = "agentic-discovery"

INCLUDE = [
    ".claude-plugin",
    "agents",
    "skills",
    "commands",
    "hooks",
    "core",
    "sample",
    "connections.json",
    "run.py",
    "requirements.txt",
    "managed_agents.json",
    "README.md",
    "CLAUDE.md",
    ".env.example"
]

SKIP_DIRS = {"__pycache__", ".git", ".venv", "runs", "tests", "dist"}
SKIP_EXT = {".pyc", ".pyo", ".log", ".tmp"}

SECRET_PATTERNS = [
    (re.compile(r"sk-ant-[A-Za-z0-9_\-]{20,}"), "Anthropic API key"),
    (re.compile(r"://[^:/\s@]+:(?!\*\*\*)[^@\s/]{3,}@(?!host\b|localhost|127\.|\[|<|example)"
                r"[A-Za-z0-9\-]+(?:\.[A-Za-z0-9\-]+)+"), "database URL with embedded password"),
    (re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"), "private key"),
]


def _iter_files():
    for entry in INCLUDE:
        p = ROOT / entry
        if p.is_file():
            yield p
        elif p.is_dir():
            for f in sorted(p.rglob("*")):
                if f.is_file() and not (set(f.relative_to(ROOT).parts) & SKIP_DIRS):
                    yield f


def _scan(path: Path) -> list[str]:
    try:
        text = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return []
    return [name for rx, name in SECRET_PATTERNS if rx.search(text)]


def build() -> Path:
    if DIST.exists():
        shutil.rmtree(DIST)
    plugin_dir = DIST / PLUGIN_NAME
    shipped, problems = [], []

    for f in _iter_files():
        rel = f.relative_to(ROOT)
        if f.name.startswith(".env") and f.name != ".env.example":
            continue
        if f.suffix in SKIP_EXT:
            continue
        for hit in _scan(f):
            problems.append(f"{rel}: {hit}")
        shipped.append(rel)

    if problems:
        print("[X] SECURITY SCAN FAILED - Build aborted:")
        for p in problems:
            print("   ", p)
        sys.exit(1)

    print(f"[*] Packaging {len(shipped)} verified files into {plugin_dir.name}...")
    for rel in shipped:
        dst = plugin_dir / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / rel, dst)

    manifest = json.loads((plugin_dir / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
    version = manifest.get("version", "1.0.0")

    # 1. Versioned zip in dist/
    zip_path = DIST / f"{PLUGIN_NAME}-{version}.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in sorted(plugin_dir.rglob("*")):
            if f.is_file():
                zf.write(f, arcname=str(f.relative_to(DIST)))

    # 2. Root-level zip for immediate upload
    root_zip = ROOT / f"{PLUGIN_NAME}.zip"
    shutil.copy2(zip_path, root_zip)

    print(f"[✔] Plugin bundle created successfully:")
    print(f"    - Dist bundle: {zip_path}")
    print(f"    - Root upload: {root_zip} ({root_zip.stat().st_size / 1024:.1f} KB)")
    return root_zip


if __name__ == "__main__":
    build()
