#include "apriltag_interface.h"

void apriltag_init(
  apriltag_detector_t* td,
  float decimate,
  float sigma,
  int refine_edges,
  int refine_decode,
  int refine_pose
) {
  apriltag_family_t *tf = tag36h11_create();
  apriltag_detector_add_family(td, tf);
  td->quad_decimate = decimate;
  td->quad_sigma = sigma;
  td->refine_edges = refine_edges;
  td->refine_decode = refine_decode;
  td->refine_pose = refine_pose;
}


struct apriltag_detection *zarray_get_detection(const zarray_t *za, int idx) {
    struct apriltag_detection *detection = malloc(sizeof(apriltag_detection_t));
    zarray_get(za, idx, &detection);
    return detection;
}

void destroy_detection(struct apriltag_detection * p) {
    free(p);
}