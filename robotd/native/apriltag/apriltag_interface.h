#include "apriltag.h"
#include "tag36h11.h"

void apriltag_init(
   apriltag_detector_t* td,
   float decimate,
   float sigma,
   int refine_edges,
   int refine_decode,
   int refine_pose
  );


struct apriltag_detection *zarray_get_detection(const zarray_t *za, int idx);

void destroy_detection(struct apriltag_detection *p);
