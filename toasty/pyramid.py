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
PyramidIO
'''.split()

from collections import namedtuple
import os.path

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


class PyramidIO(object):
    """Manage I/O on a tile pyramid."""

    def __init__(self, base_dir):
        self._base_dir = base_dir

    def tile_path(self, pos, extension='png'):
        """Get the path for a tile, creating its containing directories.

        Parameters
        ----------
        pos : Pos
          The tile to get a path for.
        extension : str, default: "png"
          The file extension to use in the path.

        Returns
        -------
        The path as a string.

        Notes
        -----
        This function does I/O itself — it creates the parent directories
        containing the tile path. It is not an error for the parent
        directories to already exist.

        """
        level = str(pos.n)
        ix = str(pos.x)
        iy = str(pos.y)

        d = os.path.join(level, iy)
        os.makedirs(d, exist_ok=True)

        return os.path.join(d, '{}_{}.{}'.format(iy, ix, extension))

    def get_path_scheme(self):
        """Get the scheme for buiding tile paths as used in the WTML standard.

        Returns
        -------
        The naming scheme, a string resembling ``{1}/{3}/{3}_{2}``.

        Notes
        -----
        The naming scheme is currently hardcoded to be the format given above,
        but in the future other options might become available.

        """
        return '{1}/{3}/{3}_{2}'
