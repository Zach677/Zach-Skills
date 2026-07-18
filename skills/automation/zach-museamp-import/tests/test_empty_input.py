import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

import check_museamp_ready  # noqa: E402
import make_museamp_ready_copy  # noqa: E402


class EmptyInputTest(unittest.TestCase):
    def test_empty_source_fails_without_creating_output(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            source = Path(temporary_directory) / "empty"
            output = Path(temporary_directory) / "output"
            source.mkdir()

            with patch.object(check_museamp_ready.shutil, "which", return_value="ffprobe"):
                with patch.object(sys, "argv", ["check_museamp_ready.py", str(source)]):
                    with self.assertRaisesRegex(SystemExit, "no supported audio files"):
                        check_museamp_ready.main()
            with patch.object(make_museamp_ready_copy.shutil, "which", return_value="ffmpeg"):
                with patch.object(sys, "argv", ["make_museamp_ready_copy.py", "--flat", str(source), str(output)]):
                    with self.assertRaisesRegex(SystemExit, "no supported audio files"):
                        make_museamp_ready_copy.main()
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
