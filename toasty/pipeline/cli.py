# -*- mode: python; coding: utf-8 -*-
# Copyright 2019-2020 the AAS WorldWide Telescope project.
# Licensed under the MIT License.

"""
Entrypoints for the "toasty pipeline" command-line tools.
"""

__all__ = '''
pipeline_getparser
pipeline_impl
'''.split()

import argparse
import os.path
import sys

from ..cli import die, warn
from . import NotActionableError


# The "init" subcommand

def init_setup_parser(parser):
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
    parser.add_argument(
        'workdir',
        nargs = '?',
        metavar = 'PATH',
        default = '.',
        help = 'The working directory for this processing session'
    )


def _pipeline_io_from_settings(settings):
    from . import azure_io, local_io

    if settings.local:
        return local_io.LocalPipelineIo(settings.local)

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

        azure_io.assert_enabled()

        return azure_io.AzureBlobPipelineIo(
            conn_str,
            settings.azure_container,
            path_prefix
        )

    die('An I/O backend must be specified with the arguments --local or --azure-*')


def init_impl(settings):
    pipeio = _pipeline_io_from_settings(settings)
    os.makedirs(settings.workdir, exist_ok=True)
    pipeio.save_config(os.path.join(settings.workdir, 'toasty-store-config.yaml'))


# The "refresh" subcommand
#
# TODO: for large feeds, we should potentially add features to make it so that
# we don't re-check every single candidate that's ever been posted.

def refresh_setup_parser(parser):
    parser.add_argument(
        'workdir',
        nargs = '?',
        metavar = 'PATH',
        default = '.',
        help = 'The working directory for this processing session'
    )


def refresh_impl(settings):
    from . import PipelineManager

    mgr = PipelineManager(settings.workdir)
    cand_dir = mgr._ensure_dir('candidates')
    rej_dir = mgr._ensure_dir('rejects')
    src = mgr.get_image_source()
    n_cand = 0
    n_saved = 0
    n_done = 0
    n_skipped = 0
    n_rejected = 0

    for cand in src.query_candidates():
        n_cand += 1
        uniq_id = cand.get_unique_id()

        if mgr._pipeio.check_exists(uniq_id, 'index.wtml'):
            n_done += 1
            continue  # skip already-done inputs

        if mgr._pipeio.check_exists(uniq_id, 'skip.flag'):
            n_skipped += 1
            continue  # skip inputs that are explicitly flagged

        cand_path = os.path.join(cand_dir, uniq_id)

        try:
            with open(cand_path, 'wb') as f:
                cand.save(f)
            n_saved += 1
        except NotActionableError as e:
            os.remove(cand_path)

            with open(os.path.join(rej_dir, uniq_id, 'wb')) as f:
                pass  # for now, just touch the file

            n_rejected += 1

    print(f'analyzed {n_cand} candidates from the image source')
    print(f'  - {n_saved} processing candidates saved')
    print(f'  - {n_rejected} rejected as definitely unusable')
    print(f'  - {n_done} were already done')
    print(f'  - {n_skipped} were already marked to be ignored')
    print()
    print('See the `candidates` directory for candidate image IDs.')


# Other subcommands not yet split out.

def pipeline_getparser(parser):
    subparsers = parser.add_subparsers(dest='pipeline_command')

    parser = subparsers.add_parser('fetch-inputs')
    parser.add_argument(
        'workdir',
        nargs = '?',
        metavar = 'WORKDIR',
        default = '.',
        help = 'The local working directory',
    )

    init_setup_parser(subparsers.add_parser('init'))

    parser = subparsers.add_parser('process-todos')
    parser.add_argument(
        'workdir',
        nargs = '?',
        metavar = 'WORKDIR',
        default = '.',
        help = 'The local working directory',
    )

    parser = subparsers.add_parser('publish-todos')
    parser.add_argument(
        'workdir',
        nargs = '?',
        metavar = 'WORKDIR',
        default = '.',
        help = 'The local working directory',
    )

    refresh_setup_parser(subparsers.add_parser('refresh'))

    parser = subparsers.add_parser('reindex')
    parser.add_argument(
        'workdir',
        nargs = '?',
        metavar = 'WORKDIR',
        default = '.',
        help = 'The local working directory',
    )


def pipeline_impl(settings):
    from . import PipelineManager

    if settings.pipeline_command is None:
        print('Run the "pipeline" command with `--help` for help on its subcommands')
        return

    if settings.pipeline_command == 'fetch-inputs':
        mgr = PipelineManager(settings.workdir)
        mgr.fetch_inputs()
    elif settings.pipeline_command == 'init':
        init_impl(settings)
    elif settings.pipeline_command == 'process-todos':
        mgr = PipelineManager(settings.workdir)
        mgr.process_todos()
    elif settings.pipeline_command == 'publish-todos':
        mgr = PipelineManager(settings.workdir)
        mgr.publish_todos()
    elif settings.pipeline_command == 'refresh':
        refresh_impl(settings)
    elif settings.pipeline_command == 'reindex':
        mgr = PipelineManager(settings.workdir)
        mgr.reindex()
    else:
        die('unrecognized "pipeline" subcommand ' + settings.pipeline_command)
