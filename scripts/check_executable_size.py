"""Check that a built Windows executable stays within the release size budget."""
import argparse
import pathlib
import sys

DEFAULT_MAX_BYTES = 31_457_280  # 30 MiB
MEBIBYTE = 1024 * 1024


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Report a Windows executable's size and enforce the release limit."
    )
    parser.add_argument("executable", type=pathlib.Path, help="built executable to measure")
    parser.add_argument(
        "--max-bytes",
        type=int,
        default=DEFAULT_MAX_BYTES,
        help=f"maximum permitted size in bytes (default: {DEFAULT_MAX_BYTES:,})",
    )
    args = parser.parse_args(argv)
    if args.max_bytes <= 0:
        parser.error("--max-bytes must be greater than zero")

    try:
        size = args.executable.stat().st_size
    except OSError as exc:
        print(f"ERROR: cannot read executable {args.executable}: {exc}", file=sys.stderr)
        return 2

    margin = args.max_bytes - size
    print(f"Built executable: {size:,} bytes ({size / MEBIBYTE:.2f} MiB)")
    print(f"Size limit: {args.max_bytes:,} bytes ({args.max_bytes / MEBIBYTE:.2f} MiB)")
    if margin < 0:
        print(f"FAIL: executable exceeds the limit by {-margin:,} bytes ({-margin / MEBIBYTE:.2f} MiB)")
        return 1

    print(f"PASS: {margin:,} bytes ({margin / MEBIBYTE:.2f} MiB) of headroom remain")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
