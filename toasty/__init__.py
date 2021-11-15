# -*- mode: python; coding: utf-8 -*-
# Copyright 2013-2021 Chris Beaumont and the AAS WorldWide Telescope project
# Licensed under the MIT License.

from __future__ import absolute_import, division, print_function


def tile_fits(fits, out_dir=None, cli_progress=False, **kwargs):
    """
    Process a file or a list of FITS files into a tile pyramid with
    a common tangential projection.

    Parameters
    ----------
    fits : str or list of str
        A single path or a list of paths to FITS files to be processed.
    out_dir : optional str
        A path to the output directory where all the tiled fits will be
        located. If not set, the output directory will be at the location of
        the first FITS file.
    cli_progress : optional boolean, defaults False
        If true, a progress bar will be printed to the terminal using tqdm.
    kwargs
        Settings for the `toasty` tiling process. Common
        settings include 'hdu_index' and 'blankval'.

    Returns
    -------
    out_dir : :class:`str`
        The relative path to the base directory where the tiled files are located
    bld : :class:`~toasty.builder.Builder`
        State for the imagery data set that's been assembled.
    """

    from toasty import builder, collection, pyramid, multi_tan, multi_wcs
    import reproject

    if isinstance(fits, str):
        fits = [fits]

    fits = list(fits)

    if out_dir is None:
        first_file_name = fits[0].split('.gz')[0]
        out_dir = first_file_name[:first_file_name.rfind('.')] + '_tiled'

    pio = pyramid.PyramidIO(out_dir, default_format='fits')
    bld = builder.Builder(pio)
    coll = collection.SimpleFitsCollection(fits, **kwargs)
    if cli_progress:
        print('Tiling base layer (Step 1 of 2)')
    if coll._is_multi_tan():
        tile_processor = multi_tan.MultiTanProcessor(coll)
        tile_processor.compute_global_pixelization(bld)
        tile_processor.tile(pio, cli_progress=cli_progress, **kwargs)
    else:
        tile_processor = multi_wcs.MultiWcsProcessor(coll)
        tile_processor.compute_global_pixelization(bld)
        tile_processor.tile(pio, reproject.reproject_interp, cli_progress=cli_progress, **kwargs)

    if cli_progress:
        print('Downsampling (Step 2 of 2)')
    bld.cascade(cli_progress=cli_progress, **kwargs)

    # Using the file name of the first FITS file as the image collection name
    bld.set_name(out_dir.split('/')[-1])
    bld.write_index_rel_wtml()

    return out_dir, bld
