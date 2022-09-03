# -*- mode: python; coding: utf-8 -*-
# Copyright 2019-2022 the AAS WorldWide Telescope project
# Licensed under the MIT License.

"""General tools for merging and downsampling tiles

The Merger Protocol
-------------------

A “merger” is a callable that takes four input tiles and downsamples them into
a smaller tile. Its prototype is ``merger(big) -> small``, where *big* is a
Numpy array of at least 2 dimensions whose first two axes are both 512
elements in size. The return value *small* should have the same number of
dimensions as the input, two initial axes of size 256, and remaining axes the
same size as the input.

To efficiently vectorize two-by-two downsampling, a useful trick is to reshape
the ``(512, 512)`` input tile into a shape ``(256, 2, 256, 2)``. You can then
use functions like ``np.mean()`` with an argument ``axes=(1, 3)`` to vectorize
the operation over sets of four adjacent pixels."""

__all__ = """
averaging_merger
cascade_images
TileMerger
""".split()

import numpy as np
import warnings

from . import pyramid
from .image import Image


SLICES_MATCHING_PARITY = [
    (slice(None, 256), slice(None, 256)),
    (slice(None, 256), slice(256, None)),
    (slice(256, None), slice(None, 256)),
    (slice(256, None), slice(256, None)),
]

SLICES_OPPOSITE_PARITY = [
    (slice(256, None), slice(None, 256)),
    (slice(256, None), slice(256, None)),
    (slice(None, 256), slice(None, 256)),
    (slice(None, 256), slice(256, None)),
]


def averaging_merger(data):
    """A merger function that averages quartets of pixels.

    Parameters
    ----------
    data : array
        See the Merger Protocol specification.

    Returns
    -------
    A downsampled array. See the Merger Protocol specification.

    """
    s = (data.shape[0] // 2, 2, data.shape[1] // 2, 2) + data.shape[2:]

    # nanmean will raise a RuntimeWarning if there are all-NaN quartets. This
    # gets annoying, so we silence them.
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return np.nanmean(data.reshape(s), axis=(1, 3)).astype(data.dtype)


def cascade_images(
    pio,
    start,
    merger,
    parallel=None,
    cli_progress=False,
    tile_filter=None,
):
    """Downsample image tiles all the way to the top of the pyramid.

    This function will walk the tiles in the tile pyramid, merging child tile
    images and writing new tile images at shallower levels of the pyramid.

    Parameters
    ----------
    pio : :class:`toasty.pyramid.PyramidIO`
        An object managing I/O on the tiles in the pyramid.
    start : nonnegative integer
        The depth at which to start the cascade process. It is assumed that
        the tiles *at this depth* are already populated by some other means.
        This function will create new tiles at shallower depths.
    merger : a merger function
        The method used to create a parent tile from its child tiles. This
        is a callable that follows the Merger Protocol.
    parallel : integer or None (the default)
        The level of parallelization to use. If unspecified, defaults to using
        all CPUs. If the OS does not support fork-based multiprocessing,
        parallel processing is not possible and serial processing will be
        forced. Pass ``1`` to force serial processing.
    cli_progress : optional boolean, defaults False
        If true, a progress bar will be printed to the terminal.
    tile_filter : callable
        A tile filtering function, suitable for passing to
        :func:`toasty.toast.generate_tiles_filtered`."""

    from .pyramid import Pyramid

    if start < 1:
        return  # Nothing to do.

    if tile_filter is None:
        # It's much faster if we can avoid calculating TOAST coordinate
        # information for the tiles.
        p = Pyramid.new_generic(start)
    else:
        p = Pyramid.new_toast_filtered(start, tile_filter)

    proc = TileMerger(pio, merger)
    p.walk(proc.walk_callback, parallel=parallel, cli_progress=cli_progress)


class TileMerger(object):
    """A utility for performing a merge operation with a
    :class:`~toasty.pyramid.Pyramid`.

    Parameters
    ----------
    pio : :class:`toasty.pyramid.PyramidIO`
        Handle for image I/O on the pyramid

    merger : a merger function
        Function for merging tile image data, such as :func:`averaging_merger`.

    Notes
    -----

    This class provides a :meth:`walk_callback` method that can be passed to the
    :meth:`toasty.pyramid.Pyramid.walk` function. This class preserves some
    state between calls to help speed up processing."""

    def __init__(self, pio, merger):
        self._pio = pio
        self._merger = merger
        self._buf = None

        # Pyramids always follow a negative-parity (JPEG-like) coordinate system:
        # tile X=0,Y=0 is at the top left. The file formats for individual tiles may
        # share the same parity, or they may be negative: pixel x=0,y=0 is at the
        # bottom-left. In particular, this is the case for FITS files. When this
        # happens, we can pretty much cascade as normal, but when putting tile
        # quartets together we need to y-flip at the tile level.

        if pio.get_default_vertical_parity_sign() == 1:
            self._slices = SLICES_OPPOSITE_PARITY
        else:
            self._slices = SLICES_MATCHING_PARITY

    def walk_callback(self, pos):
        """A callback for :meth:`toasty.pyramid.Pyramid.walk`.

        Parameters
        ----------
        pos : :class:`toasty.pyramid.Pos`
            A position for a pyramid tile.

        Notes
        -----
        This function loads up the image data for the four children of the
        specified position, merges them, and writes out the merged image."""

        # By construction, the children of this tile have all already been
        # processed.
        children = pyramid.pos_children(pos)

        img0 = self._pio.read_image(children[0], default="none")
        img1 = self._pio.read_image(children[1], default="none")
        img2 = self._pio.read_image(children[2], default="none")
        img3 = self._pio.read_image(children[3], default="none")

        if img0 is None and img1 is None and img2 is None and img3 is None:
            return

        if self._buf is not None:
            self._buf.clear()

        for slidx, subimg in zip(self._slices, (img0, img1, img2, img3)):
            if subimg is not None:
                if self._buf is None:
                    self._buf = subimg.mode.make_maskable_buffer(512, 512)
                    self._buf.clear()

                subimg.update_into_maskable_buffer(
                    self._buf,
                    slice(None),
                    slice(None),  # subimage indexer: nothing
                    *slidx,  # buffer indexer: appropriate sub-quadrant
                )

        merged = Image.from_array(self._merger(self._buf.asarray()))
        min_value, max_value = self._get_min_max_of_children([img0, img1, img2, img3])
        self._pio.write_image(pos, merged, min_value=min_value, max_value=max_value)

    def _get_min_max_of_children(self, children):
        min_value = None
        max_value = None

        if "fits" in self._pio.get_default_format():
            min_values = []
            max_values = []

            for image in children:
                if image is not None:
                    if image.data_min is not None:
                        min_values.append(image.data_min)
                    if image.data_max is not None:
                        max_values.append(image.data_max)

            if min_values:  # There may not be any valid values!
                min_value = min(min_values)

            if max_values:
                max_value = max(max_values)

        return min_value, max_value
