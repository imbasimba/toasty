# -*- mode: python; coding: utf-8 -*-
# Copyright 2013-2021 Chris Beaumont and the AAS WorldWide Telescope project
# Licensed under the MIT License.

from __future__ import absolute_import, division, print_function


__all__ = [
    "tile_fits",
    "TilingMethod",
]

from enum import Enum


class TilingMethod(Enum):
    UNTILED = 1
    TAN = 2
    TOAST = 3
    HIPS = 4
    AUTO_DETECT = 5


def tile_fits(
    fits,
    out_dir=None,
    hdu_index=None,
    override=False,
    cli_progress=False,
    parallel=None,
    tiling_method=TilingMethod.AUTO_DETECT,
    blankval=None,
    **kwargs
):
    """
    Process a file or a list of FITS files into a tile pyramid in the form of either a common tangential projection,
    TOAST, or HiPS.

    Parameters
    ----------
    fits : str or list of str
        A single path or a list of paths to FITS files to be processed.
    out_dir : optional str, defaults to None
        A path to the output directory where all the tiled fits will be located. If not set, the output directory will
        be at the location of the first FITS file.
    hdu_index : optional int or list of int, defaults to None
        Use this parameter to specify which HDU to tile. If the *fits* input is a list of FITS, you can specify the
        hdu_index of each FITS by using a list of integers like this: [0, 2, 1]. If hdu_index is not set, toasty will
        use the first HDU with tilable content in each FITS.
    override : optional boolean, defaults to False
        If there is already a tiled FITS in *out_dir*, the tiling process is skipped and the content in *out_dir* is
        served. To override the content in *out_dir*, set *override* to True.
    cli_progress : optional boolean, defaults to False
        If true, progress messages will be printed as the FITS files are being processed.
    parallel : integer or None (the default)
        The level of parallelization to use. If unspecified, defaults to using
        all CPUs. If the OS does not support fork-based multiprocessing,
        parallel processing is not possible and serial processing will be
        forced. Pass ``1`` to force serial processing.
    tiling_method : optional :class:`~toasty.TilingMethod`
        Can be used to force a specific tiling method, i.e. tiled tangential projection, TOAST, or HiPS. Defaults to
        auto-detection, which choses the most appropriate method.
    blankval : optional number, default None
        An image value to treat as undefined in all FITS inputs.
    kwargs
        Settings for the tiling process.

    Returns
    -------
    out_dir : :class:`str`
        The relative path to the base directory where the tiled files are located
    bld : :class:`~toasty.builder.Builder`
        State for the imagery data set that's been assembled.
    """
    # Importing here to keep toasty namespace clean:
    from toasty import collection, fits_tiler

    coll = collection.load(fits, hdu_index=hdu_index, blankval=blankval)
    tiler = fits_tiler.FitsTiler(
        coll,
        out_dir=out_dir,
        tiling_method=tiling_method,
    )
    tiler.tile(
        cli_progress=cli_progress, parallel=parallel, override=override, **kwargs
    )
    return tiler.out_dir, tiler.builder
