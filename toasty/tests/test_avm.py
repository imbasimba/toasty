# -*- mode: python; coding: utf-8 -*-
# Copyright 2021 the AAS WorldWide Telescope project
# Licensed under the MIT License.

import numpy as np
from numpy import testing as nt
import os.path
import pytest
import sys

from . import assert_xml_elements_equal, test_path
from .. import cli
from .. import study


class TestAvm(object):
    def setup_method(self, method):
        from tempfile import mkdtemp
        self.work_dir = mkdtemp()

    def teardown_method(self, method):
        from shutil import rmtree
        rmtree(self.work_dir)

    def work_path(self, *pieces):
        return os.path.join(self.work_dir, *pieces)

    def test_check_cli(self):
        args = [
            'check-avm',
            '--print',
            '--exitcode',
            test_path('badavm-type.png'),
        ]

        try:
            cli.entrypoint(args)
        except SystemExit as e:
            assert e.code == 1
        else:
            assert False, 'no error exit on bad AVM'
