import unittest

from robotd.vision.camera import Camera


class CameraTestCase(unittest.TestCase):
    def test_invalid_camera(self):
        """ Test the camera errors when reading from an invalid camera"""
        cam = Camera("/", (1, 1), 1)
        with self.assertRaises(RuntimeError):
            cam.init()
