from toasty import builder, collection, pyramid, multi_tan, multi_wcs
import reproject


def toast_fits_list(fits_list, **kwargs):
    """
    Process a file or a list of FITS files into a tile pyramid with
    a common tangential projection.

    Parameters
    ----------
    fits_list : str or list of str
        A single path or a list of paths to FITS files to be processed.
    kwargs
        Settings for the `toasty` tiling process. Common
        settings include 'hdu_index' and 'blankval'.

    Returns
    -------
    out_dir : :class:`str`
        The relative path to the base directory where the tiled files are located
    image_set_pattern : :class:`str`
        The pattern to be used to access specific tiles
    """

    if not isinstance(fits_list, list):
        fits_list = [fits_list]

    out_dir = fits_list[0].split('.')[0]

    pio = pyramid.PyramidIO(out_dir, default_format='fits')
    bld = builder.Builder(pio)
    coll = collection.SimpleFitsCollection(fits_list, **kwargs)
    print('Processing FITS - Step 1 of 2')
    if coll.is_multi_tan():
        tile_processor = multi_tan.MultiTanProcessor(coll)
        tile_processor.compute_global_pixelization(bld)
        tile_processor.tile(pio, cli_progress=True)
    else:
        tile_processor = multi_wcs.MultiWcsProcessor(coll)
        tile_processor.compute_global_pixelization(bld)
        tile_processor.tile(pio, reproject.reproject_interp, cli_progress=True)

    print('Processing FITS - Step 2 of 2')
    bld.cascade(cli_progress=True)

    # Using the file name of the first FITS file as the image collection name
    bld.set_name(out_dir.split('/')[-1])
    bld.write_index_rel_wtml()

    return out_dir, bld.imgset.url
