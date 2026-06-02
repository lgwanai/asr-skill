#!/usr/bin/env python3
"""Package ASR Skill into a date-versioned ZIP file.

Reads .gitignore to determine which files to exclude, performs a
security scan for secrets/API keys, and outputs to dist/.

Usage:
    python3 scripts/package_skill.py
"""

import os
import re
import sys
import zipfile
import datetime
import fnmatch
from pathlib import Path

# ── Secret detection patterns ──────────────────────────────────────────────

SENSITIVE_PATTERNS = [
    (r'(?i)(api[_-]?key|apikey)\s*[=:]\s*["\']?(?!.*(?:your|example|xxx|placeholder|test))[a-zA-Z0-9_\-]{20,}', 'API Key'),
    (r'(?i)(secret[_-]?key|secretkey)\s*[=:]\s*["\']?(?!.*(?:your|example|xxx|placeholder|test))[a-zA-Z0-9_\-]{20,}', 'Secret Key'),
    (r'(?i)(access[_-]?token|accesstoken)\s*[=:]\s*["\']?(?!.*(?:your|example|xxx|placeholder|test))[a-zA-Z0-9_\-]{20,}', 'Access Token'),
    (r'(?i)(auth[_-]?token|authtoken)\s*[=:]\s*["\']?(?!.*(?:your|example|xxx|placeholder|test))[a-zA-Z0-9_\-]{20,}', 'Auth Token'),
    (r'(?i)(bearer)\s+(?!.*(?:your|example|xxx|placeholder|test))[a-zA-Z0-9_\-\.]{20,}', 'Bearer Token'),
    (r'sk-[a-zA-Z0-9]{20,}', 'OpenAI API Key'),
    (r'sk-ant-[a-zA-Z0-9\-]{20,}', 'Anthropic API Key'),
    (r'(?i)(password|passwd)\s*[=:]\s*["\']?(?!.*(?:your|example|xxx|placeholder|test))[^\s"\']{8,}', 'Password'),
    (r'[a-f0-9]{32,}', 'Possible Hash/Secret'),
]

PLACEHOLDER_VALUES = {'your', 'example', 'xxx', 'placeholder', 'test', 'your-key', 'your-secret'}  # noqa: E501

SENSITIVE_FILES = {
    '.env', '.env.local', '.env.production', '.env.development',
    'secrets.json', 'credentials.json', 'config.secrets.json',
    'config.txt', 'private.key', 'id_rsa', 'id_ed25519',
}


# ── .gitignore parser ──────────────────────────────────────────────────────

def parse_gitignore(gitignore_path: Path) -> list[str]:
    """Parse a .gitignore file and return a list of patterns.

    Handles comments, blank lines, and negations (though negations
    are not applied here — we just collect all exclude patterns).

    Args:
        gitignore_path: Path to .gitignore file.

    Returns:
        List of gitignore pattern strings (non-comment, non-blank).
    """
    patterns: list[str] = []
    if not gitignore_path.exists():
        return patterns
    with open(gitignore_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            # Skip comments and blanks
            if not line or line.startswith("#"):
                continue
            # Skip negation patterns (we only want ignores)
            if line.startswith("!"):
                continue
            patterns.append(line)
    return patterns


def _match_pattern(path: str, pattern: str) -> bool:
    """Check if a relative path matches a gitignore-style pattern.

    Supports:
        - Exact match: ``foo.txt``
        - Directory match: ``dir/`` (matches dir itself and all files inside)
        - Wildcard: ``*.pyc``, ``*.log``
        - Glob: ``**/__pycache__``
        - Leading slash: ``/dist`` (root-only)

    Args:
        path: File or directory path relative to project root.
        pattern: Gitignore pattern.

    Returns:
        True if the pattern matches.
    """
    # Strip leading / (root-only designation, just removes ambiguity)
    if pattern.startswith("/"):
        pattern = pattern[1:]

    # Directory-only pattern (trailing /): matches dir and everything inside
    if pattern.endswith("/"):
        pattern = pattern[:-1]
        # Match the directory itself
        if path == pattern or path.startswith(pattern + "/"):
            return True

    # fnmatch on full path
    if fnmatch.fnmatch(path, pattern):
        return True

    # fnmatch on filename only (for simple patterns like *.pyc)
    basename = path.split("/")[-1]
    if fnmatch.fnmatch(basename, pattern):
        return True

    # Match any parent path component (for patterns like __pycache__/ or .claude/)
    parts = path.split("/")
    for i in range(len(parts)):
        subpath = "/".join(parts[:i+1])
        if fnmatch.fnmatch(subpath, pattern):
            return True

    return False


def _is_ignored(rel_path: str, is_dir: bool, patterns: list[str]) -> bool:
    """Check if a relative path should be ignored based on gitignore patterns.

    Args:
        rel_path: Path relative to project root.
        is_dir: True if the path is a directory.
        patterns: List of gitignore patterns.

    Returns:
        True if the path should be excluded.
    """
    path = rel_path + "/" if is_dir else rel_path

    for pattern in patterns:
        if _match_pattern(path, pattern):
            return True

    return False


# ── Secret check ───────────────────────────────────────────────────────────

def check_file_for_secrets(file_path: str) -> list[str]:
    """Scan a file for potential secrets/API keys."""
    warnings = []
    filename = os.path.basename(file_path)
    if filename in SENSITIVE_FILES:
        warnings.append(f"  ⚠️  Sensitive file: {filename}")
        return warnings
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        for pattern, secret_type in SENSITIVE_PATTERNS:
            for match in re.finditer(pattern, content):
                line_num = content[:match.start()].count('\n') + 1
                warnings.append(f"  ⚠️  {secret_type} at line {line_num}")
    except Exception:
        pass
    return warnings


# ── Main packaging logic ───────────────────────────────────────────────────

def package_skill(yes: bool = False) -> None:
    """Package the project into a date-versioned ZIP in dist/.

    Args:
        yes: Skip interactive confirmation prompt.
    """
    project_root = Path(__file__).resolve().parent.parent
    dist_dir = project_root / "dist"
    dist_dir.mkdir(exist_ok=True)

    today = datetime.datetime.now().strftime("%Y%m%d")
    zip_path = dist_dir / f"asr-skill-{today}.zip"

    # Load gitignore patterns
    gitignore = project_root / ".gitignore"
    ignore_patterns = parse_gitignore(gitignore)
    print(f"📋 Loaded {len(ignore_patterns)} patterns from .gitignore")

    # Hard exclusions (always skip)
    hard_exclude_dirs = {".git", "__pycache__"}
    hard_exclude_files = {
        ".DS_Store", "*.pyc",
        # Sensitive (in case .gitignore is missing entries)
        "config.txt", "config.json",
        ".env", ".env.local", ".env.production", ".env.development",
        "secrets.json", "credentials.json", "private.key",
    }

    # Scan project
    all_warnings: list[str] = []
    files_to_pack: list[tuple[Path, str]] = []

    print("🔍 Scanning project...")

    for dirpath, dirnames, filenames in os.walk(project_root):
        rel_dir = os.path.relpath(dirpath, project_root)
        if rel_dir == ".":
            rel_dir = ""

        # ── Filter directories ──────────────────────────────────────────
        keep_dirs = []
        for d in dirnames:
            if d in hard_exclude_dirs:
                continue
            d_rel = os.path.join(rel_dir, d) if rel_dir else d
            if _is_ignored(d_rel, is_dir=True, patterns=ignore_patterns):
                continue
            keep_dirs.append(d)
        dirnames[:] = keep_dirs

        # ── Filter files ────────────────────────────────────────────────
        for f in filenames:
            if f in hard_exclude_files:
                continue
            # Wildcard hard excludes
            if any(fnmatch.fnmatch(f, p) for p in hard_exclude_files if "*" in p):
                continue

            f_rel = os.path.join(rel_dir, f) if rel_dir else f

            # Check gitignore
            if _is_ignored(f_rel, is_dir=False, patterns=ignore_patterns):
                continue

            file_path = os.path.join(dirpath, f)

            # Secret scan
            warnings = check_file_for_secrets(file_path)
            if warnings:
                all_warnings.append(f"\n📄 {f_rel}:")
                all_warnings.extend(warnings)

            # Zip arcname: relative path within project
            zip_name = f_rel.replace(os.sep, "/")
            files_to_pack.append((Path(file_path), zip_name))

    # ── Security check results ──────────────────────────────────────────
    if all_warnings:
        print("\n" + "=" * 60)
        print("⚠️  SECURITY WARNING: Potential secrets detected!")
        print("=" * 60)
        for w in all_warnings:
            print(w)
        print("=" * 60)
        if yes:
            print("⚠️  --yes flag set, continuing despite warnings.\n")
        else:
            response = input("\n⚠️  Continue packaging? (yes/no): ").strip().lower()
            if response not in ('yes', 'y'):
                print("❌ Cancelled.")
                sys.exit(1)
            print()
    else:
        print("✅ No secrets detected")

    # ── Create ZIP ──────────────────────────────────────────────────────
    print(f"\n📦 Packaging {len(files_to_pack)} files → {zip_path.name}...")

    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for file_path, arcname in sorted(files_to_pack, key=lambda x: x[1]):
            print(f"  ✓ {arcname}")
            zf.write(file_path, arcname)

    size_kb = os.path.getsize(zip_path) / 1024
    print(f"\n✅ Done: {zip_path}")
    print(f"   Size: {size_kb:.1f} KB | Files: {len(files_to_pack)}")


if __name__ == "__main__":
    yes = "--yes" in sys.argv or "-y" in sys.argv
    package_skill(yes=yes)
