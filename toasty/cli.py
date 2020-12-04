# -*- mode: python; coding: utf-8 -*-
# Copyright 2019-2020 the AAS WorldWide Telescope project.
# Licensed under the MIT License.

"""Entrypoint for the "toasty" command-line interface.

"""

from __future__ import absolute_import, division, print_function

__all__ = '''
die
entrypoint
warn
'''.split()

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
        '--parallelism', '-j',
        metavar = 'COUNT',
        type = int,
        help = 'The parallelization level (default: use all CPUs; specify `1` to force serial processing)',
    )
    parser.add_argument(
        '--format', '-f',
        metavar = 'FORMAT',
        default = None,
        choices = ['png', 'jpg', 'npy', 'fits'],
        help = 'The format of data files to cascade. If not specified, this will be guessed.',
    )
    parser.add_argument(
        '--start',
        metavar = 'DEPTH',
        type = int,
        help = 'The depth of the TOAST layer to start the cascade',
    )
    parser.add_argument(
        'pyramid_dir',
        metavar = 'DIR',
        help = 'The directory containing the tile pyramid to cascade',
    )


def cascade_impl(settings):
    from .image import ImageMode
    from .merge import averaging_merger, cascade_images
    from .pyramid import PyramidIO

    pio = PyramidIO(settings.pyramid_dir, default_format=settings.format)

    start = settings.start
    if start is None:
        die('currently, you must specify the start layer with the --start option')

    cascade_images(
        pio,
        start,
        averaging_merger,
        parallel=settings.parallelism,
        cli_progress=True
    )


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

    pio = PyramidIO(settings.outdir, default_format='npy')
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


# "pipeline" subcommands

from .pipeline.cli import pipeline_getparser, pipeline_impl


# "tile_allsky" subcommand

def tile_allsky_getparser(parser):
    from .image import ImageLoader
    ImageLoader.add_arguments(parser)

    parser.add_argument(
        '--name',
        metavar = 'NAME',
        default = 'Toasty',
        help = 'The image name to embed in the output WTML file (default: %(default)s)',
    )
    parser.add_argument(
        '--outdir',
        metavar = 'PATH',
        default = '.',
        help = 'The root directory of the output tile pyramid (default: %(default)s)',
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
        choices = ['plate-carree', 'plate-carree-galactic', 'plate-carree-ecliptic', 'plate-carree-planet'],
    )
    parser.add_argument(
        '--parallelism', '-j',
        metavar = 'COUNT',
        type = int,
        help = 'The parallelization level (default: use all CPUs if OS supports; specify `1` to force serial processing)',
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
    is_planet = False

    if settings.projection == 'plate-carree':
        from .samplers import plate_carree_sampler
        sampler = plate_carree_sampler(img.asarray())
    elif settings.projection == 'plate-carree-galactic':
        from .samplers import plate_carree_galactic_sampler
        sampler = plate_carree_galactic_sampler(img.asarray())
    elif settings.projection == 'plate-carree-ecliptic':
        from .samplers import plate_carree_ecliptic_sampler
        sampler = plate_carree_ecliptic_sampler(img.asarray())
    elif settings.projection == 'plate-carree-planet':
        from .samplers import plate_carree_planet_sampler
        sampler = plate_carree_planet_sampler(img.asarray())
        is_planet = True
    else:
        die('the image projection type {!r} is not recognized'.format(settings.projection))

    builder = Builder(pio)

    # Do the thumbnail first since for large inputs it can be the memory high-water mark!
    if settings.placeholder_thumbnail:
        builder.make_placeholder_thumbnail()
    else:
        builder.make_thumbnail_from_other(img)

    builder.toast_base(
        sampler,
        settings.depth,
        is_planet=is_planet,
        parallel=settings.parallelism,
        cli_progress=True,
    )
    builder.set_name(settings.name)
    builder.write_index_rel_wtml()

    print(f'Successfully tiled input "{settings.imgpath}" at level {builder.imgset.tile_levels}.')
    print('To create parent tiles, consider running:')
    print()
    print(f'   toasty cascade --start {builder.imgset.tile_levels} {settings.outdir}')


# "tile_healpix" subcommand

def tile_healpix_getparser(parser):
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


def tile_healpix_impl(settings):
    from .builder import Builder
    from .image import ImageMode
    from .pyramid import PyramidIO
    from .samplers import healpix_fits_file_sampler

    pio = PyramidIO(settings.outdir, default_format='npy')
    sampler = healpix_fits_file_sampler(settings.fitspath)
    builder = Builder(pio)
    builder.toast_base(sampler, settings.depth)
    builder.write_index_rel_wtml()

    print(f'Successfully tiled input "{settings.fitspath}" at level {builder.imgset.tile_levels}.')
    print('To create parent tiles, consider running:')
    print()
    print(f'   toasty cascade --start {builder.imgset.tile_levels} {settings.outdir}')


# "tile_study" subcommand

def tile_study_getparser(parser):
    from .image import ImageLoader
    ImageLoader.add_arguments(parser)

    parser.add_argument(
        '--name',
        metavar = 'NAME',
        default = 'Toasty',
        help = 'The image name to embed in the output WTML file (default: %(default)s)',
    )
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
    pio = PyramidIO(settings.outdir, default_format=img.default_format)
    builder = Builder(pio)

    if img.wcs is None:
        builder.default_tiled_study_astrometry()
    else:
        builder.apply_wcs_info(img.wcs, img.width, img.height)

    # Do the thumbnail first since for large inputs it can be the memory high-water mark!
    if settings.placeholder_thumbnail:
        builder.make_placeholder_thumbnail()
    else:
        builder.make_thumbnail_from_other(img)

    builder.tile_base_as_study(img, cli_progress=True)
    builder.set_name(settings.name)
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


# "transform" subcommand

def transform_getparser(parser):
    subparsers = parser.add_subparsers(dest='transform_command')

    parser = subparsers.add_parser('fx3-to-rgb')
    parser.add_argument(
        '--parallelism', '-j',
        metavar = 'COUNT',
        type = int,
        help = 'The parallelization level (default: use all CPUs; specify `1` to force serial processing)',
    )
    parser.add_argument(
        '--start',
        metavar = 'DEPTH',
        type = int,
        help = 'The depth of the pyramid layer to start the cascade',
    )
    parser.add_argument(
        '--clip', '-c',
        metavar = 'NUMBER',
        type = float,
        default = 1.0,
        help = 'The level at which to start flipping the floating-point data',
    )
    parser.add_argument(
        'pyramid_dir',
        metavar = 'DIR',
        help = 'The directory containing the tile pyramid to cascade',
    )


def transform_impl(settings):
    from .pyramid import PyramidIO

    if settings.transform_command is None:
        print('Run the "transform" command with `--help` for help on its subcommands')
        return

    if settings.transform_command == 'fx3-to-rgb':
        from .transform import f16x3_to_rgb
        pio = PyramidIO(settings.pyramid_dir)
        f16x3_to_rgb(
            pio, settings.start,
            clip = settings.clip,
            parallel = settings.parallelism,
            cli_progress = True,
        )
    else:
        die('unrecognized "transform" subcommand ' + settings.transform_command)


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
