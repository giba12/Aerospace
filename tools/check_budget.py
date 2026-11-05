#!/usr/bin/env python3
"""Fail if the test suite took longer than its time budget (NFR-006).

The budget is 30 seconds for the whole suite, INCLUDING the seed-ensemble tests (EST-008, EST-012).
This adds up the `time` of every test case in the JUnit files and compares the total with the limit.
It is run by CI after `ctest`. Sanitizer and coverage builds are slower by design and are not held to
this budget.

    python tools/check_budget.py --junit build/test-reports/gtest.xml build/test-reports/pytest.xml
"""
import argparse
import sys
import xml.etree.ElementTree as ET

DEFAULT_LIMIT_S = 30.0


def total_seconds(junit_paths):
    """Sum of the `time` attribute (seconds) of every <testcase> in the files. Returns (total, count)."""
    total, count = 0.0, 0
    for path in junit_paths:
        for case in ET.parse(path).getroot().iter("testcase"):
            total += float(case.get("time", "0"))
            count += 1
    return total, count


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--junit", required=True, nargs="+")
    p.add_argument("--limit", type=float, default=DEFAULT_LIMIT_S, help="seconds (default 30)")
    args = p.parse_args(argv)
    try:
        total, count = total_seconds(args.junit)
    except (OSError, ET.ParseError, ValueError) as e:
        print(f"budget: error: cannot read an input file: {e!r}", file=sys.stderr)
        return 1
    if count == 0:
        print("budget: error: the JUnit files contain no tests, so the time proves nothing", file=sys.stderr)
        return 1
    print(f"budget: {count} tests took {total:.1f} s (limit {args.limit:g} s)")
    if total > args.limit:
        print(f"budget: error: over the time budget by {total - args.limit:.1f} s", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
