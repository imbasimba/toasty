# -*- mode: python; coding: utf-8 -*-
# Copyright 2019-2022 the AAS WorldWide Telescope project
# Licensed under the MIT License.

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


def test_pyramid_gen_generic():
    p = pyramid.Pyramid.new_generic(0)

    assert list(p._generator()) == [(Pos(0, 0, 0), None)]
    assert p.count_leaf_tiles() == 1
    assert p.count_live_tiles() == 1
    assert p.count_operations() == 0

    p = pyramid.Pyramid.new_generic(1)

    assert list(p._generator()) == [
        (Pos(1, 0, 0), None),
        (Pos(1, 1, 0), None),
        (Pos(1, 0, 1), None),
        (Pos(1, 1, 1), None),
        (Pos(0, 0, 0), None),
    ]
    assert p.count_leaf_tiles() == 4
    assert p.count_live_tiles() == 5
    assert p.count_operations() == 1

    p = pyramid.Pyramid.new_generic(2).subpyramid(Pos(1, 1, 1))

    assert list(p._generator()) == [
        (Pos(2, 2, 2), None),
        (Pos(2, 3, 2), None),
        (Pos(2, 2, 3), None),
        (Pos(2, 3, 3), None),
        (Pos(1, 1, 1), None),
        (Pos(0, 0, 0), None),
    ]
    assert p.count_leaf_tiles() == 4
    assert p.count_live_tiles() == 5
    assert p.count_operations() == 1


def test_pyramid_gen_toast():
    p = pyramid.Pyramid.new_toast(0)

    assert list([t[0] for t in p._generator()]) == [Pos(0, 0, 0)]
    assert p.count_leaf_tiles() == 1
    assert p.count_live_tiles() == 1
    assert p.count_operations() == 0

    p = pyramid.Pyramid.new_toast(1)

    assert list([t[0] for t in p._generator()]) == [
        Pos(1, 0, 0),
        Pos(1, 1, 0),
        Pos(1, 0, 1),
        Pos(1, 1, 1),
        Pos(0, 0, 0),
    ]
    assert p.count_leaf_tiles() == 4
    assert p.count_live_tiles() == 5
    assert p.count_operations() == 1

    p = pyramid.Pyramid.new_toast(2).subpyramid(Pos(1, 1, 1))

    assert list([t[0] for t in p._generator()]) == [
        Pos(2, 2, 2),
        Pos(2, 3, 2),
        Pos(2, 2, 3),
        Pos(2, 3, 3),
        Pos(1, 1, 1),
        Pos(0, 0, 0),
    ]
    assert p.count_leaf_tiles() == 4
    assert p.count_live_tiles() == 5
    assert p.count_operations() == 1


def test_pyramid_gen_toast_filtered():
    from ..samplers import _latlon_tile_filter

    # These bounds are roughly from the DECaPS2 dataset
    # which I've been processing.
    tf = _latlon_tile_filter(0.106, 4.878, -1.285, -0.120)

    p = pyramid.Pyramid.new_toast_filtered(0, tf)

    assert list([t[0] for t in p._generator()]) == [Pos(0, 0, 0)]
    assert p.count_leaf_tiles() == 1
    assert p.count_live_tiles() == 1
    assert p.count_operations() == 0

    p = pyramid.Pyramid.new_toast_filtered(3, tf)
    REFXY = [
        (0, 0),
        (0, 1),
        (0, 2),
        (0, 3),
        (1, 0),
        (1, 3),
        (2, 0),
        (2, 3),
        (3, 0),
        (3, 1),
        (3, 3),
    ]
    assert sorted(t[0] for t in p._generator() if t[0].n == 2) == [
        Pos(2, *t) for t in REFXY
    ]
    assert p.count_leaf_tiles() == 34
    assert p.count_live_tiles() == 50
    assert p.count_operations() == 16


def test_pyramid_toast_filtered_gap_child():
    """
    This examines a corner case where the tile filter matches the level-4 tile
    in question, but not any of its children -- this is correct behavior because
    the filtering is only done with bounding boxes, and the union of the
    bounding boxes of the children is smaller than the bounding box of the
    parent. Correct behavior for the pyramid is to say that we have no live
    tiles.
    """
    from ..samplers import _latlon_tile_filter

    THE_POS = Pos(4, 15, 7)

    # These bounds are roughly from the DECaPS2 dataset
    # which I've been processing.
    tf = _latlon_tile_filter(0.106, 4.878, -1.285, -0.120)

    p = pyramid.Pyramid.new_toast_filtered(4, tf)
    riter = p._make_iter_reducer()

    for pos, tile, _is_leaf, _data in riter:
        if pos == THE_POS:
            assert tf(tile)
        riter.set_data(True)

    p = pyramid.Pyramid.new_toast_filtered(6, tf).subpyramid(THE_POS)
    assert p.count_leaf_tiles() == 0
    assert p.count_live_tiles() == 0
    assert p.count_operations() == 0
