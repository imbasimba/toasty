# -*- mode: python; coding: utf-8 -*-
# Copyright 2020 the AAS WorldWide Telescope project
# Licensed under the MIT License.

"""A framework for automating the ingest of source images into the formats
used by AAS WorldWide Telescope.

"""
from __future__ import absolute_import, division, print_function

__all__ = '''
CandidateInput
ImageSource
NotActionableError
PipelineIo
'''.split()

from abc import ABC, abstractclassmethod, abstractmethod
from datetime import datetime, timezone
import numpy as np
import os.path
import shutil
import sys
from urllib.parse import urlsplit, quote as urlquote
from wwt_data_formats import write_xml_doc
from wwt_data_formats.folder import Folder
from wwt_data_formats.imageset import ImageSet
from wwt_data_formats.place import Place
import yaml


def splitall(path):
    """Split a path into individual components.

    E.g.: "/a/b" => ["/", "a", "b"]; "b/c" => ["b", "c"]

    From https://www.oreilly.com/library/view/python-cookbook/0596001673/ch04s16.html.
    """
    allparts = []

    while True:
        parts = os.path.split(path)
        if parts[0] == path:  # sentinel for absolute paths
            allparts.insert(0, parts[0])
            break
        elif parts[1] == path: # sentinel for relative paths
            allparts.insert(0, parts[1])
            break
        else:
            path = parts[0]
            allparts.insert(0, parts[1])
    return allparts


class NotActionableError(Exception):
    """Raised when an image is provided to the pipeline but for some reason we're
    not going to be able to get it into a WWT-compatible form.

    """


class PipelineIo(ABC):
    """
    An abstract base class for I/O relating to pipeline processing. An instance
    of this class might be used to fetch files from, and send them to, a cloud
    storage system like S3 or Azure Storage.
    """

    @abstractmethod
    def _export_config(self):
        """
        Export this object's configuration for serialization.

        Returns
        -------
        A dictionary of settings that can be saved as YAML format. There should
        be a key named "_type" with a string value identifying the I/O
        implementation type.
        """

    def save_config(self, path):
        """
        Save this object's configuration to the specified filesystem path.
        """
        cfg = self._export_config()

        # The config contains secrets, so create it privately and securely.
        opener = lambda path, _mode: os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, mode=0o600)

        with open(path, 'wt', opener=opener, encoding='utf8') as f:
            yaml.dump(cfg, f, yaml.SafeDumper)

    @abstractclassmethod
    def _new_from_config(cls, config):
        """
        Create a new instance of this class based on serialized configuration.

        Parameters
        ----------
        config : dict
            A dict of configuration that was created with ``_export_config``

        Returns
        -------
        A new instance of the class.
        """

    @classmethod
    def load_from_config(self, path):
        """
        Create a new I/O backend from saved configuration.

        Parameters
        ----------
        path : path-like
            The path where the configuration was saved.

        Returns
        -------
        A new instance implementing the PipelineIO abstract base class.
        """

        with open(path, 'rt', encoding='utf8') as f:
            config = yaml.safe_load(f)

        ty = config.get('_type')

        if ty == 'local':
            from .local_io import LocalPipelineIo
            cls = LocalPipelineIo
        elif ty == 'azure-blob':
            from .azure_io import AzureBlobPipelineIo
            cls = AzureBlobPipelineIo
        else:
            raise Exception(f'unrecognized pipeline I/O storage type {ty!r}')

        return cls._new_from_config(config)

    @abstractmethod
    def check_exists(self, *path):
        """Test whether an item at the specified path exists.

        Parameters
        ----------
        *path : strings
            The path to the item, intepreted as components in a folder hierarchy.

        Returns
        -------
        A boolean indicating whether the item in question exists.

        """

    @abstractmethod
    def get_item(self, *path, dest=None):
        """Fetch a file-like item at the specified path, writing its contents into the
        specified file-like object *dest*.

        Parameters
        ----------
        *path : strings
            The path to the item, intepreted as components in a folder hierarchy.
        dest : writeable file-like object
            The object into which the item's data will be written as bytes.

        Returns
        -------
        None.

        """

    @abstractmethod
    def put_item(self, *path, source=None):
        """Put a file-like item at the specified path, reading its contents from the
        specified file-like object *source*.

        Parameters
        ----------
        *path : strings
            The path to the item, intepreted as components in a folder hierarchy.
        source : readable file-like object
            The object from which the item's data will be read, as bytes.

        Returns
        -------
        None.

        """

    @abstractmethod
    def list_items(self, *path):
        """List the items contained in the folder at the specified path.

        Parameters
        ----------
        *path : strings
            The path to the item, intepreted as components in a folder hierarchy.

        Returns
        -------
        An iterable of ``(stem, is_folder)``, where *stem* is the "basename" of an
        item contained within the specified folder and *is_folder* is a boolean
        indicating whether this item appears to be a folder itself.

        """


class ImageSource(ABC):
    """An abstract base class representing a source of images to be processed in
    the image-processing pipeline. An instance of this class might fetch
    images from an RSS feed or an AstroPix search.

    """
    @abstractclassmethod
    def get_config_key(cls):
        """Get the name of the section key used for this source's configuration data.

        Returns
        -------
        A string giving a key name usable in a YAML file.

        """

    @abstractclassmethod
    def deserialize(cls, data):
        """Create an instance of this class by deserializing configuration data.

        Parameters
        ----------
        data : dict-like object
            A dict-like object containing configuration items deserialized from
            a format such as JSON or YAML. The particular contents can vary
            depending on the implementation.

        Returns
        -------
        An instance of *cls*

        """

    @abstractmethod
    def query_candidates(self):
        """
        Generate a sequence of candidate input images that the pipeline may want
        to process.

        Returns
        -------
        A generator that yields a sequence of :class:`toasty.pipeline.CandidateInput` instances.

        """

    @abstractmethod
    def fetch_candidate(self, unique_id, cand_data_stream, cachedir):
        """
        Download a candidate image and prepare it for processing.

        Parameters
        ----------
        unique_id : str
            The unique ID returned by the :class:`toasty.pipeline.CandidateInput` instance
            that was returned from the initial query.
        cand_data_stream : readable stream returning bytes
            A data stream returning the data that were saved when the candidate
            was queried (:meth:`toasty.pipeline.CandidateInput.save`).
        cachedir : path-like
            A path pointing to a local directory inside of which the
            full image data and metadata should be cached.
        """

    @abstractmethod
    def process(self, unique_id, cand_data_stream, cachedir, builder):
        """
        Process an input into WWT format.

        Parameters
        ----------
        unique_id : str
            The unique ID returned by the :class:`toasty.pipeline.CandidateInput` instance
            that was returned from the initial query.
        cand_data_stream : readable stream returning bytes
            A data stream returning the data that were saved when the candidate
            was queried (:meth:`toasty.pipeline.CandidateInput.save`).
        cachedir : path-like
            A path pointing to a local directory inside of which the
            full image data and metadata should be cached.
        builder : :class:`toasty.builder.Builder`
            State object for constructing the WWT data files.

        Notes
        -----
        Your image processor should run the tile cascade, if needed, but the
        caller will take care of emitting the ``index_rel.wtml`` file.
        """


class CandidateInput(ABC):
    """An abstract base class representing an image from one of our sources. If it
    has not been processed before, we will fetch its data and queue it for
    processing.

    """
    @abstractmethod
    def get_unique_id(self):
        """
        Get an ID for this image that will be unique in its :class:`toasty.pipeline.ImageSource`.

        Returns
        -------
        An identifier as a string. Should be limited to path-friendly
        characters, i.e. ASCII without spaces.

        """

    @abstractmethod
    def save(self, stream):
        """
        Serialize candidate information for future processing

        Parameters
        ----------
        stream : writeable stream accepting bytes
           The stream into which the candidate information should be serialized.

        Raises
        ------
        May raise :exc:`toasty.pipeline.NotActionableError` if it turns out that this
        candidate is not one that can be imported into WWT.

        Returns
        -------
        None.

        """


# The PipelineManager class that orchestrates it all

class PipelineManager(object):
    _config = None
    _pipeio = None
    _workdir = None
    _img_source = None

    def __init__(self, workdir):
        self._workdir = workdir
        self._pipeio = PipelineIo.load_from_config(self._path('toasty-store-config.yaml'))

    def _path(self, *path):
        return os.path.join(self._workdir, *path)

    def _ensure_dir(self, *path):
        path = self._path(*path)
        os.makedirs(path, exist_ok=True)
        return path

    def ensure_config(self):
        if self._config is not None:
            return self._config

        self._ensure_dir()
        cfg_path = self._path('toasty-pipeline-config.yaml')

        if not os.path.exists(cfg_path):  # racey
            with open(cfg_path, 'wb') as f:
                self._pipeio.get_item('toasty-pipeline-config.yaml', dest=f)

        with open(cfg_path, 'rt', encoding='utf8') as f:
            config = yaml.safe_load(f)

        if config is None:
            raise Exception('no toasty-pipeline-config.yaml found in the storage')

        self._config = config
        return self._config

    def get_image_source(self):
        if self._img_source is not None:
            return self._img_source

        self.ensure_config()

        source_type = self._config.get('source_type')
        if not source_type:
            raise Exception('toasty pipeline configuration must have a source_type key')

        if source_type == 'astropix':
            from .astropix import AstroPixImageSource
            cls = AstroPixImageSource
        else:
            raise Exception('unrecognized image source type %s' % source_type)

        cfg_key = cls.get_config_key()
        source_config = self._config.get(cfg_key)
        if source_config is None:
            raise Exception('no image source configuration key %s in the config file' % cfg_key)

        self._img_source = cls.deserialize(source_config)
        return self._img_source

    def process_todos(self):
        from ..builder import Builder
        from ..pyramid import PyramidIO

        src = self.get_image_source()
        cand_dir = self._path('candidates')
        self._ensure_dir('cache_done')
        baseoutdir = self._ensure_dir('processed')

        for uniq_id in os.listdir(self._path('cache_todo')):
            cachedir = self._path('cache_todo', uniq_id)
            outdir = self._path('processed', uniq_id)

            pio = PyramidIO(outdir, scheme='LXY')
            builder = Builder(pio)
            cdata = open(os.path.join(cand_dir, uniq_id), 'rb')

            print(f'processing {uniq_id} ... ', end='')
            sys.stdout.flush()

            src.process(uniq_id, cdata, cachedir, builder)
            cdata.close()
            builder.write_index_rel_wtml()
            print('done')

            # Woohoo, done!
            os.rename(cachedir, self._path('cache_done', uniq_id))

    def publish_todos(self):
        done_dir = self._ensure_dir('out_done')
        todo_dir = self._path('out_todo')
        pfx = todo_dir + os.path.sep

        for dirpath, dirnames, filenames in os.walk(todo_dir, topdown=False):
            # If there's a index.wtml file, save it for last -- that will
            # indicate that this directory has uploaded fully successfully.

            try:
                index_index = filenames.index('index.wtml')
            except ValueError:
                pass
            else:
                temp = filenames[-1]
                filenames[-1] = 'index.wtml'
                filenames[index_index] = temp

            print(f'publishing {dirpath} ...')

            for filename in filenames:
                # Get the components of the item path relative to todo_dir.
                p = os.path.join(dirpath, filename)
                assert p.startswith(pfx)
                sub_components = splitall(p[len(pfx):])

                with open(p, 'rb') as f:
                    self._pipeio.put_item(*sub_components, source=f)

                done_path = os.path.join(done_dir, *sub_components)
                self._ensure_dir('out_done', *sub_components[:-1])
                os.rename(p, done_path)

            # All the files are gone. We can remove this directory.
            os.rmdir(dirpath)

    def reindex(self):
        from io import BytesIO
        from xml.etree import ElementTree as etree

        self.ensure_config()

        def get_items():
            for stem, is_folder in self._pipeio.list_items():
                if not is_folder:
                    continue
                if not self._pipeio.check_exists(stem, 'index.wtml'):
                    continue

                wtml_data = BytesIO()
                self._pipeio.get_item(stem, 'index.wtml', dest=wtml_data)
                wtml_data = wtml_data.getvalue()
                if not len(wtml_data):
                    continue

                xml = etree.fromstring(wtml_data)
                folder = Folder.from_xml(xml)
                pl = folder.children[0]
                assert isinstance(pl, Place)
                yield pl

        def get_updated(pl):
            ludt = datetime.fromisoformat(pl.xmeta.LastUpdated)
            if ludt.tzinfo is None:
                ludt = ludt.replace(tzinfo=timezone.utc)
            return ludt

        items = sorted(
            get_items(),
            key = get_updated,
            reverse = True
        )

        folder = Folder()
        folder.children = items
        folder.name = self._config['folder_name']
        folder.thumbnail = self._config['folder_thumbnail_url']

        indexed = BytesIO()
        write_xml_doc(folder.to_xml(), dest_stream=indexed, dest_wants_bytes=True)

        indexed.seek(0)
        self._pipeio.put_item('index.wtml', source=indexed)

        n = len(folder.children)

        pub_url_prefix = self._config.get('publish_url_prefix')
        if pub_url_prefix:
            if pub_url_prefix[-1] != '/':
                pub_url_prefix += '/'

        print(f'Published new index of {n} items to: {pub_url_prefix}index.wtml')
