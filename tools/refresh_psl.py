#!/usr/bin/env python3
"""
tools/refresh_psl.py — Download and cache the official Public Suffix List

Usage:
    python3 tools/refresh_psl.py [--output prototypes/public_suffix_list.dat]

Downloads the official Public Suffix List from https://publicsuffix.org/list/
and saves it to the specified output file. This file is used by aegis_psl.py
when the PSL_PATH environment variable or --psl-file argument is set.

The prototype aegis_psl.py has a small built-in fallback subset. For real use,
run this script to fetch the full list and point the loader at it.

This script uses ONLY the Python standard library.

WARNING: This script makes a single outbound HTTPS request to publicsuffix.org.
Ask the owner before running in a network-restricted environment.
"""

import argparse
import hashlib
import pathlib
import sys
import urllib.request
import urllib.error

PSL_URL = "https://publicsuffix.org/list/public_suffix_list.dat"
DEFAULT_OUTPUT = pathlib.Path(__file__).resolve().parent.parent / "prototypes" / "public_suffix_list.dat"


def download_psl(output_path: pathlib.Path) -> None:
    print(f"Downloading Public Suffix List from {PSL_URL} ...")
    try:
        with urllib.request.urlopen(PSL_URL, timeout=30) as resp:
            data = resp.read()
    except urllib.error.URLError as e:
        print(f"ERROR: Download failed: {e}", file=sys.stderr)
        sys.exit(1)

    sha256 = hashlib.sha256(data).hexdigest()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(data)

    print(f"Saved to: {output_path}")
    print(f"Size:     {len(data):,} bytes")
    print(f"SHA-256:  {sha256}")
    print()
    print("Record these values in docs/VERIFY.md or docs/BUILD.md.")
    print("Set PSL_PATH environment variable or pass --psl-file to aegis_psl.py.")


def main():
    parser = argparse.ArgumentParser(description="Refresh the Public Suffix List")
    parser.add_argument(
        "--output",
        type=pathlib.Path,
        default=DEFAULT_OUTPUT,
        help=f"Output file path (default: {DEFAULT_OUTPUT})",
    )
    args = parser.parse_args()
    download_psl(args.output)


if __name__ == "__main__":
    main()
