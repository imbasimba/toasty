from libc.math cimport sin, cos, atan2, hypot
import numpy as np

cimport cython

cimport numpy as np

DTYPE = np.float64
ctypedef np.float64_t DTYPE_t

cdef struct Point:
    DTYPE_t x
    DTYPE_t y

cdef void _mid(Point a, Point b, Point *cen):
    """
    Return the midpoint of two points on a great circle arc

    Parameters
    ----------
    a, b: Point
    Two lon, lat pairs, in radians
    """
    cdef DTYPE_t dl, bx, by, b3, l3, outb, outl
    cdef Point out

    dl = b.x - a.x
    bx = cos(b.y) * cos(dl)
    by = cos(b.y) * sin(dl)
    outb = atan2(sin(a.y) + sin(b.y), hypot(cos(a.y) + bx, by))
    outl = a.x + atan2(by, cos(a.y) + bx)
    cen.x = outl
    cen.y = outb


def mid(a, b):
    cdef Point l = Point(a[0], a[1]), m = Point(b[0], b[1]), n
    _mid(l, m, &n)
    return n.x, n.y


@cython.boundscheck(False)
cdef void _subsample(Point ul, Point ur, Point lr, Point ll,
                    DTYPE_t [:, :] x,
                    DTYPE_t [:, :] y,
                    int increasing):
    """
    Given the corners of a toast tile, return the
    sky locations of a subsampled version

    Parameters
    ----------
    ul, ur, lr, ll: Points
        The (lon, lat) coordinates of the four corners of the toast
        tile to subdivide. In radians
    x, y : arrays
        The arrays in which to hold the subdivided locations
    increasing : int
         If 1, the shared edge of the toast tile's two sub-HTM
         trixels increases from left to right. Otherwise, it
         decreases from left to right
    n : int
        The number of pixels in x and y
    """
    cdef Point le, up, lo, ri, cen
    cdef int n = x.shape[0]
    cdef int n2 = n // 2

    _mid(ul, ur, &up)
    _mid(ul, ll, &le)
    _mid(ur, lr, &ri)
    _mid(ll, lr, &lo)

    if increasing:
        _mid(ll, ur, &cen)
    else:
        _mid(ul, lr, &cen)

    if n == 1:
        x[0] = cen.x
        y[0] = cen.y
        return

    _subsample(ul, up, cen, le, x[:n2, :n2], y[:n2, :n2], increasing)
    _subsample(up, ur, ri, cen, x[:n2, n2:], y[:n2, n2:], increasing)
    _subsample(le, cen, lo, ll, x[n2:, :n2], y[n2:, :n2], increasing)
    _subsample(cen, ri, lr, lo, x[n2:, n2:], y[n2:, n2:], increasing)


def subsample(ul, ur, lr, ll, npix, increasing):
    """Subdivide a toast quad, and return the pixel locations

    Parameters
    ----------
    ul, ur, lr, ll : array-like
        Two-element arrays giving the (lon, lat) position of each corner
        of the toast tile, in radians
    npix: int
        The pixel resolution of the subsampled image. Must be a power of 2
    increasing: bool
        Whether the two HTM trixels that define this toast tile are joined
        along the diagonal which increases from left to right


    Returns
    --------
    Two arrays, giving the lon/lat of each point in the subsampled image
    """
    if len(ul) != 2 or len(ur) != 2 or len(lr) != 2 or len(ll) != 2:
        raise ValueError("Toast corners must be two-element arrays")
    if 2 ** int(np.log2(npix)) != npix:
        raise ValueError("npix must be a power of 2: %i" % npix)

    cdef Point _ul, _ur, _lr, _ll
    cdef int _inc = (1 if increasing else 0)

    x = np.zeros((npix, npix), dtype=DTYPE)
    y = np.zeros((npix, npix), dtype=DTYPE)

    _ul = Point(DTYPE(ul[0]), DTYPE(ul[1]))
    _ur = Point(DTYPE(ur[0]), DTYPE(ur[1]))
    _lr = Point(DTYPE(lr[0]), DTYPE(lr[1]))
    _ll = Point(DTYPE(ll[0]), DTYPE(ll[1]))
    _subsample(_ul, _ur, _lr, _ll, x, y, increasing)
    return x, y


@cython.boundscheck(False)
@cython.wraparound(False)
cdef void _order_pair_1d(np.ndarray[DTYPE_t, ndim=1] arr, int i, int j):
    """
    Swap two elements of a 1D array to ensure that that arr[i] < arr[j].
    """
    cdef DTYPE_t z

    if arr[i] > arr[j]:
        z = arr[j]
        arr[j] = arr[i]
        arr[i] = z


DEF TWOPI = 6.28318530717958623200


@cython.boundscheck(False)
@cython.wraparound(False)
cdef bint _tile_intersects_latlon_bbox(
    np.ndarray[DTYPE_t, ndim=2] corner_lonlats,
    DTYPE_t bbox_lon_min,
    DTYPE_t bbox_lon_max,
    DTYPE_t bbox_lat_min,
    DTYPE_t bbox_lat_max
):
    """
    Return true if a tile seems to intersect a bounding box.

    This function is implemented in Cython because the np.min/max calls turn out
    to become relatively expensive when this function is called millions of times.
    """

    # Latitudes are easy -- no wrapping.

    cdef DTYPE_t tile_lat_min = corner_lonlats[0,1]
    cdef DTYPE_t tile_lat_max = tile_lat_min
    cdef DTYPE_t x = 0

    for i in range(1, 4):
        x = corner_lonlats[i, 1]
        if x < tile_lat_min:
            tile_lat_min = x
        if x > tile_lat_max:
            tile_lat_max = x

    if bbox_lat_min > tile_lat_max:
        return False
    if bbox_lat_max < tile_lat_min:
        return False

    # Can't reject based on latitudes. Longitudes are trickier.
    #
    # Step 1: If we hit one of the poles, longitudes become
    # ~meaningless, so all we can really do (in our simplistic approach
    # here) is accept the tile. We compare to ~(pi - 1e-8) here to
    # account for inevitable roundoff. Note that if we don't apply the
    # lat-bounds filter first, every single chunk will accept tiles at
    # the poles, even if it's right on the equator.

    if tile_lat_max > 1.5707963 or tile_lat_min < -1.5707963:
        return True

    # Step 2: get good a coverage range for tile longitudes. Some tiles
    # span a full pi in longitude, and sometimes the "corners"
    # longitudes span all sorts of values from -2pi to 2pi. We need to
    # shuffle them around to get self-consistent values.
    #
    # We do this by sorting the longitudes and adjusting by 2pi until
    # the difference between the maximum and minimum longitudes is
    # less than or equal to pi (which we know a priori is as big as
    # it should ever be). In particular, if the condition isn't met,
    # we add 2pi to the smallest longitude and try again.

    cdef np.ndarray[DTYPE_t, ndim=1] lons = corner_lonlats[:, 0]

    # This "sorting network" always delivers a sorted list:

    _order_pair_1d(lons, 0, 2)
    _order_pair_1d(lons, 1, 3)
    _order_pair_1d(lons, 0, 1)
    _order_pair_1d(lons, 2, 3)
    _order_pair_1d(lons, 1, 2)

    # Now shuffle. After adjusting the lowest longitude, we
    # re-insert it into the list in the appropriate spot.

    cdef DTYPE_t updated_lon = 0

    while lons[3] - lons[0] > np.pi:
        updated_lon = lons[0] + TWOPI

        for i in range(3):
            if lons[i + 1] > updated_lon:
                lons[i] = updated_lon
                break

            # Shift the current element to the left since the
            # new longitude is going to be placed somewhere
            # ahead of it.
            lons[i] = lons[i + 1]
        else:
            # This code is invoked if we don't break out of
            # the loop -- i.e., if updated_lon is the new
            # maximum value.
            lons[3] = updated_lon

    cdef DTYPE_t tile_lon_min = lons[0]
    cdef DTYPE_t tile_lon_max = lons[3]

    # Step 3: Now, shuffle the tile longitudes so that the left edge of the
    # tile is to the right of the left edge of the bounding box. We might drag it
    # to the left (in chunks of 360 degrees) if it's really far to the
    # right.

    while tile_lon_min < bbox_lon_min:
        tile_lon_min += TWOPI
        tile_lon_max += TWOPI

    while tile_lon_min - bbox_lon_min > TWOPI:
        tile_lon_min -= TWOPI
        tile_lon_max -= TWOPI

    # Step 4. Now we can test. In this configuration, if the left edge of
    # the tile is not clear of the right edge of the bounding box, there's an
    # overlap.

    if tile_lon_min < bbox_lon_max:
        return True

    # But we must also check for wraparound! If we imagine that the image is
    # duplicated at its current position + 2pi radians, if the right edge of
    # the tile passes the "next" left edge of the bounding box, we also overlap.

    if tile_lon_max > bbox_lon_min + TWOPI:
        return True

    # Otherwise, there is no overlap.

    return False

def tile_intersects_latlon_bbox(corner_lonlats, bbox_lon_min, bbox_lon_max, bbox_lat_min, bbox_lat_max):
    return _tile_intersects_latlon_bbox(corner_lonlats, bbox_lon_min, bbox_lon_max, bbox_lat_min, bbox_lat_max)
