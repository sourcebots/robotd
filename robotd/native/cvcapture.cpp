#include <stdlib.h>
#include <string.h>
#include <stdbool.h>

extern "C" {
    int cvcapture(void* buffer, size_t width, size_t height);
}

#include "opencv2/opencv.hpp"

static cv::VideoCapture* s_instance = NULL;

static cv::VideoCapture* shared_instance() {
    if (s_instance == NULL) {
        s_instance = new cv::VideoCapture(0);
        s_instance->set(CV_CAP_PROP_FOURCC, CV_FOURCC('B', 'G', 'R', 3));
    }
    return s_instance;
}

int cvcapture(void* buffer, size_t width, size_t height) {
    cv::VideoCapture* cap = shared_instance();
    cap->set(CV_CAP_PROP_FRAME_WIDTH, width);
    cap->set(CV_CAP_PROP_FRAME_HEIGHT, height);

    cv::Mat colour_image, greyscale_image, denoised_image;

    if (!cap->isOpened()) {
        return 0;
    }

    (*cap) >> colour_image;
    cv::cvtColor(colour_image, greyscale_image, cv::COLOR_BGR2GRAY);
    cv::medianBlur(greyscale_image, denoised_image, 3);
    memcpy(
        buffer,
        denoised_image.ptr(),
        width * height
    );
    return 1;
}
