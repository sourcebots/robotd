import threading

from robotd.native import _cvcapture

class CaptureDevice(object):
    def __init__(self, path=None):
        if path is not None:
            argument_c = _cvcapture.ffi.new(
                'char[]',
                path.encode('utf-8'),
            )
        else:
            argument_c = _cvcapture.ffi.NULL
        self.instance = _cvcapture.lib.cvopen(argument_c)
        self.lock = threading.Lock()

    def capture(self, width, height):
        if self.instance is None:
            raise RuntimeError("capture device is closed")

        capture_buffer = _cvcapture.ffi.new(
            'uint8_t[{}]'.format(width * height),
        )

        with self.lock:
            status = _cvcapture.lib.cvcapture(
                self.instance,
                capture_buffer,
                width,
                height,
            )

        if status == 0:
            raise RuntimeError("cvcapture() failed")

        return bytes(_cvcapture.ffi.buffer(capture_buffer))

    def __enter__(self):
        return self

    def __exit__(self, exc_value, exc_type, exc_traceback):
        self.close()

    def close(self):
        if self.instance is not None:
            with self.lock:
                _cvcapture.lib.cvclose(self.instance)
            self.instance = None

    __del__ = close

def cvcapture(device, width, height):
    capture_buffer = _cvcapture.ffi.new('uint8_t[{}]'.format(width * height))
    print(capture_buffer)

    result = _cvcapture.lib.cvcapture(
        capture_buffer,
        width,
        height,
    )

    if result == 0:
        raise RuntimeError("cvcapture() failed")

    return bytes(_cvcapture.ffi.buffer(capture_buffer))
