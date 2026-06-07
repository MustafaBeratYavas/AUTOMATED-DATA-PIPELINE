"""Unit tests for product-code queue seeding."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.tasks.seed_targets import seed_from_file


class TestSeedTargets(unittest.TestCase):
    """Validate target file parsing and database queue synchronization."""

    def test_seed_from_file_normalizes_splits_and_deduplicates_codes(self):
        """Seed only unique normalized product codes from a text file."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            file_path = Path(tmp_dir) / "product_codes.txt"
            file_path.write_text(
                "\n".join(
                    [
                        " rz01-04620100-r3g1 / previous-url",
                        "RZ01-04620100-R3G1",
                        "rz02 03050200 r3m1",
                        "",
                    ]
                ),
                encoding="utf-8",
            )

            db = MagicMock()
            with patch("src.tasks.seed_targets.DatabaseService") as mock_db_cls:
                mock_db_cls.return_value.__enter__.return_value = db

                seed_from_file(str(file_path))

        added_codes = [call.args[0] for call in db.add_target_product.call_args_list]
        self.assertEqual(
            added_codes,
            [
                "RZ01-04620100-R3G1",
                "RZ02 03050200 R3M1",
            ],
        )

    def test_seed_from_file_missing_file_exits(self):
        """Reject a missing input file before touching the database."""
        with patch("src.tasks.seed_targets.DatabaseService") as mock_db_cls:
            with self.assertRaises(SystemExit) as ctx:
                seed_from_file("missing-product-codes.txt")

        self.assertEqual(ctx.exception.code, 1)
        mock_db_cls.assert_not_called()

    def test_seed_from_file_empty_file_skips_database(self):
        """Avoid opening the database when no usable product code exists."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            file_path = Path(tmp_dir) / "empty_codes.txt"
            file_path.write_text("\n\n   \n", encoding="utf-8")

            with patch("src.tasks.seed_targets.DatabaseService") as mock_db_cls:
                seed_from_file(str(file_path))

        mock_db_cls.assert_not_called()


if __name__ == "__main__":
    unittest.main()
