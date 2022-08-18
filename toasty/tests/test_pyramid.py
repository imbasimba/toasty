# -*- mode: python; coding: utf-8 -*-
# Copyright 2019 the AAS WorldWide Telescope project
# Licensed under the MIT License.

import numpy as np
import pytest

from .. import pyramid
from ..pyramid import Pos


def test_next_highest_power_of_2():
    assert pyramid.next_highest_power_of_2(1) == 256
    assert pyramid.next_highest_power_of_2(256) == 256
    assert pyramid.next_highest_power_of_2(257) == 512


def test_depth2tiles():
    assert pyramid.depth2tiles(0) == 1
    assert pyramid.depth2tiles(1) == 5
    assert pyramid.depth2tiles(2) == 21
    assert pyramid.depth2tiles(10) == 1398101


def test_is_subtile():
    from ..pyramid import is_subtile

    assert is_subtile(Pos(2, 0, 0), Pos(1, 0, 0)) == True

    with pytest.raises(ValueError):
        is_subtile(Pos(1, 0, 0), Pos(2, 0, 0))


def test_pos_parent():
    from ..pyramid import pos_parent

    assert pos_parent(Pos(7, 65, 33)) == (Pos(6, 32, 16), 1, 1)

    with pytest.raises(ValueError):
        pos_parent(Pos(0, 0, 0))


def test_get_parents():
    from ..pyramid import get_parents

    assert get_parents((Pos(1, 0, 0), Pos(1, 1, 0))) == {Pos(0, 0, 0)}

    all_ancestors = {
        Pos(n=0, x=0, y=0),
        Pos(n=1, x=0, y=0),
        Pos(n=1, x=1, y=0),
        Pos(n=2, x=1, y=1),
        Pos(n=2, x=2, y=1),
        Pos(n=3, x=3, y=2),
        Pos(n=3, x=4, y=2),
        Pos(n=4, x=7, y=4),
        Pos(n=4, x=8, y=4),
        Pos(n=5, x=15, y=8),
        Pos(n=5, x=16, y=8),
        Pos(n=6, x=31, y=16),
        Pos(n=6, x=32, y=16),
    }
    assert (
        get_parents(
            {Pos(7, 63, 33), Pos(7, 64, 33), Pos(7, 65, 33)}, get_all_ancestors=True
        )
        == all_ancestors
    )


def test_generate_pos():
    from ..pyramid import generate_pos

    assert list(generate_pos(0)) == [Pos(0, 0, 0)]

    assert list(generate_pos(1)) == [
        Pos(1, 0, 0),
        Pos(1, 1, 0),
        Pos(1, 0, 1),
        Pos(1, 1, 1),
        Pos(0, 0, 0),
    ]


def test_guess_base_layer_level():
    from ..pyramid import guess_base_layer_level
    from astropy.wcs import WCS

    wcs = WCS()
    wcs.wcs.ctype = "RA---GLS", "DEC--GLS"
    wcs.wcs.crval = 0, 0
    wcs.wcs.crpix = 1, 1
    wcs._naxis = [1, 1]

    wcs.wcs.cdelt = 0.36, 0.36
    assert guess_base_layer_level(wcs=wcs) == 1

    wcs.wcs.cdelt = 0.35, 0.35
    assert guess_base_layer_level(wcs=wcs) == 2

    wcs.wcs.cdelt = 0.15, 0.15
    assert guess_base_layer_level(wcs=wcs) == 3

    wcs.wcs.cdelt = 0.005, 0.005
    assert guess_base_layer_level(wcs=wcs) == 8

    wcs.wcs.cdelt = 0.0001, 0.0001
    assert guess_base_layer_level(wcs=wcs) == 13
