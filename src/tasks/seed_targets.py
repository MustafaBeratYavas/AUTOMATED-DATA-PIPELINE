"""CLI utility for loading product codes into the scraping queue."""

import argparse
import os
import sys

if __name__ == "__main__" and __package__ is None:
    current_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.dirname(os.path.dirname(current_dir))
    sys.path.append(root_dir)

from src.services.database import DatabaseService
from src.utils import string_utils


def seed_from_file(file_path: str) -> None:
    """Read product codes from a text file and enqueue unique targets."""
    if not os.path.exists(file_path):
        print(f"Error: Input file not found at '{file_path}'")
        sys.exit(1)

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            codes = [
                string_utils.normalize_product_code(line.split("/")[0])
                for line in f
                if line.strip()
            ]

        seen = set()
        unique_codes = []
        for c in codes:
            if c and c not in seen:
                seen.add(c)
                unique_codes.append(c)

        if not unique_codes:
            print("Warning: No valid product codes found in the provided file.")
            return

        print(f"Read {len(unique_codes)} unique product codes from {file_path}")

        # INSERT OR IGNORE in DatabaseService keeps repeated seeding idempotent.
        with DatabaseService() as db:
            added = 0
            for code in unique_codes:
                try:
                    db.add_target_product(code)
                    added += 1
                except Exception as e:
                    print(f"  [ERROR] Failed to add '{code}': {e}")

            print(f"Successfully synchronized {added} product(s) to the database task queue.")

    except Exception as e:
        print(f"Fatal error during seeding: {e}")
        sys.exit(1)


def main() -> None:
    """Parse command-line arguments and seed the queue."""
    parser = argparse.ArgumentParser(
        description="Automated Data Pipeline - Database Seeding Utility",
        formatter_class=argparse.RawTextHelpFormatter
    )

    parser.add_argument(
        "--file", "-f",
        required=True,
        help="Path to the .txt file containing product codes (one per line)"
    )

    args = parser.parse_args()
    seed_from_file(args.file)


if __name__ == "__main__":
    main()
