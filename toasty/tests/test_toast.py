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

from .. import toast
from .._libtoasty import mid
from ..image import ImageMode
from ..samplers import plate_carree_sampler, healpix_fits_file_sampler
from ..toast import generate_images, gen_wtml, read_image, save_png, SamplingToastDataSource


def mock_sampler(x, y):
    return x


@pytest.mark.parametrize('depth', (0, 1, 2))
def test_generate_images_path(depth):
    result = set(r[0] for r in generate_images(mock_sampler, depth))
    expected = set(['{n}/{y}/{y}_{x}.png'.format(n=n, x=x, y=y)
                    for n in range(depth + 1)
                    for y in range(2 ** n)
                    for x in range(2 ** n)])
    assert result == expected


def test_mid():
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
    save_png(pth, np.hstack((expected, actual)))

    pytest.fail("%s. Saved to %s" % (err_msg, pth))


def test_reference_wtml():
    ref = parseString(reference_wtml)
    opts = {'FolderName': 'ADS All Sky Survey',
            'Name': 'allSources_512',
            'Credits': 'ADS All Sky Survey',
            'CreditsUrl': 'adsass.org',
            'ThumbnailUrl': 'allSources_512.jpg'
            }
    wtml = gen_wtml('allSources_512', 3, **opts)
    val = parseString(wtml)

    assert ref.getElementsByTagName('Folder')[0].getAttribute('Name') == \
        val.getElementsByTagName('Folder')[0].getAttribute('Name')

    for n in ['Credits', 'CreditsUrl', 'ThumbnailUrl']:
        assert ref.getElementsByTagName(n)[0].childNodes[0].nodeValue == \
            val.getElementsByTagName(n)[0].childNodes[0].nodeValue

    ref = ref.getElementsByTagName('ImageSet')[0]
    val = val.getElementsByTagName('ImageSet')[0]
    for k in ref.attributes.keys():
        assert ref.getAttribute(k) == val.getAttribute(k)


def cwd():
    return os.path.split(os.path.abspath(__file__))[0]


def test_wwt_compare_sky():
    """Assert that the toast tiling looks similar to the WWT tiles"""
    direc = cwd()

    im = read_image(os.path.join(direc, 'Equirectangular_projection_SW-tweaked.jpg'))
    sampler = plate_carree_sampler(im)

    for pth, result in generate_images(sampler, depth=1):
        expected = read_image(os.path.join(direc, 'earth_toasted_sky', pth))
        expected = expected[:, :, :3]

        image_test(expected, result, "Failed for %s" % pth)


@pytest.mark.skipif('not HAS_ASTRO')
def test_healpix_sampler_equ():
    direc = cwd()
    sampler = healpix_fits_file_sampler(os.path.join(direc, 'earth_healpix_equ.fits'))

    for pth, result in generate_images(sampler, depth=1):
        expected = read_image(os.path.join(direc, 'earth_toasted_sky', pth))
        expected = expected.sum(axis=2) // 3

        image_test(expected, result, "Failed for %s" % pth)


@pytest.mark.skipif('not HAS_ASTRO')
def test_healpix_sampler_gal():
    direc = cwd()
    sampler = healpix_fits_file_sampler(os.path.join(direc, 'earth_healpix_gal.fits'))

    for pth, result in generate_images(sampler, depth=1):
        expected = read_image(os.path.join(direc, 'earth_toasted_sky', pth))
        expected = expected.sum(axis=2) // 3

        image_test(expected, result, "Failed for %s" % pth)


def test_merge():
    # test that merge function called on non-terminal nodes
    im = read_image(os.path.join(cwd(), 'Equirectangular_projection_SW-tweaked.jpg'))

    def null_merge(mosaic):
        return np.zeros((256, 256, 3), dtype=np.uint8)

    sampler = plate_carree_sampler(im)

    for pth, im in generate_images(sampler, 2, null_merge):
        if pth[0] != '2':
            assert im.max() == 0
        else:
            assert im.max() != 0


class TestToaster(object):

    def setup_method(self, method):
        self.base = mkdtemp()
        self.cwd = cwd()

        im = read_image(os.path.join(self.cwd, 'Equirectangular_projection_SW-tweaked.jpg'))
        self.sampler = plate_carree_sampler(im)

    def teardown_method(self, method):
        rmtree(self.base)

    def verify_toast(self):
        """ Zip the expected and actual tiles """
        for n, x, y in [(0, 0, 0), (1, 0, 0), (1, 0, 1),
                        (1, 1, 0), (1, 1, 1)]:
            subpth = os.path.join(str(n), str(y), "%i_%i.png" % (y, x))
            a = read_image(os.path.join(self.base, subpth))[:, :, :3]
            b = read_image(os.path.join(self.cwd, 'earth_toasted_sky', subpth))[:, :, :3]
            image_test(b, a, 'Failed for %s' % subpth)

    def test_default(self):

        wtml = os.path.join(self.base, 'test.wtml')
        toast.toast(self.sampler, 1, self.base, wtml_file=wtml)

        assert os.path.exists(wtml)
        self.verify_toast()

    def test_no_merge(self):
        toast.toast(self.sampler, 1, self.base, merge=False)
        self.verify_toast()


reference_wtml = """
<Folder Name="ADS All Sky Survey">
<ImageSet Generic="False" DataSetType="Sky" BandPass="Visible" Name="allSources_512" Url="allSources_512/{1}/{3}/{3}_{2}.png" BaseTileLevel="0" TileLevels="3" BaseDegreesPerTile="180" FileType=".png" BottomsUp="False" Projection="Toast" QuadTreeMap="" CenterX="0" CenterY="0" OffsetX="0" OffsetY="0" Rotation="0" Sparse="False" ElevationModel="False">
<Credits> ADS All Sky Survey </Credits>
<CreditsUrl>adsass.org</CreditsUrl>
<ThumbnailUrl>allSources_512.jpg</ThumbnailUrl>
<Description/>
</ImageSet>
</Folder>
"""


class TestSamplingToastDataSource(object):
    def setup_method(self, method):
        self.base = mkdtemp()
        self.cwd = cwd()
        im = read_image(os.path.join(self.cwd, 'Equirectangular_projection_SW-tweaked.jpg'))
        self.sampler = plate_carree_sampler(im)

        from ..pyramid import PyramidIO
        self.pio = PyramidIO(self.base)

    def teardown_method(self, method):
        rmtree(self.base)

    def verify_toast(self):
        """ Zip the expected and actual tiles """
        for n, x, y in [(1, 0, 0), (1, 0, 1),
                        (1, 1, 0), (1, 1, 1)]:
            subpth = os.path.join(str(n), str(y), "%i_%i.png" % (y, x))
            a = read_image(os.path.join(self.base, subpth))[:, :, :3]
            b = read_image(os.path.join(self.cwd, 'earth_toasted_sky', subpth))[:, :, :3]
            image_test(b, a, 'Failed for %s' % subpth)

    def test_default(self):
        stds = SamplingToastDataSource(ImageMode.RGB, self.sampler)
        stds.sample_layer(self.pio, 1)
        self.verify_toast()
