# -*- mode: python; coding: utf-8 -*-
# Copyright 2020 the AAS WorldWide Telescope project
# Licensed under the MIT License.

from __future__ import absolute_import, division, print_function

import numpy as np
from numpy import testing as nt
import os.path
import pytest
import sys

from . import assert_xml_elements_equal, test_path
from .. import cli
from .. import study


class TestStudy(object):
    WTML = """<?xml version='1.0' encoding='UTF-8'?>
<Folder Browseable="True" Group="Explorer" MSRCommunityId="0" MSRComponentId="0" Name="Toasty" Permission="0" Searchable="True" Type="Sky">
  <Place Angle="0.0" AngularSize="0.0" DataSetType="Sky" Dec="0.0" Distance="0.0" DomeAlt="0.0" DomeAz="0.0" Lat="0.0" Lng="0.0" Magnitude="0.0" MSRCommunityId="0" MSRComponentId="0" Name="Toasty" Opacity="100.0" Permission="0" RA="0.0" Rotation="0.0" Thumbnail="thumb.jpg" ZoomLevel="1.0">
    <ForegroundImageSet>
      <ImageSet BandPass="Visible" BaseDegreesPerTile="1.0" BaseTileLevel="0" BottomsUp="False" CenterX="0.0" CenterY="0.0" DataSetType="Sky" ElevationModel="False" FileType=".png" Generic="False" MeanRadius="0.0" MSRCommunityId="0" MSRComponentId="0" Name="Toasty" OffsetX="0.0" OffsetY="0.0" Permission="0" Projection="Tan" Rotation="0.0" Sparse="True" StockSet="False" TileLevels="4" Url="{1}/{3}/{3}_{2}.png" WidthFactor="2">
        <ThumbnailUrl>thumb.jpg</ThumbnailUrl>
      </ImageSet>
    </ForegroundImageSet>
  </Place>
</Folder>
"""

    def setup_method(self, method):
        from tempfile import mkdtemp
        self.work_dir = mkdtemp()

    def teardown_method(self, method):
        from shutil import rmtree
        rmtree(self.work_dir)

    def work_path(self, *pieces):
        return os.path.join(self.work_dir, *pieces)

    def test_basic(self):
        tiling = study.StudyTiling(2048, 2048)
        assert tiling._width == 2048
        assert tiling._height == 2048
        assert tiling._p2n == 2048
        assert tiling._tile_size == 8
        assert tiling._tile_levels == 3
        assert tiling._img_gx0 == 0
        assert tiling._img_gy0 == 0


    def test_preconditions(self):
        with pytest.raises(ValueError):
            study.StudyTiling(0, 1)

        with pytest.raises(ValueError):
            study.StudyTiling(1, -1)

        with pytest.raises(ValueError):
            study.StudyTiling(1, np.nan)


    def test_image_to_tile(self):
        tiling = study.StudyTiling(514, 514)
        assert tiling._p2n == 1024
        assert tiling.image_to_tile(0, 0) == (0, 0, 255, 255)
        assert tiling.image_to_tile(0, 513) == (0, 3, 255, 0)
        assert tiling.image_to_tile(513, 0) == (3, 0, 0, 255)
        assert tiling.image_to_tile(513, 513) == (3, 3, 0, 0)


    def test_sample_cli(self):
        from xml.etree import ElementTree as etree
        expected = etree.fromstring(self.WTML)

        for variants in ([], ['--placeholder-thumbnail']):
            args = ['tile-study']
            args += variants
            args += [
                '--outdir', self.work_path(),
                test_path('NGC253ALMA.jpg')
            ]
            cli.entrypoint(args)

        with open(self.work_path('index_rel.wtml'), 'rt', encoding='utf8') as f:
            observed = etree.fromstring(f.read())

        assert_xml_elements_equal(observed, expected)
