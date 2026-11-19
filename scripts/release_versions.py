"""Read/verify release versions shared by release.yml and checks.yml.

Sources of truth:
  - mcp/pyproject.toml            -> project.version
  - server.json                   -> version
  - server.json packages[0]       -> version
  - server.json packages[0]       -> identifier's OCI tag (after last ':')

Usage:
  python scripts/release_versions.py --print pyproject|server|package|identifier|oci-tag
  python scripts/release_versions.py --check <expected-version>
  python scripts/release_versions.py --json
"""

from __future__ import annotations

import argparse
import json
import sys

if sys.version_info < (3, 11):
    sys.stderr.write("ERROR: Python >= 3.11 is required (tomllib).\n")
    raise SystemExit(2)

import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PYPROJECT = ROOT / "mcp" / "pyproject.toml"
SERVER_JSON = ROOT / "server.json"


def read_versions() -> dict[str, str]:
    try:
        with open(PYPROJECT, "rb") as f:
            pyproject_version = tomllib.load(f)["project"]["version"]
    except (OSError, KeyError) as exc:
        raise SystemExit(f"ERROR: cannot read project.version from {PYPROJECT}: {exc}") from exc
    try:
        server = json.loads(SERVER_JSON.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"ERROR: cannot parse {SERVER_JSON}: {exc}") from exc
    try:
        package = server["packages"][0]
        server_version = server["version"]
        package_version = package["version"]
        identifier = package["identifier"]
    except (KeyError, IndexError, TypeError) as exc:
        raise SystemExit(f"ERROR: unexpected server.json shape: {exc}") from exc
    if ":" not in identifier:
        raise SystemExit(
            f"ERROR: packages[0].identifier has no OCI tag (no ':'): {identifier!r}"
        )
    oci_tag = identifier.rsplit(":", 1)[1]
    return {
        "pyproject": str(pyproject_version),
        "server": str(server_version),
        "package": str(package_version),
        "identifier": str(identifier),
        "oci-tag": str(oci_tag),
    }


def check(expected: str, versions: dict[str, str]) -> list[str]:
    expected = expected[1:] if expected.startswith("v") else expected
    errors = []
    if versions["pyproject"] != expected:
        errors.append(
            f"mcp/pyproject.toml version ({versions['pyproject']}) != expected ({expected})"
        )
    if versions["server"] != expected:
        errors.append(
            f"server.json version ({versions['server']}) != expected ({expected})"
        )
    if versions["package"] != expected:
        errors.append(
            f"server.json packages[0].version ({versions['package']}) != expected ({expected})"
        )
    if versions["oci-tag"] != expected:
        errors.append(
            f"server.json packages[0].identifier tag ({versions['oci-tag']}) != expected ({expected})"
        )
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Read or verify release versions.")
    parser.add_argument(
        "--print",
        dest="print_key",
        choices=["pyproject", "server", "package", "identifier", "oci-tag"],
        help="print a single version value",
    )
    parser.add_argument(
        "--check",
        metavar="VERSION",
        help="verify all versions equal VERSION (leading 'v' allowed)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="print all versions as JSON",
    )
    args = parser.parse_args(argv)
    versions = read_versions()
    if args.print_key:
        print(versions[args.print_key])
        return 0
    if args.check is not None:
        expected = args.check[1:] if args.check.startswith("v") else args.check
        print(f"expected={expected}")
        print(
            "pyproject={pyproject} server.json={server} "
            "package={package} oci_tag={oci-tag}".format(**versions)
        )
        errors = check(expected, versions)
        if errors:
            for err in errors:
                print(f"ERROR: {err}", file=sys.stderr)
            return 1
        print(f"All versions match: {expected}")
        return 0
    if args.json:
        print(json.dumps(versions, indent=2))
        return 0
    parser.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
