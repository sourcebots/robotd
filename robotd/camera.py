from pathlib import Path

import time
from .devices_base import Board

from sb_vision import Camera as VisionCamera, Vision, Token

class Camera(Board):
    """A camera."""

    lookup_keys = {
        'subsystem': 'video4linux',
    }

    DISTANCE_MODEL = 'c270'
    IMAGE_SIZE = (1280, 720)

    def __init__(self, node, camera=None):
        super().__init__(node)
        self.camera = camera

    @classmethod
    def name(cls, node):
        # Get device name
        return Path(node['DEVNAME']).stem

    def start(self):
        if not self.camera:
            self.camera = VisionCamera(
                int(self.node['MINOR']),
                self.IMAGE_SIZE,
                self.DISTANCE_MODEL,
            )
        self.vision = Vision(self.camera)

        self._status = {
            'snapshot_timestamp': None,
            'markers': [],
        }

    def _update_status(self, markers):
        self._status = {
            'snapshot_timestamp': time.time(),
            'markers': markers,
        }

    @staticmethod
    def _serialise_marker(marker: Token):
        d = marker.__dict__
        d['homography_matrix'] = marker.homography_matrix.tolist()
        d['cartesian'] = marker.cartesian.tolist()
        return d

    def status(self):
        return self._status

    def command(self, cmd):
        """Run user-provided command."""
        if cmd.get('see', False):
            self._update_status(markers=[
                self._serialise_marker(x)
                for x in self.vision.snapshot()
            ])
            # rely on the status being sent back to the requesting connection
            # by the ``BoardRunner``.
