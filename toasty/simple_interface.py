from toasty import builder, collection, pyramid, multi_tan, multi_wcs
import reproject


def toast(fits_list, **kwargs):
    # TODO docs

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
