
class CameraBase:
    def __init__(self):
        self.initialised = False
        self.cam_image_size = None

    def init(self):
        """ Initialise the camera"""
        self.initialised = True

    def get_image_size(self):
        if not self.initialised:
            raise Exception("Must Initialise camera before getting image size")
        return self.cam_image_size

    def capture_image(self):
        """
        :return: PIL Image captured
        """
        pass

