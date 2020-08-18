# -*- mode: python; coding: utf-8 -*-
# Copyright 2019-2020 the AAS WorldWide Telescope project.
# Licensed under the MIT License.

"""Entrypoint for the "toasty" command-line interface.

"""
from __future__ import absolute_import, division, print_function

import argparse
import os.path
import sys


# General CLI utilities

def die(msg):
    print('error:', msg, file=sys.stderr)
    sys.exit(1)

def warn(msg):
    print('warning:', msg, file=sys.stderr)


def stub_wtml(imgset, wtml_path, place=None):
    """Given an ImageSet object and potential a Place, save its information into a
    stub WTML file.

    """
    from wwt_data_formats import write_xml_doc
    from wwt_data_formats.enums import DataSetType
    from wwt_data_formats.folder import Folder
    from wwt_data_formats.place import Place

    folder = Folder()

    if place is None:
        place = Place()
        place.data_set_type = DataSetType.SKY
        place.foreground_image_set = imgset
        place.name = 'Toasty'
        place.thumbnail = imgset.thumbnail_url
        place.zoom_level = 1.0

    folder.children = [place]

    with open(wtml_path, 'wt') as f:
        write_xml_doc(folder.to_xml(), dest_stream=f)


# "cascade" subcommand

def cascade_getparser(parser):
    parser.add_argument(
        '--start',
        metavar = 'DEPTH',
        type = int,
        help = 'The depth of the TOAST layer to start the cascade',
    )
    parser.add_argument(
        'pyramid_dir',
        metavar = 'DIR',
        help = 'The directory containg the tile pyramid to cascade',
    )


def cascade_impl(settings):
    from .image import ImageMode
    from .merge import averaging_merger, cascade_images
    from .pyramid import PyramidIO

    pio = PyramidIO(settings.pyramid_dir)

    start = settings.start
    if start is None:
        die('currently, you must specify the start layer with the --start option')

    cascade_images(pio, ImageMode.RGBA, start, averaging_merger)


# "healpix_sample_data_tiles" subcommand

def healpix_sample_data_tiles_getparser(parser):
    parser.add_argument(
        '--outdir',
        metavar = 'PATH',
        default = '.',
        help = 'The root directory of the output tile pyramid',
    )
    parser.add_argument(
        'fitspath',
        metavar = 'PATH',
        help = 'The HEALPix FITS file to be tiled',
    )
    parser.add_argument(
        'depth',
        metavar = 'DEPTH',
        type = int,
        help = 'The depth of the TOAST layer to sample',
    )


def healpix_sample_data_tiles_impl(settings):
    from .pyramid import PyramidIO
    from .samplers import healpix_fits_file_sampler
    from .toast import SamplingToastDataSource

    pio = PyramidIO(settings.outdir)
    sampler = healpix_fits_file_sampler(settings.fitspath)
    ds = SamplingToastDataSource(sampler)
    ds.sample_data_layer(pio, settings.depth)


# "image_sample_tiles" subcommand

def image_sample_tiles_getparser(parser):
    parser.add_argument(
        '--outdir',
        metavar = 'PATH',
        default = '.',
        help = 'The root directory of the output tile pyramid',
    )
    parser.add_argument(
        '--projection',
        metavar = 'PROJTYPE',
        default = 'plate-carree',
        help = 'The projection of the image; "plate-carree" is the only allowed choice',
    )
    parser.add_argument(
        'imgpath',
        metavar = 'PATH',
        help = 'The image file to be tiled',
    )
    parser.add_argument(
        'depth',
        metavar = 'DEPTH',
        type = int,
        help = 'The depth of the TOAST layer to sample',
    )


def image_sample_tiles_impl(settings):
    from .io import read_image
    from .pyramid import PyramidIO
    from .toast import SamplingToastDataSource

    pio = PyramidIO(settings.outdir)
    data = read_image(settings.imgpath)

    if settings.projection == 'plate-carree':
        from .samplers import plate_carree_sampler
        sampler = plate_carree_sampler(data)
    else:
        die('the image projection type {!r} is not recognized'.format(settings.projection))

    ds = SamplingToastDataSource(sampler)
    ds.sample_image_layer(pio, settings.depth)


# "multi_tan_make_data_tiles" subcommand

def multi_tan_make_data_tiles_getparser(parser):
    parser.add_argument(
        '--hdu-index',
        metavar = 'INDEX',
        type = int,
        default = 0,
        help = 'Which HDU to load in each input FITS file',
    )
    parser.add_argument(
        '--outdir',
        metavar = 'PATH',
        default = '.',
        help = 'The root directory of the output tile pyramid',
    )
    parser.add_argument(
        'paths',
        metavar = 'PATHS',
        nargs = '+',
        help = 'The FITS files with image data',
    )

def multi_tan_make_data_tiles_impl(settings):
    from .multi_tan import MultiTanDataSource
    from .pyramid import PyramidIO

    pio = PyramidIO(settings.outdir)
    ds = MultiTanDataSource(settings.paths, hdu_index=settings.hdu_index)
    ds.compute_global_pixelization()

    print('Generating Numpy-formatted data tiles in directory {!r} ...'.format(settings.outdir))
    percentiles = ds.generate_deepest_layer_numpy(pio)

    if len(percentiles):
        print()
        print('Median percentiles in the data:')
        for p in sorted(percentiles.keys()):
            print('   {} = {}'.format(p, percentiles[p]))

    # TODO: this should populate and emit a stub index_rel.wtml file.


# "pipeline_fetch_inputs" subcommand

def _pipeline_add_io_args(parser):
    parser.add_argument(
        '--azure-conn-env',
        metavar = 'ENV-VAR-NAME',
        help = 'The name of an environment variable contain an Azure Storage '
                'connection string'
    )
    parser.add_argument(
        '--azure-container',
        metavar = 'CONTAINER-NAME',
        help = 'The name of a blob container in the Azure storage account'
    )
    parser.add_argument(
        '--azure-path-prefix',
        metavar = 'PATH-PREFIX',
        help = 'A slash-separated path prefix for blob I/O within the container'
    )
    parser.add_argument(
        '--local',
        metavar = 'PATH',
        help = 'Use the local-disk I/O backend'
    )

def _pipeline_io_from_settings(settings):
    from .pipeline import AzureBlobPipelineIo, LocalPipelineIo

    if settings.local:
        return LocalPipelineIo(settings.local)

    if settings.azure_conn_env:
        conn_str = os.environ.get(settings.azure_conn_env)
        if not conn_str:
            die('--azure-conn-env=%s provided, but that environment variable is unset'
                % settings.azure_conn_env)

        if not settings.azure_container:
            die('--azure-container-name must be provided if --azure-conn-env is')

        path_prefix = settings.azure_path_prefix
        if not path_prefix:
            path_prefix = ''

        return AzureBlobPipelineIo(
            conn_str,
            settings.azure_container,
            path_prefix
        )

    die('An I/O backend must be specified with the arguments --local or --azure-*')


def pipeline_fetch_inputs_getparser(parser):
    _pipeline_add_io_args(parser)
    parser.add_argument(
        'workdir',
        metavar = 'WORKDIR',
        default = '.',
        help = 'The local working directory',
    )

def pipeline_fetch_inputs_impl(settings):
    from .pipeline import PipelineManager

    pipeio = _pipeline_io_from_settings(settings)
    mgr = PipelineManager(pipeio, settings.workdir)
    mgr.fetch_inputs()


# "pipeline_process_todos" subcommand

def pipeline_process_todos_getparser(parser):
    _pipeline_add_io_args(parser)
    parser.add_argument(
        'workdir',
        metavar = 'WORKDIR',
        default = '.',
        help = 'The local working directory',
    )

def pipeline_process_todos_impl(settings):
    from .pipeline import PipelineManager

    pipeio = _pipeline_io_from_settings(settings)
    mgr = PipelineManager(pipeio, settings.workdir)
    mgr.process_todos()


# "pipeline_publish_todos" subcommand

def pipeline_publish_todos_getparser(parser):
    _pipeline_add_io_args(parser)
    parser.add_argument(
        'workdir',
        metavar = 'WORKDIR',
        default = '.',
        help = 'The local working directory',
    )

def pipeline_publish_todos_impl(settings):
    from .pipeline import PipelineManager

    pipeio = _pipeline_io_from_settings(settings)
    mgr = PipelineManager(pipeio, settings.workdir)
    mgr.publish_todos()


# "pipeline_reindex" subcommand

def pipeline_reindex_getparser(parser):
    _pipeline_add_io_args(parser)
    parser.add_argument(
        'workdir',
        metavar = 'WORKDIR',
        default = '.',
        help = 'The local working directory',
    )

def pipeline_reindex_impl(settings):
    from .pipeline import PipelineManager

    pipeio = _pipeline_io_from_settings(settings)
    mgr = PipelineManager(pipeio, settings.workdir)
    mgr.reindex()


# "study_sample_image_tiles" subcommand

def study_sample_image_tiles_getparser(parser):
    from .image import ImageLoader
    ImageLoader.add_arguments(parser)

    parser.add_argument(
        '--outdir',
        metavar = 'PATH',
        default = '.',
        help = 'The root directory of the output tile pyramid',
    )
    parser.add_argument(
        'imgpath',
        metavar = 'PATH',
        help = 'The study image file to be tiled',
    )


def study_sample_image_tiles_impl(settings):
    import numpy as np
    import PIL.Image
    from wwt_data_formats.imageset import ImageSet
    from .image import ImageLoader
    from .pyramid import PyramidIO
    from .study import tile_study_image

    # Load image and prep tiling
    img = ImageLoader.create_from_args(settings).load_path(settings.imgpath)
    pio = PyramidIO(settings.outdir)
    tiling = tile_study_image(img, pio)

    # Thumbnail.
    thumb = img.make_thumbnail_bitmap()
    thumb.save(os.path.join(settings.outdir, 'thumb.jpg'), format='JPEG')

    # Write out a stub WTML file. The only information this will actually
    # contain is the number of tile levels. Other information can be filled
    # in as processing continues.
    imgset = ImageSet()
    tiling.apply_to_imageset(imgset)
    imgset.base_degrees_per_tile = 1.0  # random default to make it viewable
    imgset.name = 'Toasty'
    imgset.thumbnail_url = 'thumb.jpg'
    imgset.url = pio.get_path_scheme() + '.png'
    stub_wtml(imgset, os.path.join(settings.outdir, 'index_rel.wtml'))

    # Helpful hint:
    print(f'Successfully tiled input "{settings.imgpath}" at level {imgset.tile_levels}.')
    print('To create parent tiles, consider running:')
    print()
    print(f'   toasty cascade --start {imgset.tile_levels} {settings.outdir}')


# "wwtl_sample_image_tiles" subcommand

def wwtl_sample_image_tiles_getparser(parser):
    from .image import ImageLoader
    ImageLoader.add_arguments(parser)

    parser.add_argument(
        '--outdir',
        metavar = 'PATH',
        default = '.',
        help = 'The root directory of the output tile pyramid',
    )
    parser.add_argument(
        'wwtl_path',
        metavar = 'WWTL-PATH',
        help = 'The WWTL layer file to be processed',
    )


def wwtl_sample_image_tiles_impl(settings):
    # TODO: implement WWTL loading as an Image mode.
    from io import BytesIO
    import numpy as np
    import PIL.Image

    from wwt_data_formats.enums import DataSetType, ProjectionType
    from wwt_data_formats.layers import ImageSetLayer, LayerContainerReader
    from wwt_data_formats.place import Place

    from .image import ImageLoader
    from .pyramid import PyramidIO
    from .study import tile_study_image

    # Load WWTL and see if it matches expectations
    lc = LayerContainerReader.from_file(settings.wwtl_path)

    if len(lc.layers) != 1:
        die('WWTL file must contain exactly one layer')

    layer = lc.layers[0]
    if not isinstance(layer, ImageSetLayer):
        die('WWTL file must contain an imageset layer')

    imgset = layer.image_set
    if imgset.projection != ProjectionType.SKY_IMAGE:
        die('WWTL imageset layer must have "SkyImage" projection type')

    # Looks OK. Read and parse the image.
    loader = ImageLoader.create_from_args(settings)
    img_data = lc.read_layer_file(layer, layer.extension)
    img = loader.load_stream(BytesIO(img_data))

    # Tile it!
    pio = PyramidIO(settings.outdir)
    tiling = tile_study_image(img, pio)

    # Thumbnail.
    thumb = img.make_thumbnail_bitmap()
    thumb.save(os.path.join(settings.outdir, 'thumb.jpg'), format='JPEG')

    # Write a WTML file. We reuse the existing imageset as much as possible,
    # but update the parameters that change in the tiling process.

    place = Place()
    wcs_keywords = imgset.wcs_headers_from_position()
    tiling.apply_to_imageset(imgset)
    imgset.set_position_from_wcs(wcs_keywords, img.width, img.height, place=place)

    if not imgset.name:
        imgset.name = 'Toasty'
    imgset.file_type = '.png'
    imgset.thumbnail_url = 'thumb.jpg'
    imgset.url = pio.get_path_scheme() + '.png'

    place.data_set_type = DataSetType.SKY
    place.foreground_image_set = imgset
    place.name = imgset.name
    place.thumbnail = imgset.thumbnail_url

    stub_wtml(imgset, os.path.join(settings.outdir, 'index_rel.wtml'), place=place)

    # Helpful hint:

    print(f'Successfully tiled input "{settings.wwtl_path}" at level {imgset.tile_levels}.')
    print('To create parent tiles, consider running:')
    print()
    print(f'   toasty cascade --start {imgset.tile_levels} {settings.outdir}')


# The CLI driver:

def entrypoint(args=None):
    """The entrypoint for the \"toasty\" command-line interface.

    Parameters
    ----------
    args : iterable of str, or None (the default)
      The arguments on the command line. The first argument should be
      a subcommand name or global option; there is no ``argv[0]``
      parameter.

    """
    # Set up the subcommands from globals()

    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="subcommand")
    commands = set()

    for py_name, value in globals().items():
        if py_name.endswith('_getparser'):
            cmd_name = py_name[:-10].replace('_', '-')
            subparser = subparsers.add_parser(cmd_name)
            value(subparser)
            commands.add(cmd_name)

    # What did we get?

    settings = parser.parse_args(args)

    if settings.subcommand is None:
        print('Run me with --help for help. Allowed subcommands are:')
        print()
        for cmd in sorted(commands):
            print('   ', cmd)
        return

    py_name = settings.subcommand.replace('-', '_')

    impl = globals().get(py_name + '_impl')
    if impl is None:
        die('no such subcommand "{}"'.format(settings.subcommand))

    # OK to go!

    impl(settings)
