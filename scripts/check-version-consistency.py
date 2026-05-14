#!/usr/bin/env python3
"""
Version consistency validator for GLOW releases.

Ensures all version strings across the project match the target release version.
Source of truth: VERSION file at repo root
Required locations:
  - desktop/pyproject.toml: version = "X.X.X"
  - office-addin/package.json: "version": "X.X.X"
  - web/pyproject.toml: version = "X.X.X"
  - web/package.json: "version": "X.X.X"
  - CHANGELOG.md: ## [X.X.X] - YYYY-MM-DD
"""

import re
import sys
from pathlib import Path

# Repository root
REPO_ROOT = Path(__file__).parent.parent

# Target release version from VERSION file (single source of truth)
def get_target_version() -> str:
    """Extract version from VERSION file (source of truth)."""
    version_file = REPO_ROOT / "VERSION"
    if not version_file.exists():
        raise FileNotFoundError(f"Cannot find {version_file}")
    
    version = version_file.read_text().strip()
    if not version:
        raise ValueError("VERSION file is empty")
    
    # Validate semantic versioning
    if not re.match(r'^\d+\.\d+\.\d+$', version):
        raise ValueError(f"Invalid version format in VERSION file: {version}")
    
    return version


def check_version_in_file(filepath: Path, pattern: str, expected_version: str) -> bool:
    """Check if a file contains the expected version."""
    if not filepath.exists():
        print(f"[WARN] {filepath} not found")
        return True  # Non-blocking
    
    content = filepath.read_text()
    
    # Replace placeholder with expected version
    pattern_with_version = pattern.replace("VERSION", re.escape(expected_version))
    
    if re.search(pattern_with_version, content):
        return True
    
    print(f"[FAIL] {filepath}: version {expected_version} not found")
    print(f"       Expected pattern: {pattern}")
    return False


def main():
    """Validate all version strings."""
    try:
        target_version = get_target_version()
    except Exception as e:
        print(f"[FAIL] Cannot determine target version from VERSION file: {e}")
        return 1
    
    print(f"[CHECK] Verifying all versions match VERSION file: {target_version}\n")
    
    errors = []
    
    # Files to check with their patterns
    checks = [
        (REPO_ROOT / "desktop/pyproject.toml", r'version\s*=\s*"VERSION"'),
        (REPO_ROOT / "office-addin/package.json", r'"version":\s*"VERSION"'),
        (REPO_ROOT / "web/pyproject.toml", r'version\s*=\s*"VERSION"'),
        (REPO_ROOT / "web/package.json", r'"version":\s*"VERSION"'),
        (REPO_ROOT / "CHANGELOG.md", r"## \[VERSION\]"),
    ]
    
    for filepath, pattern in checks:
        if not check_version_in_file(filepath, pattern, target_version):
            errors.append(str(filepath))
    
    print()
    
    if errors:
        print(f"[FAIL] {len(errors)} version check(s) failed:")
        for path in errors:
            print(f"   - {path}")
        print("\nPlease update all version strings to match the release version:")
        print(f"   Version: {target_version}")
        return 1
    else:
        print(f"[PASS] All versions consistent: {target_version}")
        return 0


if __name__ == "__main__":
    sys.exit(main())
