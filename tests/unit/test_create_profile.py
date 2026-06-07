"""Unit tests for Chrome profile directory creation."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.tasks.create_profile import create_chrome_profile


class TestCreateProfile(unittest.TestCase):
    """Validate Chrome profile directory setup without launching a browser."""

    def test_create_chrome_profile_creates_missing_profile_directory(self):
        """Create the requested nested profile directory when it does not exist."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            profile_name = "Profile 1"
            create_chrome_profile(tmp_dir, profile_name)

            self.assertTrue((Path(tmp_dir) / profile_name).is_dir())

    def test_create_chrome_profile_keeps_existing_directory(self):
        """Leave an existing profile directory in place."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            profile_path = Path(tmp_dir) / "Profile 1"
            profile_path.mkdir()

            create_chrome_profile(tmp_dir, "Profile 1")

            self.assertTrue(profile_path.is_dir())

    def test_create_chrome_profile_exits_on_directory_creation_error(self):
        """Surface filesystem creation errors as the CLI's failure exit."""
        with patch("src.tasks.create_profile.os.path.exists", return_value=False), patch(
            "src.tasks.create_profile.os.makedirs",
            side_effect=OSError("permission denied"),
        ):
            with self.assertRaises(SystemExit) as ctx:
                create_chrome_profile(".browser_profile", "Profile 1")

        self.assertEqual(ctx.exception.code, 1)


if __name__ == "__main__":
    unittest.main()
