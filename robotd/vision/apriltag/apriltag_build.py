#!/usr/bin/env python3
from cffi import FFI
import glob
from pathlib import Path

ffi = FFI()


source_files = Path("..").glob("contrib/april/**/*.c")

with open('apriltag_interface.c', 'r') as apriltag_interface:
    ffi.set_source("_apriltag",
                   apriltag_interface.read(),
                   include_dirs=["../contrib/april", "../contrib/april/common"],
                   sources=source_files
                   )

# Define the functions to be used.

with open('apriltag_cdefs.h', 'r') as apriltag_interface_h:
    ffi.cdef(apriltag_interface_h.read())

if __name__ == "__main__":
    ffi.compile(verbose=True)
