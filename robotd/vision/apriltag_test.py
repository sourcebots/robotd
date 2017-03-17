#!/usr/bin/env/ python2

import pygame.camera
from _apriltag import lib


DEVICE = '/dev/video0'
SIZE = (1240, 720)

detector = lib.apriltag_detector_create()
try:
    # apriltag_detector_t* td,
    # float decimate,
    #   default: 1.0, "Decimate input image by this factor"
    # float sigma,
    #   default: 0.0, "Apply low-pass blur to input; negative sharpens"
    # int refine_edges,
    #   default: 1, "Spend more time trying to align edges of tags"
    # int refine_decode,
    #   default: 0, "Spend more time trying to decode tags"
    # int refine_pose
    #   default: 0, "Spend more time trying to find the position of the tag"
    lib.apriltag_init(detector, 1.0, 0.0, 1, 0, 0)


    pygame.camera.init()
    camera = pygame.camera.Camera(DEVICE, SIZE)
    camera.start()
    while True:
        img = camera.get_image()
        pygame.surfarray.pixels2d()
        print(img)
    camera.stop()

    # # Take a webcam shot
    # import cv2
    # # initialize the camera
    # cap = cv2.VideoCapture(0)   # 0 -> index of camera
    # #set the width and height, and UNSUCCESSFULLY set the exposure time
    # cap.set(3,1240)
    # cap.set(4,720)
    # start_time = time.time()
    # count = 0
    # while True:
    #     s, img = cap.read()
    #     if s:    # frame captured without any errors
    #         # Convert to grayscale
    #         gray_image = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    #         # get the data into a numpy buffer
    #         np_buff = gray_image.ctypes.data
    #         gray_image = numpy.transpose(gray_image)
    #         # cast it to cffi
    #         image_buff = ffi.cast("uint8_t*", np_buff)
    #
    #         image = ffi.new("image_u8_t*")
    #         image.width, image.height = gray_image.shape
    #         image.stride = image.width
    #         image.buf = image_buff
    #         results = lib.apriltag_detector_detect(detector, image)
    #         count += 1
    #         print("I can see {} markers".format(results.size))

finally:
    # Always destroy the detector
    lib.apriltag_detector_destroy(detector)
