import tempfile
import unittest
from pathlib import Path
from unittest import mock

from robotd.devices import GameState


class GameStateBoardTests(unittest.TestCase):
    def assertStatus(self, expected):
        board = GameState({})
        status = board.status()
        self.assertEqual(
            expected,
            status,
            "Wrong status",
        )

    def setUp(self):
        tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(tempdir.cleanup)

        file_glob_mock = mock.patch(
            'robotd.devices.GameState.FILE_GLOB',
            new=tempdir.name + GameState.FILE_GLOB,
        )
        file_glob_mock.start()
        self.addCleanup(file_glob_mock.stop)

        self.tempdir_path = Path(tempdir.name)

    def test_no_zone_file(self):
        self.assertStatus({'mode': 'development', 'zone': 0})

    def test_zone_file_at_wrong_level(self):
        zone_file = self.tempdir_path / 'media' / 'zone-2'
        zone_file.parent.mkdir()
        zone_file.touch()

        self.assertStatus({'mode': 'development', 'zone': 0})

    def test_one_zone_file(self):
        zone_file = self.tempdir_path / 'media/usb0' / 'zone-2'
        zone_file.parent.mkdir(parents=True)
        zone_file.touch()

        self.assertStatus({'mode': 'competition', 'zone': 2})

    def test_after_zone_file_removed(self):
        zone_file = self.tempdir_path / 'media/usb0' / 'zone-6'
        zone_file.parent.mkdir(parents=True)
        zone_file.touch()

        self.assertStatus({'mode': 'competition', 'zone': 6})

        zone_file.unlink()

        self.assertStatus({'mode': 'development', 'zone': 0})
