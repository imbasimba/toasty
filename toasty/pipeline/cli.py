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


def pipeline_getparser(parser):
    subparsers = parser.add_subparsers(dest='pipeline_command')

    parser = subparsers.add_parser('fetch-inputs')
    _pipeline_add_io_args(parser)
    parser.add_argument(
        'workdir',
        metavar = 'WORKDIR',
        default = '.',
        help = 'The local working directory',
    )

    parser = subparsers.add_parser('process-todos')
    _pipeline_add_io_args(parser)
    parser.add_argument(
        'workdir',
        metavar = 'WORKDIR',
        default = '.',
        help = 'The local working directory',
    )

    parser = subparsers.add_parser('publish-todos')
    _pipeline_add_io_args(parser)
    parser.add_argument(
        'workdir',
        metavar = 'WORKDIR',
        default = '.',
        help = 'The local working directory',
    )

    parser = subparsers.add_parser('reindex')
    _pipeline_add_io_args(parser)
    parser.add_argument(
        'workdir',
        metavar = 'WORKDIR',
        default = '.',
        help = 'The local working directory',
    )


def pipeline_impl(settings):
    from . import PipelineManager

    if settings.pipeline_command is None:
        print('Run the "pipeline" command with `--help` for help on its subcommands')
        return

    pipeio = _pipeline_io_from_settings(settings)
    mgr = PipelineManager(pipeio, settings.workdir)

    if settings.pipeline_command == 'fetch-inputs':
        mgr.fetch_inputs()
    elif settings.pipeline_command == 'process-todos':
        mgr.process_todos()
    elif settings.pipeline_command == 'publish-todos':
        mgr.publish_todos()
    elif settings.pipeline_command == 'reindex':
        mgr.reindex()
    else:
        die('unrecognized "pipeline" subcommand ' + settings.pipeline_command)
