# -*- mode: python; coding: utf-8 -*-
# Copyright 2020 the AAS WorldWide Telescope project
# Licensed under the MIT License.

"""
Building up WWT imagery data sets.

This gets a little complex since the generation of a tiled image involves
several tasks that may or may not be implemented in several, swappable ways:
generating the tiled pixel data; positioning the image on the sky; filling in
metadata; and so on. We try to provide a framework that allows the
implementations of different tasks to be swapped out without getting too airy
and abstract.

"""
from __future__ import absolute_import, division, print_function

__all__ = '''
Builder
'''.split()

from wwt_data_formats.enums import DataSetType, ProjectionType
from wwt_data_formats.imageset import ImageSet
from wwt_data_formats.layers import ImageSetLayer, LayerContainerReader
from wwt_data_formats.place import Place

from .image import ImageLoader


class Builder(object):
    """
    State for some kind of imagery data set that's being assembled.
    """

    pio = None
    "A PyramidIO object representing the backing storage of the tiles and other image data."

    imgset = None
    """
    The WWT ImageSet data describing the image data and their positioning on the sky.

    Data URLs in this ImageSet should be populated as relative URLs.

    """
    place = None
    "The WWT Place data describing a default view of the image data."

    def __init__(self, pio):
        self.pio = pio
        self.imgset = ImageSet()
        self.imgset.name = 'Toasty'
        self.place = Place()
        self.place.foreground_image_set = self.imgset
        self.place.name = 'Toasty'


    def tile_base_as_study(self, image, **kwargs):
        from .study import tile_study_image

        tiling = tile_study_image(image, self.pio, **kwargs)
        tiling.apply_to_imageset(self.imgset)
        self.imgset.url = self.pio.get_path_scheme() + '.png'
        self.imgset.file_type = '.png'

        return self


    def default_tiled_study_astrometry(self):
        self.imgset.data_set_type = DataSetType.SKY
        self.imgset.base_degrees_per_tile = 1.0
        self.imgset.projection = ProjectionType.TAN
        self.place.zoom_level = 1.0
        return self


    def load_from_wwtl(self, cli_settings, wwtl_path):
        from contextlib import closing
        from io import BytesIO

        # Load WWTL and see if it matches expectations
        with closing(LayerContainerReader.from_file(wwtl_path)) as lc:
            if len(lc.layers) != 1:
                raise Exception('WWTL file must contain exactly one layer')

            layer = lc.layers[0]
            if not isinstance(layer, ImageSetLayer):
                raise Exception('WWTL file must contain an imageset layer')

            imgset = layer.image_set
            if imgset.projection != ProjectionType.SKY_IMAGE:
                raise Exception('WWTL imageset layer must have "SkyImage" projection type')

            # Looks OK. Read and parse the image.
            loader = ImageLoader.create_from_args(cli_settings)
            img_data = lc.read_layer_file(layer, layer.extension)
            img = loader.load_stream(BytesIO(img_data))

        # Transmogrify untiled image info to tiled image info. We reuse the
        # existing imageset as much as possible, but update the parameters that
        # change in the tiling process.
        self.imgset = imgset
        self.place.foreground_image_set = self.imgset
        wcs_keywords = self.imgset.wcs_headers_from_position()
        self.tile_base_as_study(img)
        self.imgset.set_position_from_wcs(wcs_keywords, img.width, img.height, place=self.place)

        return img


    def toast_base(self, sampler, depth, is_planet=False, **kwargs):
        from .toast import sample_layer
        sample_layer(self.pio, sampler, depth, **kwargs)

        if is_planet:
            self.imgset.data_set_type = DataSetType.PLANET
        else:
            self.imgset.data_set_type = DataSetType.SKY

        self.imgset.base_degrees_per_tile = 180
        self.imgset.file_type = '.png'
        self.imgset.projection = ProjectionType.TOAST
        self.imgset.tile_levels = depth
        self.imgset.url = self.pio.get_path_scheme() + '.png'
        self.place.zoom_level = 360

        return self


    def cascade(self, **kwargs):
        from .merge import averaging_merger, cascade_images
        cascade_images(self.pio, self.imgset.tile_levels, averaging_merger, **kwargs)
        return self


    def make_thumbnail_from_other(self, thumbnail_image):
        thumb = thumbnail_image.make_thumbnail_bitmap()
        with self.pio.open_metadata_for_write('thumb.jpg') as f:
            thumb.save(f, format='JPEG')
        self.imgset.thumbnail_url = 'thumb.jpg'

        return self


    def make_placeholder_thumbnail(self):
        import numpy as np
        from .image import Image

        arr = np.zeros((45, 96, 3), dtype=np.uint8)
        img = Image.from_array(arr)

        with self.pio.open_metadata_for_write('thumb.jpg') as f:
            img.aspil().save(f, format='JPEG')

        self.imgset.thumbnail_url = 'thumb.jpg'
        return self


    def apply_wcs_info(self, wcs, width, height):
        self.imgset.set_position_from_wcs(
            wcs.to_header(),
            width, height,
            place = self.place,
        )

        return self


    def apply_avm_info(self, avm, width, height):
        self.apply_wcs_info(avm.to_wcs(target_shape=(width, height)), width, height)

        if avm.Title:
            self.imgset.name = avm.Title

        if avm.Description:
            self.imgset.description = avm.Description

        if avm.Credit:
            self.imgset.credits = avm.Credit

        if avm.ReferenceURL:
            self.imgset.credits_url = avm.ReferenceURL

        return self


    def set_name(self, name):
        self.imgset.name = name
        self.place.name = name
        return self


    def write_index_rel_wtml(self):
        from wwt_data_formats import write_xml_doc
        from wwt_data_formats.folder import Folder

        self.place.name = self.imgset.name
        self.place.data_set_type = self.imgset.data_set_type
        self.place.thumbnail = self.imgset.thumbnail_url

        folder = Folder()
        folder.name = self.imgset.name

        # For all-sky/all-planet datasets, don't associate the imageset with a
        # particular Place. Otherwise, loading up the imageset causes the view
        # to zoom to a particular RA/Dec or lat/lon, likely 0,0. We might want
        # to make this manually configurable but this heuristic should Do The
        # Right Thing most times.
        if self.imgset.projection == ProjectionType.TOAST:
            folder.children = [self.imgset]
        else:
            folder.children = [self.place]

        with self.pio.open_metadata_for_write('index_rel.wtml') as f:
            write_xml_doc(folder.to_xml(), dest_stream=f, dest_wants_bytes=True)

        return self
