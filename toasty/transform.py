# -*- mode: python; coding: utf-8 -*-
# Copyright 2020 the AAS WorldWide Telescope project
# Licensed under the MIT License.

"""
Within-tile data transformations. Mainly, transforming floating-point data to
RGB.
"""

__all__ = '''
f16x3_to_rgb
'''.split()

from astropy import visualization as viz
import numpy as np
from tqdm import tqdm

from .image import ImageMode, Image
from .pyramid import depth2tiles, generate_pos


def f16x3_to_rgb(pio, start_depth, clip=1, parallel=None, cli_progress=False):
    transform = viz.SqrtStretch() + viz.ManualInterval(0, clip)
    _float_to_rgb(pio, start_depth, ImageMode.F16x3, transform, parallel=parallel, cli_progress=cli_progress)


def _float_to_rgb(pio, depth, read_mode, transform, parallel=None, cli_progress=False):
    from .par_util import resolve_parallelism
    parallel = resolve_parallelism(parallel)

    if parallel > 1:
        _float_to_rgb_parallel(pio, depth, read_mode, transform, cli_progress, parallel)
    else:
        _float_to_rgb_serial(pio, depth, read_mode, transform, cli_progress)


def _float_to_rgb_serial(pio, depth, read_mode, transform, cli_progress):
    buf = np.empty((256, 256, 4), dtype=np.uint8)

    with tqdm(total=depth2tiles(depth), disable=not cli_progress) as progress:
        for pos in generate_pos(depth):
            _float_to_rgb_do_one(buf, pos, pio, read_mode, transform)
            progress.update(1)

    if cli_progress:
        print()


def _float_to_rgb_parallel(pio, depth, read_mode, transform, cli_progress, parallel):
    import multiprocessing as mp

    # Start up the workers

    queue = mp.Queue(maxsize = 16 * parallel)
    workers = []

    for _ in range(parallel):
        w = mp.Process(target=_float_to_rgb_mp_worker, args=(queue, pio, read_mode, transform))
        w.daemon = True
        w.start()
        workers.append(w)

    # Send out them tiles

    with tqdm(total=depth2tiles(depth), disable=not cli_progress) as progress:
        for pos in generate_pos(depth):
              queue.put(pos)
              progress.update(1)

        queue.close()

        for w in workers:
            w.join()

    if cli_progress:
        print()


def _float_to_rgb_mp_worker(queue, pio, read_mode, transform):
    """
    Do the colormapping.
    """
    from queue import Empty

    buf = np.empty((256, 256, 4), dtype=np.uint8)

    while True:
        try:
            pos = queue.get(True, timeout=1)
        except (OSError, ValueError, Empty):
            # OSError or ValueError => queue closed. This signal seems not to
            # cross multiprocess lines, though.
            break

        _float_to_rgb_do_one(buf, pos, pio, read_mode, transform)


def _float_to_rgb_do_one(buf, pos, pio, read_mode, transform):
    """
    Do one float-to-RGB job. This problem is embarassingly parallel so we can
    share code between the serial and parallel implementations.
    """
    img = pio.read_image(pos, format='npy')
    if img is None:
        return

    mapped = transform(img.asarray())

    if mapped.ndim == 2:
        # TODO: allow real colormaps
        valid = np.isfinite(mapped)
        mapped[~valid] = 0
        mapped = np.clip(mapped * 255, 0, 255).astype(np.uint8)
        buf[...,:3] = mapped.reshape((256, 256, 1))
        buf[...,3] = 255 * valid
    else:
        valid = np.all(np.isfinite(mapped), axis=2)
        mapped[~valid] = 0
        mapped = np.clip(mapped * 255, 0, 255).astype(np.uint8)
        buf[...,:3] = mapped
        buf[...,3] = 255 * valid

    rgb = Image.from_array(buf)
    pio.write_image(pos, rgb, format='png', mode=ImageMode.RGB)
