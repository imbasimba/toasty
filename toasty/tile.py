"""
Generate PNG tile directories
"""
from __future__ import print_function, division
import os
import logging

import numpy as np

from ._libtoasty import subsample, mid
from .io import save_png, read_png
from .norm import normalize
from collections import defaultdict, namedtuple

__all__ = '''
normalizer
'''.split()

level1 = [[np.radians(c) for c in row]
          for row in [[(0, -90), (90, 0), (0, 90), (180, 0)],
                      [(90, 0), (0, -90), (0, 0), (0, 90)],
                      [(0, 90), (0, 0), (0, -90), (270, 0)],
                      [(180, 0), (0, 90), (270, 0), (0, -90)]]
          ]

Pos = namedtuple('Pos', 'n x y')
Tile = namedtuple('Tile', 'pos increasing corners')


def minmax(arr):
    """Returns the minimum and maximum values of an array."""
    return min(arr),max(arr)


def default_tile_in_range(tile):
    """Default tile_in_range, always returns true, so all tiles are toasted."""
    return True


def minmax_tile_in_range(ra_range, dec_range):
    """Returns the tile_in_range function based on a ra/dec range.

    Parameters
    ----------
    ra_range, dec_range: (array)
      The ra and dec ranges to be toasted (in the form [min,max]).
    """

    def is_overlap(tile):
        c = tile[1]

        minRa,maxRa = minmax([ (x[0] + 2*np.pi) if x[0] < 0 else x[0] for x in [y for y in c if np.abs(y[1]) !=  np.pi/2] ])
        minDec,maxDec = minmax([x[1] for x in c])
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

def is_subtile(subLoc, loc):
    """Function to determine if a lower level tile (subLoc) is contained
    within a higher level tile (loc)"""

    if subLoc.n == loc.n:
        if (subLoc.x == loc.x) and (subLoc.y == loc.y):
            return True
        return False

    return is_subtile(Pos(n=subLoc.n-1, x=int(subLoc.x/2), y=int(subLoc.y/2)),loc)


def nxy_tile_in_range(layer,tx,ty):
    """Returns the tile_in_range function based on a given super-tile.

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


def _postfix_corner(tile, depth, bottom_only, tile_in_range = None):
    """
    Yield subtiles of a given tile, in postfix order


    Parameters
    ----------
    tile : (Pos, corner, increasing)
      Description of Current tile
    depth : int
      Depth to descend to
    bottom_only : bool
      If True, only yield tiles at max_depth
    """

    n = tile[0].n
    if n > depth:
        return

    if not tile_in_range:
        tile_in_range = default_tile_in_range

    if not tile_in_range(tile):
        return

    for child in _div4(*tile):
        for item in _postfix_corner(child, depth, bottom_only, tile_in_range):
            yield item

    if n == depth or not bottom_only:
        yield tile


def _div4(pos, c, increasing):
    n, x, y = pos.n, pos.x, pos.y
    ul, ur, lr, ll = c
    to = mid(ul, ur)
    ri = mid(ur, lr)
    bo = mid(lr, ll)
    le = mid(ll, ul)
    ce = mid(ll, ur) if increasing else mid(ul, lr)

    return [(Pos(n=n + 1, x=2 * x, y=2 * y), (ul, to, ce, le), increasing),
            (Pos(n=n + 1, x=2 * x + 1, y=2 * y), (to, ur, ri, ce), increasing),
            (Pos(n=n + 1, x=2 * x, y=2 * y + 1), (le, ce, bo, ll), increasing),
            (Pos(n=n + 1, x=2 * x + 1, y=2 * y + 1), (ce, ri, lr, bo),
             increasing)]


def _parent(child):
    """
    Given a toast tile, return the address of the parent,
    as well as the corner of the parent that this tile occupies

    Returns
    -------
    Pos, xcorner, ycorner
    """
    parent = Pos(n=child.n - 1, x=child.x // 2, y=child.y // 2)
    left = child.x % 2
    top = child.y % 2
    return (parent, left, top)


def iter_corners(depth, bottom_only=True, tile_in_range = None):
    """
    Iterate over toast tiles and return the corners.
    Tiles are traversed in post-order (children before parent)

    Parameters
    ----------
    depth : int
      The tile depth to recurse to
    bottom_only : bool
      If True, then only the lowest tiles will be yielded
    tile_in_range : callable (optional)
      The function that determines which tiles are in the range to be
      toasted (default is all of them).

    Yields
    ------
    pos, corner
    """
    todo = [(Pos(n=1, x=0, y=0), level1[0], True),
            (Pos(n=1, x=1, y=0), level1[1], False),
            (Pos(n=1, x=1, y=1), level1[2], True),
            (Pos(n=1, x=0, y=1), level1[3], False)]

    for t in todo:
        for item in _postfix_corner(t, depth, bottom_only, tile_in_range):
            yield item


def iter_tiles(data_sampler, depth, merge=True,
               base_level_only=False,tile_in_range=None,restartDir=None, top=0):
    """
    Create a hierarchy of toast tiles

    Parameters
    ----------
    data_sampler : func or string
      - A function that takes two 2D numpy arrays of (lon, lat) as input,
        and returns an image of the original dataset sampled
        at these locations
      - A string giving a base toast directory that contains the
        base level of toasted tiles, using this option, only the
        merge step takes place, the given directory must contain
        a "depth" directory for the given depth parameter

    depth : int
      The maximum depth to tile to. A depth of N creates
      4^N pngs at the deepest level
    merge : bool or callable (default True)
      How to treat lower resolution tiles.

      - If True, tiles above the lowest level (highest resolution)
        will be computed by averaging and downsampling the 4 subtiles.
      - If False, sampler will be called explicitly for all tiles
      - If a callable object, this object will be passed the
        4x oversampled image to downsample

    base_level_only : bool (default False)
      If True only the bottem level of tiles will be created.
      In this case merge will be set to True, but no merging will happen,
      and only the highest resolution layer of images will be created.
    tile_in_range: callable (optional)
      A function that takes a tile and determines if it is in toasting range.
      If not given default_tile_in_range will be used which simply returns True.
    restartDir: string (optional)
      For restart jobs, the directory in which to check for toast tiles
      before toasting (if tile is found, the toasting step is skipped)
    top: int (optional)
      The topmost layer of toast tiles to create (only relevant if
      base_level_only is False), default is 0.

    Yields
    ------
    (pth, tile) : str, ndarray
      pth is the relative path where the tile image should be saved
    """
    if merge is True:
        merge = _default_merge

    parents = defaultdict(dict)


    for node, c, increasing in iter_corners(max(depth, 1),
                                            bottom_only=merge, tile_in_range=tile_in_range):

        n, x, y = node.n, node.x, node.y

        if type(data_sampler) == str:
            imgDir = data_sampler + '/' + str(n) + '/'
            try:
                img = read_png(imgDir + str(y) + '/' + str(y) + '_' + str(x) + '.png')
            except: # could not read image
                img = None
        elif restartDir and os.path.isfile(restartDir + '/' + str(n) + '/' + str(y) + '/' + str(y) + '_' + str(x) + '.png'):
            img = None
        else:
            l, b = subsample(c[0], c[1], c[2], c[3], 256, increasing)
            img = data_sampler(l, b)

        # No image was returned by the sampler,
        # either image data was not availible for the given ra/dec range
        # or it is a restart job, and that image was already computed
        if (img is None) and  base_level_only:
                continue

        if not base_level_only:
            for pth, img in _trickle_up(img, node, parents, merge, depth, top):
                if img is None:
                    continue
                yield pth, img
        else:
            pth = os.path.join('%i' % n, '%i' % y, '%i_%i.png' % (y, x))
            yield pth, img


def _trickle_up(im, node, parents, merge, depth, top=0):
    """
    When a new toast tile is ready, propagate it up the hierarchy
    and recursively yield its completed parents
    """

    n, x, y = node.n, node.x, node.y

    pth = os.path.join('%i' % n, '%i' % y, '%i_%i.png' % (y, x))

    nparent = sum(len(v) for v in parents.values())
    assert nparent <= 4 * max(depth, 1)

    if depth >= n: # handle special case of depth=0, n=1
        yield pth, im

    if n == top: # This is the uppermost level desired
        return

    # - If not merging and not at level 1, no need to accumulate
    if not merge and n > 1:
        return

    parent, xc, yc = _parent(node)
    corners = parents[parent]
    corners[(xc, yc)] = im

    if len(corners) < 4:  # parent not yet ready
        return

    parents.pop(parent)

    # imgs = [ul,ur,bl,br]
    #imgs = np.array([corners[(0, 0)],corners[(1, 0)],corners[(1, 0)],corners[(1, 1)]])

    ul = corners[(0, 0)]
    ur = corners[(1, 0)]
    bl = corners[(0, 1)]
    br = corners[(1, 1)]

    # dealing with any children lacking image data
    if all(x is None for x in [ul,ur,bl,br]):
        im = None
    else:
        # get img shape
        imgShape = [x for x in [ul,ur,bl,br] if x is not None][0].shape

        if not imgShape: # This shouldn't happen but...
            print([type(x) for x in [ul,ur,bl,br]])
            im = None
        else:

            if ul is None:
                ul = np.zeros(imgShape,dtype=np.uint8)
            if ur is None:
                ur = np.zeros(imgShape,dtype=np.uint8)
            if bl is None:
                bl = np.zeros(imgShape,dtype=np.uint8)
            if br is None:
                br = np.zeros(imgShape,dtype=np.uint8)

            try:
                mosaic = np.vstack((np.hstack((ul, ur)), np.hstack((bl, br))))
                im = (merge or _default_merge)(mosaic)
            except:
                print(imgShape)
                im = None


    for item in _trickle_up(im, parent, parents, merge, depth, top):
        yield item


def _default_merge(mosaic):
    """The default merge strategy -- just average all 4 pixels"""
    return (mosaic[::2, ::2] / 4. +
            mosaic[1::2, ::2] / 4. +
            mosaic[::2, 1::2] / 4. +
            mosaic[1::2, 1::2] / 4.).astype(mosaic.dtype)


def gen_wtml(base_dir, depth, **kwargs):
    """
    Create a minimal WTML record for a pyramid generated by toasty

    Parameters
    ----------
    base_dir : str
      The base path to a toast pyramid, as you wish for it to appear
      in the WTML file (i.e., this should be a path visible to a server)
    depth : int
      The maximum depth of the pyramid

    Optional Keywords
    -----------------
    FolderName
    BandPass
    Name
    Credits
    CreditsUrl
    ThumbnailUrl

    Returns
    -------
    wtml : str
      A WTML record
    """
    kwargs.setdefault('FolderName', 'Toasty')
    kwargs.setdefault('BandPass', 'Visible')
    kwargs.setdefault('Name', 'Toasty map')
    kwargs.setdefault('Credits', 'Toasty')
    kwargs.setdefault('CreditsUrl', 'http://github.com/ChrisBeaumont/toasty')
    kwargs.setdefault('ThumbnailUrl', '')
    kwargs['url'] = base_dir
    kwargs['depth'] = depth

    template = ('<Folder Name="{FolderName}">\n'
                '<ImageSet Generic="False" DataSetType="Sky" '
                'BandPass="{BandPass}" Name="{Name}" '
                'Url="{url}/{{1}}/{{3}}/{{3}}_{{2}}.png" BaseTileLevel="0" '
                'TileLevels="{depth}" BaseDegreesPerTile="180" '
                'FileType=".png" BottomsUp="False" Projection="Toast" '
                'QuadTreeMap="" CenterX="0" CenterY="0" OffsetX="0" '
                'OffsetY="0" Rotation="0" Sparse="False" '
                'ElevationModel="False">\n'
                '<Credits> {Credits} </Credits>\n'
                '<CreditsUrl>{CreditsUrl}</CreditsUrl>\n'
                '<ThumbnailUrl>{ThumbnailUrl}</ThumbnailUrl>\n'
                '<Description/>\n</ImageSet>\n</Folder>')
    return template.format(**kwargs)


def toast(data_sampler, depth, base_dir,
          wtml_file=None, merge=True, base_level_only=False,
          ra_range=None, dec_range=None,toast_tile=None,restart=False,top_layer=0):
    """
    Build a directory of toast tiles

    Parameters
    ----------
    data_sampler : func or string
      - A function of (lon, lat) that samples a dataset
        at the input 2D coordinate arrays
      - A string giving a base toast directory that contains the
        base level of toasted tiles, using this option, only the
        merge step takes place, the given directory must contain
        a "depth" directory for the given depth parameter
    depth : int
      The maximum depth to generate tiles for.
      4^n tiles are generated at each depth n
    base_dir : str
      The path to create the files at
    wtml_file : str (optional)
      The path to write a WTML file to. If not present,
      no file will be written
    merge : bool or callable (default True)
      How to treat lower resolution tiles.

      - If True, tiles above the lowest level (highest resolution)
        will be computed by averaging and downsampling the 4 subtiles.
      - If False, sampler will be called explicitly for all tiles
      - If a callable object, this object will be passed the
        4x oversampled image to downsample
    base_level_only : bool (default False)
      If True only the bottem level of tiles will be created.
      In this case merge will be set to True, but no merging will happen,
      and only the highest resolution layer of images will be created.
    ra_range: array (optional)
    dec_range: array (optional)
      To toast only a portion of the sky give min and max ras and decs
      ([minRA,maxRA],[minDec,maxDec]) in degrees
      If these keywords are used base_level_only will be automatically set to
      true, regardless of its given value.
    toast_tile: array[n,x,y] (optional)
      If this keyword is used the output will be all the subtiles of toast_tile
      at the given depth (base_level_only will be automatically set to
      true, regardless of its given value.
    top_layer: int (optional)
      If merging this indicates the uppermost layer to be created.
    """
    if wtml_file is not None:
        wtml = gen_wtml(base_dir, depth)
        with open(wtml_file, 'w') as outfile:
            outfile.write(wtml)

    if ra_range and dec_range:
        ra_range = [np.radians(ra) for ra in ra_range]
        dec_range = [np.radians(dec) for dec in dec_range]
        tile_in_range = minmax_tile_in_range(ra_range, dec_range)
    else:
        tile_in_range = None

    if toast_tile:
        tile_in_range = nxy_tile_in_range(*toast_tile)

    if base_level_only:
        merge = True

    if restart:
        restartDir = base_dir
    else:
        restartDir = None

    num = 0
    for pth, tile in iter_tiles(data_sampler, depth, merge, base_level_only, tile_in_range,restartDir,top_layer):
        num += 1
        if num % 10 == 0:
            logging.getLogger(__name__).info("Finished %i of %i tiles" %
                                             (num, depth2tiles(depth)))
        pth = os.path.join(base_dir, pth)
        direc, _ = os.path.split(pth)
        if not os.path.exists(direc):
            try:
                os.makedirs(direc)
            except FileExistsError:
                print("%s already exists." % direc)
        try:
            save_png(pth, tile)
        except:
            print(pth)
            print(type(tile))


def depth2tiles(depth):
    return (4 ** (depth + 1) - 1) // 3


def _find_extension(pth):
    """
    Find the first HEALPIX extension in a fits file,
    and return the extension number. Else, raise an IndexError
    """
    for i, hdu in enumerate(pth):
        if hdu.header.get('PIXTYPE') == 'HEALPIX':
            return i
    else:
        raise IndexError("No HEALPIX extensions found in %s" % pth.filename())


def _guess_healpix(pth, extension=None):
    # try to guess healpix_sampler arguments from
    # a file

    from astropy.io import fits
    f = fits.open(pth)

    if extension is None:
        extension = _find_extension(f)

    data, hdr = f[extension].data, f[extension].header
    # grab the first healpix parameter
    data = data[data.dtype.names[0]]

    nest = hdr.get('ORDERING') == 'NESTED'
    coord = hdr.get('COORDSYS', 'C')

    return data, nest, coord


def healpix_sampler(data, nest=False, coord='C', interpolation='nearest'):
    """
    Build a sampler for Healpix images

    Parameters
    ----------
    data : array
      The healpix data
    nest : bool (default: False)
      Whether the data is ordered in the nested healpix style
    coord : 'C' | 'G'
      Whether the image is in Celestial (C) or Galactic (G) coordinates
    interpolation : 'nearest' | 'bilinear'
      What interpolation scheme to use.

      WARNING: bilinear uses healpy's get_interp_val,
               which seems prone to segfaults

    Returns
    -------
    A function which samples the healpix image, given arrays
    of (lon, lat)
    """
    from healpy import ang2pix, get_interp_val, npix2nside
    from astropy.coordinates import Galactic, FK5
    import astropy.units as u

    interp_opts = ['nearest', 'bilinear']
    if interpolation not in interp_opts:
        raise ValueError("Invalid interpolation %s. Must be one of %s" %
                         (interpolation, interp_opts))
    if coord.upper() not in 'CG':
        raise ValueError("Invalid coord %s. Must be 'C' or 'G'" % coord)

    galactic = coord.upper() == 'G'
    interp = interpolation == 'bilinear'
    nside = npix2nside(data.size)

    def vec2pix(l, b):
        if galactic:
            f = FK5(l * u.rad, b * u.rad)
            g = f.transform_to(Galactic)
            l, b = g.l.rad, g.b.rad

        theta = np.pi / 2 - b
        phi = l

        if interp:
            return get_interp_val(data, theta, phi, nest=nest)

        return data[ang2pix(nside, theta, phi, nest=nest)]

    return vec2pix


def cartesian_sampler(data):
    """Return a sampler function for a dataset in the cartesian projection

    The image is assumed to be oriented with longitude increasing to the left,
    with (l,b) = (0,0) at the center pixel

    Parameters
    ----------
    data : array-like
      The map to sample
    """
    data = np.asarray(data)
    ny, nx = data.shape[0:2]

    if ny * 2 != nx:
        raise ValueError("Map must be twice as wide as it is tall")

    def vec2pix(l, b):
        l = (l + np.pi) % (2 * np.pi)
        l[l < 0] += 2 * np.pi
        l = nx * (1 - l / (2 * np.pi))
        l = np.clip(l.astype(np.int), 0, nx - 1)
        b = ny * (1 - (b + np.pi / 2) / np.pi)
        b = np.clip(b.astype(np.int), 0, ny - 1)
        return data[b, l]

    return vec2pix


def normalizer(sampler, vmin, vmax, scaling='linear',
               bias=0.5, contrast=1):
    """
    Apply an intensity scaling to a sampler function

    Parameters
    ----------
    sampler : function
       A function of (lon, lat) that samples a dataset

    vmin : float
      The data value to assign to black
    vmin : float
      The data value to assign to white
    bias : float between 0-1. Default=0.5
      Where to assign middle-grey, relative to (vmin, vmax).
    contrast : float, default=1
      How quickly to ramp from black to white. The default of 1
      ramps over a data range of (vmax - vmin)
    scaling : 'linear' | 'log' | 'arcsinh' | 'sqrt' | 'power'
      The type of intensity scaling to apply

    Returns
    -------
    A function of (lon, lat) that samples an image,
    scales the intensity, and returns an array of dtype=np.uint8
    """
    def result(x, y):
        raw = sampler(x, y)
        if raw is None:
            return raw
        else:
            r = normalize(raw, vmin, vmax, bias, contrast, scaling)
            return r
    return result
