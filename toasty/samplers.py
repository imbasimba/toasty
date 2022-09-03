# -*- mode: python; coding: utf-8 -*-
# Copyright 2013-2022 Chris Beaumont and the AAS WorldWide Telescope project
# Licensed under the MIT License.

"""
“Sampler” functions that fetch image data as a function of sky coordinates.

The Sampler Protocol
--------------------

A sampler is a callable object that obeys the following signature: ``func(lon,
lat) -> data``, where *lon* and *lat* are 2D numpy arrays of spherical
coordinates measured in radians, and the returned *data* array is a numpy
array of at least two dimensions whose first two axes have the same shape as
*lon* and *lat*. The *data* array gives the map values sampled at the
corresponding coordinates. Its additional dimensions can be used to encode
color information: one standard is for *data* to have a dtype of
``np.uint8`` and a shape of ``(ny, nx, 3)``, where the final axis samples
RGB colors.

"""
from __future__ import absolute_import, division, print_function

__all__ = """
ChunkedPlateCarreeSampler
plate_carree_sampler
plate_carree_galactic_sampler
plate_carree_ecliptic_sampler
plate_carree_planet_sampler
plate_carree_planet_zeroleft_sampler
plate_carree_zeroright_sampler
healpix_fits_file_sampler
healpix_sampler
WcsSampler
""".split()

import numpy as np

TWOPI = 2 * np.pi
HALFPI = 0.5 * np.pi


def healpix_sampler(data, nest=False, coord="C", interpolation="nearest"):
    """Create a sampler for HEALPix image data.

    Parameters
    ----------
    data : array
        The HEALPix data
    nest : bool (default: False)
        Whether the data is ordered in the nested HEALPix style
    coord : 'C' | 'G'
        Whether the image is in Celestial (C) or Galactic (G) coordinates
    interpolation : 'nearest' | 'bilinear'
        What interpolation scheme to use.

        WARNING: bilinear uses healpy's get_interp_val, which seems prone to segfaults

    Returns
    -------
    A function that samples the HEALPix data; the call signature is
    ``vec2pix(lon, lat) -> data``, where the inputs and output are 2D arrays
    and *lon* and *lat* are in radians.

    """
    from healpy import ang2pix, get_interp_val, npix2nside
    from astropy.coordinates import Galactic, ICRS
    import astropy.units as u

    interp_opts = ["nearest", "bilinear"]
    if interpolation not in interp_opts:
        raise ValueError(
            "Invalid interpolation %s. Must be one of %s" % (interpolation, interp_opts)
        )
    if coord.upper() not in "CG":
        raise ValueError("Invalid coord %s. Must be 'C' or 'G'" % coord)

    galactic = coord.upper() == "G"
    interp = interpolation == "bilinear"
    nside = npix2nside(data.size)

    def vec2pix(l, b):
        if galactic:
            f = ICRS(l * u.rad, b * u.rad)
            g = f.transform_to(Galactic())
            l, b = g.l.rad, g.b.rad

        theta = np.pi / 2 - b
        phi = l

        if interp:
            return get_interp_val(data, theta, phi, nest=nest)

        return data[ang2pix(nside, theta, phi, nest=nest)]

    return vec2pix


def _find_healpix_extension_index(pth):
    """Find the first HEALPIX extension in a FITS file and return the extension
    number. Raises IndexError if none is found.

    """
    for i, hdu in enumerate(pth):
        if hdu.data is None:
            continue

        if hdu.header.get("PIXTYPE") != "HEALPIX":
            continue

        return i
    else:
        raise IndexError("No HEALPIX extensions found in %s" % pth.filename())


def healpix_fits_file_sampler(
    path, extension=None, interpolation="nearest", force_galactic=False
):
    """Create a sampler for HEALPix data read from a FITS file.

    Parameters
    ----------
    path : string
        The path to the FITS file.
    extension : integer or None (default: None)
        Which extension in the FITS file to read. If not specified, the first
        extension with PIXTYPE = "HEALPIX" will be used.
    interpolation : 'nearest' | 'bilinear'
        What interpolation scheme to use.

        WARNING: bilinear uses healpy's get_interp_val, which seems prone to segfaults
    force_galactic : bool
        If true, force use of Galactic coordinate system, regardless of
        what the headers say.

    Returns
    -------
    A function that samples the HEALPix image; the call signature is
    ``vec2pix(lon, lat) -> data``, where the inputs and output are 2D arrays
    and *lon* and *lat* are in radians.

    """
    from astropy.io import fits

    with fits.open(path) as f:
        if extension is None:
            extension = _find_healpix_extension_index(f)

        data, hdr = f[extension].data, f[extension].header

        # grab the first healpix parameter and convert to native endianness if
        # needed.
        data = data[data.dtype.names[0]]
        if data.dtype.byteorder not in "=|":
            data = data.byteswap().newbyteorder()

        nest = hdr.get("ORDERING") == "NESTED"
        coord = hdr.get("COORDSYS", "C")

    if force_galactic:
        coord = "G"

    return healpix_sampler(data, nest, coord, interpolation)


def plate_carree_sampler(data):
    """Create a sampler function for all-sky data in a “plate carrée” projection.

    In this projection, the X and Y axes of the image correspond to the
    longitude and latitude spherical coordinates, respectively. Both axes map
    linearly, the X axis to the longitude range [2pi, 0] (i.e., longitude
    increases to the left), and the Y axis to the latitude range [pi/2,
    -pi/2]. Therefore the point with lat = lon = 0 corresponds to the image
    center and ``data[0,0]`` is the pixel touching lat = pi/2, lon=pi, one of
    a row adjacent to the North Pole. Typically the image is twice as wide as
    it is tall.

    Parameters
    ----------
    data : array-like, at least 2D
        The map to sample in plate carrée projection.

    Returns
    -------
    A function that samples the image; the call signature is
    ``vec2pix(lon, lat) -> data``, where the inputs and output are 2D arrays
    and *lon* and *lat* are in radians.

    """
    data = np.asarray(data)
    ny, nx = data.shape[:2]

    dx = nx / TWOPI  # pixels per radian in the X direction
    dy = ny / np.pi  # ditto, for the Y direction
    lon0 = np.pi - 0.5 / dx  # longitudes of the centers of the pixels with ix = 0
    lat0 = HALFPI - 0.5 / dy  # latitudes of the centers of the pixels with iy = 0

    def vec2pix(lon, lat):
        lon = (lon + np.pi) % TWOPI - np.pi  # ensure in range [-pi, pi]
        ix = (lon0 - lon) * dx
        ix = np.round(ix).astype(int)
        ix = np.clip(ix, 0, nx - 1)

        iy = (lat0 - lat) * dy  # *assume* in range [-pi/2, pi/2]
        iy = np.round(iy).astype(int)
        iy = np.clip(iy, 0, ny - 1)

        return data[iy, ix]

    return vec2pix


def plate_carree_galactic_sampler(data):
    """
    Create a sampler function for all-sky data in a “plate carrée” projection
    using Galactic coordinates.

    Parameters
    ----------
    data : array-like, at least 2D
        The map to sample in plate carrée projection.

    Returns
    -------
    A function that samples the image. The call signature is
    ``sampler(lon, lat) -> data``, where the inputs and output are 2D arrays and
    *lon* and *lat* are in radians.

    """
    from astropy.coordinates import Galactic, ICRS
    import astropy.units as u

    data = np.asarray(data)
    ny, nx = data.shape[:2]

    dx = nx / TWOPI  # pixels per radian in the X direction
    dy = ny / np.pi  # ditto, for the Y direction
    lon0 = np.pi - 0.5 / dx  # longitudes of the centers of the pixels with ix = 0
    lat0 = HALFPI - 0.5 / dy  # latitudes of the centers of the pixels with iy = 0

    def vec2pix(lon, lat):
        gal = ICRS(lon * u.rad, lat * u.rad).transform_to(Galactic)
        lon, lat = gal.l.rad, gal.b.rad

        lon = (lon + np.pi) % TWOPI - np.pi  # ensure in range [-pi, pi]
        ix = (lon0 - lon) * dx
        ix = np.round(ix).astype(int)
        ix = np.clip(ix, 0, nx - 1)

        iy = (lat0 - lat) * dy  # *assume* in range [-pi/2, pi/2]
        iy = np.round(iy).astype(int)
        iy = np.clip(iy, 0, ny - 1)

        return data[iy, ix]

    return vec2pix


def plate_carree_ecliptic_sampler(data):
    """
    Create a sampler function for all-sky data in a “plate carrée” projection
    using ecliptic coordinates.

    Parameters
    ----------
    data : array-like, at least 2D
        The map to sample in plate carrée projection.

    Returns
    -------
    A function that samples the image. The call signature is
    ``sampler(lon, lat) -> data``, where the inputs and output are 2D arrays and
    *lon* and *lat* are in radians.

    """
    from astropy.coordinates import BarycentricTrueEcliptic as Ecliptic, ICRS
    import astropy.units as u

    data = np.asarray(data)
    ny, nx = data.shape[:2]

    dx = nx / TWOPI  # pixels per radian in the X direction
    dy = ny / np.pi  # ditto, for the Y direction
    lon0 = np.pi - 0.5 / dx  # longitudes of the centers of the pixels with ix = 0
    lat0 = HALFPI - 0.5 / dy  # latitudes of the centers of the pixels with iy = 0

    def vec2pix(lon, lat):
        ecl = ICRS(lon * u.rad, lat * u.rad).transform_to(Ecliptic)
        lon, lat = ecl.lon.rad, ecl.lat.rad
        lon = lon % TWOPI - np.pi  # ensure in range [-pi, pi]

        ix = (lon0 - lon) * dx
        ix = np.round(ix).astype(int)
        ix = np.clip(ix, 0, nx - 1)

        iy = (lat0 - lat) * dy  # *assume* in range [-pi/2, pi/2]
        iy = np.round(iy).astype(int)
        iy = np.clip(iy, 0, ny - 1)

        return data[iy, ix]

    return vec2pix


def plate_carree_planet_sampler(data):
    """
    Create a sampler function for planetary data in a “plate carrée” projection.

    This is the same as :func:`plate_carree_sampler`, except that the X axis
    is mirrored: longitude increases to the right. This is generally what is
    desired for planetary surface maps (looking at a sphere from the outside)
    instead of sky maps (looking at a sphere from the inside).

    Parameters
    ----------
    data : array-like, at least 2D
        The map to sample in plate carrée projection.

    Returns
    -------
    A function that samples the image; the call signature is
    ``vec2pix(lon, lat) -> data``, where the inputs and output are 2D arrays
    and *lon* and *lat* are in radians.
    """

    data = np.asarray(data)
    ny, nx = data.shape[:2]

    dx = nx / TWOPI  # pixels per radian in the X direction
    dy = ny / np.pi  # ditto, for the Y direction
    lon0 = -np.pi + 0.5 / dx  # longitudes of the centers of the pixels with ix = 0
    lat0 = HALFPI - 0.5 / dy  # latitudes of the centers of the pixels with iy = 0

    def vec2pix(lon, lat):
        lon = (lon + np.pi) % TWOPI - np.pi  # ensure in range [-pi, pi]
        ix = (lon - lon0) * dx
        ix = np.round(ix).astype(int)
        ix = np.clip(ix, 0, nx - 1)

        iy = (lat0 - lat) * dy  # *assume* in range [-pi/2, pi/2]
        iy = np.round(iy).astype(int)
        iy = np.clip(iy, 0, ny - 1)

        return data[iy, ix]

    return vec2pix


def plate_carree_planet_zeroleft_sampler(data):
    """
    Create a sampler function for planetary data in a “plate carrée” projection
    where the ``longitude=0`` line is on the left edge of the image.

    This is the same as :func:`plate_carree_planet_sampler`, except that line of
    zero longitude is at the left edge of the image, not its center. Longitude
    still increases to the right, unlike :func:`plate_carree_sampler` or
    :func:`plate_carree_zeroright_sampler`. Some planetary maps use this
    convention.

    Parameters
    ----------
    data : array-like, at least 2D
        The map to sample in plate carrée projection.

    Returns
    -------
    A function that samples the image; the call signature is
    ``vec2pix(lon, lat) -> data``, where the inputs and output are 2D arrays
    and *lon* and *lat* are in radians.
    """

    data = np.asarray(data)
    ny, nx = data.shape[:2]

    dx = nx / TWOPI  # pixels per radian in the X direction
    dy = ny / np.pi  # ditto, for the Y direction
    lon0 = 0.5 / dx  # longitudes of the centers of the pixels with ix = 0
    lat0 = HALFPI - 0.5 / dy  # latitudes of the centers of the pixels with iy = 0

    def vec2pix(lon, lat):
        lon = lon % TWOPI  # ensure in range [0, 2pi]
        ix = (lon - lon0) * dx
        ix = np.round(ix).astype(int)
        ix = np.clip(ix, 0, nx - 1)

        iy = (lat0 - lat) * dy  # *assume* in range [-pi/2, pi/2]
        iy = np.round(iy).astype(int)
        iy = np.clip(iy, 0, ny - 1)

        return data[iy, ix]

    return vec2pix


def plate_carree_zeroright_sampler(data):
    """
    Create a sampler function for data in a “plate carrée” projection where the
    ``longitude=0`` line is on the right edge of the image.

    This is the same as :func:`plate_carree_sampler`, except that line of zero
    longitude is at the right edge of the image, not its center.

    Parameters
    ----------
    data : array-like, at least 2D
        The map to sample in plate carrée projection.

    Returns
    -------
    A function that samples the image; the call signature is
    ``vec2pix(lon, lat) -> data``, where the inputs and output are 2D arrays
    and *lon* and *lat* are in radians.
    """

    data = np.asarray(data)
    ny, nx = data.shape[:2]

    dx = nx / TWOPI  # pixels per radian in the X direction
    dy = ny / np.pi  # ditto, for the Y direction
    lon0 = TWOPI - 0.5 / dx  # longitudes of the centers of the pixels with ix = 0
    lat0 = HALFPI - 0.5 / dy  # latitudes of the centers of the pixels with iy = 0

    def vec2pix(lon, lat):
        lon = lon % TWOPI  # ensure in range [0, 2pi]
        ix = (lon0 - lon) * dx
        ix = np.round(ix).astype(int)
        ix = np.clip(ix, 0, nx - 1)

        iy = (lat0 - lat) * dy  # *assume* in range [-pi/2, pi/2]
        iy = np.round(iy).astype(int)
        iy = np.clip(iy, 0, ny - 1)

        return data[iy, ix]

    return vec2pix


class WcsSampler(object):
    """Create a sampler for data with a generic WCS specification.

    The sampler returns values in float32, regardless of input data type.

    Parameters
    ----------
    data : array
        The image data.
    wcs : :class:`astropy.wcs.WCS`
        A WCS data structure describing the data.

    Returns
    -------
    A function that samples the data; the call signature is
    ``vec2pix(lon, lat)-> data``, where the inputs and output are 2D arrays
    and *lon* and *lat* are in radians.
    """

    def __init__(self, data, wcs):
        import numpy as np

        self._image = np.float32(data)
        self._wcs = wcs

    def _image_bounds(self):
        """
        Get the bounds of the image.

        Returns ``(lon_min, lon_max, lat_min, lat_max)``, in radians. Latitudes
        should be "unwrapped", so that ``lat_min=30, lat_max=60`` implies that
        the image spans 30 degrees in latitude. ``lat_min=60, lat_max=390`` has
        the same effective bounding values, but represents an image that spans
        330 degrees in longitude.
        """

        # First, we calculate lats and lons in a "coarse" grid spanning the
        # entire image. This is necessary for images that, e.g., traverse the
        # north pole, where the maximum latitude occurs *inside* the image, not
        # at a corner, and not even along an edge.

        D2R = np.pi / 180
        N_COARSE = 32
        naxis2, naxis1 = self._image.shape
        coarse_pix = np.empty((N_COARSE, N_COARSE, 2))
        coarse_idx1 = np.linspace(0.5, naxis1 + 0.5, N_COARSE)
        coarse_idx2 = np.linspace(0.5, naxis2 + 0.5, N_COARSE)
        coarse_pix[..., 0] = coarse_idx1.reshape((-1, 1))
        coarse_pix[..., 1] = coarse_idx2.reshape((1, -1))

        coarse_world = self._wcs.wcs_pix2world(coarse_pix.reshape((-1, 2)), 1).reshape(
            (N_COARSE, N_COARSE, 2)
        )

        # It's really important that our bounds are precise, in the sense that
        # every piece of every pixel of the image is contained within them. To
        # get this precision, we'll identify the extreme values on our coarse
        # grid and then resample at pixel resolution. Unless the output
        # pixelization is significantly oversampling the input image, this
        # should yield bounds that are definitionally good enough to make sure
        # that we cover every tile that we should.

        # Latitudes don't wrap, but latitude extrema can happen in the middle of
        # the image (e.g. if it contains the north pole). So we need to refine
        # in a 2D search across the entire coarse grid.

        coarse_lat = coarse_world[..., 1]

        def refine_lat(arg_op):
            """
            `arg_op` is something like `np.argmax()`: an extreme-value finder.
            """
            e1, e2 = np.unravel_index(arg_op(coarse_lat), coarse_lat.shape)

            # Construct a sub-grid around the extreme-value point. We know that
            # the edges of `coarse_pix` correspond exactly to the edges of the
            # image, so we don't have to go beyond them if the maximum lies on
            # an edge.
            #
            # First, compute indices into `coarse_pix`.

            lo1 = max(e1 - 1, 0)
            hi1 = min(e1 + 1, coarse_lat.shape[0] - 1)
            lo2 = max(e2 - 1, 0)
            hi2 = min(e2 + 1, coarse_lat.shape[1] - 1)

            # Now figure out how many samples to compute in our refined grid.
            # We want to sample essentially every pixel.

            n1 = max(int(np.ceil(coarse_idx1[hi1] - coarse_idx1[lo1])), 1)
            n2 = max(int(np.ceil(coarse_idx2[hi2] - coarse_idx2[lo2])), 1)

            # Generate that grid.

            refined_pix = np.empty((n1, n2, 2))
            refined_idx1 = np.linspace(coarse_idx1[lo1], coarse_idx1[hi1], n1)
            refined_idx2 = np.linspace(coarse_idx2[lo2], coarse_idx2[hi2], n2)
            refined_pix[..., 0] = refined_idx1.reshape((-1, 1))
            refined_pix[..., 1] = refined_idx2.reshape((1, -1))

            # Compute the refined world grid.

            refined_world = self._wcs.wcs_pix2world(
                refined_pix.reshape((-1, 2)), 1
            ).reshape((n1, n2, 2))

            # Find the *real* extreme value and convert to radians

            refined_grid = refined_world[..., 1].flatten()
            return refined_grid[arg_op(refined_grid)] * D2R

        lat_min = refine_lat(np.argmin)
        lat_max = refine_lat(np.argmax)

        # Longitudes are annoying since we need to make sure they're unwrapped.
        # On the other hand, I can't think of a non-pathological way in which an
        # image's maximum longitude would occur anywhere other than its edge.
        # Which is good, since I don't think "unwrapping" in 2D is feasible:
        # that's why complex functions have branch cuts and such. To avoid all
        # that, we search for the extreme values only along the edge of the
        # image, after unwrapping the coordinates into a 1D array.

        coarse_lon = coarse_world[..., 0]

        nm = N_COARSE - 1
        coarse_edge_lons = np.empty(4 * nm + 1)
        coarse_edge_lons[0:nm] = coarse_lon[:nm, 0]
        coarse_edge_lons[nm : 2 * nm] = coarse_lon[nm, :nm]
        coarse_edge_lons[2 * nm : 3 * nm] = coarse_lon[-1:0:-1, nm]
        coarse_edge_lons[3 * nm :] = coarse_lon[0, -1::-1]

        deltas = np.zeros(coarse_edge_lons.shape, dtype=int)

        for i in range(1, coarse_edge_lons.size):
            v0 = coarse_edge_lons[i - 1]
            v1 = coarse_edge_lons[i]
            d = 0

            while v1 - v0 > 180:
                v1 -= 360
                d -= 1

            while v0 - v1 > 180:
                v1 += 360
                d += 1

            coarse_edge_lons[i] = v1
            deltas[i] = d

        def refine_lon(arg_op):
            e = arg_op(coarse_edge_lons)

            if e < nm:
                # "top" edge (thinking of array as [lon, lat] ~ [x, y])
                lo = max(e - 1, 0)
                hi = min(e + 1, nm)
                n = max(int(np.ceil(coarse_idx1[hi] - coarse_idx1[lo])), 1)
                refined_idx1 = np.linspace(coarse_idx1[lo], coarse_idx1[hi], n)
                refined_idx2 = np.zeros(n) + coarse_idx2[0]
            elif e < 2 * nm:
                # "right" edge
                rel = e - nm
                lo = max(rel - 1, 0)
                hi = min(rel + 1, nm)
                n = max(int(np.ceil(coarse_idx2[hi] - coarse_idx2[lo])), 1)
                refined_idx1 = np.zeros(n) + coarse_idx1[nm]
                refined_idx2 = np.linspace(coarse_idx2[lo], coarse_idx2[hi], n)
            elif e < 3 * nm:
                # "bottom" edge, traversed backwards (right-to-left)
                rel = 3 * nm - (1 + e)
                lo = max(rel - 1, 0)
                hi = min(rel + 1, nm)
                n = max(int(np.ceil(coarse_idx1[hi] - coarse_idx1[lo])), 1)
                refined_idx1 = np.linspace(coarse_idx1[lo], coarse_idx1[hi], n)
                refined_idx2 = np.zeros(n) + coarse_idx2[nm]
            else:
                # "left" edge, traversed backwards (bottom-to-top). This "side"
                # has an extra pixel to close back to [0,0].
                rel = 4 * nm - e
                lo = max(rel - 1, 0)
                hi = min(rel + 1, nm)
                n = max(int(np.ceil(coarse_idx2[hi] - coarse_idx2[lo])), 1)
                refined_idx1 = np.zeros(n) + coarse_idx1[0]
                refined_idx2 = np.linspace(coarse_idx2[lo], coarse_idx2[hi], n)

            refined_pix = np.empty((n, 2))
            refined_pix[..., 0] = refined_idx1
            refined_pix[..., 1] = refined_idx2

            # Compute the refined world grid.

            refined_lon = self._wcs.wcs_pix2world(refined_pix, 1)[:, 0]

            # But wait! We need to re-apply whatever delta was involved in the
            # global unwrapping. I'm 95% sure that we won't ever need to
            # re-unwrap here.

            refined_lon += 360 * deltas[e]

            # Convert to radians and we're done.
            return refined_lon[arg_op(refined_lon)] * D2R

        lon_min = refine_lon(np.argmin)
        lon_max = refine_lon(np.argmax)
        return lon_min, lon_max, lat_min, lat_max

    def filter(self):
        """
        Get a TOAST tile-filter function for the specified chunk.

        Returns
        -------
        A callable object, ``filter(tile) -> bool``, suitable for use as a tile
        filter function.
        """
        return _latlon_tile_filter(*self._image_bounds())

    def sampler(self):
        from astropy.coordinates import SkyCoord
        from astropy import units as u

        def vec2pix(lon, lat):
            c = SkyCoord(lon * u.rad, lat * u.rad, frame="icrs")
            idx = self._wcs.world_to_array_index(c)

            # Flag out-of-bounds pixels. Currently (April 2022) world_to_array_index
            # returns a tuple of lists, so we need to array-ify.
            idx = tuple(np.asarray(i) for i in idx)
            bad = (idx[0] < 0) | (idx[0] >= self._image.shape[0])

            for i, i_idx in enumerate(idx[1:]):
                bad |= i_idx < 0
                bad |= i_idx >= self._image.shape[i + 1]  # note that i is off by 1 here

            for i_idx in idx:
                i_idx[bad] = 0

            samp = self._image[idx]

            # We could potentially allow integer values, and utilize the FITS "BLANK" keyword to set the NaN values.
            # However, there are plenty of integer FITS files out there lacking the BLANK keyword in the FITS header.
            # In these cases we would have to find an unused value and designate it as the "BLANK" value.
            if samp.dtype.kind != "f":
                raise ValueError(
                    "Can not process dtype {0}. Convert the data to floating point values first. ".format(
                        samp.dtype
                    )
                )

            samp[bad] = np.nan

            return samp

        return vec2pix


def _latlon_tile_filter(image_lon_min, image_lon_max, image_lat_min, image_lat_max):
    """
    Return a "tile filter" function that only accepts tiles that overlap a
    bounding box in latitude and longitude.

    The arguments to this function give the bounding box edges, measured in
    radians. We refer to the lat/lon bounding box as the "image" bounds although
    this filtering process can be useful even if you don't have an actual image
    handy.

    The image longitudes should be "unwrapped" such that ``image_lon_min <
    image_lon_max`` always. For instance, longitude bounds of ``(170, 400)``
    define an image that spans 230 degrees in longitude. The longitude bounds
    can span more than 360 degrees if the image really covers all longitudes.
    (This can happen if it touches one of the poles.)

    Usual bounding box semantics apply. If your bounding box is "too big" the
    only problem is that more tiles are touched than strictly necessary.

    Note that this filter can give somewhat surprising semantics: if the filter
    matches tile T, it is possible that it does not match any of T's children.
    This is because we're doing a bounding-box test, and it is possible that the
    bounding box of T overlaps the image while the union of the bounding boxes
    of T's children does not.
    """
    assert image_lon_min < image_lon_max
    assert image_lat_min < image_lat_max

    from ._libtoasty import tile_intersects_latlon_bbox

    def latlon_tile_filter(tile):
        corner_lonlats = np.asarray(tile.corners)
        return tile_intersects_latlon_bbox(
            corner_lonlats, image_lon_min, image_lon_max, image_lat_min, image_lat_max
        )

    return latlon_tile_filter


class ChunkedPlateCarreeSampler(object):
    """
    Setup for TOAST sampling of a chunked plate-carree image.

    This only works with the ChunkedJPEG2000Reader image right now, but in
    principle we could extend to accept other chunked formats.

    Assume a typical image coordinate system, where (x,y) = (0,0) is the
    top-left edge of the image. The "global" coordinate system refers to the
    un-chunked image, which is probably too big to fit into memory.

    In the planetary plate carree projection, (global) X and Y measure latitude
    and longitude orthogonally. The left edge of the X=0 column has lon = -pi,
    while the right edge of the X=(W-1) column has lon = +pi. The top edge of
    the Y=0 row has lat = +pi/2, and the bottom edge of the Y=(H-1) row has lat
    = -pi/2.
    """

    def __init__(self, chunked_image, planetary=False):
        self._image = chunked_image

        assert planetary, "XXX non-planetary plate carree not implemented"

        self.sx = TWOPI / self._image.shape[1]  # radians per pixel, X direction
        self.sy = np.pi / self._image.shape[0]  # ditto, for the Y direction

    @property
    def n_chunks(self):
        return self._image.n_chunks

    def _chunk_bounds(self, ichunk):
        cx, cy, cw, ch = self._image.chunk_spec(ichunk)

        # Note that the following are all intended to be coordinates at
        # pixel edges, in the appropriate direction, not pixel centers.
        lon_l = self.sx * cx - np.pi
        lon_r = self.sx * (cx + cw) - np.pi
        lat_u = HALFPI - self.sy * cy
        lat_d = HALFPI - self.sy * (cy + ch)  # note: lat_u > lat_d

        return lon_l, lon_r, lat_d, lat_u

    def filter(self, ichunk):
        """
        Get a TOAST tile-filter function for the specified chunk.

        Parameters
        ----------
        ichunk : :class:`int`
            The index of the chunk to query, between 0 and ``self.n_chunks - 1``
            (inclusive).

        Returns
        -------
        A callable object, ``filter(tile) -> bool``, suitable for use as a tile
        filter function.
        """
        return _latlon_tile_filter(*self._chunk_bounds(ichunk))

    def sampler(self, ichunk):
        """
        Get a TOAST sampler function for the specified chunk.

        Parameters
        ----------
        ichunk : :class:`int`
            The index of the chunk to query, between 0 and ``self.n_chunks - 1``
            (inclusive).

        Returns
        -------
        A callable object, ``sampler(lon, lat) -> data``, suitable for use as a tile
        sampler function.
        """
        from .image import Image

        chunk_lon_min, chunk_lon_max, chunk_lat_min, chunk_lat_max = self._chunk_bounds(
            ichunk
        )
        data = self._image.chunk_data(ichunk)
        data_img = Image.from_array(data)
        buffer = data_img.mode.make_maskable_buffer(256, 256)
        biy, bix = np.indices((256, 256))

        ny, nx = data.shape[:2]
        dx = nx / (
            chunk_lon_max - chunk_lon_min
        )  # pixels per radian in the X direction
        dy = ny / (chunk_lat_max - chunk_lat_min)  # ditto, for the Y direction
        lon0 = (
            chunk_lon_min + 0.5 / dx
        )  # longitudes of the centers of the pixels with ix = 0
        lat0 = (
            chunk_lat_max - 0.5 / dy
        )  # latitudes of the centers of the pixels with iy = 0

        def plate_carree_planet_sampler(lon, lat):
            lon = (lon + np.pi) % TWOPI - np.pi  # ensure in range [-pi, pi]
            ix = (lon - lon0) * dx
            ix = np.round(ix).astype(int)
            ok = (ix >= 0) & (ix < nx)

            iy = (lat0 - lat) * dy  # *assume* in range [-pi/2, pi/2]
            iy = np.round(iy).astype(int)
            ok &= (iy >= 0) & (iy < ny)

            data_img.fill_into_maskable_buffer(buffer, iy[ok], ix[ok], biy[ok], bix[ok])
            return buffer.asarray()

        return plate_carree_planet_sampler
