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
from ..builder import Builder
from .. import cli
from .. import collection
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
        coll = collection.SimpleFitsCollection([test_path('wcs512.fits.gz')])

        proc = multi_tan.MultiTanProcessor(coll)

        from ..pyramid import PyramidIO
        pio = PyramidIO(self.work_path('basic'), default_format='fits')

        builder = Builder(pio)

        proc.compute_global_pixelization(builder)
        proc.tile(pio)

    def test_basic_cli(self):
        """
        Test the CLI interface. We don't go out of our way to validate the
        computations in detail -- that's for the unit tests that probe the
        module directly.
        """

        args = [
            'tile-multi-tan',
            '--hdu-index', '0',
            '--outdir', self.work_path('basic_cli'),
            test_path('wcs512.fits.gz')
        ]
        cli.entrypoint(args)
