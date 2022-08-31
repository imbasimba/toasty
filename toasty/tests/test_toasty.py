# -*- mode: python; coding: utf-8 -*-
# Copyright 2021 the AAS WorldWide Telescope project
# Licensed under the MIT License.

from __future__ import absolute_import, division, print_function

import pytest
from . import test_path
from .. import TilingMethod, tile_fits
from wwt_data_formats.enums import ProjectionType
from shutil import rmtree
from pathlib import Path

try:
    from astropy.io import fits

    HAS_ASTRO = True
except ImportError:
    HAS_ASTRO = False


class TestToasty(object):
    @pytest.mark.skipif("not HAS_ASTRO")
    def test_tile_fits_tan(self):
        out_dir_input = "test_tiled"
        out_dir, bld = tile_fits(
            fits=test_path("herschel_spire.fits.gz"),
            out_dir=out_dir_input,
            tiling_method=TilingMethod.TAN,
            cli_progress=True,
            override=True,
        )
        # source image is smaller than one tile (256x256),so it is conveted to a sky image
        assert bld.imgset.projection == ProjectionType.SKY_IMAGE
        assert out_dir == out_dir_input
        assert Path(out_dir, "index_rel.wtml").is_file()
        assert Path(out_dir, "0", "0", "0_0.fits").is_file()
        assert bld.imgset.url == "{1}/{3}/{3}_{2}.fits"
        rmtree(out_dir)

        # Only testing with a multi tan collection, since multi WCS
        # collections take a significant time to process
        out_dir, bld = tile_fits(
            fits=[test_path("wcs512.fits.gz"), test_path("wcs512.fits.gz")],
            tiling_method=TilingMethod.TAN,
            override=True,
        )
        assert bld.imgset.projection == ProjectionType.TAN
        assert out_dir == test_path("wcs512_tiled")
        assert Path(out_dir, "index_rel.wtml").is_file()
        assert Path(out_dir, "0", "0", "0_0.fits").is_file()
        rmtree(out_dir)

    @pytest.mark.skipif("not HAS_ASTRO")
    def test_tile_fits_toast(self):
        out_dir_input = "test_tiled"
        out_dir, bld = tile_fits(
            fits=test_path("herschel_spire.fits.gz"),
            out_dir=out_dir_input,
            tiling_method=TilingMethod.TOAST,
            cli_progress=True,
            override=True,
        )
        assert bld.imgset.projection == ProjectionType.TOAST
        assert out_dir == out_dir_input
        assert Path(out_dir, "index_rel.wtml").is_file()
        assert Path(out_dir, "0", "0", "0_0.fits").is_file()
        assert bld.imgset.url == "{1}/{3}/{3}_{2}.fits"
        rmtree(out_dir)

        out_dir, bld = tile_fits(
            fits=[test_path("wcs512.fits.gz")],
            tiling_method=TilingMethod.TOAST,
            override=True,
        )
        assert bld.imgset.projection == ProjectionType.TOAST
        assert out_dir == test_path("wcs512_tiled_TOAST")
        assert Path(out_dir, "index_rel.wtml").is_file()
        assert Path(out_dir, "0", "0", "0_0.fits").is_file()
        rmtree(out_dir)
