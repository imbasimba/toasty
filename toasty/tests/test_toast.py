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

try:
    import OpenEXR
    HAS_OPENEXR = True
except ImportError:
    HAS_OPENEXR = False

from . import test_path
from .. import cli, toast
from ..image import ImageLoader
from ..pyramid import Pos, PyramidIO
from ..toast import sample_layer
from ..transform import f16x3_to_rgb


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


def test_tile_for_point_boundaries():
    # These test points occur at large-scale tile boundaries and so we're not
    # picky about where they land in the tiling -- either tile on a border is
    # OK.

    from ..toast import toast_tile_for_point

    latlons = [
        (0., 0.),

        (0., -0.5 * np.pi),
        (0., 0.5 * np.pi),
        (0., np.pi),
        (0., 1.5 * np.pi),
        (0., 2 * np.pi),
        (0., 2.5 * np.pi),

        (-0.5 * np.pi, 0.),
        (-0.5 * np.pi, -np.pi),
        (-0.5 * np.pi, np.pi),

        (0.5 * np.pi, 0.),
        (0.5 * np.pi, -np.pi),
        (0.5 * np.pi, np.pi),
    ]

    for depth in range(4):
        for lat, lon in latlons:
            tile = toast_tile_for_point(depth, lat, lon)


def test_tile_for_point_specifics():
    from ..toast import toast_tile_for_point

    test_data = {
        (0.1, 0.1): [
            (0, 0, 0),
            (1, 1, 0),
            (2, 3, 1),
            (3, 7, 3),
            (4, 14, 7),
            (5, 29, 14),
            (6, 59, 29),
            (7, 119, 59),
            (8, 239, 119),
            (9, 479, 239),
            (10, 959, 479),
            (11, 1918, 959),
            (12, 3837, 1918),
        ]
    }

    for (lat, lon), nxys in test_data.items():
        for nxy in nxys:
            tile = toast_tile_for_point(nxy[0], lat, lon)
            assert tile.pos.n == nxy[0]
            assert tile.pos.x == nxy[1]
            assert tile.pos.y == nxy[2]


def test_pixel_for_point():
    from ..toast import toast_pixel_for_point

    test_data = {
        (0.1, 0.1): (3, 7, 3, 126, 191),
        (-0.4, 2.2): (3, 1, 1, 200, 75),
    }

    for (lat, lon), (n, x, y, px, py) in test_data.items():
        shallow_tile, frac_x, frac_y = toast_pixel_for_point(n, lat, lon)
        assert shallow_tile.pos.n == n
        assert shallow_tile.pos.x == x
        assert shallow_tile.pos.y == y
        assert px == int(round(frac_x))
        assert py == int(round(frac_y))
        deep_tile, _, _ = toast_pixel_for_point(n + 8, lat, lon)
        assert deep_tile.pos.x % 256 == px
        assert deep_tile.pos.y % 256 == py


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

    def verify_level1(self, ref='earth_toasted_sky', format=None, expected_2d=False):
        for n, x, y in [(1, 0, 0), (1, 0, 1), (1, 1, 0), (1, 1, 1)]:
            ref_path = test_path(ref, str(n), str(y), "%i_%i.png" % (y, x))
            expected = ImageLoader().load_path(ref_path).asarray()

            pos = Pos(n=n, x=x, y=y)
            observed = self.pio.read_image(pos, format=format).asarray()

            if expected_2d:
                expected = expected.mean(axis=2)

            image_test(expected, observed, 'Failed for %s' % ref_path)

    def test_plate_carree(self):
        from ..samplers import plate_carree_sampler
        img = ImageLoader().load_path(test_path('Equirectangular_projection_SW-tweaked.jpg'))
        sampler = plate_carree_sampler(img.asarray())
        sample_layer(self.pio, sampler, 1, format='png')
        self.verify_level1()

    def test_plate_carree_ecliptic(self):
        from ..samplers import plate_carree_ecliptic_sampler

        img = ImageLoader().load_path(test_path('tess_platecarree_ecliptic_512.jpg'))
        sampler = plate_carree_ecliptic_sampler(img.asarray())
        sample_layer(self.pio, sampler, 1, format='png')
        self.verify_level1(ref='tess')

    @pytest.mark.skipif('not HAS_OPENEXR')
    def test_earth_plate_caree_exr(self):
        from ..samplers import plate_carree_sampler

        img = ImageLoader().load_path(test_path('Equirectangular_projection_SW-tweaked.exr'))
        sampler = plate_carree_sampler(img.asarray())
        sample_layer(self.pio, sampler, 1, format='npy')
        f16x3_to_rgb(self.pio, 1, parallel=1)
        self.verify_level1()

    @pytest.mark.skipif('not HAS_ASTRO')
    def test_healpix_equ(self):
        from ..samplers import healpix_fits_file_sampler

        sampler = healpix_fits_file_sampler(test_path('earth_healpix_equ.fits'))
        sample_layer(self.pio, sampler, 1, format='npy')
        self.verify_level1(format='npy', expected_2d=True)

    @pytest.mark.skipif('not HAS_ASTRO')
    def test_healpix_gal(self):
        from ..samplers import healpix_fits_file_sampler

        sampler = healpix_fits_file_sampler(test_path('earth_healpix_gal.fits'))
        sample_layer(self.pio, sampler, 1, format='fits')
        self.verify_level1(format='fits', expected_2d=True)


class TestCliBasic(object):
    """
    Basic smoketests for the CLI. The more library-focused routines validate
    detailed outputs.
    """

    def setup_method(self, method):
        self.work_dir = mkdtemp()

    def teardown_method(self, method):
        from shutil import rmtree
        rmtree(self.work_dir)

    def work_path(self, *pieces):
        return os.path.join(self.work_dir, *pieces)

    def test_planet(self):
        args = [
            'tile-allsky',
            '--name=Earth',
            '--projection=plate-carree-planet',
            '--outdir', self.work_path('basic_cli'),
            test_path('Equirectangular_projection_SW-tweaked.jpg'),
            '2',
        ]
        cli.entrypoint(args)
