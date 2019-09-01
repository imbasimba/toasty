# Copyright 2019 the AAS WorldWide Telescope project
# Licensed under the MIT License.

"""General tools for working with tile pyramids.

Toasty and the AAS WorldWide Telescope support two kinds of tile pyramid
formats: the all-sky TOAST projection, and “studies” which are tile pyramids
rooted in a subset of the sky using a tangential projection. Both kinds of
tile pyramids have much in common, and this module implements their
overlapping functionality.

"""
from __future__ import absolute_import, division, print_function

__all__ = '''
depth2tiles
is_subtile
Pos
pos_parent
'''.split()

from collections import namedtuple

Pos = namedtuple('Pos', 'n x y')


def depth2tiles(depth):
    """Return the total number of tiles in a WWT tile pyramid of depth *depth*."""
    return (4 ** (depth + 1) - 1) // 3


def is_subtile(deeper_pos, shallower_pos):
    """Determine if one tile is a child of another.

    Parameters
    ----------
    deeper_pos : Pos
      A tile position.
    shallower_pos : Pos
      A tile position that is shallower than *deeper_pos*.

    Returns
    -------
    True if *deeper_pos* represents a tile that is a child of *shallower_pos*.

    """
    if deeper_pos.n < shallower_pos.n:
        raise ValueError('deeper_pos has a lower depth than shallower_pos')

    if deeper_pos.n == shallower_pos.n:
        return deeper_pos.x == shallower_pos.x and deeper_pos.y == shallower_pos.y

    return is_subtile(_parent(deeper_pos)[0], shallower_pos)


def pos_parent(pos):
    """Return a tile position's parent.

    Parameters
    ----------
    pos : Pos
      A tile position.

    Returns
    -------
    parent : Pos
      The tile position that is the parent of *pos*.
    x_index : integer, 0 or 1
      The horizontal index of the child inside its parent.
    y_index : integer, 0 or 1
      The vertical index of the child inside its parent.

    """
    if pos.n < 1:
        raise ValueError('cannot take the parent of a tile position with depth < 1')

    parent = Pos(
        n = pos.n - 1,
        x = pos.x // 2,
        y = pos.y // 2
    )
    return parent, pos.x % 2, pos.y % 2
