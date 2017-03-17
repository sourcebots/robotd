// Define the detector as empty for simplicity (it isn't actually void.)

typedef void apriltag_detector_t;
typedef void apriltag_family_t;

// zarray, c implementation of java arraylists
// Used for storing detections
struct zarray
{
    size_t el_sz; // size of each element

    int size; // how many elements?
    int alloc; // we've allocated storage for how many elements?
    char *data;
};
typedef struct zarray zarray_t;

// Images, defined as arrays of uint8's
typedef struct image_u8 image_u8_t;
struct image_u8
{
    const int32_t width;
    const int32_t height;
    const int32_t stride;

    uint8_t *buf;
};

// Create an image
image_u8_t *image_u8_create(unsigned int width, unsigned int height);
image_u8_t *image_u8_create_stride(unsigned int width, unsigned int height, unsigned int stride);
void image_u8_destroy(image_u8_t *im);

// Destructor for zarray
void apriltag_detections_destroy(zarray_t *detections);

//  Detector object creation
apriltag_detector_t* apriltag_detector_create(void);

// Detector object destruction
void apriltag_detector_destroy(apriltag_detector_t *td);


// Detector object Initialisation

void apriltag_init(
   apriltag_detector_t* td,
   float decimate,
   float sigma,
   int refine_edges,
   int refine_decode,
   int refine_pose
  );

//Run detection
zarray_t *apriltag_detector_detect(apriltag_detector_t *td, image_u8_t *im_orig);

static inline void zarray_get(const zarray_t *za, int idx, void *p);

static inline void zarray_destroy(zarray_t *za);

/**
 * Defines a matrix structure for holding double-precision values with
 * data in row-major order (i.e. index = row*ncols + col).
 *
 * nrows and ncols are 1-based counts with the exception that a scalar (non-matrix)
 *   is represented with nrows=0 and/or ncols=0.
 */
typedef struct
{
    unsigned int nrows, ncols;
    double data[];
} matd_t;

// Represents the detection of a tag. These are returned to the user
// and must be individually destroyed by the user.
typedef struct apriltag_detection apriltag_detection_t;
struct apriltag_detection
{
    // a pointer for convenience. not freed by apriltag_detection_destroy.
    apriltag_family_t *family;

    // The decoded ID of the tag
    int id;

    // How many error bits were corrected? Note: accepting large numbers of
    // corrected errors leads to greatly increased false positive rates.
    // NOTE: As of this implementation, the detector cannot detect tags with
    // a hamming distance greater than 2.
    int hamming;

    // A measure of the quality of tag localization: measures the
    // average contrast of the pixels around the border of the
    // tag. refine_pose must be enabled, or this field will be zero.
    float goodness;

    // A measure of the quality of the binary decoding process: the
    // average difference between the intensity of a data bit versus
    // the decision threshold. Higher numbers roughly indicate better
    // decodes. This is a reasonable measure of detection accuracy
    // only for very small tags-- not effective for larger tags (where
    // we could have sampled anywhere within a bit cell and still
    // gotten a good detection.)
    float decision_margin;

    // The 3x3 homography matrix describing the projection from an
    // "ideal" tag (with corners at (-1,-1), (1,-1), (1,1), and (-1,
    // 1)) to pixels in the image. This matrix will be freed by
    // apriltag_detection_destroy.
    matd_t *H;

    // The center of the detection in image pixel coordinates.
    double c[2];

    // The corners of the tag in image pixel coordinates. These always
    // wrap counter-clock wise around the tag.
    double p[4][2];
};

struct apriltag_detection *zarray_get_detection(const zarray_t *za, int idx);

void destroy_detection(apriltag_detection_t* p);

