from PIL import Image

from robotd.vision.camera_base import CameraBase
from robotd.cvcapture import CaptureDevice


class Camera(CameraBase):
    def __init__(self, camera_path, proposed_image_size, focal_length):
        """Initialise camera with focal length and image size."""
        super().__init__()
        self.cam_image_size = proposed_image_size
        self.cam_path = camera_path
        self.camera = None
        self.focal_length = focal_length

    def init(self):
        super().init()  # Call parent
        self._init_camera()

    def _init_camera(self):
        self.camera = CaptureDevice(self.cam_path)

    def _deinit_camera(self):
        if self.camera:
            self.camera.close()
        self.camera = None

    def __del__(self):
        self._deinit_camera()

    def capture_image(self):
        """
        Capture an image
        :return: PIL image object of the captured image in Luminosity color scale
        """
        image_bytes = self.camera.capture(*self.cam_image_size)
        return Image.frombytes('L', self.cam_image_size, image_bytes)

    # TODO: Cancel out lens distortions


class FileCamera(CameraBase):
    """ Debug class for cameras, returns an image instead of querying a camera"""
    def __init__(self, file_path, focal_length):
        super().__init__()
        self.file_name = file_path
        self.image = None
        self.focal_length = focal_length

    def init(self):
        super().init()
        self.image = Image.open(self.file_name)
        self.image = self.image.convert('L')
        self.cam_image_size = self.image.size

    def capture_image(self):
        return self.image
