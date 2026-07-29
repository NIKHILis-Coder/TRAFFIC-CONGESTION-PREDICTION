"""Download the raw datasets used by this project into data/raw/.

Raw data is not committed to git (~188 MB, all publicly re-downloadable), so this
script is the reproducibility path: clone the repo, run this, and data/raw/ is
restored byte-for-byte from the original sources.

Usage:
    python scripts/fetch_data.py              # fetch everything
    python scripts/fetch_data.py --only abilene
    python scripts/fetch_data.py --check      # report what's present, download nothing

NOTE: this is a data-acquisition utility only. It does no parsing, feature
engineering, or modelling -- see docs/dataset_selection.md for what the data is.
"""

from __future__ import annotations

import argparse
import sys
import urllib.request
from pathlib import Path

RAW = Path(__file__).resolve().parent.parent / "data" / "raw"

ABILENE_BASE = "https://www.cs.utexas.edu/~yzhang/research/AbileneTM"
GEANT_URL = (
    "https://totem.run.montefiore.uliege.be/files/data/"
    "traffic-matrices-anonymized-v2.tar.bz2"
)
SNDLIB_URL = "https://sndlib.put.poznan.pl/download/sndlib-networks-xml.zip"

# (relative destination, source url)
FILES: dict[str, list[tuple[str, str]]] = {
    "abilene": (
        [(f"abilene/{n}", f"{ABILENE_BASE}/{n}")
         for n in ("readme.txt", "topo-2003-04-10.txt", "links", "demands", "A")]
        + [(f"abilene/traffic-matrices/X{i:02d}.gz", f"{ABILENE_BASE}/X{i:02d}.gz")
           for i in range(1, 25)]
    ),
    "geant": [("geant/traffic-matrices-anonymized-v2.tar.bz2", GEANT_URL)],
    "sndlib": [("sndlib/sndlib-networks-xml.zip", SNDLIB_URL)],
}


def fetch(rel: str, url: str, *, check_only: bool) -> str:
    dest = RAW / rel
    if dest.exists() and dest.stat().st_size > 0:
        return f"  present  {rel} ({dest.stat().st_size / 1e6:.1f} MB)"
    if check_only:
        return f"  MISSING  {rel}"
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        urllib.request.urlretrieve(url, dest)
    except Exception as exc:  # noqa: BLE001 - report and continue to next file
        if dest.exists():
            dest.unlink()
        return f"  FAILED   {rel}: {exc}"
    return f"  fetched  {rel} ({dest.stat().st_size / 1e6:.1f} MB)"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--only", choices=sorted(FILES), help="fetch a single dataset")
    ap.add_argument("--check", action="store_true", help="report status, download nothing")
    args = ap.parse_args()

    groups = [args.only] if args.only else sorted(FILES)
    failures = 0
    for group in groups:
        print(f"\n{group}:")
        for rel, url in FILES[group]:
            line = fetch(rel, url, check_only=args.check)
            failures += line.strip().startswith(("FAILED", "MISSING"))
            print(line)

    print("\nSNDlib note: unzip data/raw/sndlib/sndlib-networks-xml.zip to get "
          "geant.xml / abilene.xml reference topologies.")
    if failures:
        print(f"\n{failures} file(s) missing or failed.")
    return 1 if failures and not args.check else 0


if __name__ == "__main__":
    sys.exit(main())
