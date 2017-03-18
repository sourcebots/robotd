#!/usr/bin/env python3
from cffi import FFI
import glob
from pathlib import Path

ffi = FFI()


base = Path(__file__).parent
source_files = base.glob("contrib/april/**/*.c")

with (base / 'apriltag_interface.c').open('r') as apriltag_interface:
    ffi.set_source(
        "robotd.native.apriltag._apriltag",
        apriltag_interface.read(),
        include_dirs=[
            str(base),
            str(base / 'contrib' / 'april'),
            str(base / 'contrib' / 'april' / 'common'),
        ],
        sources=[str(x) for x in source_files],
        extra_compile_args=['-std=c11'],
    )

# Define the functions to be used.

with (base / 'apriltag_cdefs.h').open('r') as apriltag_interface_h:
    ffi.cdef(apriltag_interface_h.read())

if __name__ == "__main__":
    ffi.compile(verbose=True)
