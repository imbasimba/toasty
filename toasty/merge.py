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

__all__ = """
averaging_merger
cascade_images
""".split()

import numpy as np
import os
import sys
from tqdm import tqdm
import warnings

from . import pyramid
from .pyramid import Pos
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
    pio, start, merger, parallel=None, cli_progress=False, tile_filter=None
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
        If true, a progress bar will be printed to the terminal using tqdm.
    tile_filter : callable
        A tile filtering function, suitable for passing to
        :func:`toasty.toast.generate_tiles_filtered`.

    """
    from .par_util import resolve_parallelism

    parallel = resolve_parallelism(parallel)

    if start < 1:
        return  # Nothing to do.

    if parallel > 1:
        _cascade_images_parallel(
            pio, start, merger, cli_progress, parallel, tile_filter
        )
    else:
        _cascade_images_serial(pio, start, merger, cli_progress, tile_filter)


def _cascade_images_serial(pio, start, merger, cli_progress, tile_filter=None):
    from .toast import count_tiles_matching_filter, generate_tiles_filtered

    buf = None

    # Pyramids always follow a negative-parity (JPEG-like) coordinate system:
    # tile X=0,Y=0 is at the top left. The file formats for individual tiles may
    # share the same parity, or they may be negative: pixel x=0,y=0 is at the
    # bottom-left. In particular, this is the case for FITS files. When this
    # happens, we can pretty much cascade as normal, but when putting tile
    # quartets together we need to y-flip at the tile level.

    if pio.get_default_vertical_parity_sign() == 1:
        slices = SLICES_OPPOSITE_PARITY
    else:
        slices = SLICES_MATCHING_PARITY

    if tile_filter is None:
        total = pyramid.depth2tiles(start - 1)
        with tqdm(total=total, disable=not cli_progress) as progress:
            for pos in pyramid.generate_pos(
                start - 1
            ):  # start layer is already there; we're cascading up
                _process_tile(pos, buf, pio, slices, merger)
                progress.update(1)
    else:
        # +1 because tile 0 is not counted by count_tiles_matching_filter
        total = (
            count_tiles_matching_filter(start - 1, tile_filter, bottom_only=False) + 1
        )
        with tqdm(total=total, disable=not cli_progress) as progress:
            for tile in generate_tiles_filtered(
                start - 1, tile_filter, bottom_only=False
            ):
                _process_tile(tile.pos, buf, pio, slices, merger)
                progress.update(1)
            _process_tile(Pos(0, 0, 0), buf, pio, slices, merger)
            progress.update(1)

    if cli_progress:
        print()


def _process_tile(pos, buf, pio, slices, merger):
    # By construction, the children of this tile have all already been
    # processed.
    children = pyramid.pos_children(pos)

    img0 = pio.read_image(children[0], default="none")
    img1 = pio.read_image(children[1], default="none")
    img2 = pio.read_image(children[2], default="none")
    img3 = pio.read_image(children[3], default="none")

    if img0 is None and img1 is None and img2 is None and img3 is None:
        return

    if buf is not None:
        buf.clear()

    for slidx, subimg in zip(slices, (img0, img1, img2, img3)):
        if subimg is not None:
            if buf is None:
                buf = subimg.mode.make_maskable_buffer(512, 512)
                buf.clear()

            subimg.update_into_maskable_buffer(
                buf,
                slice(None),
                slice(None),  # subimage indexer: nothing
                *slidx,  # buffer indexer: appropriate sub-quadrant
            )

    merged = Image.from_array(merger(buf.asarray()))
    min_value, max_value = _get_min_max_of_children(pio, [img0, img1, img2, img3])

    pio.write_image(pos, merged, min_value=min_value, max_value=max_value)


def _get_min_max_of_children(pio, children):
    min_value = None
    max_value = None
    if "fits" in pio.get_default_format():
        min_values = _get_existing_min_values(children)
        if min_values:  # Check there are any valid min values
            min_value = min(min_values)
        max_values = _get_existing_max_values(children)
        if max_values:  # Check there are any valid max values
            max_value = max(max_values)
    return min_value, max_value


def _get_existing_min_values(images):
    values = []
    for image in images:
        if image is not None and image.data_min is not None:
            values.append(image.data_min)
    return values


def _get_existing_max_values(images):
    values = []
    for image in images:
        if image is not None and image.data_max is not None:
            values.append(image.data_max)
    return values


def _cascade_images_parallel(pio, start, merger, cli_progress, parallel, tile_filter):
    """Parallelized cascade operation

    At the moment, we require fork-based multiprocessing because the PyramidIO
    and ``merger`` items are not pickle-able. This could be relaxed, but we
    might plausibly want to support custom merger functions, so pickle-ability
    is likely to be a continuing issue.

    """
    import multiprocessing as mp
    from queue import Empty
    from .pyramid import Pos, pos_parent
    from .toast import count_tiles_matching_filter, generate_tiles_filtered

    # The dispatcher process keeps track of finished tiles (reported in
    # `done_queue`) and notifiers worker when new tiles are ready to process
    # (`ready_queue`).

    first_level_to_do = start - 1
    if tile_filter is None:
        n_todo = pyramid.depth2tiles(first_level_to_do)
    else:
        n_todo = (
            count_tiles_matching_filter(
                first_level_to_do, tile_filter, bottom_only=False
            )
            + 1
        )  # +1 because tile 0 is not counted by count_tiles_matching_filter
    ready_queue = mp.Queue()
    done_queue = mp.Queue(maxsize=2 * parallel)
    done_event = mp.Event()

    # Seed the queue of ready tiles. We use generate_pos to try to seed the
    # queue in an order that will get us to generate higher-level tiles as early
    # as possible, to make it easier to evaluate the output during processing ...
    # but in practice this isn't working. Seems that we're saturating the ready
    # queue before any higher-level tiles can become eligible for processing.
    readiness = {}
    if tile_filter is None:
        for pos in pyramid.generate_pos(first_level_to_do):
            if pos.n == first_level_to_do:
                ready_queue.put(pos)
    else:
        tiles_to_process = set()
        for tile in generate_tiles_filtered(
            first_level_to_do, tile_filter, bottom_only=True
        ):
            ready_queue.put(tile.pos)
            tiles_to_process.add(tile.pos)
        _initiate_readiness_state(tiles_to_process, readiness)

    # The workers pick up tiles that are ready to process and do the merging.

    workers = []

    for _ in range(parallel):
        w = mp.Process(
            target=_mp_cascade_worker,
            args=(done_queue, ready_queue, done_event, pio, merger),
        )
        w.daemon = True
        w.start()
        workers.append(w)

    # Start dispatching tiles

    with tqdm(total=n_todo, disable=not cli_progress) as progress:
        while True:
            # Did anybody finish a tile?
            try:
                pos = done_queue.get(True, timeout=1)
            except (OSError, ValueError, Empty):
                # OSError or ValueError => queue closed. This signal seems not to
                # cross multiprocess lines, though.
                continue

            progress.update(1)

            # If the n=0 tile was done, that's everything.
            if pos.n == 0:
                break

            # If this tile was finished, its parent is one step
            # closer to being ready to process.
            ppos, x_index, y_index = pos_parent(pos)
            bit_num = 2 * y_index + x_index
            flags = readiness.get(ppos, 0)
            flags |= 1 << bit_num

            # If this tile was the last of its siblings to be finished,
            # the parent is now ready for processing.
            if flags == 0xF:
                readiness.pop(ppos)
                ready_queue.put(ppos)
            else:
                readiness[ppos] = flags

    # All done!

    ready_queue.close()
    ready_queue.join_thread()
    done_event.set()

    for w in workers:
        w.join()

    if cli_progress:
        print()


def _mp_cascade_worker(done_queue, ready_queue, done_event, pio, merger):
    """
    Process tiles that are ready.
    """
    from queue import Empty

    buf = None

    # See discussion in the serial implementation.
    if pio.get_default_vertical_parity_sign() == 1:
        slices = SLICES_OPPOSITE_PARITY
    else:
        slices = SLICES_MATCHING_PARITY

    while True:
        try:
            pos = ready_queue.get(True, timeout=1)
        except Empty:
            if done_event.is_set():
                break
            continue

        _process_tile(pos, buf, pio, slices, merger)

        done_queue.put(pos)


def _initiate_readiness_state(tiles_to_process, readiness):
    """
    Marking sibling tiles with no data (as well as their ancestors) as already processed.
    This allows us to properly detect when ancestors of the tiles to be processed are
    actually ready to be processed (i.e. when all children of a tile are marked as processed)
    """
    from .pyramid import pos_children, get_parents

    if len(tiles_to_process) == 0 or Pos(0, 0, 0) in tiles_to_process:
        return

    parents = get_parents(tiles_to_process, get_all_ancestors=False)
    for parent in parents:
        for child in pos_children(parent):
            if child not in tiles_to_process:
                flags = readiness.get(parent, 0)
                # Using the child's position within the parent tile (0-1x, 0-1y)
                bit_num = 2 * (child.y % 2) + child.x % 2
                flags |= 1 << bit_num
                readiness[parent] = flags

    _initiate_readiness_state(parents, readiness)
