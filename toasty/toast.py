# -*- mode: python; coding: utf-8 -*-
# Copyright 2013-2020 Chris Beaumont and the AAS WorldWide Telescope project
# Licensed under the MIT License.

"""Computations for the TOAST projection scheme and tile pyramid format.

TODO this all needs to be ported to modern Toasty infrastructure and
wwt_data_formats.

"""
from __future__ import absolute_import, division, print_function

__all__ = '''
generate_tiles
minmax_tile_filter
nxy_tile_filter
sample_layer
Tile
toast_tile_area
'''.split()

from collections import defaultdict, namedtuple
import os
import logging
import numpy as np
from tqdm import tqdm

from ._libtoasty import subsample, mid
from .image import Image
from .norm import normalize
from .pyramid import Pos, depth2tiles, is_subtile, pos_parent, tiles_at_depth

level1 = [
    [np.radians(c) for c in row]
    for row in [
        [(0, -90), (90, 0), (0, 90), (180, 0)],
        [(90, 0), (0, -90), (0, 0), (0, 90)],
        [(0, 90), (0, 0), (0, -90), (270, 0)],
        [(180, 0), (0, 90), (270, 0), (0, -90)],
    ]
]

Tile = namedtuple('Tile', 'pos corners increasing')


def _arclength(lat1, lon1, lat2, lon2):
    """Compute the length of an arc along the great circle defined by spherical
    latitude and longitude coordinates. Inputs and return value are all in
    radians.

    """
    c = np.sin(lat1) * np.sin(lat2) + np.cos(lon1 - lon2) * np.cos(lat1) * np.cos(lat2)
    return np.arccos(c)


def _spherical_triangle_area(lat1, lon1, lat2, lon2, lat3, lon3):
    """Compute the area of the specified spherical triangle in steradians. Inputs
    are in radians. From https://math.stackexchange.com/a/66731 . My initial
    implementation used unit vectors on the sphere instead of latitudes and
    longitudes; there might be a faster way to do things in lat/lon land.

    """
    c = _arclength(lat1, lon1, lat2, lon2)
    a = _arclength(lat2, lon2, lat3, lon3)
    b = _arclength(lat3, lon3, lat1, lon1)
    s = 0.5 * (a + b + c)
    tane4 = np.sqrt(np.tan(0.5 * s) * np.tan(0.5 * (s - a)) * np.tan(0.5 * (s - b)) * np.tan(0.5 * (s - c)))
    e = 4 * np.arctan(tane4)
    return e


def toast_tile_area(tile):
    """Calculate the area of a TOAST tile in steradians.

    Parameters
    ----------
    tile : :class:`Tile`
        A TOAST tile.

    Returns
    -------
    The area of the tile in steradians.

    Notes
    -----
    This computation is not very fast.

    """
    ul, ur, lr, ll = tile.corners

    if tile.increasing:
        a1 = _spherical_triangle_area(ul[1], ul[0], ur[1], ur[0], ll[1], ll[0])
        a2 = _spherical_triangle_area(ur[1], ur[0], lr[1], lr[0], ll[1], ll[0])
    else:
        a1 = _spherical_triangle_area(ul[1], ul[0], ur[1], ur[0], lr[1], lr[0])
        a2 = _spherical_triangle_area(ul[1], ul[0], ll[1], ll[0], lr[1], lr[0])

    return a1 + a2


def _minmax(arr):
    return min(arr), max(arr)


def minmax_tile_filter(ra_range, dec_range):
    """Returns the tile_filter function based on a ra/dec range.

    Parameters
    ----------
    ra_range, dec_range: (array)
        The ra and dec ranges to be toasted (in the form [min,max]).
    """

    def is_overlap(tile):
        c = tile[1]

        minRa,maxRa = _minmax([(x[0] + 2*np.pi) if x[0] < 0 else x[0] for x in [y for y in c if np.abs(y[1]) !=  np.pi/2]])
        minDec,maxDec = _minmax([x[1] for x in c])
        if (dec_range[0] > maxDec) or (dec_range[1] < minDec): # tile is not within dec range
            return False
        if (maxRa - minRa) > np.pi: # tile croses circle boundary
            if (ra_range[0] < maxRa) and (ra_range[1] > minRa): # tile is not within ra range
                return False
        else:
            if (ra_range[0] > maxRa) or (ra_range[1] < minRa): # tile is not within ra range
                return False

        return True

    return is_overlap


def nxy_tile_filter(layer,tx,ty):
    """Returns the tile_filter function based on a given super-tile.

    Parameters
    ----------
    layer,tx,ty: (int)
        Layer and x,y coordinates, for a tile that will serve at the "super-tile"
        such that all subtiles will be toasted/merged.
    """


    regionLoc = Pos(n=layer,x=tx,y=ty)

    def is_overlap(tile):
        tileLoc = tile[0]

        if tileLoc.n > regionLoc.n:
            return True

        return is_subtile(regionLoc,tileLoc)

    return is_overlap


def _postfix_corner(tile, depth, bottom_only, tile_filter):
    """
    Yield subtiles of a given tile, in postfix (deepest-first) order.

    Parameters
    ----------
    tile : Tile
        Parameters of the current tile.
    depth : int
        The depth to descend to.
    bottom_only : bool
        If True, only yield tiles at max_depth.
    tile_filter : callable
        A function with signature ``tile_filter(tile) -> bool`` that determines
        which tiles will be yielded; tiles for which it returns ``False`` will
        be skipped.

    """
    n = tile[0].n
    if n > depth:
        return

    if not tile_filter(tile):
        return

    for child in _div4(tile):
        for item in _postfix_corner(child, depth, bottom_only, tile_filter):
            yield item

    if n == depth or not bottom_only:
        yield tile


def _div4(tile):
    """Return the four child tiles of an input tile."""
    n, x, y = tile.pos.n, tile.pos.x, tile.pos.y
    ul, ur, lr, ll = tile.corners
    increasing = tile.increasing

    to = mid(ul, ur)
    ri = mid(ur, lr)
    bo = mid(lr, ll)
    le = mid(ll, ul)
    ce = mid(ll, ur) if increasing else mid(ul, lr)

    n += 1
    x *= 2
    y *= 2

    return [
        Tile(Pos(n=n, x=x,     y=y    ), (ul, to, ce, le), increasing),
        Tile(Pos(n=n, x=x + 1, y=y    ), (to, ur, ri, ce), increasing),
        Tile(Pos(n=n, x=x,     y=y + 1), (le, ce, bo, ll), increasing),
        Tile(Pos(n=n, x=x + 1, y=y + 1), (ce, ri, lr, bo), increasing),
    ]


def generate_tiles(depth, bottom_only=True, tile_filter=None):
    """Generate a pyramid of TOAST tiles in deepest-first order.

    Parameters
    ----------
    depth : int
        The tile depth to recurse to.
    bottom_only : bool
        If True, then only the lowest tiles will be yielded.
    tile_filter : callable or None (the default)
        If not None, a filter function applied to the process;
        only tiles for which ``tile_filter(tile)`` returns True
        will be yielded

    Yields
    ------
    tile : Tile
        An individual tile to process. Tiles are yield deepest-first.

    The ``n = 0`` depth is not included.

    """
    if tile_filter is None:
        tile_filter = lambda t: True

    todo = [
        Tile(Pos(n=1, x=0, y=0), level1[0], True),
        Tile(Pos(n=1, x=1, y=0), level1[1], False),
        Tile(Pos(n=1, x=1, y=1), level1[2], True),
        Tile(Pos(n=1, x=0, y=1), level1[3], False),
    ]

    for t in todo:
        for item in _postfix_corner(t, depth, bottom_only, tile_filter):
            yield item


def sample_layer(pio, mode, sampler, depth, cli_progress=False):
    """Generate a layer of the TOAST tile pyramid through direct sampling.

    Parameters
    ----------
    pio : :class:`toasty.pyramid.PyramidIO`
        A :class:`~toasty.pyramid.PyramidIO` instance to manage the I/O with
        the tiles in the tile pyramid.
    mode : :class:`toasty.image.ImageMode`
        The image mode of this data source.
    sampler : callable
        The sampler callable that will produce data for tiling.
    depth : int
        The depth of the layer of the TOAST tile pyramid to generate. The
        number of tiles in each layer is ``4**depth``. Each tile is 256×256
        TOAST pixels, so the resolution of the pixelization at which the
        data will be sampled is a refinement level of ``2**(depth + 8)``.
    cli_progress : optional boolean, defaults False
        If true, a progress bar will be printed to the terminal using tqdm.

    """
    with tqdm(total=tiles_at_depth(depth), disable=not cli_progress) as progress:
        for tile in generate_tiles(depth, bottom_only=True):
            lon, lat = subsample(
                tile.corners[0],
                tile.corners[1],
                tile.corners[2],
                tile.corners[3],
                256,
                tile.increasing,
            )
            sampled_data = sampler(lon, lat)
            pio.write_toasty_image(tile.pos, Image.from_array(mode, sampled_data))
            progress.update(1)

    if cli_progress:
        print()
