import os

from robotd.vision.vision import Vision
from robotd.vision.camera import FileCamera

import unittest

image_root = os.path.dirname(os.path.realpath(__file__))


class DistanceAndRotationTestCase(unittest.TestCase):
    """The Test each check one of the six photos to make sure it works"""

    def test_photos(self):
        cases = [
            ("Photo 1.jpg", 9, 0.4),
            ("Photo 2.jpg", 12, 0.9),
            ("Photo 3.jpg", 15, 1),
            ("Photo 4.jpg", 26, 0.7),
            ("Photo 5.jpg", 78, 0.2),
            ("Photo 6.jpg", 95, 1.5),
        ]
        for case in cases:
            self.verify_distance(case[2], case[0], case[1])

    def verify_distance(self, distance, file_path, token_number):
        cam = FileCamera(image_root+"/test_photos/"+file_path, 720)
        v = Vision(cam, (0.075, 0.075))
        v.init()
        img = v.snapshot()
        tokens = v.process_image(img)
        self.assertEqual(len(tokens), 1)
        for token in tokens:
            self.assertEqual(int(token.id), token_number)
            self.assertAlmostEqual(token.polar[1], distance, delta=0.05)
