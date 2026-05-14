#!/usr/bin/env python3
"""
Release version incrementer for GLOW.

Updates the VERSION file and syncs it across all product configurations.
Usage:
  python scripts/increment-version.py 7.1.0 7.2.0
  python scripts/increment-version.py --patch    (e.g. 7.1.0 -> 7.1.1)
  python scripts/increment-version.py --minor    (e.g. 7.1.0 -> 7.2.0)
  python scripts/increment-version.py --major    (e.g. 7.1.0 -> 8.0.0)
"""

import re
import sys
from pathlib import Path
from typing import Tuple

# Repository root
REPO_ROOT = Path(__file__).parent.parent

def get_current_version() -> str:
    """Read current version from VERSION file."""
    version_file = REPO_ROOT / "VERSION"
    if not version_file.exists():
        raise FileNotFoundError(f"Cannot find {version_file}")
    
    version = version_file.read_text().strip()
    if not version or not re.match(r'^\d+\.\d+\.\d+$', version):
        raise ValueError(f"Invalid version in VERSION file: {version}")
    
    return version


def increment_version(current: str, increment_type: str) -> str:
    """Increment version based on type."""
    parts = [int(x) for x in current.split('.')]
    major, minor, patch = parts
    
    if increment_type == "patch":
        patch += 1
    elif increment_type == "minor":
        minor += 1
        patch = 0
    elif increment_type == "major":
        major += 1
        minor = 0
        patch = 0
    else:
        raise ValueError(f"Unknown increment type: {increment_type}")
    
    return f"{major}.{minor}.{patch}"


def update_version_file(new_version: str) -> None:
    """Update the VERSION file."""
    version_file = REPO_ROOT / "VERSION"
    version_file.write_text(f"{new_version}\n")
    print(f"[OK] Updated {version_file}")


def update_pyproject(filepath: Path, new_version: str) -> None:
    """Update version in pyproject.toml file."""
    if not filepath.exists():
        print(f"[WARN] {filepath} not found, skipping")
        return
    
    content = filepath.read_text()
    updated = re.sub(
        r'version\s*=\s*"[^"]+"',
        f'version = "{new_version}"',
        content
    )
    
    if updated != content:
        filepath.write_text(updated)
        print(f"[OK] Updated {filepath}")
    else:
        print(f"[WARN] No version found in {filepath}")


def update_package_json(filepath: Path, new_version: str) -> None:
    """Update version in package.json file."""
    if not filepath.exists():
        print(f"[WARN] {filepath} not found, skipping")
        return
    
    content = filepath.read_text()
    updated = re.sub(
        r'"version"\s*:\s*"[^"]+"',
        f'"version": "{new_version}"',
        content
    )
    
    if updated != content:
        filepath.write_text(updated)
        print(f"[OK] Updated {filepath}")
    else:
        print(f"[WARN] No version found in {filepath}")


def update_changelog(filepath: Path, new_version: str) -> None:
    """Add or update [Unreleased] section in CHANGELOG.md."""
    if not filepath.exists():
        print(f"[WARN] {filepath} not found, skipping")
        return
    
    content = filepath.read_text()
    
    # Check if [Unreleased] exists
    if "## [Unreleased]" not in content:
        # Add it at the top after the header
        content = re.sub(
            r'(---\n\n)',
            f'---\n\n## [Unreleased]\n\n### Added\n\n### Changed\n\n### Fixed\n\n',
            content,
            count=1
        )
    
    filepath.write_text(content)
    print(f"[OK] Ensured [Unreleased] section in {filepath}")


def main():
    """Main increment logic."""
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    
    current_version = get_current_version()
    print(f"[INFO] Current version: {current_version}\n")
    
    # Determine new version
    if len(sys.argv) == 2:
        arg = sys.argv[1]
        if arg in ["--patch", "--minor", "--major"]:
            new_version = increment_version(current_version, arg.lstrip("--"))
        else:
            new_version = arg
    elif len(sys.argv) == 3:
        # python increment-version.py 7.1.0 7.2.0
        new_version = sys.argv[2]
    else:
        print(__doc__)
        return 1
    
    # Validate new version format
    if not re.match(r'^\d+\.\d+\.\d+$', new_version):
        print(f"[FAIL] Invalid version format: {new_version}")
        return 1
    
    if new_version == current_version:
        print(f"[FAIL] New version must differ from current version")
        return 1
    
    print(f"[INFO] New version: {new_version}\n")
    
    # Update all files
    update_version_file(new_version)
    update_pyproject(REPO_ROOT / "desktop/pyproject.toml", new_version)
    update_pyproject(REPO_ROOT / "web/pyproject.toml", new_version)
    update_package_json(REPO_ROOT / "office-addin/package.json", new_version)
    update_package_json(REPO_ROOT / "web/package.json", new_version)
    update_changelog(REPO_ROOT / "CHANGELOG.md", new_version)
    
    print(f"\n[OK] Version incremented to {new_version}")
    print(f"\nNext steps:")
    print(f"  1. Review changes: git diff")
    print(f"  2. Run checks: python scripts/check-version-consistency.py")
    print(f"  3. Commit: git commit -m 'chore: bump version to {new_version}'")
    print(f"  4. Tag: git tag -a v{new_version} -m 'Release {new_version}'")
    print(f"  5. Push: git push origin main --tags")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
