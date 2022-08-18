# -*- mode: python; coding: utf-8 -*-
# Copyright 2019-2020 the AAS WorldWide Telescope project
# Licensed under the MIT License.

import numpy as np
import numpy.testing as nt
import os.path
import pytest

from . import test_path
from .. import cli
from .. import merge


def test_averaging_merger():
    from ..merge import averaging_merger

    t = np.array([[np.nan, 1], [3, np.nan]])
    nt.assert_almost_equal(averaging_merger(t), [[2.0]])


def test_initiate_readiness_state():
    from ..merge import _initiate_readiness_state
    from ..pyramid import Pos

    readiness_state = {}
    _initiate_readiness_state({Pos(1, 0, 0), Pos(1, 1, 0)}, readiness_state)
    assert readiness_state.get(Pos(n=0, x=0, y=0)) == 0b1100

    readiness_state = {}
    _initiate_readiness_state({Pos(3, 7, 7), Pos(3, 3, 1)}, readiness_state)
    assert readiness_state.get(Pos(n=0, x=0, y=0)) == 0b0110
    assert readiness_state.get(Pos(n=1, x=1, y=1)) == 0b0111
    assert readiness_state.get(Pos(n=1, x=0, y=0)) == 0b1101
    assert readiness_state.get(Pos(n=2, x=3, y=3)) == 0b0111
    assert readiness_state.get(Pos(n=2, x=1, y=0)) == 0b0111


class TestCascade(object):
    def setup_method(self, method):
        from tempfile import mkdtemp

        self.work_dir = mkdtemp()

    def teardown_method(self, method):
        from shutil import rmtree

        rmtree(self.work_dir)

    def work_path(self, *pieces):
        return os.path.join(self.work_dir, *pieces)

    def test_basic_cli(self):
        """Test the CLI interface. We don't go out of our way to validate the
        computations in detail -- that's for the unit tests that probe the
        module directly.

        """
        for variants in (
            ["--parallelism=1"],
            ["--parallelism=2", "--placeholder-thumbnail"],
        ):
            args = ["tile-allsky"]
            args += variants
            args += [
                "--outdir",
                self.work_path("basic_cli"),
                test_path("Equirectangular_projection_SW-tweaked.jpg"),
                "1",
            ]
            cli.entrypoint(args)

        for parallelism in "12":
            args = [
                "cascade",
                "--parallelism",
                parallelism,
                "--start",
                "1",
                self.work_path("basic_cli"),
            ]
            cli.entrypoint(args)
