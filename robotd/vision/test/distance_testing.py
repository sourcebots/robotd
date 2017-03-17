from robotd.vision.vision import Vision
from robotd.vision.camera import FileCamera

import unittest

class DistanceAndRotationTestCase(unittest.TestCase):
    """The Test each check one of the six photos to make sure it works"""
    def test_photo_one(self):
        distance = 0.4
        token_number = 9
        file_path= "test_photos/Photo 1.jpg"
        cam = FileCamera(file_path, 720)
        v = Vision(cam, (0.075,0.075))
        v.init()
        tokens = v.snapshot()
        self.assertEqual(len(tokens), 1)
        for token in tokens:
            self.assertEqual(int(token.id), token_number)
            self.assertAlmostEqual(token.distance, distance, delta=0.05)


    def test_photo_two(self):
        distance = 0.9
        token_number = 12
        file_path= "test_photos/Photo 2.jpg"
        cam = FileCamera(file_path, 720)
        v = Vision(cam, (0.075,0.075))
        v.init()
        tokens = v.snapshot()
        self.assertEqual(len(tokens), 1)
        for token in tokens:
            self.assertEqual(int(token.id), token_number)
            self.assertAlmostEqual(token.distance, distance, delta=0.05)

    def test_photo_three(self):
        distance = 1.0
        token_number = 15
        file_path= "test_photos/Photo 3.jpg"
        cam = FileCamera(file_path, 720)
        v = Vision(cam, (0.075,0.075))
        v.init()
        tokens = v.snapshot()
        self.assertEqual(len(tokens), 1)
        for token in tokens:
            self.assertEqual(int(token.id), token_number)
            self.assertAlmostEqual(token.distance, distance, delta=0.05)

    def test_photo_four(self):
        distance = 0.7
        token_number = 26
        file_path= "test_photos/Photo 4.jpg"
        cam = FileCamera(file_path, 720)
        v = Vision(cam, (0.075,0.075))
        v.init()
        tokens = v.snapshot()
        self.assertEqual(len(tokens), 1)
        for token in tokens:
            self.assertEqual(int(token.id), token_number)
            self.assertAlmostEqual(token.distance, distance, delta=0.05)

    def test_photo_five(self):
        distance = 0.2
        token_number = 78
        file_path= "test_photos/Photo 5.jpg"
        cam = FileCamera(file_path, 720)
        v = Vision(cam, (0.075,0.075))
        v.init()
        tokens = v.snapshot()
        self.assertEqual(len(tokens), 1)
        for token in tokens:
            self.assertEqual(int(token.id), token_number)
            self.assertAlmostEqual(token.distance, distance, delta=0.05)

    def test_photo_six(self):
        distance = 1.5
        token_number = 95
        file_path= "test_photos/Photo 6.jpg"
        cam = FileCamera(file_path, 720)
        v = Vision(cam, (0.075,0.075))
        v.init()
        tokens = v.snapshot()
        self.assertEqual(len(tokens), 1)
        for token in tokens:
            self.assertEqual(int(token.id), token_number)
            self.assertAlmostEqual(token.distance, distance, delta=0.05)
