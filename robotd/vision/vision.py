"""Classes for handling vision"""

from robotd.vision.apriltag._apriltag import ffi, lib

from robotd.vision.camera import Camera
from robotd.vision.camera_base import CameraBase
from robotd.vision.tokens import Token


class Vision:
    """Class that handles the vision library"""

    def __init__(self, camera: CameraBase, token_size):
        # Pygame camera object
        self.camera = camera
        # size of the tokens the camera is testing
        self.token_size = token_size
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
        lib.apriltag_init(self._detector, 1.0, 0.0, 1, 0, 1)
        size = self.camera.get_image_size()
        self.image = lib.image_u8_create_stride(size[0], size[1], size[0])

    def _deinit_library(self):
        # Always destroy the detector
        if self._detector:
            lib.apriltag_detector_destroy(self._detector)
        if self.image:
            lib.image_u8_destroy(self.image)

    def _parse_results(self, results):
        markers = []
        for i in range(results.size):
            detection = lib.zarray_get_detection(results, i)
            markers.append(Token(detection, self.token_size, self.camera.focal_length))
            lib.destroy_detection(detection)
        return markers

    def snapshot(self):
        """ Take an image and process it """
        # get the PIL image from the camera
        img = self.camera.capture_image()
        total_length = img.size[0] * img.size[1]
        # Detect the markers
        ffi.memmove(self.image.buf, img.tobytes(), total_length)
        results = lib.apriltag_detector_detect(self._detector, self.image)

        tokens = self._parse_results(results)

        # Remove the array now we've got them
        lib.zarray_destroy(results)

        return tokens, img


if __name__ == "__main__":
    # webcam
    CAM_DEVICE = "/dev/video0"
    CAM_IMAGE_SIZE = (1280, 720)
    FOCAL_DISTANCE = 720
    camera = Camera(CAM_DEVICE, CAM_IMAGE_SIZE, 720)
    # File Camera
    # camera = FileCamera()
    v = Vision(camera, (0.1, 0.1))
    v.init()
    while True:
        tokens, _ = v.snapshot()
        print(len(tokens), "tokens seen")
