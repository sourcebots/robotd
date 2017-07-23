#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <stdbool.h>
#include <string>

extern "C" {
    void* cvopen(const char* path);
    void cvclose(void* context);
    int cvcapture(void* context, void* buffer, size_t width, size_t height);
}

#include "opencv2/opencv.hpp"

void* cvopen(const char* path) {
    cv::VideoCapture* context;
    if (path) {
        context = new cv::VideoCapture(std::string(path));
    } else {
        context = new cv::VideoCapture(0);
    }
    return reinterpret_cast<void*>(context);
}

void cvclose(void* context) {
    cv::VideoCapture* cap = reinterpret_cast<cv::VideoCapture*>(context);
    delete cap;
}

static void describe_image(const char* stage, const cv::Mat& mat) {
    fprintf(stderr, "%s: %d x %d\n", stage, mat.size().width, mat.size().height);
}

int cvcapture(void* context, void* buffer, size_t width, size_t height) {
    cv::VideoCapture* cap = reinterpret_cast<cv::VideoCapture*>(context);
    cap->set(CV_CAP_PROP_FRAME_WIDTH, width);
    cap->set(CV_CAP_PROP_FRAME_HEIGHT, height);
    cap->set(CV_CAP_PROP_FOURCC, CV_FOURCC('B', 'G', 'R', 3));

    if (cap->get(CV_CAP_PROP_FRAME_WIDTH) != (double)width) {
        fprintf(stderr, "Incorrect width set on cap: %f\n", cap->get(CV_CAP_PROP_FRAME_WIDTH));
        return 0;
    }

    if (cap->get(CV_CAP_PROP_FRAME_HEIGHT) != (double)height) {
        fprintf(stderr, "Incorrect height set on cap: %f\n", cap->get(CV_CAP_PROP_FRAME_HEIGHT));
        return 0;
    }

    cv::Mat colour_image, greyscale_image, denoised_image;

    if (!cap->isOpened()) {
        return 0;
    }

    (*cap) >> colour_image;
    describe_image("colour", colour_image);
    cv::cvtColor(colour_image, greyscale_image, cv::COLOR_BGR2GRAY);
    describe_image("greyscale", greyscale_image);
    cv::medianBlur(greyscale_image, denoised_image, 3);
    describe_image("denoised", denoised_image);
    if (!denoised_image.isContinuous()) {
        return 0;
    }
    int died_horribly = 0;
    if (denoised_image.size().width != width) {
        fprintf(
            stderr,
            "Width mismatch: %d expected, %d actual\n",
            width,
            denoised_image.size().width
        );
        died_horribly = 1;
    }
    if (denoised_image.size().height != height) {
        fprintf(
            stderr,
            "Height mismatch: %d expected, %d actual\n",
            height,
            denoised_image.size().height
        );
        died_horribly = 1;
    }
    if (died_horribly) {
        return 0;
    }
    memcpy(
        buffer,
        denoised_image.ptr(),
        width * height
    );
    return 1;
}
