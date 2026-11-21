"""Write the executable-size table for the CI run summary (T-035).

    python scripts/size_report.py RELEASE_EXE PROBE_EXE [--previous BYTES]

Prints Markdown: the release build, the component-enabled build, the headroom
under 30 MiB for each, and growth since the last release when `--previous`
(the byte size of the last published executable) is given.
"""

from __future__ import annotations

import argparse
import pathlib

LIMIT = 31_457_280  # 30 MiB
MIB = 1024 * 1024


def _mib(n: int) -> str:
    return f"{n / MIB:.2f}"


def report(release: int, probe: int, previous: int = 0, limit: int = LIMIT) -> str:
    rows = [
        "## Executable size",
        "| Build | Bytes | MiB | Headroom under 30 MiB (MiB) |",
        "| --- | ---: | ---: | ---: |",
        f"| Release build | {release:,} | {_mib(release)} | {_mib(limit - release)} |",
        f"| With component modules forced in | {probe:,} | {_mib(probe)} | {_mib(limit - probe)} |",
        f"| Added by the component modules | {probe - release:,} | {_mib(probe - release)} | |",
    ]
    if previous > 0:
        grown = release - previous
        sign = "+" if grown >= 0 else "-"
        rows.append(
            f"| Change since the last release ({previous:,} bytes) | {sign}{abs(grown):,} | "
            f"{sign}{_mib(abs(grown))} | |"
        )
    return "\n".join(rows) + "\n"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("release", type=pathlib.Path)
    parser.add_argument("probe", type=pathlib.Path)
    parser.add_argument("--previous", type=int, default=0)
    args = parser.parse_args(argv)
    print(report(args.release.stat().st_size, args.probe.stat().st_size, args.previous), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
