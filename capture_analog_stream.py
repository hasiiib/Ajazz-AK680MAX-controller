"""One-shot, explicitly authorized analog-stream hardware probe (board 2255).

Sends a temporary stream-start flag, reads a bounded number of Report ID 5
samples, and attempts one stream-stop flag. No persistent settings are written.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "app"))

from analog_stream import AnalogStreamError, AnalogStreamSession  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--confirm-one-temporary-0x1b-stream-test",
        action="store_true",
        help="Confirm one bounded temporary 0x1B stream start/read/stop test.",
    )
    parser.add_argument(
        "--max-reports",
        type=int,
        default=16,
        choices=range(1, 33),
        help="Maximum Report ID 5 reports to read (default: 16; maximum: 32).",
    )
    args = parser.parse_args()
    if not args.confirm_one_temporary_0x1b_stream_test:
        parser.error("No hardware command sent. Add the explicit confirmation flag.")

    session = AnalogStreamSession()
    started = False
    samples = []
    try:
        session.start()
        started = True
        samples = session.poll(max_reports=args.max_reports)
        print(f"Read batch complete: {len(samples)} valid analog samples.")
        if samples:
            slots = sorted({sample.slot for sample in samples})
            print("Slots observed:", ", ".join(str(slot) for slot in slots))
            for sample in samples[:16]:
                print(f"Sample: slot={sample.slot}, raw_travel={sample.raw_travel}")
        else:
            print("No valid samples observed in the bounded read.")
    except AnalogStreamError as exc:
        print(f"Analog stream test failed: {exc}", file=sys.stderr)
        return 1
    finally:
        if started or session.active:
            try:
                session.stop()
                print("Temporary stream stop command sent; handles closed.")
            except AnalogStreamError as exc:
                print(f"Stream stop could not be confirmed: {exc}", file=sys.stderr)
    print("No capture file or serial number/device path recorded.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
