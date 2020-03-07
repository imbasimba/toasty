# -*- mode: python; coding: utf-8 -*-
# Copyright 2020 the AAS WorldWide Telescope project
# Licensed under the MIT License.

"""Common routines for tiling images anchored to the sky in a gnomonic
(tangential) projection.

"""
from __future__ import absolute_import, division, print_function

__all__ = '''
StudyTiling
make_thumbnail_bitmap
tile_study_image
'''.split()

import argparse
import numpy as np
import os.path

from .pyramid import Pos, next_highest_power_of_2


class StudyTiling(object):
    """Information about how a WWT "study" image is broken into tiles.

    In WWT a "study" is a large astronomical image projected onto the sky
    using a gnomonic (tangential or TAN) projection. The image may have many
    pixels, so it is broken up into tiles for efficient visualization.

    Note that this class doesn't know anything about how the image is
    projected onto the sky, or whether it is projected at all. The core tiling
    functionality doesn't need to care about that.

    """
    _width = None
    "The width of the region in which image data are available, in pixels (int)."

    _height = None
    "The height of the region in which image data are available, in pixels (int)."

    _p2n = None
    "The size of the study when tiled, in pixels - a power of 2."

    _tile_size = None
    "The number of tiles wide and high in the tiled study - a power of 2."

    _tile_levels = None
    "The number of levels in the tiling - ``log2(tile_size)``."

    _img_gx0 = None
    """The pixel position of the image data within the global (tiled)
    pixelization, in pixels right from the left edge (int). Nonnegative.

    """
    _img_gy0 = None
    """The pixel position of the image data within the global (tiled)
    pixelization, in pixels down from the top edge (int). Nonnegative.

    """
    def __init__(self, width, height):
        """Set up the tiling information.

        Parameters
        ----------
        width : positive integer
          The width of the full-resolution image, in pixels.
        height : positive integer
          The height of the full-resolution image, in pixels.

        """
        width = int(width)
        height = int(height)

        if width <= 0:
            raise ValueError('bad width value: %r' % (width, ))
        if height <= 0:
            raise ValueError('bad height value: %r' % (height, ))

        self._width = width
        self._height = height
        p2w = next_highest_power_of_2(self._width)
        p2h = next_highest_power_of_2(self._height)
        self._p2n = max(p2w, p2h)
        self._tile_size = self._p2n // 256
        self._tile_levels = int(np.log2(self._tile_size))
        self._img_gx0 = (self._p2n - self._width) // 2
        self._img_gy0 = (self._p2n - self._height) // 2


    def apply_to_imageset(self, imgset):
        """Fill the specific ``wwt_data_formats.imageset.ImageSet`` object
        with parameters defined by this tiling,

        Parameters
        ----------
        imgset : ``wwt_data_formats.imageset.ImageSet``
            The object to modify

        Remarks
        -------
        The only setting currently transferred is the number of tile levels.

        """
        imgset.tile_levels = self._tile_levels


    def image_to_tile(self, im_ix, im_iy):
        """Convert an image pixel position to a tiled pixel position.

        Parameters
        ----------
        im_ix : integer
          A 0-based horizontal pixel position in the image coordinate system.
        im_iy : integer
          A 0-based vertical pixel position in the image coordinate system.

        Remarks
        -------
        ``(0, 0)`` is the top-left corner of the image. The input values need
        not lie on the image. (I.e., they may be negative.)

        Returns ``(tile_ix, tile_iy, subtile_ix, subtile_iy)``, where

        - *tile_ix* is X index of the matched tile in the tiling, between 0
          and 2**tile_size - 1. Measured right from the left edge of the
          tiling.

        - *tile_iy* is Y index of the matched tile in the tiling, between 0
          and 2**tile_size - 1. Measured down from the top of the tiling.

        - *subtile_ix* is the pixel X position within that tile, between 0 and
          255. Measured right from the left edge of the tiling.

        - *subtile_iy* is the pixel Y position within that tile, between 0 and
          255. Measured down from the top edge of the tiling.

        """
        gx = im_ix + self._img_gx0
        gy = im_iy + self._img_gy0
        tile_ix = np.floor(gx // 256).astype(np.int)
        tile_iy = np.floor(gy // 256).astype(np.int)
        return (tile_ix, tile_iy, gx % 256, gy % 256)


    def generate_populated_positions(self):
        """Generate information about tiles containing image data.

        Generates a sequence of tuples ``(pos, width, height, image_x,
        image_y, tile_x, tile_y)`` where:

        - *pos* is a :class:`toasty.pyramid.Pos` tuple giving parameters of a tile
        - *width* is the width of the rectangle of image data contained in this tile,
          between 1 and 256.
        - *height* is the height of the rectangle of image data contained in this tile,
          between 1 and 256.
        - *image_x* is the pixel X coordinate of the left edge of the image data in this tile
          in the image rectangle, increasing from the left edge of the tile. Between 0 and
          ``self._width - 1`` (inclusive).
        - *image_y* is the pixel Y coordinate of the *top* edge of the image data in this tile
          in the image rectangle, increasing from the top edge of the tile. Between 0 and
          ``self._height - 1`` (inclusive).
        - *tile_x* is the pixel X coordinate of the left edge of the image data in this tile
          in the tile rectangle, increasing from the left edge of the tile. Between 0 and
          255 (inclusive).
        - *tile_y* is the pixel Y coordinate of the *top* edge of the image data in this tile
          in the tile rectangle, increasing from the top edge of the tile. Between 0 and
          255 (inclusive).

        Tiles that do not overlap the image at all are not generated. Tiles
        that are completely filled with image data will yield tuples of the
        form ``(pos, 256, 256, im_x, im_y, 0, 0)``. An image that fits
        entirely in one tile will yield a tuple of the form ``(Pos(n=0, x=0,
        y=0), width, height, 0, 0, tx, ty)``.

        """
        # Get the position of the actual image data in "global pixel
        # coordinates", which span the whole tiled region (a superset of the
        # image itself) with x=0, y=0 being the left-top corner of the tiled
        # region.

        img_gx1 = self._img_gx0 + self._width - 1  # inclusive: there are image data in this column
        img_gy1 = self._img_gy0 + self._height - 1  # ditto

        tile_start_tx = self._img_gx0 // 256
        tile_start_ty = self._img_gy0 // 256
        tile_end_tx = img_gx1 // 256  # inclusive; there are image data in this column of tiles
        tile_end_ty = img_gy1 // 256  # ditto

        for ity in range(tile_start_ty, tile_end_ty + 1):
            for itx in range(tile_start_tx, tile_end_tx + 1):
                # (inclusive) tile bounds in global pixel coords
                tile_gx0 = itx * 256
                tile_gy0 = ity * 256
                tile_gx1 = tile_gx0 + 255
                tile_gy1 = tile_gy0 + 255

                # overlap (= intersection) of the image and the tile in global pixel coords
                overlap_gx0 = max(tile_gx0, self._img_gx0)
                overlap_gy0 = max(tile_gy0, self._img_gy0)
                overlap_gx1 = min(tile_gx1, img_gx1)
                overlap_gy1 = min(tile_gy1, img_gy1)

                # coordinates of the overlap in image pixel coords
                img_overlap_x0 = overlap_gx0 - self._img_gx0
                img_overlap_x1 = overlap_gx1 - self._img_gx0
                img_overlap_y0 = overlap_gy0 - self._img_gy0
                img_overlap_y1 = overlap_gy1 - self._img_gy0

                # shape of the overlap
                overlap_width = img_overlap_x1 + 1 - img_overlap_x0
                overlap_height = img_overlap_y1 + 1 - img_overlap_y0

                # coordinates of the overlap in this tile's coordinates
                tile_overlap_x0 = overlap_gx0 - tile_gx0
                tile_overlap_y0 = overlap_gy0 - tile_gy0

                yield (
                    Pos(self._tile_levels, itx, ity),
                    overlap_width,
                    overlap_height,
                    img_overlap_x0,
                    img_overlap_y0,
                    tile_overlap_x0,
                    tile_overlap_y0,
                )


def tile_study_image(img_data, pio):
    """Tile an image as a study, loading the whole thing into memory.

    Parameters
    ----------
    img_data : array-like
        An array of image data, of shape ``(height, width, nchan)``,
        where nchan is 3 (RGB) or 4 (RGBA). The dtype should be compatible
        with :class:`np.uint8`.
    pio : :class:`toasty.pyramid.PyramidIO`
        A handle for doing I/O on the tile pyramid

    Returns
    -------
    A :class:`StudyTiling` defining the tiling of the image.

    """
    img_data = np.asarray(img_data)
    tiling = StudyTiling(img_data.shape[1], img_data.shape[0])
    buffer = np.empty((256, 256, 4), dtype=np.uint8)

    if img_data.shape[2] == 3:
        has_alpha = False
    elif img_data.shape[2] == 4:
        has_alpha = True
    else:
        raise ValueError('unexpected number of image channels; shape %r' % (img_data.shape,))

    for pos, width, height, image_x, image_y, tile_x, tile_y in tiling.generate_populated_positions():
        buffer.fill(0)

        if has_alpha:
            buffer[tile_y:tile_y+height,tile_x:tile_x+width] = \
                img_data[image_y:image_y+height,image_x:image_x+width]
        else:
            buffer[tile_y:tile_y+height,tile_x:tile_x+width,:3] = \
                img_data[image_y:image_y+height,image_x:image_x+width]
            buffer[tile_y:tile_y+height,tile_x:tile_x+width,3] = 255

        pio.write_image(pos, buffer)

    return tiling


def make_thumbnail_bitmap(bitmap):
    """Create a thumbnail bitmap from a :class:`PIL.Image`.

    Parameters
    ----------
    bitmap : :class:`PIL.Image`
        The image to thumbnail.

    Returns
    -------
    A :class:`PIL.Image` representing a thumbnail of the input image. WWT
    thumbnails are 96 pixels wide and 45 pixels tall and should be saved in
    JPEG format.

    """
    THUMB_SHAPE = (96, 45)
    THUMB_ASPECT = THUMB_SHAPE[0] / THUMB_SHAPE[1]

    if bitmap.width / bitmap.height > THUMB_ASPECT:
        # The image is wider than desired; we'll need to crop off the sides.
        target_width = int(round(bitmap.height * THUMB_ASPECT))
        dx = (bitmap.width - target_width) // 2
        crop_box = (dx, 0, dx + target_width, bitmap.height)
    else:
        # The image is taller than desired; crop off top and bottom.
        target_height = int(round(bitmap.width / THUMB_ASPECT))
        dy = (bitmap.height - target_height) // 2
        crop_box = (0, dy, bitmap.width, dy + target_height)

    thumb = bitmap.crop(crop_box)
    thumb.thumbnail(THUMB_SHAPE)
    return thumb
