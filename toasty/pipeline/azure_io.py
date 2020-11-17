# -*- mode: python; coding: utf-8 -*-
# Copyright 2020 the AAS WorldWide Telescope project
# Licensed under the MIT License.

"""
Azure Blob Storage I/O backend for the pipeline framework.

This module requires that the ``azure.storage.blob`` Python module be available.
If it is not, this module will still be importable, but it won't work. Check the
``ENABLED`` boolean variable or call :func:`assert_enabled` to raise an
exception offering guidance if the needed support is missing.

"""

__all__ = '''
AzureBlobPipelineIo
ENABLED
assert_enabled
'''.split()

from . import PipelineIo

try:
    from azure.storage.blob import BlockBlobService
    ENABLED = True
except ImportError:
    ENABLED = False


def assert_enabled():
    if not ENABLED:
        raise Exception('Azure pipeline I/O backend is needed but unavailable -'
            ' install the `azure-storage-blob` package')


class AzureBlobPipelineIo(PipelineIo):
    """I/O for pipeline processing that uses Microsoft Azure Blob Storage.

    Parameters
    ----------
    connection_string : str
      The Azure "connection string" to use
    container_name : str
      The name of the blob container within the storage account
    path_prefix : str or iterable of str
      A list folder names within the blob container that will be
      prepended to all paths accessed through this object.

    """
    _svc = None
    _container_name = None
    _path_prefix = None

    def __init__(self, connection_string, container_name, path_prefix):
        assert_enabled()

        if isinstance(path_prefix, str):
            path_prefix = (path_prefix, )
        else:
            try:
                path_prefix = tuple(path_prefix)
                for item in path_prefix:
                    assert isinstance(item, str)
            except Exception:
                raise ValueError('path_prefix should be a string or iterable of strings; '
                                 'got %r' % (path_prefix, ))

        self._svc = BlockBlobService(connection_string=connection_string)
        self._container_name = container_name
        self._path_prefix = path_prefix

    def _make_blob_name(self, path_array):
        """TODO: is this actually correct? Escaping?"""
        return '/'.join(self._path_prefix + tuple(path_array))

    def check_exists(self, *path):
        return self._svc.exists(
            self._container_name,
            self._make_blob_name(path),
        )

    def get_item(self, *path, dest=None):
        self._svc.get_blob_to_stream(
            self._container_name,
            self._make_blob_name(path),
            dest,
        )

    def put_item(self, *path, source=None):
        self._svc.create_blob_from_stream(
            self._container_name,
            self._make_blob_name(path),
            source,
        )

    def list_items(self, *path):
        from azure.storage.blob.models import BlobPrefix
        prefix = self._make_blob_name(path) + '/'

        for item in self._svc.list_blobs(
                self._container_name,
                prefix = prefix,
                delimiter = '/'
        ):
            assert item.name.startswith(prefix)
            stem = item.name[len(prefix):]
            is_folder = isinstance(item, BlobPrefix)

            if is_folder:
                # Returned names end with a '/' too
                assert stem[-1] == '/'
                stem = stem[:-1]

            yield stem, is_folder
