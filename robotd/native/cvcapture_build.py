import cffi
from pathlib import Path

base = Path(__file__).parent

ffibuilder = cffi.FFI()

ffibuilder.set_source("robotd.native._cvcapture", """
    int cvcapture(void* buffer, size_t width, size_t height);
""", sources=[
    base / 'cvcapture.cpp',
], libraries=[
    'opencv_core',
    'opencv_highgui',
    'opencv_imgproc',
])

ffibuilder.cdef("""
    int cvcapture(void* buffer, size_t width, size_t height);
""")

if __name__ == '__main__':
    ffibuilder.compile(verbose=True)
