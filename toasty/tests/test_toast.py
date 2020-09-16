# -*- mode: python; coding: utf-8 -*-
# Copyright 2013-2020 Chris Beaumont and the AAS WorldWide Telescope project
# Licensed under the MIT License.

from __future__ import absolute_import, division, print_function

import os
from xml.dom.minidom import parseString
from tempfile import mkstemp, mkdtemp
from shutil import rmtree

import pytest
import numpy as np

try:
    import healpy as hp
    from astropy.io import fits
    HAS_ASTRO = True
except ImportError:
    HAS_ASTRO = False

from . import test_path
from .. import toast
from ..image import ImageLoader, ImageMode
from ..pyramid import Pos, PyramidIO
from ..samplers import plate_carree_sampler, healpix_fits_file_sampler
from ..toast import sample_layer


def test_mid():
    from .._libtoasty import mid

    result = mid((0, 0), (np.pi / 2, 0))
    expected = np.pi / 4, 0
    np.testing.assert_array_almost_equal(result, expected)

    result = mid((0, 0), (0, 1))
    expected = 0, .5
    np.testing.assert_array_almost_equal(result, expected)


def test_area():
    MAX_DEPTH = 6
    areas = {}

    for t in toast.generate_tiles(MAX_DEPTH, bottom_only=False):
        a = areas.get(t.pos.n, 0)
        areas[t.pos.n] = a + toast.toast_tile_area(t)

    for d in range(1, MAX_DEPTH + 1):
        np.testing.assert_almost_equal(areas[d], 4 * np.pi)


def image_test(expected, actual, err_msg):
    resid = np.abs(1. * actual - expected)
    if np.median(resid) < 15:
        return

    _, pth = mkstemp(suffix='.png')
    import PIL.Image
    PIL.Image.fromarray(np.hstack((expected, actual))).save(pth)
    pytest.fail("%s. Saved to %s" % (err_msg, pth))


class TestSampleLayer(object):
    def setup_method(self, method):
        self.base = mkdtemp()
        self.pio = PyramidIO(self.base)

    def teardown_method(self, method):
        rmtree(self.base)

    def verify_level1(self, mode):
        for n, x, y in [(1, 0, 0), (1, 0, 1), (1, 1, 0), (1, 1, 1)]:
            ref_path = test_path('earth_toasted_sky', str(n), str(y), "%i_%i.png" % (y, x))
            expected = ImageLoader().load_path(ref_path).asarray()
            if mode == ImageMode.F32:
                expected = expected.mean(axis=2)

            pos = Pos(n=n, x=x, y=y)
            observed = self.pio.read_toasty_image(pos, mode).asarray()

            image_test(expected, observed, 'Failed for %s' % ref_path)

    def test_plate_carree(self):
        img = ImageLoader().load_path(test_path('Equirectangular_projection_SW-tweaked.jpg'))
        sampler = plate_carree_sampler(img.asarray())
        sample_layer(self.pio, ImageMode.RGB, sampler, 1)
        self.verify_level1(ImageMode.RGB)

    def test_earth_plate_caree_exr(self):
        img = ImageLoader().load_path(test_path('Equirectangular_projection_SW-tweaked.exr'))
        sampler = plate_carree_sampler(img.asarray())
        sample_layer(self.pio, ImageMode.RGB, sampler, 1)
        self.verify_level1(ImageMode.RGB)

    def test_healpix_equ(self):
        sampler = healpix_fits_file_sampler(test_path('earth_healpix_equ.fits'))
        sample_layer(self.pio, ImageMode.F32, sampler, 1)
        self.verify_level1(ImageMode.F32)

    def test_healpix_gal(self):
        sampler = healpix_fits_file_sampler(test_path('earth_healpix_gal.fits'))
        sample_layer(self.pio, ImageMode.F32, sampler, 1)
        self.verify_level1(ImageMode.F32)
