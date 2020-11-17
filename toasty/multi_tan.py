# -*- mode: python; coding: utf-8 -*-
# Copyright 2019-2020 the AAS WorldWide Telescope project
# Licensed under the MIT License.

"""Generate tiles from a collection of images on a common TAN projection.

TODO: shuld be migrated to wwt_data_formats.

"""
from __future__ import absolute_import, division, print_function

__all__ = '''
MultiTanDataSource
'''.split()

import numpy as np

from .pyramid import Pos, next_highest_power_of_2

MATCH_HEADERS = [
    'CTYPE1', 'CTYPE2',
    'CRVAL1', 'CRVAL2',
]

# In my sample set, some of these files vary minutely from one header to the
# next, so we save them but don't demand exact matching. We should use
# np.isclose() or whatever it is.
SAVE_HEADERS = [
    'CD1_1', 'CD2_2',
]


class MultiTanDataSource(object):
    """Generate tiles from a collection of images on a common TAN projection.

    Some large astronomical images are stored as a collection of sub-images
    that share a common tangential projection, a format is that is nice and
    easy to convert into a WWT "study" tile pyramid. This class can process a
    collection of such images and break them into the highest-resolution layer
    of such a tile pyramid.

    """
    _ra_deg = None
    "The RA of the center of the TAN projection on the sky, in degrees."
    _dec_deg = None
    "The declination of the center of the TAN projection on the sky, in degrees."
    _rot_rad = None
    "The rotation of the TAN projection on the sky, in radians."
    _width = None
    "The width of the region in which image data are available, in pixels."
    _height = None
    "The height of the region in which image data are available, in pixels."
    _scale_x = None
    "The horizontal pixel scale, in degrees per pixel. May be negative."
    _scale_y = None
    "The vertical pixel scale, in degrees per pixel. Always positive."
    _tile_levels = None
    "How many levels there are in the tile pyramid for this study."
    _p2w = None
    """The width of the highest-resolution tiling, in pixels. This is the
    first power of 2 greater than or equal to _width."""
    _p2h = None
    """The height of the highest-resolution tiling, in pixels. This is the
    first power of 2 greater than or equal to _height."""
    _center_crx = None
    """The X position of the image center, in pixels relative to the center of
    the tangential projection."""
    _center_cry = None
    """The Y position of the image center, in pixels relative to the center of
    the tangential projection."""
    _crxmin = None
    "The minimum observed pixel X index, relative to the CRPIX of the projection."
    _crymin = None
    "The minimum observed pixel Y index, relative to the CRPIX of the projection."

    def __init__(self, paths, hdu_index=0):
        self._paths = paths
        self._hdu_index = hdu_index


    def _input_hdus(self):
        from astropy.io import fits

        for path in self._paths:
            with fits.open(path) as hdu_list:
                yield path, hdu_list[self._hdu_index]


    def compute_global_pixelization(self):
        """Read the input images to determine the global pixelation of this data set.

        This function reads the FITS headers of all of the input data files to
        determine the overall image size and the parameters of its tiling as a
        WWT study.

        """
        ref_headers = None
        crxmin = None

        for path, hdu in self._input_hdus():
            if ref_headers is None:
                ref_headers = {}

                for header in MATCH_HEADERS:
                    ref_headers[header] = hdu.header[header]

                for header in SAVE_HEADERS:
                    ref_headers[header] = hdu.header[header]

                if ref_headers['CTYPE1'] != 'RA---TAN':
                    raise Exception('all inputs must be in a TAN projection, but {} is not'.format(path))
                if ref_headers['CTYPE2'] != 'DEC--TAN':
                    raise Exception('all inputs must be in a TAN projection, but {} is not'.format(path))
            else:
                for header in MATCH_HEADERS:
                    expected = ref_headers[header]
                    observed = hdu.header[header]

                    if observed != expected:
                        raise Exception('inputs are not on uniform WCS grid; in file {}, expected '
                                        'value {} for header {} but observed {}'.format(path, expected, header, observed))

            crpix1 = hdu.header['CRPIX1'] - 1
            crpix2 = hdu.header['CRPIX2'] - 1

            this_crxmin = 0 - crpix1
            this_crxmax = (hdu.shape[1] - 1) - crpix1
            this_crymin = 0 - crpix2
            this_crymax = (hdu.shape[0] - 1) - crpix2

            if crxmin is None:
                crxmin = this_crxmin
                crxmax = this_crxmax
                crymin = this_crymin
                crymax = this_crymax
            else:
                crxmin = min(crxmin, this_crxmin)
                crxmax = max(crxmax, this_crxmax)
                crymin = min(crymin, this_crymin)
                crymax = max(crymax, this_crymax)

        # Figure out the global properties of the tiled TAN representation
        self._crxmin = crxmin
        self._crymin = crymin

        self._width = int(crxmax - self._crxmin) + 1
        self._height = int(crymax - self._crymin) + 1
        self._p2w = next_highest_power_of_2(self._width)
        self._p2h = next_highest_power_of_2(self._height)

        if self._p2w != self._p2h:  # TODO: figure this out and make it work.
            raise Exception('TODO: we don\'t properly handle non-square-ish images; got {},{}'.format(self._p2w, self._p2h))
        p2max = max(self._p2w, self._p2h)
        self._tile_levels = int(np.log2(p2max / 256))
        nfullx = self._p2w // 256
        nfully = self._p2h // 256

        self._ra_deg = ref_headers['CRVAL1']
        self._dec_deg = ref_headers['CRVAL2']

        cd1_1 = ref_headers['CD1_1']
        cd2_2 = ref_headers['CD2_2']
        cd1_2 = ref_headers.get('CD1_2', 0.0)
        cd2_1 = ref_headers.get('CD2_1', 0.0)

        if cd1_1 * cd2_2 - cd1_2 * cd2_1 < 0:
            cd_sign = -1
        else:
            cd_sign = 1

        self._rot_rad = np.arctan2(-cd_sign * cd1_2, cd2_2)
        self._scale_x = np.sqrt(cd1_1**2 + cd2_1**2) * cd_sign
        self._scale_y = np.sqrt(cd1_2**2 + cd2_2**2)

        self._center_crx = self._width // 2 + self._crxmin
        self._center_cry = self._height // 2 + self._crymin

        return self  # chaining convenience

    def create_wtml(
            self,
            name = 'MultiTan',
            url_prefix = './',
            fov_factor = 1.7,
            bandpass = 'Visible',
            description_text = '',
            credits_text = 'Created by toasty, part of the AAS WorldWide Telescope.',
            credits_url = '',
            thumbnail_url = '',
    ):
        """Create a WTML document with the proper metadata for this data set.

        :meth:`compute_global_pixelization` must have been called first.

        Parameters
        ----------
        name : str, defaults to "MultiTan"
          The dataset name to embed in the WTML file.
        url_prefix : str, default to "./"
          The beginning of the URL path to the tile data. The URL given in
          the WTML will be "URL_PREFIX{1}/{3}/{3}_{2}.png"
        fov_factor : float, defaults to 1.7
          The WTML file specifies the height of viewport that the client should
          zoom to when viewing this image. The value used is *fov_factor* times
          the height of the image.
        bandpass : str, defaults to "Visible"
          The bandpass of the image, as chosen from a menu of options
          supported by the WTML format: "Gamma", "HydrogenAlpha", "IR",
          "Microwave", "Radio", "Ultraviolet", "Visible", "VisibleNight",
          "XRay".
        description_text : str, defaults to ""
          Free text describing what this image is.
        credits_text : str, defaults to a toasty credit
          A brief textual credit of who created and processed the image data.
        credits_url: str, defaults to ""
          A URL with additional image credit information, or the empty string
          if no such URL is available.
        thumbnail_url : str, defaults to ""
          A URL of a thumbnail image (96x45 JPEG) representing this image data
          set, or the empty string for a default to be used.

        Returns
        -------
        folder : xml.etree.ElementTree.Element
          An XML element containing the WWT metadata.

        Examples
        --------
        To convert the returned XML structure into text, use
        :func:`xml.etree.ElementTree.tostring`:
        >>> from xml.etree import ElementTree as etree
        >>> folder = data_source.create_wtml()
        >>> print(etree.tostring(folder))

        """
        from xml.etree import ElementTree as etree

        folder = etree.Element('Folder')
        folder.set('Name', name)
        folder.set('Group', 'Explorer')

        place = etree.SubElement(folder, 'Place')
        place.set('Name', name)
        place.set('DataSetType', 'Sky')
        place.set('Rotation', str(self._rot_rad * 180 / np.pi))
        place.set('Angle', '0')
        place.set('Opacity', '100')
        place.set('RA', str(self._ra_deg / 15))  # this RA is in hours
        place.set('Dec', str(self._dec_deg))
        place.set('ZoomLevel', str(self._height * self._scale_y * fov_factor * 6))  # zoom = 6 * (FOV height in deg)
        # skipped: Constellation, Classification, Magnitude, AngularSize

        fgimgset = etree.SubElement(place, 'ForegroundImageSet')

        imgset = etree.SubElement(fgimgset, 'ImageSet')
        imgset.set('Name', name)
        imgset.set('Url', url_prefix + '{1}/{3}/{3}_{2}.png')
        imgset.set('WidthFactor', '2')
        imgset.set('BaseTileLevel', '0')
        imgset.set('TileLevels', str(self._tile_levels))
        imgset.set('BaseDegreesPerTile', str(self._scale_y * self._p2h))
        imgset.set('FileType', '.png')
        imgset.set('BottomsUp', 'False')
        imgset.set('Projection', 'Tan')
        imgset.set('CenterX', str(self._ra_deg))
        imgset.set('CenterY', str(self._dec_deg))
        imgset.set('OffsetX', str(self._center_crx * np.abs(self._scale_x)))
        imgset.set('OffsetY', str(self._center_cry * self._scale_y))
        imgset.set('Rotation', str(self._rot_rad * 180 / np.pi))
        imgset.set('DataSetType', 'Sky')
        imgset.set('BandPass', bandpass)
        imgset.set('Sparse', 'True')

        credits = etree.SubElement(imgset, 'Credits')
        credits.text = credits_text

        credurl = etree.SubElement(imgset, 'CreditsUrl')
        credurl.text = credits_url

        thumburl = etree.SubElement(imgset, 'ThumbnailUrl')
        thumburl.text = thumbnail_url

        desc = etree.SubElement(imgset, 'Description')
        desc.text = description_text

        return folder


    def generate_deepest_layer_numpy(
            self,
            pio,
            percentiles = [1, 99],
    ):
        """Fill in the deepest layer of the tile pyramid with Numpy-format data.

        Parameters
        ----------
        pio : :class:`toasty.pyramid.PyramidIO`
          A :class:`~toasty.pyramid.PyramidIO` instance to manage the I/O with
          the tiles in the tile pyramid.
        percentiles : iterable of numbers
          This is a list of percentile points to calculate while reading the
          data. Each number should be between 0 and 100. For each
          high-resolution tile, the percentiles are computed; then the *median*
          across all tiles is computed and returned.

        Returns
        -------
        percentiles : dict mapping numbers to numbers
          This dictionary contains the result of the median-percentile
          computation. The keys are the values provided in the *percentiles*
          parameter. The values are the median of each percentile across
          all of the tiles.

        Notes
        -----
        The implementation assumes that if individual images overlap, we can
        just use the pixels from any one of them without caring which
        particular one we choose.

        Because this operation involves reading the complete image data set,
        it offers a convenient opportunity to do some statistics on the data.
        This motivates the presence of the *percentiles* feature.

        """
        crxofs = (self._p2w - self._width) // 2
        cryofs = (self._p2h - self._height) // 2

        percentile_data = {p: [] for p in percentiles}

        for path, hdu in self._input_hdus():
            crpix1 = hdu.header['CRPIX1'] - 1
            crpix2 = hdu.header['CRPIX2'] - 1

            # (inclusive) image bounds in global pixel coords, which range
            # from 0 to p2{w,h} (non-inclusive), and have y=0 at the top. The FITS
            # data have y=0 at the bottom, so we need to flip them vertically.
            img_gx0 = int((crxofs - self._crxmin) - crpix1)
            img_gx1 = img_gx0 + hdu.shape[1] - 1
            img_gy1 = self._p2h - 1 - int((cryofs - self._crymin) - crpix2)
            img_gy0 = img_gy1 - (hdu.shape[0] - 1)

            assert img_gx0 >= 0
            assert img_gy0 >= 0
            assert img_gx1 < self._p2w
            assert img_gy1 < self._p2h

            # Tile indices at the highest resolution.

            ix0 = img_gx0 // 256
            iy0 = img_gy0 // 256
            ix1 = img_gx1 // 256
            iy1 = img_gy1 // 256

            # OK, load up the data, with a vertical flip, and grid them. While
            # we're doing that, calculate percentiles to inform the RGB-ification.

            data = hdu.data[::-1]
            n_tiles = 0

            pvals = np.nanpercentile(data, percentiles)
            for pct, pv in zip(percentiles, pvals):
                percentile_data[pct].append(pv)

            for iy in range(iy0, iy1 + 1):
                for ix in range(ix0, ix1 + 1):
                    # (inclusive) tile bounds in global pixel coords
                    tile_gx0 = ix * 256
                    tile_gy0 = iy * 256
                    tile_gx1 = tile_gx0 + 255
                    tile_gy1 = tile_gy0 + 255

                    # overlap (= intersection) of the image and the tile in global pixel coords
                    overlap_gx0 = max(tile_gx0, img_gx0)
                    overlap_gy0 = max(tile_gy0, img_gy0)
                    overlap_gx1 = min(tile_gx1, img_gx1)
                    overlap_gy1 = min(tile_gy1, img_gy1)

                    # coordinates of the overlap in image pixel coords
                    img_overlap_x0 = overlap_gx0 - img_gx0
                    img_overlap_x1 = overlap_gx1 - img_gx0
                    img_overlap_xslice = slice(img_overlap_x0, img_overlap_x1 + 1)
                    img_overlap_y0 = overlap_gy0 - img_gy0
                    img_overlap_y1 = overlap_gy1 - img_gy0
                    img_overlap_yslice = slice(img_overlap_y0, img_overlap_y1 + 1)

                    # coordinates of the overlap in this tile's coordinates
                    tile_overlap_x0 = overlap_gx0 - tile_gx0
                    tile_overlap_x1 = overlap_gx1 - tile_gx0
                    tile_overlap_xslice = slice(tile_overlap_x0, tile_overlap_x1 + 1)
                    tile_overlap_y0 = overlap_gy0 - tile_gy0
                    tile_overlap_y1 = overlap_gy1 - tile_gy0
                    tile_overlap_yslice = slice(tile_overlap_y0, tile_overlap_y1 + 1)

                    ###print(f'   {ix} {iy} -- {overlap_gx0} {overlap_gy0} {overlap_gx1} {overlap_gy1} -- '
                    ###      f'{tile_overlap_x0} {tile_overlap_y0} {tile_overlap_x1} {tile_overlap_y1} -- '
                    ###      f'{img_overlap_x0} {img_overlap_y0} {img_overlap_x1} {img_overlap_y1}')

                    pos = Pos(self._tile_levels, ix, iy)
                    p = pio.tile_path(pos)

                    try:
                        a = np.load(p)
                    except IOError as e:
                        if e.errno == 2:
                            a = np.empty((256, 256))
                            a.fill(np.nan)
                        else:
                            raise

                    a[tile_overlap_yslice,tile_overlap_xslice] = data[img_overlap_yslice,img_overlap_xslice]
                    np.save(p, a)

        percentile_data = {p: np.median(a) for p, a in percentile_data.items()}
        return percentile_data
