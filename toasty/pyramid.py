# -*- mode: python; coding: utf-8 -*-
# Copyright 2019-2022 the AAS WorldWide Telescope project
# Licensed under the MIT License.

"""General tools for working with tile pyramids.

Toasty and the AAS WorldWide Telescope support two kinds of tile pyramid
formats: the all-sky TOAST projection, and “studies” which are tile pyramids
rooted in a subset of the sky using a tangential projection. Both kinds of
tile pyramids have much in common, and this module implements their
overlapping functionality."""

__all__ = """
depth2tiles
generate_pos
is_subtile
next_highest_power_of_2
Pos
pos_children
pos_parent
guess_base_layer_level
Pyramid
PyramidIO
tiles_at_depth
""".split()

import glob
from collections import namedtuple
from contextlib import contextmanager
import os.path

from .image import ImageLoader, SUPPORTED_FORMATS, get_format_vertical_parity_sign
from .progress import progress_bar

Pos = namedtuple("Pos", "n x y")


def next_highest_power_of_2(n):
    """Ugh, this implementation is so dumb.

    We also assume that we are being called in a tiling context, in which case
    numbers less than 256 should be bumped up to 256 (the number of pixels in
    a single tile).

    """
    p = 256
    while p < n:
        p *= 2
    return p


def depth2tiles(depth):
    """Return the total number of tiles in a WWT tile pyramid of depth *depth*."""
    return (4 ** (depth + 1) - 1) // 3


def tiles_at_depth(depth):
    """
    Return the number of tiles in the WWT tile pyramid layer at depth *depth*.
    """
    return 4**depth


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
        raise ValueError("deeper_pos has a lower depth than shallower_pos")

    if deeper_pos.n == shallower_pos.n:
        return deeper_pos.x == shallower_pos.x and deeper_pos.y == shallower_pos.y

    return is_subtile(pos_parent(deeper_pos)[0], shallower_pos)


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
        raise ValueError("cannot take the parent of a tile position with depth < 1")

    parent = Pos(n=pos.n - 1, x=pos.x // 2, y=pos.y // 2)
    return parent, pos.x % 2, pos.y % 2


def pos_children(pos):
    """Return the children of a tile position.

    Parameters
    ----------
    pos : :class:`Pos`
        A tile position.

    Returns
    -------
    A list of four child :class:`Pos` instances. The return value is
    guaranteed to always be a list, and the order of the children will always
    be: top left, top right, bottom left, bottom right.

    """
    n, x, y = pos.n, pos.x, pos.y
    n += 1
    x *= 2
    y *= 2

    return [
        Pos(n=n, x=x, y=y),
        Pos(n=n, x=x + 1, y=y),
        Pos(n=n, x=x, y=y + 1),
        Pos(n=n, x=x + 1, y=y + 1),
    ]


def _postfix_pos(pos, depth):
    if pos.n > depth:
        return

    for immed_child in pos_children(pos):
        for item in _postfix_pos(immed_child, depth):
            yield item

    yield pos


def generate_pos(depth):
    """Generate a pyramid of tile positions.

    The generate proceeds in a broadly deeper-first fashion. In particular, if
    a position *p* is yielded, you can assume that its four children have been
    yielded previously, unless the depth of *p* is equal to *depth*.

    Parameters
    ----------
    depth : int
        The tile depth to recurse to.

    Yields
    ------
    pos : :class:`Pos`
        An individual position to process.

    """
    for item in _postfix_pos(Pos(0, 0, 0), depth):
        yield item


def guess_base_layer_level(wcs):
    from astropy import units as u
    from astropy.wcs.utils import proj_plane_pixel_area
    import math

    tile_arcmin_per_pixel = 21.095
    if wcs.celestial.wcs.cunit[0] != wcs.celestial.wcs.cunit[1]:
        import warnings

        warnings.warn(
            "Toasty is having problems guessing an appropriate level, because the image axes are described in different units"
        )

    tile_size_per_pixel = u.arcmin.to(
        wcs.celestial.wcs.cunit[0], value=tile_arcmin_per_pixel
    )

    # Assuming roughly a square image
    side_length = math.sqrt(proj_plane_pixel_area(wcs.celestial))

    level = 1
    while tile_size_per_pixel > side_length:
        level += 1
        tile_size_per_pixel /= 2

    return level


class PyramidIO(object):
    """
    Manage I/O on a tile pyramid.

    Parameters
    ----------
    base_dir : str
        The base directory containing the tiles
    scheme : str
        The tile organization scheme, should be either 'L/Y/YX' or 'LXY'
    default_format : str
        The file format to assume for the tiles if none is specified when
        reading/writing tiles. If not specified, and base_dir exists and
        contains files, these are used to guess default_format. Otherwise
        defaults to 'png'.
    """

    def __init__(self, base_dir, scheme="L/Y/YX", default_format=None):

        self._base_dir = base_dir

        if scheme == "L/Y/YX":
            self._tile_path = self._tile_path_LsYsYX
            self._scheme = "{1}/{3}/{3}_{2}"
            tile_pattern = "*/*/*_*.*"
        elif scheme == "LXY":
            self._tile_path = self._tile_path_LXY
            self._scheme = "L{1}X{2}Y{3}"
            tile_pattern = "L*X*Y*.*"
        else:
            raise ValueError(f'unsupported "scheme" option for PyramidIO: {scheme}')

        if default_format is None:
            default_format = "png"

            if os.path.exists(base_dir) and os.path.isdir(base_dir):
                for filename in glob.iglob(os.path.join(base_dir, tile_pattern)):
                    extension = os.path.splitext(filename)[1][1:]
                    if extension in SUPPORTED_FORMATS:
                        default_format = extension
                        break

        self._default_format = default_format

    def tile_path(self, pos, format=None, makedirs=True):
        """Get the path for a tile, creating its containing directories.

        Parameters
        ----------
        pos : Pos
            The tile to get a path for.test_plate_carree_ecliptic
        makedirs : optional :class:`bool`
            If True (the default), create containing directories.

        Returns
        -------
        The path as a string.

        Notes
        -----
        In its default mode this function does I/O itself — it creates the
        parent directories containing the tile path. It is not an error for
        the parent directories to already exist.
        """

        level = str(pos.n)
        ix = str(pos.x)
        iy = str(pos.y)
        return self._tile_path(level, ix, iy, format=format, makedirs=makedirs)

    def _tile_path_LsYsYX(self, level, ix, iy, format=None, makedirs=True):
        d = os.path.join(self._base_dir, level, iy)
        if makedirs:
            os.makedirs(d, exist_ok=True)
        return os.path.join(
            d, "{}_{}.{}".format(iy, ix, format or self._default_format)
        )

    def _tile_path_LXY(self, level, ix, iy, format=None, makedirs=True):
        if makedirs:
            os.makedirs(self._base_dir, exist_ok=True)

        return os.path.join(
            self._base_dir,
            "L{}X{}Y{}.{}".format(level, ix, iy, format or self._default_format),
        )

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
        return self._scheme

    def get_default_format(self):
        """
        Get the default image storage format for this pyramid.

        Returns
        -------
        The format, a string resembling ``"png"`` or ``"fits"``.
        """
        return self._default_format

    def get_default_vertical_parity_sign(self):
        """
        Get the parity sign (vertical data layout) of the tiles in this pyramid's
        default format.

        Returns
        -------
        Either +1 or -1, depending on the format.
        """

        if self._default_format is None:
            raise Exception("cannot get default parity sign without a default format")
        return get_format_vertical_parity_sign(self._default_format)

    def read_image(self, pos, default="none", masked_mode=None, format=None):
        """
        Read an Image for the specified tile position.

        Parameters
        ----------
        pos : :class:`Pos`
            The tile position to read.
        default : str, defaults to "none"
            What to do if the specified tile file does not exist. If this is
            "none", ``None`` will be returned instead of an image. If this is
            "masked", an all-masked image will be returned, using
            :meth:`~toasty.image.ImageMode.make_maskable_buffer`.
            Otherwise, :exc:`ValueError` will be raised.
        masked_mode : :class:`toasty.image.ImageMode`
            The image data mode to use if ``default`` is set to ``'masked'``.
        """
        p = self.tile_path(pos, format=format)

        loader = ImageLoader()

        try:
            img = loader.load_path(p)
        except IOError as e:
            if e.errno != 2:
                raise  # not EEXIST

            if default == "none":
                return None
            elif default == "masked":
                if masked_mode is None:
                    raise ValueError('masked_mode should be set if default="masked"')
                buf = masked_mode.make_maskable_buffer(256, 256)
                buf.clear()
                return buf
            else:
                raise ValueError('unexpected value for "default": {!r}'.format(default))

        return img

    def write_image(
        self, pos, image, format=None, mode=None, min_value=None, max_value=None
    ):
        """Write an Image for the specified tile position.

        Parameters
        ----------
        pos : :class:`Pos`
            The tile position to write.
        image : :class:`toasty.image.Image`
            The image to write.
        format : :class:`str` or ``None`` (the default)
            The format name; one of ``SUPPORTED_FORMATS``
        mode : :class:`toasty.image.ImageMode` or ``None`` (the default)
            The image data mode to use if ``format`` is a ``PIL_FORMATS``
        min_value : number or ``None`` (the default)
            An optional number only used for FITS images.
            The value represents to the lowest data value in this image and its children.
            If not set, the minimum value will be extracted from this image.
        max_value : number or ``None`` (the default)
            An optional number only used for FITS images.
            The value represents to the highest data value in this image and its children.
            If not set, the maximum value will be extracted from this image.

        """
        p = self.tile_path(pos, format=format or self._default_format)

        if image.is_completely_masked():
            # Fully masked tiles are not written to disk. If we're overwriting a
            # tile pyramid, we can't just leave any existing file lying around;
            # we must ensure that it is destroyed.
            try:
                os.unlink(p)
            except (FileNotFoundError, OSError):
                pass
        else:
            image.save(
                p,
                format=format or self._default_format,
                mode=mode,
                min_value=min_value,
                max_value=max_value,
            )

    @contextmanager
    def update_image(self, pos, default="none", masked_mode=None, format=None):
        # Plain FileLock doesn't work in HPC contexts, where we might be running
        # multiple processes on different hosts simultaneously. But it might be
        # more efficient in the non-HPC context? Should maybe choose the right
        # one automagically.
        from filelock import SoftFileLock

        p = self.tile_path(pos)

        with SoftFileLock(p + ".lock"):
            img = self.read_image(
                pos,
                default=default,
                masked_mode=masked_mode,
                format=format or self._default_format,
            )

            yield img
            self.write_image(pos, img, format=format or self._default_format)

    def clean_lockfiles(self, level):
        """
        Clean up any lockfiles created during parallelized pyramid creation.

        Parameters
        ----------
        level : :class:`int` A tile pyramid depth.

        Notes
        -----
        If you use the :meth:`update_image` method, you should call this
        function after your processing is complete to remove lockfiles that are
        created to ensure that multiple processes don't stomp on each other's
        work. The "cascade" stage doesn't need locking, so in general only the
        deepest level of the pyramid will need to be cleaned.
        """
        for x in range(0, 2**level):
            for y in range(0, 2**level):
                pos = Pos(level, x, y)
                p = self.tile_path(pos, makedirs=False) + ".lock"

                try:
                    os.unlink(p)
                except FileNotFoundError:
                    pass

    def open_metadata_for_read(self, basename):
        """
        Open a metadata file in read mode.

        Parameters
        ----------
        basename : str
            The basename of the metadata file

        Returns
        -------
        A readable and closeable file-like object returning bytes.

        """
        return open(os.path.join(self._base_dir, basename), "rb")

    def open_metadata_for_write(self, basename):
        """
        Open a metadata file in write mode.

        Parameters
        ----------
        basename : str
            The basename of the metadata file

        Returns
        -------
        A writable and closeable file-like object accepting bytes.

        """
        # We can't use the `exist_ok` kwarg because it's not available in Python 2.
        try:
            os.makedirs(self._base_dir)
        except OSError as e:
            if e.errno != 17:
                raise  # not EEXIST
        return open(os.path.join(self._base_dir, basename), "wb")


class Pyramid(object):
    """An object representing a tile pyramid.

    Pyramids may be "generic", without any associated world coordinate
    information, or TOAST-based, where each tile in the pyramid has associated
    spatial information. TOAST-based pyramids may have a spatial filter applied
    if only a subset of tiles are known to be of interest. In both cases, the
    pyramid may be limited to a "subpyramid"."""

    depth = None
    _coordsys = None
    _tile_filter = None
    _apex = Pos(n=0, x=0, y=0)

    @classmethod
    def new_generic(cls, depth):
        """
        Define a tile pyramid without TOAST coordinate information.

        Parameters
        ----------
        depth : int
            The tile depth to recurse to.

        Returns
        ------
        New :class:`Pyramid` instance.
        """
        inst = cls()
        inst.depth = depth
        inst._coordsys = None
        return inst

    @classmethod
    def new_toast(cls, depth, coordsys=None):
        """
        Define a TOAST tile pyramid.

        Parameters
        ----------
        depth : int
            The tile depth to recurse to.
        coordsys : optional :class:`ToastCoordinateSystem`
            The TOAST coordinate system to use. Default is
            :attr:`ToastCoordinateSystem.ASTRONOMICAL`.

        Returns
        ------
        New :class:`Pyramid` instance.
        """

        # We use None for the default here to not create a circular dep between
        # this and the `toast` module
        from .toast import ToastCoordinateSystem

        if coordsys is None:
            coordsys = ToastCoordinateSystem.ASTRONOMICAL

        inst = cls()
        inst.depth = depth
        inst._coordsys = coordsys
        return inst

    @classmethod
    def new_toast_filtered(cls, depth, tile_filter, coordsys=None):
        """
        Define a TOAST tile pyramid where some tiles are filtered out.

        Parameters
        ----------
        depth : int
            The tile depth to recurse to.
        tile_filter : function(Tile)->bool
            A tile filter function; only tiles for which the function returns True will
            be investigated.
        coordsys : optional :class:`ToastCoordinateSystem`
            The TOAST coordinate system to use. Default is
            :attr:`ToastCoordinateSystem.ASTRONOMICAL`.

        Returns
        ------
        New :class:`Pyramid` instance.
        """
        from .toast import ToastCoordinateSystem

        if coordsys is None:
            coordsys = ToastCoordinateSystem.ASTRONOMICAL

        inst = cls()
        inst.depth = depth
        inst._coordsys = coordsys
        inst._tile_filter = tile_filter
        return inst

    def subpyramid(self, apex):
        if apex.n > self.depth:
            raise ValueError(
                "cannot select a subpyramid past the parent pyramid's depth"
            )

        if self._apex.n != 0:
            raise Exception("cannot repeatedly call subpyramid() on a pyramid")

        self._apex = apex

        # In non-TOAST pyramids, it's easy to subpyramid analytically. But in
        # TOAST, we need to implement the subpyramid as a tile filter, because
        # (1) the user might have their own tile filter and (2) we still need to
        # start at the top to compute coordinates.

        if self._coordsys is not None:
            pos_filter = _make_position_filter(apex)

            if self._tile_filter is None:
                self._tile_filter = lambda t: pos_filter(t.pos)
            else:
                user_filter = self._tile_filter
                self._tile_filter = lambda t: pos_filter(t.pos) and user_filter(t)

        return self

    def _generator(self):
        if self._coordsys is None:
            # Not TOAST - we can generate positions much more efficiently
            # if we don't have to compute the TOAST coordinates.

            na = self._apex.n

            if na == 0:
                # Not doing a subpyramid - easy
                for pos in generate_pos(self.depth):
                    yield pos, None
            else:
                # Subpyramid case is still not too hard.

                for pos in generate_pos(self.depth - na):
                    n_eff = pos.n + na
                    x_eff = pos.x + self._apex.x * 2**pos.n
                    y_eff = pos.y + self._apex.y * 2**pos.n
                    yield Pos(n_eff, x_eff, y_eff), None

                # Keep compatible behavior with the TOAST version by producing
                # positions up to level 0.

                if na > 0:
                    ipos = self._apex

                    while True:
                        ipos = pos_parent(ipos)[0]
                        yield ipos, None

                        if ipos.n == 0:
                            break
        else:
            from . import toast

            if self._tile_filter is None:
                gen = toast.generate_tiles(
                    self.depth, coordsys=self._coordsys, bottom_only=False
                )
            else:
                gen = toast.generate_tiles_filtered(
                    self.depth,
                    self._tile_filter,
                    coordsys=self._coordsys,
                    bottom_only=False,
                )

            for tile in gen:
                yield tile.pos, tile

            yield Pos(n=0, x=0, y=0), None

    def _make_iter_reducer(self, default_value=None):
        return PyramidReductionIterator(self, default_value=default_value)

    def count_live_tiles(self):
        if self._tile_filter is None:
            # In this case, we know analytically.
            return depth2tiles(self.depth - self._apex.n)

        riter = self._make_iter_reducer(default_value=0)

        for _pos, _tile, is_leaf, data in riter:
            if is_leaf:
                count = 1
            else:
                count = data[0] + data[1] + data[2] + data[3]

                # Only count this tile as "live" if it has any live children.
                if count:
                    count += 1

            riter.set_data(count)

        return riter.result()

    def count_operations(self):
        if self._tile_filter is None:
            # In this case, we know analytically.
            return depth2tiles(self.depth - (self._apex.n + 1))

        riter = self._make_iter_reducer(default_value=(False, 0))

        for _pos, _tile, is_leaf, data in riter:
            if is_leaf:
                is_live = True
                ops = 0
            else:
                is_live = data[0][0] or data[1][0] or data[2][0] or data[3][0]
                ops = data[0][1] + data[1][1] + data[2][1] + data[3][1]

                if is_live:
                    ops += 1

            riter.set_data((is_live, ops))

        return riter.result()[1]

    def walk(
        self,
        callback,
        parallel=None,
        cli_progress=False,
    ):
        from .par_util import resolve_parallelism

        parallel = resolve_parallelism(parallel)

        if parallel > 1:
            self._walk_parallel(callback, cli_progress, parallel)
        else:
            self._walk_serial(callback, cli_progress)

    def _walk_serial(self, callback, cli_progress):
        import time

        if self.depth > 9 and self._tile_filter is not None:
            # This is around where there are enough tiles that the prep stage
            # might take a noticeable amount of time.
            print("Counting tiles ...")
            t0 = time.time()

        total = self.count_operations()

        if self.depth > 9 and self._tile_filter is not None:
            print(f"... {time.time() - t0:.1f}s elapsed")

        # In serial mode, we can do actual processing as another reduction:

        riter = self._make_iter_reducer(default_value=False)

        with progress_bar(total=total, show=cli_progress) as progress:
            for pos, _tile, is_leaf, data in riter:
                if is_leaf:
                    is_live = True
                else:
                    is_live = data[0] or data[1] or data[2] or data[3]

                    if is_live:
                        callback(pos)
                        progress.update(1)

                riter.set_data(is_live)

    def _walk_parallel(self, callback, cli_progress, parallel):
        import multiprocessing as mp
        from queue import Empty
        import time
        from tqdm import tqdm

        # When dispatching we keep track of finished tiles (reported in
        # `done_queue`) and notify workers when new tiles are ready to process
        # (`ready_queue`).

        ready_queue = mp.Queue()
        done_queue = mp.Queue(maxsize=2 * parallel)
        done_event = mp.Event()

        # Walk the pyramid in preparation. We have three things to do: (1) count
        # number of operations; (2) seed ready queue; (3) prefill "readiness"
        # table for cases where not all of child tiles are "live".
        #
        # We could optimize this a lot for the case when there's no tile filter
        # -- the number of operations is knowable analytically, all tiles are
        # live, and the ready queue can be filled automatically.

        if self.depth > 9:
            # This is around where there are enough tiles that the prep stage
            # might take a noticeable amount of time.
            print("Counting tiles and preparing data structures ...")
            t0 = time.time()

        readiness = {}
        riter = self._make_iter_reducer(default_value=(False, 0))

        for pos, _tile, is_leaf, data in riter:
            # Counting ops - same as count_operations()

            if is_leaf:
                is_live = True
                ops = 0
            else:
                is_live = data[0][0] or data[1][0] or data[2][0] or data[3][0]
                ops = data[0][1] + data[1][1] + data[2][1] + data[3][1]

                if is_live:
                    ops += 1

            # Prepping readiness:

            if not is_leaf:
                pre_readied = 0

                for i in range(4):
                    if not data[i][0]:
                        pre_readied |= 1 << i

                if pre_readied:
                    readiness[pos] = pre_readied

            # Seeding ready queue

            if pos.n == self.depth - 1 and is_live:
                ready_queue.put(pos)

            riter.set_data((is_live, ops))

        total = riter.result()[1]

        if self.depth > 9:
            print(
                f"... {time.time() - t0:.1f}s elapsed; queue size {ready_queue.qsize()}; ready map size {len(readiness)}"
            )

        # Ready to create workers! These workers pick up tiles that are ready to
        # process and do the merging.

        workers = []

        for _ in range(parallel):
            w = mp.Process(
                target=_mp_walk_worker,
                args=(done_queue, ready_queue, done_event, callback),
            )
            w.daemon = True
            w.start()
            workers.append(w)

        # Start dispatching tiles

        with progress_bar(total=total, show=cli_progress) as progress:
            while True:
                # Did anybody finish a tile?
                try:
                    pos = done_queue.get(True, timeout=1)
                except (OSError, ValueError, Empty):
                    # OSError or ValueError => queue closed. This signal seems not to
                    # cross multiprocess lines, though.
                    continue

                progress.update(1)

                # If we did our final tile, well, we're done.
                if pos == self._apex:
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


class PyramidReductionIterator(object):
    def __init__(self, pyramid, default_value=None):
        self._pyramid = pyramid
        self._generator = pyramid._generator()
        self._d = default_value
        self._levels = [[0, 0, self._d, self._d, self._d, self._d]]
        self._most_recent_pos = None
        self._got_data = False
        self._final_result = default_value

    def __iter__(self):
        if self._generator is None:
            raise Exception(f"can only iterate {self} once")
        return self

    def _ensure_levels(self, pos):
        n_before = len(self._levels)

        if pos.n < n_before:
            return

        new_levels = []
        ipos = pos

        while ipos.n >= n_before:
            new_levels.append([ipos.x, ipos.y, self._d, self._d, self._d, self._d])
            ipos = pos_parent(ipos)[0]

        self._levels += new_levels[::-1]

    def __next__(self):
        if self._most_recent_pos is not None and not self._got_data:
            raise Exception(
                "cannot continue to next item without setting data for the previous"
            )

        if self._generator is None:
            raise StopIteration()

        try:
            pos, info = next(self._generator)
        except StopIteration:
            self._generator = None
            raise StopIteration()

        # If we're subpyramiding and the user has a tile filter that's disjoint
        # with the subpyramid, the generator will return one of the parents of
        # the apex. If that's the case, there are no positions to reduce.
        if pos.n < self._pyramid._apex.n:
            self._generator = None
            raise StopIteration()

        is_leaf = pos.n == self._pyramid.depth

        self._ensure_levels(pos)
        assert len(self._levels) == pos.n + 1
        assert self._levels[-1][0] == pos.x
        assert self._levels[-1][1] == pos.y
        child_data = self._levels.pop()[2:]

        self._most_recent_pos = pos
        self._got_data = False
        return pos, info, is_leaf, child_data

    def set_data(self, value):
        if self._got_data:
            raise Exception("cannot set data repeatedly for the same position")

        if self._most_recent_pos == self._pyramid._apex:
            self._generator = iter([])
            self._final_result = value
        else:
            ppos, ix, iy = pos_parent(self._most_recent_pos)
            self._ensure_levels(ppos)
            assert self._levels[ppos.n][0] == ppos.x
            assert self._levels[ppos.n][1] == ppos.y
            self._levels[ppos.n][2 + 2 * iy + ix] = value

        self._got_data = True

    def result(self):
        if self._generator is not None:
            raise Exception("cannot get final reduction result yet")

        return self._final_result


def _make_position_filter(apex):
    """
    A simple pyramid filter that only accepts positions leading up to a
    specified subpyramid "apex" position, and all below it.

    We're a bit lazy here where we accept *all* positions deeper than the apex,
    when in principle we should only accept ones that are its descendants. But
    we know that in a filtered walk the only deeper positions that we'll ever
    visit will be such descendants, so we can get away with it.
    """

    level = apex.n
    parent_positions = set()

    while True:
        parent_positions.add(apex)

        if apex.n == 0:
            break

        apex = pos_parent(apex)[0]

    def position_filter(pos):
        if pos.n > level:
            return True

        return pos in parent_positions

    return position_filter


def _mp_walk_worker(done_queue, ready_queue, done_event, callback):
    """
    Process tiles that are ready.
    """
    from queue import Empty

    while True:
        try:
            pos = ready_queue.get(True, timeout=1)
        except Empty:
            if done_event.is_set():
                break
            continue

        callback(pos)
        done_queue.put(pos)
