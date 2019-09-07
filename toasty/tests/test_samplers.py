# -*- mode: python; coding: utf-8 -*-
# Copyright 2019 the AAS WorldWide Telescope project
# Licensed under the MIT License.

import numpy as np
import numpy.testing as nt
import os.path
import pytest

from .. import cli
from .. import samplers


TESTS_DIR = os.path.dirname(os.path.abspath(__file__))

def make_path(*pieces):
    return os.path.join(TESTS_DIR, *pieces)


class TestSamplers(object):
    def setup_method(self, method):
        from tempfile import mkdtemp
        self.work_dir = mkdtemp()

    def teardown_method(self, method):
        from shutil import rmtree
        rmtree(self.work_dir)

    def work_path(self, *pieces):
        return os.path.join(self.work_dir, *pieces)

    def test_basic_cli(self):
        """Test some CLI interfaces. We don't go out of our way to validate the
        computations in detail -- that's for the unit tests that probe the
        module directly.

        """
        args = [
            'healpix-sample-data-tiles',
            '--outdir', self.work_path('basic_cli'),
            make_path('earth_healpix_equ.fits'),
            '1',
        ]
        cli.entrypoint(args)
