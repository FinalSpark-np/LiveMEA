import argparse
import sys

sys.path.append("../fetch_live")
from MEA_live import LiveMEA


def main():
    parser = argparse.ArgumentParser(description="Record live MEA data.")
    parser.add_argument(
        "-d",
        "--duration",
        type=int,
        default=5,
        help="Duration of the recording in seconds",
    )
    parser.add_argument(
        "-p",
        "--path",
        type=str,
        default="live_data.h5",
        help="Path to save the recorded data",
    )
    parser.add_argument(
        "-m", "--MEA", type=int, default=0, help="MEA ID to record data from"
    )
    args = parser.parse_args()
    LiveMEA.quick_record(args.path, args.duration, args.MEA)


if __name__ == "__main__":
    main()
