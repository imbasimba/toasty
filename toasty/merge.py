# -*- mode: python; coding: utf-8 -*-
# Copyright 2019-2020 the AAS WorldWide Telescope project
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
the operation over sets of four adjacent pixels.

"""
from __future__ import absolute_import, division, print_function

__all__ = '''
averaging_merger
cascade_images
'''.split()

import numpy as np
from tqdm import tqdm

from . import pyramid
from .image import Image


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
    return np.nanmean(data.reshape(s), axis=(1, 3)).astype(data.dtype)


def cascade_images(pio, mode, start, merger, cli_progress=False):
    """Downsample image tiles all the way to the top of the pyramid.

    This function will walk the tiles in the tile pyramid, merging child tile
    images and writing new tile images at shallower levels of the pyramid.

    Parameters
    ----------
    pio : :class:`toasty.pyramid.PyramidIO`
        An object managing I/O on the tiles in the pyramid.
    mode : :class:`toasty.image.ImageMode`
        The image mode (i.e., RGB or scientific) to process.
    start : nonnegative integer
        The depth at which to start the cascade process. It is assumed that
        the tiles *at this depth* are already populated by some other means.
        This function will create new tiles at shallower depths.
    merger : a merger function
        The method used to create a parent tile from its child tiles. This
        is a callable that follows the Merger Protocol.
    cli_progress : optional boolean, defaults False
        If true, a progress bar will be printed to the terminal using tqdm.

    """
    buf = None
    SLICES = [
        (slice(None, 256), slice(None, 256)),
        (slice(None, 256), slice(256, None)),
        (slice(256, None), slice(None, 256)),
        (slice(256, None), slice(256, None)),
    ]

    with tqdm(total=pyramid.depth2tiles(start - 1), disable=not cli_progress) as progress:
        for pos in pyramid.generate_pos(start):
            if pos.n == start:
                continue  # start layer is already there; we're cascading up

            # By construction, the children of this tile have all already been
            # processed.
            children = pyramid.pos_children(pos)

            img0 = pio.read_toasty_image(children[0], mode, default='none')
            img1 = pio.read_toasty_image(children[1], mode, default='none')
            img2 = pio.read_toasty_image(children[2], mode, default='none')
            img3 = pio.read_toasty_image(children[3], mode, default='none')

            if img0 is None and img1 is None and img2 is None and img3 is None:
                progress.update(1)
                continue  # No data here; ignore

            if buf is not None:
                buf.clear()

            for slidx, subimg in zip(SLICES, (img0, img1, img2, img3)):
                if subimg is not None:
                    if buf is None:
                        buf = mode.make_maskable_buffer(512, 512)

                    buf.asarray()[slidx] = subimg.asarray()

            merged = Image.from_array(mode, merger(buf.asarray()))
            pio.write_toasty_image(pos, merged)
            progress.update(1)

    if cli_progress:
        print()
