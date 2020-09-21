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

    cascade_images(pio, ImageMode.RGBA, start, averaging_merger, cli_progress=True)


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
    from .builder import Builder
    from .image import ImageMode
    from .pyramid import PyramidIO
    from .samplers import healpix_fits_file_sampler

    pio = PyramidIO(settings.outdir)
    sampler = healpix_fits_file_sampler(settings.fitspath)
    builder = Builder(pio)
    builder.toast_base(ImageMode.F32, sampler, settings.depth)
    builder.write_index_rel_wtml()

    print(f'Successfully tiled input "{settings.fitspath}" at level {builder.imgset.tile_levels}.')
    print('To create parent tiles, consider running:')
    print()
    print(f'   toasty cascade --start {builder.imgset.tile_levels} {settings.outdir}')


# "make_thumbnail" subcommand

def make_thumbnail_getparser(parser):
    from .image import ImageLoader
    ImageLoader.add_arguments(parser)

    parser.add_argument(
        'imgpath',
        metavar = 'IN-PATH',
        help = 'The image file to be thumbnailed',
    )
    parser.add_argument(
        'outpath',
        metavar = 'OUT-PATH',
        help = 'The location of the new thumbnail file',
    )


def make_thumbnail_impl(settings):
    from .image import ImageLoader

    olp = settings.outpath.lower()
    if not (olp.endswith('.jpg') or olp.endswith('.jpeg')):
        warn('saving output in JPEG format even though filename is "{}"'.format(settings.outpath))

    img = ImageLoader.create_from_args(settings).load_path(settings.imgpath)
    thumb = img.make_thumbnail_bitmap()

    with open(settings.outpath, 'wb') as f:
        thumb.save(f, format='JPEG')


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


# "tile_allsky" subcommand

def tile_allsky_getparser(parser):
    from .image import ImageLoader
    ImageLoader.add_arguments(parser)

    parser.add_argument(
        '--outdir',
        metavar = 'PATH',
        default = '.',
        help = 'The root directory of the output tile pyramid',
    )
    parser.add_argument(
        '--placeholder-thumbnail',
        action = 'store_true',
        help = 'Do not attempt to thumbnail the input image -- saves memory for large inputs',
    )
    parser.add_argument(
        '--projection',
        metavar = 'PROJTYPE',
        default = 'plate-carree',
        help = 'The projection type of the input image (default: %(default)s; choices: %(choices)s)',
        choices = ['plate-carree', 'plate-carree-galactic', 'plate-carree-planet'],
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


def tile_allsky_impl(settings):
    from .builder import Builder
    from .image import ImageLoader
    from .pyramid import PyramidIO

    img = ImageLoader.create_from_args(settings).load_path(settings.imgpath)
    pio = PyramidIO(settings.outdir)

    if settings.projection == 'plate-carree':
        from .samplers import plate_carree_sampler
        sampler = plate_carree_sampler(img.asarray())
    elif settings.projection == 'plate-carree-galactic':
        from .samplers import plate_carree_galactic_sampler
        sampler = plate_carree_galactic_sampler(img.asarray())
    elif settings.projection == 'plate-carree-planet':
        from .samplers import plate_carree_planet_sampler
        sampler = plate_carree_planet_sampler(img.asarray())
    else:
        die('the image projection type {!r} is not recognized'.format(settings.projection))

    builder = Builder(pio)

    # Do the thumbnail first since for large inputs it can be the memory high-water mark!
    if settings.placeholder_thumbnail:
        builder.make_placeholder_thumbnail()
    else:
        builder.make_thumbnail_from_other(img)

    builder.toast_base(img.mode, sampler, settings.depth, cli_progress=True)
    builder.write_index_rel_wtml()

    print(f'Successfully tiled input "{settings.imgpath}" at level {builder.imgset.tile_levels}.')
    print('To create parent tiles, consider running:')
    print()
    print(f'   toasty cascade --start {builder.imgset.tile_levels} {settings.outdir}')


# "tile_study" subcommand

def tile_study_getparser(parser):
    from .image import ImageLoader
    ImageLoader.add_arguments(parser)

    parser.add_argument(
        '--placeholder-thumbnail',
        action = 'store_true',
        help = 'Do not attempt to thumbnail the input image -- saves memory for large inputs',
    )
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


def tile_study_impl(settings):
    from .builder import Builder
    from .image import ImageLoader
    from .pyramid import PyramidIO

    img = ImageLoader.create_from_args(settings).load_path(settings.imgpath)
    pio = PyramidIO(settings.outdir)
    builder = Builder(pio)
    builder.default_tiled_study_astrometry()

    # Do the thumbnail first since for large inputs it can be the memory high-water mark!
    if settings.placeholder_thumbnail:
        builder.make_placeholder_thumbnail()
    else:
        builder.make_thumbnail_from_other(img)

    builder.tile_base_as_study(img, cli_progress=True)
    builder.write_index_rel_wtml()

    print(f'Successfully tiled input "{settings.imgpath}" at level {builder.imgset.tile_levels}.')
    print('To create parent tiles, consider running:')
    print()
    print(f'   toasty cascade --start {builder.imgset.tile_levels} {settings.outdir}')


# "tile_wwtl" subcommand

def tile_wwtl_getparser(parser):
    from .image import ImageLoader
    ImageLoader.add_arguments(parser)

    parser.add_argument(
        '--placeholder-thumbnail',
        action = 'store_true',
        help = 'Do not attempt to thumbnail the input image -- saves memory for large inputs',
    )
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


def tile_wwtl_impl(settings):
    from .builder import Builder
    from .image import ImageLoader
    from .pyramid import PyramidIO

    pio = PyramidIO(settings.outdir)
    builder = Builder(pio)
    img = builder.load_from_wwtl(settings, settings.wwtl_path)

    # Do the thumbnail first since for large inputs it can be the memory high-water mark!
    if settings.placeholder_thumbnail:
        builder.make_placeholder_thumbnail()
    else:
        builder.make_thumbnail_from_other(img)

    builder.tile_base_as_study(img, cli_progress=True)
    builder.write_index_rel_wtml()

    print(f'Successfully tiled input "{settings.wwtl_path}" at level {builder.imgset.tile_levels}.')
    print('To create parent tiles, consider running:')
    print()
    print(f'   toasty cascade --start {builder.imgset.tile_levels} {settings.outdir}')


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
