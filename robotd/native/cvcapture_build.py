import cffi
from pathlib import Path

base = Path(__file__).parent

ffibuilder = cffi.FFI()

CVCAPTURE_DECLS = """
    int cvcapture(void* context, void* buffer, size_t width, size_t height);
    void* cvopen(const char* path);
    void cvclose(void* context);
"""

ffibuilder.set_source(
    "robotd.native._cvcapture",
    CVCAPTURE_DECLS, sources=[
        str(base / 'cvcapture.cpp'),
    ], libraries=[
        'opencv_core',
        'opencv_highgui',
        'opencv_imgproc',
    ],
)

ffibuilder.cdef(CVCAPTURE_DECLS)

if __name__ == '__main__':
    ffibuilder.compile(verbose=True)
