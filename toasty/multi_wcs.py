# -*- mode: python; coding: utf-8 -*-
# Copyright 2020 the AAS WorldWide Telescope project
# Licensed under the MIT License.

"""
Generate tiles from a collection of images with associated WCS coordinate
systems.

This module has the following Python package dependencies:

- astropy
- ccdproc (to trim FITS CCD datasets)
- reproject
- shapely (to optimize the projection in reproject)

"""

__all__ = '''
make_lsst_directory_loader_generator
MultiWcsProcessor
'''.split()

import numpy as np
from tqdm import tqdm
import warnings

from .image import Image, ImageMode
from .study import StudyTiling


def make_lsst_directory_loader_generator(dirname, unit=None):
    from astropy.io import fits
    from astropy.nddata import ccddata
    import ccdproc
    from glob import glob
    from os.path import join

    def loader_generator(actually_load_data):
        # Ideally we would just return a shape instead of an empty data array in
        # the case where actually_load_data is false, but we can't use
        # `ccdproc.trim_image()` without having a CCDData in hand, so to get the
        # right shape we're going to need to create a full CCDData anyway.

        for fits_path in glob(join(dirname, '*.fits')):
            # `astropy.nddata.ccddata.fits_ccddata_reader` only opens FITS from
            # filenames, not from an open HDUList, which means that creating
            # multiple CCDDatas from the same FITS file rapidly becomes
            # inefficient. So, we emulate its logic.

            with fits.open(fits_path) as hdu_list:
                for idx, hdu in enumerate(hdu_list):
                    if idx == 0:
                        header0 = hdu.header
                    else:
                        hdr = hdu.header
                        hdr.extend(header0, unique=True)

                        # This ccddata function often generates annoying warnings
                        with warnings.catch_warnings():
                            warnings.simplefilter('ignore')
                            hdr, wcs = ccddata._generate_wcs_and_update_header(hdr)

                        # Note: we skip all the unit-handling logic here since the LSST
                        # sim data I'm using don't have anything useful.

                        if actually_load_data:
                            data = hdu.data
                        else:
                            data = np.empty(hdu.shape, dtype=np.void)

                        ccd = ccddata.CCDData(data, meta=hdr, unit=unit, wcs=wcs)

                        ccd = ccdproc.trim_image(ccd, fits_section=ccd.header['DATASEC'])
                        yield (f'{fits_path}:{idx}', ccd)

    return loader_generator


class MultiWcsDescriptor(object):
    ident = None
    in_shape = None
    in_wcs = None

    imin = None
    imax = None
    jmin = None
    jmax = None

    sub_tiling = None


class MultiWcsProcessor(object):
    def __init__(self, loader_generator):
        self._loader_generator = loader_generator


    def compute_global_pixelization(self):
        from reproject.mosaicking.wcs_helpers import find_optimal_celestial_wcs

        # Load up current WCS information for all of the inputs

        def create_descriptor(loader_data):
            desc = MultiWcsDescriptor()
            desc.ident = loader_data[0]
            desc.in_shape = loader_data[1].shape
            desc.in_wcs = loader_data[1].wcs
            return desc

        self._descs = [create_descriptor(tup) for tup in self._loader_generator(False)]

        # Compute the optimal tangential tiling that fits all of them.

        self._combined_wcs, self._combined_shape = find_optimal_celestial_wcs(
            ((desc.in_shape, desc.in_wcs) for desc in self._descs),
            auto_rotate = True,
            projection = 'TAN',
        )

        self._tiling = StudyTiling(self._combined_shape[1], self._combined_shape[0])

        # While we're here, figure out how each input will map onto the global
        # tiling. This makes sure that nothing funky happened during the
        # computation and allows us to know how many tiles we'll have to visit.

        self._n_todo = 0

        for desc in self._descs:
            # XXX: this functionality is largely copied from
            # `reproject.mosaicking.coadd.reproject_and_coadd`, and redundant
            # with it, but it's sufficiently different that I think the best
            # approach is to essentially fork the implementation.

            # Figure out where this array lands in the mosaic.

            ny, nx = desc.in_shape
            xc = np.array([-0.5, nx - 0.5, nx - 0.5, -0.5])
            yc = np.array([-0.5, -0.5, ny - 0.5, ny - 0.5])
            xc_out, yc_out = self._combined_wcs.world_to_pixel(desc.in_wcs.pixel_to_world(xc, yc))

            if np.any(np.isnan(xc_out)) or np.any(np.isnan(yc_out)):
                raise Exception(f'segment {desc.ident} does not fit within the global mosaic')

            desc.imin = max(0, int(np.floor(xc_out.min() + 0.5)))
            desc.imax = min(self._combined_shape[1], int(np.ceil(xc_out.max() + 0.5)))
            desc.jmin = max(0, int(np.floor(yc_out.min() + 0.5)))
            desc.jmax = min(self._combined_shape[0], int(np.ceil(yc_out.max() + 0.5)))

            # Compute the sub-tiling now so that we can count how many total
            # tiles we'll need to process. Note that the combined WCS coordinate
            # system has y=0 on the bottom, whereas the tiling coordinate system
            # has y=0 at the top. So we need to invert the coordinates
            # vertically when determining the sub-tiling.

            if desc.imax < desc.imin or desc.jmax < desc.jmin:
                raise Exception(f'segment {desc.ident} maps to zero size in the global mosaic')

            desc.sub_tiling = self._tiling.compute_for_subimage(
                desc.imin,
                self._combined_shape[0] - desc.jmax,
                desc.imax - desc.imin,
                desc.jmax - desc.jmin,
            )

            self._n_todo += desc.sub_tiling.count_populated_positions()

        return self  # chaining convenience


    def tile(self, pio, reproject_function, parallel=None, cli_progress=False, **kwargs):
        """
        Tile!!!!

        Parameters
        ----------
        pio : :class:`toasty.pyramid.PyramidIO`
            A :class:`~toasty.pyramid.PyramidIO` instance to manage the I/O with
            the tiles in the tile pyramid.
        reproject_function : TKTK
            TKTK
        parallel : integer or None (the default)
            The level of parallelization to use. If unspecified, defaults to using
            all CPUs. If the OS does not support fork-based multiprocessing,
            parallel processing is not possible and serial processing will be
            forced. Pass ``1`` to force serial processing.
        cli_progress : optional boolean, defaults False
            If true, a progress bar will be printed to the terminal using tqdm.

        """
        from .par_util import resolve_parallelism
        parallel = resolve_parallelism(parallel)

        if parallel > 1:
            self._tile_parallel(pio, reproject_function, cli_progress, parallel, **kwargs)
        else:
            self._tile_serial(pio, reproject_function, cli_progress, **kwargs)


    def _tile_serial(self, pio, reproject_function, cli_progress, **kwargs):
        with tqdm(total=self._n_todo, disable=not cli_progress) as progress:
            for (ident, ccd), desc in zip(self._loader_generator(True), self._descs):
                # XXX: more copying from
                # `reproject.mosaicking.coadd.reproject_and_coadd`.

                wcs_out_indiv = self._combined_wcs[desc.jmin:desc.jmax, desc.imin:desc.imax]
                shape_out_indiv = (desc.jmax - desc.jmin, desc.imax - desc.imin)

                array = reproject_function(
                    (ccd.data, ccd.wcs),
                    output_projection=wcs_out_indiv,
                    shape_out=shape_out_indiv,
                    return_footprint=False,
                    **kwargs
                )

                # Once again, FITS coordinates have y=0 at the bottom and our
                # coordinates have y=0 at the top, so we need a vertical flip.
                image = Image.from_array(array.astype(np.float32)[::-1])

                for pos, width, height, image_x, image_y, tile_x, tile_y in desc.sub_tiling.generate_populated_positions():
                    iy_idx = slice(image_y, image_y + height)
                    ix_idx = slice(image_x, image_x + width)
                    by_idx = slice(tile_y, tile_y + height)
                    bx_idx = slice(tile_x, tile_x + width)

                    with pio.update_image(pos, masked_mode=image.mode, default='masked') as basis:
                        image.update_into_maskable_buffer(basis, iy_idx, ix_idx, by_idx, bx_idx)

                    progress.update(1)

        if cli_progress:
            print()


    def _tile_parallel(self, pio, reproject_function, cli_progress, parallel, **kwargs):
        import multiprocessing as mp

        # Start up the workers

        queue = mp.Queue(maxsize = 2 * parallel)
        workers = []

        for _ in range(parallel):
            w = mp.Process(target=_mp_tile_worker, args=(queue, pio, reproject_function, kwargs))
            w.daemon = True
            w.start()
            workers.append(w)

        # Send out them segments

        with tqdm(total=len(self._descs), disable=not cli_progress) as progress:
            for (ident, ccd), desc in zip(self._loader_generator(True), self._descs):
                wcs_out_indiv = self._combined_wcs[desc.jmin:desc.jmax, desc.imin:desc.imax]
                queue.put((ident, ccd, desc, wcs_out_indiv))
                progress.update(1)

            queue.close()

            for w in workers:
                w.join()

        if cli_progress:
            print()


def _mp_tile_worker(queue, pio, reproject_function, kwargs):
    """
    Generate and enqueue the tiles that need to be processed.
    """
    from queue import Empty

    while True:
        try:
            # un-pickling WCS objects always triggers warnings right now
            with warnings.catch_warnings():
                warnings.simplefilter('ignore')
                ident, ccd, desc, wcs_out_indiv = queue.get(True, timeout=1)
        except (OSError, ValueError, Empty):
            # OSError or ValueError => queue closed. This signal seems not to
            # cross multiprocess lines, though.
            break

        shape_out_indiv = (desc.jmax - desc.jmin, desc.imax - desc.imin)

        array = reproject_function(
            (ccd.data, ccd.wcs),
            output_projection=wcs_out_indiv,
            shape_out=shape_out_indiv,
            return_footprint=False,
            **kwargs
        )

        # Once again, FITS coordinates have y=0 at the bottom and our
        # coordinates have y=0 at the top, so we need a vertical flip.
        image = Image.from_array(array.astype(np.float32)[::-1])

        for pos, width, height, image_x, image_y, tile_x, tile_y in desc.sub_tiling.generate_populated_positions():
            iy_idx = slice(image_y, image_y + height)
            ix_idx = slice(image_x, image_x + width)
            by_idx = slice(tile_y, tile_y + height)
            bx_idx = slice(tile_x, tile_x + width)

            with pio.update_image(pos, masked_mode=image.mode, default='masked') as basis:
                image.update_into_maskable_buffer(basis, iy_idx, ix_idx, by_idx, bx_idx)
