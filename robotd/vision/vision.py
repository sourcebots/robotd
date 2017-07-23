"""Classes for handling vision"""

from robotd.native.apriltag._apriltag import ffi, lib

from robotd.game_specific import MARKER_SIZES
from robotd.vision.camera import Camera, FileCamera
from robotd.vision.camera_base import CameraBase
from robotd.vision.token_display import display_tokens
from robotd.vision.tokens import Token


class Vision:
    """Class that handles the vision library and the camera."""

    def __init__(self, camera: CameraBase, token_sizes):
        self.camera = camera
        # index for marker sizes
        self.token_sizes = token_sizes
        # apriltag detector object
        self._detector = None
        # image from camera
        self.image = None

    def init(self):
        self.camera.init()
        self._init_library()

    def __del__(self):
        self._deinit_library()

    def _init_library(self):
        """
        Initialise the library
        :return:
        """
        # init detector
        self._detector = lib.apriltag_detector_create()
        """
        apriltag_detector_t* td,
        float decimate,
          default: 1.0, "Decimate input image by this factor"
        float sigma,
          default: 0.0, "Apply low-pass blur to input; negative sharpens"
        int refine_edges,
          default: 1, "Spend more time trying to align edges of tags"
        int refine_decode,
          default: 0, "Spend more time trying to decode tags"
        int refine_pose
          default: 0, "Spend more time trying to find the position of the tag"
        """
        lib.apriltag_init(self._detector, 1.0, 0.0, 1, 0, 0)
        size = self.camera.get_image_size()
        self.image = lib.image_u8_create_stride(size[0], size[1], size[0])

    def _deinit_library(self):
        """
        Deinitialise the library
        :return:
        """
        # Always destroy the detector
        if self._detector:
            lib.apriltag_detector_destroy(self._detector)
        if self.image:
            lib.image_u8_destroy(self.image)

    def _parse_results(self, results):
        """
        Parse the array of results
        :param results: cffi array of results
        :return: python list of individual token objects
        """
        markers = []
        for i in range(results.size):
            detection = lib.zarray_get_detection(results, i)
            markers.append(Token(detection, self.token_sizes, self.camera.focal_length))
            lib.destroy_detection(detection)
        return markers

    def snapshot(self):
        """
        Capture an image from the camera

        returns: (List of Token objects, PIL Image Captured)

        """
        # get the PIL image from the camera
        img = self.camera.capture_image()
        return img.point(lambda x: 255 if x > 128 else 0)

    def process_image(self, img):
        """
        Run the given image through the apriltags detection library
        :param img: PIL Luminosity image to be processed
        :return: python list of Token objects.
        """
        total_length = img.size[0] * img.size[1]
        # Detect the markers
        ffi.memmove(self.image.buf, img.tobytes(), total_length)
        results = lib.apriltag_detector_detect(self._detector, self.image)
        tokens = self._parse_results(results)
        # Remove the array now we've got them
        lib.zarray_destroy(results)
        return tokens


if __name__ == "__main__":
    """
    Debug code, load the first video device seen and capture an image
    """
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('-f', nargs='?', default=False,
                        help="""Pass an image file to use, otherwise use webcam,
                        if filename is blank, uses 'tagsampler.png'""")
    args = parser.parse_args()
    # Change the below for quick debugging
    if args.f is False:
        CAM_IMAGE_SIZE = (1280, 720)
        FOCAL_DISTANCE = 720
        camera = Camera(None, CAM_IMAGE_SIZE, 720)
    else:
        if args.f is None:
            f = "tagsampler.png"
        else:
            f = args.f
        camera = FileCamera(f, 720)
    v = Vision(camera, MARKER_SIZES)
    v.init()
    while True:
        img = v.snapshot()
        tokens = v.process_image(img)
        img = display_tokens(tokens, img)
        img.show()
        if tokens:
            print(tokens[0].pixel_centre)
