# -*- mode: python; coding: utf-8 -*-
# Copyright 2013-2021 Chris Beaumont and the AAS WorldWide Telescope project
# Licensed under the MIT License.

from __future__ import absolute_import, division, print_function


def tile_fits(fits, out_dir=None, hdu_index=None, override=False, cli_progress=False, force_hipsgen=False,
              force_tan=False, **kwargs):
    """
    Process a file or a list of FITS files into a tile pyramid using either a common tangential projection or HiPSgen.

    Parameters
    ----------
    fits : str or list of str
        A single path or a list of paths to FITS files to be processed.
    out_dir : optional str, defaults to None
        A path to the output directory where all the tiled fits will be located. If not set, the output directory will
        be at the location of the first FITS file.
    hdu_index : optional int or list of int, defaults to None
        Use this parameter to specify which HDU to tile. If the `fits` input is a list of FITS, you can specify the
        hdu_index of each FITS by using a list of integers like this: [0, 2, 1]. If hdu_index is not set, toasty will
        use the first HDU with tilable content in each FITS.
    override : optional boolean, defaults to False
        If there is already a tiled FITS in `out_dir`, the tiling process is skipped and the content in `out_dir` is
        served. To override the content in `out_dir`, set `override` to True.
    cli_progress : optional boolean, defaults to False
        If true, progress messages will be printed as the FITS files are being processed.
    force_hipsgen : optional boolean, defaults to False
        Force usage of HiPSgen tiling over tangential projection. If this and `force_tan` is set to False, this method
        will figure out when to use the different projections. Tangential projection for smaller angular areas and
        HiPSgen larger regions of the sky.
    force_tan : optional boolean, defaults to False
        Force usage of tangential projection tiling over HiPSgen. If this and `force_hipsgen` is set to False, this
        method will figure out when to use the different projections. Tangential projection for smaller angular areas
        and HiPSgen larger regions of the sky.
    kwargs
        Settings for the `toasty` tiling process. For example, 'blankval'.

    Returns
    -------
    out_dir : :class:`str`
        The relative path to the base directory where the tiled files are located
    bld : :class:`~toasty.builder.Builder`
        State for the imagery data set that's been assembled.
    """

    # Importing here to keep toasty namespace clean
    from toasty import fits_tiler, pyramid, builder
    import os

    if isinstance(fits, str):
        fits = [fits]

    fits = list(fits)

    tiler = fits_tiler.FitsTiler()

    use_hipsgen = force_hipsgen or (tiler.fits_covers_large_area(fits, hdu_index) and
                                    tiler.is_java_installed() and not force_tan)

    if out_dir is None:
        first_file_name = fits[0].split('.gz')[0]
        out_dir = first_file_name[:first_file_name.rfind('.')] + '_tiled'
        if use_hipsgen:
            out_dir += '_HiPS'

    if os.path.isdir(out_dir):
        if cli_progress:
            print('Folder already exist')
        if override:
            import shutil
            shutil.rmtree(out_dir)
        else:
            if cli_progress:
                print('Using existing tiles')
            pio = pyramid.PyramidIO(out_dir, default_format='fits')
            bld = builder.Builder(pio)
            bld.set_name(out_dir.split('/')[-1])
            if os.path.exists('{0}/properties'.format(out_dir)):
                bld = tiler.copy_hips_properties_to_builder(bld, out_dir)
            return out_dir, bld

    if use_hipsgen:
        return tiler.tile_hips(fits, out_dir, hdu_index, cli_progress)

    return tiler.tile_tan(fits, out_dir, hdu_index, cli_progress, **kwargs)
