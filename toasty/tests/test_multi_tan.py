# -*- mode: python; coding: utf-8 -*-
# Copyright 2019-2020 the AAS WorldWide Telescope project
# Licensed under the MIT License.

from __future__ import absolute_import, division, print_function

import numpy as np
from numpy import testing as nt
import os.path
import pytest
import sys

from . import assert_xml_elements_equal, test_path
from .. import cli
from .. import multi_tan


class TestMultiTan(object):
    WTML = """
<Folder Group="Explorer" Name="TestName">
  <Place Angle="0" DataSetType="Sky" Dec="0.74380165289257" Name="TestName"
         Opacity="100" RA="14.419753086419734" Rotation="0.0"
         ZoomLevel="0.1433599999999144">
    <ForegroundImageSet>
      <ImageSet BandPass="Gamma" BaseDegreesPerTile="0.023893333333319066"
                BaseTileLevel="0" BottomsUp="False" CenterX="216.296296296296"
                CenterY="0.74380165289257" DataSetType="Sky" FileType=".png"
                Name="TestName" OffsetX="4.66666666666388e-05"
                OffsetY="4.66666666666388e-05" Projection="Tan" Rotation="0.0"
                Sparse="True" TileLevels="1" Url="UP{1}/{3}/{3}_{2}.png"
                WidthFactor="2">
        <Credits>CT</Credits>
        <CreditsUrl>CU</CreditsUrl>
        <ThumbnailUrl>TU</ThumbnailUrl>
        <Description>DT</Description>
      </ImageSet>
    </ForegroundImageSet>
  </Place>
</Folder>"""

    # Gross workaround for Python 2.7, where the XML serialization is
    # apparently slightly different from Python >=3 (for Numpy types only, I
    # think?). Fun times. We could avoid this by comparing floats as floats,
    # not text, but then we basically have to learn how to deserialize WTML
    # with the full semantics of the format.

    if sys.version_info.major == 2:
        WTML = (WTML
                .replace('Dec="0.74380165289257"', 'Dec="0.743801652893"')
                .replace('RA="14.419753086419734"', 'RA="14.4197530864"')
                .replace('CenterX="216.296296296296"', 'CenterX="216.296296296"')
                .replace('CenterY="0.74380165289257"', 'CenterY="0.743801652893"')
        )

    # Back to the non-gross stuff.

    def setup_method(self, method):
        from tempfile import mkdtemp
        self.work_dir = mkdtemp()

    def teardown_method(self, method):
        from shutil import rmtree
        rmtree(self.work_dir)

    def work_path(self, *pieces):
        return os.path.join(self.work_dir, *pieces)

    def test_basic(self):
        ds = multi_tan.MultiTanDataSource([test_path('wcs512.fits.gz')])
        ds.compute_global_pixelization()

        from xml.etree import ElementTree as etree
        expected = etree.fromstring(self.WTML)

        folder = ds.create_wtml(
            name = 'TestName',
            url_prefix = 'UP',
            fov_factor = 1.0,
            bandpass = 'Gamma',
            description_text = 'DT',
            credits_text = 'CT',
            credits_url = 'CU',
            thumbnail_url = 'TU',
        )
        assert_xml_elements_equal(folder, expected)

        from ..pyramid import PyramidIO
        pio = PyramidIO(self.work_path('basic'), default_format='npy')
        percentiles = ds.generate_deepest_layer_numpy(pio)

        # These are all hardcoded parameters of this test dataset, derived
        # from a manual processing with checking that the results are correct.
        # Note that to make the file more compressible, I quantized its data,
        # which explains why some of the samples below are identical.

        PERCENTILES = {
            1: 0.098039217,
            99: 0.76862746,
        }

        for pct, expected in PERCENTILES.items():
            nt.assert_almost_equal(percentiles[pct], expected)

        MEAN, TLC, TRC, BLC, BRC = range(5)
        SAMPLES = {
            (0, 0): [0.20828014, 0.20392157, 0.22745098, 0.18431373, 0.20000000],
            (0, 1): [0.22180051, 0.18431373, 0.18823530, 0.16470589, 0.18431373],
            (1, 0): [0.22178716, 0.16470589, 0.18431373, 0.11372549, 0.19607843],
            (1, 1): [0.21140813, 0.18431373, 0.20784314, 0.12549020, 0.14117648],
        }

        for (y, x), expected in SAMPLES.items():
            data = np.load(self.work_path('basic', '1', str(y), '{}_{}.npy'.format(y, x)))
            nt.assert_almost_equal(data.mean(), expected[MEAN])
            nt.assert_almost_equal(data[10,10], expected[TLC])
            nt.assert_almost_equal(data[10,-10], expected[TRC])
            nt.assert_almost_equal(data[-10,10], expected[BLC])
            nt.assert_almost_equal(data[-10,-10], expected[BRC])


    def test_basic_cli(self):
        """Test the CLI interface. We don't go out of our way to validate the
        computations in detail -- that's for the unit tests that probe the
        module directly.

        """
        args = [
            'multi-tan-make-data-tiles',
            '--hdu-index', '0',
            '--outdir', self.work_path('basic_cli'),
            test_path('wcs512.fits.gz')
        ]
        cli.entrypoint(args)
