import pygame.camera
from PIL import Image

from robotd.vision.camera_base import CameraBase



class Camera(CameraBase):
    def __init__(self, camera_path, proposed_image_size,focal_length):
        super().__init__()
        self.cam_proposed_image_size = proposed_image_size
        self.cam_path = camera_path
        # pygame camera object
        self.camera = None
        # pygame surface object from camera
        self._cam_surface = None
        self.focal_length = focal_length

    def init(self):
        super().init()  # Call parent
        self._init_camera()

    def _init_camera(self):
        pygame.camera.init()
        try:
            self.camera = pygame.camera.Camera(self.cam_path, self.cam_proposed_image_size)
            self.camera.start()
            self.cam_image_size = self.camera.get_size()
        except SystemError as e:
            # Rethrow with extra info
            raise RuntimeError("Error connecting to camera", e)

        self._cam_surface = pygame.Surface(self.cam_image_size)

    def _deinit_camera(self):
        if self.camera:
            self.camera.stop()

    def __del__(self):
        self._deinit_camera()

    def capture_image(self):
        self.camera.get_image(self._cam_surface)
        # Convert the surface to RGB
        img_bytes = pygame.image.tostring(self._cam_surface, "RGB", False)
        img = Image.frombytes('RGB', self.cam_image_size, img_bytes)
        img = img.convert('L')
        img = img.rotate(180)
        return img

    # TODO: Remove lens distortions


class FileCamera(CameraBase):
    """ Debug class for cameras, displays a file"""
    def __init__(self, filepath, focal_length):
        super().__init__()
        self.filename = filepath
        self.image = None
        self.focal_length = focal_length

    def init(self):
        super().init()
        self.image = Image.open(self.filename)
        self.image = self.image.convert('L')
        self.cam_image_size = self.image.size

    def capture_image(self):
        return self.image
