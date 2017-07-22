from robotd.native import _cvcapture

def cvcapture(width, height):
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
