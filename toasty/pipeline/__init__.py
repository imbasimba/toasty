# -*- mode: python; coding: utf-8 -*-
# Copyright 2020 the AAS WorldWide Telescope project
# Licensed under the MIT License.

"""A framework for automating the ingest of source images into the formats
used by AAS WorldWide Telescope.

"""
from __future__ import absolute_import, division, print_function

__all__ = '''
BitmapInputImage
CandidateInput
ImageSource
InputImage
NotActionableError
PipelineIo
'''.split()

from abc import ABC, abstractclassmethod, abstractmethod
from datetime import datetime, timezone
import numpy as np
import os.path
import shutil
from urllib.parse import urlsplit, quote as urlquote
from wwt_data_formats import write_xml_doc
from wwt_data_formats.folder import Folder
from wwt_data_formats.imageset import ImageSet
from wwt_data_formats.place import Place
import yaml


def maybe_prefix_url(url, prefix):
    """Add a prefix to a URL *if* it is relative URL. This function is used to
    manipulate URLs such as credits_url but only if they're not absolute URLs
    pointing to external resources. Empty URLs will also be unmodified

    """
    if not url:
        return url
    is_relative = not bool(urlsplit(url).netloc)
    if is_relative:
        return prefix + url
    return url

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

EXTENSION_REMAPPING = {
    'jpeg': 'jpg',
}


# The `PipelineIo` ABC

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


# The `ImageSource` ABC and implementations

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
        """Generate a sequence of candidate input images that the pipeline may want to
        process.

        Returns
        -------
        A generator that yields a sequence of :class:`CandidateInput` instances.

        """

    @abstractmethod
    def open_input(self, unique_id, cachedir):
        """Open an input image for processing.

        Parameters
        ----------
        unique_id : str
            The unique ID returned by the :class:`CandidateInput` instance that created
            the cached data for this input image.
        cachedir : str
           A path pointing to a local directory inside of which the
           source data were cached.

        Returns
        -------
        An instance of :class:`InputImage` corresponding to the cached data.

        """


# The `CandidateInput` ABC and implementation

class CandidateInput(ABC):
    """An abstract base class representing an image from one of our sources. If it
    has not been processed before, we will fetch its data and queue it for
    processing.

    """
    @abstractmethod
    def get_unique_id(self):
        """Get an ID for this image that will be unique in its :class:`ImageSource`.

        Returns
        -------
        An identifier as a string. Should be limited to path-friendly
        characters, i.e. ASCII without spaces.

        """

    @abstractmethod
    def cache_data(self, cachedir):
        """Cache all of the source image data and metadata locally.

        Parameters
        ----------
        cachedir : str
           A path pointing to a local directory inside of which the
           source data should be cached.

        Raises
        ------
        May raise :exc:`NotActionableError` if it turns out that this
        candidate is not one that can be imported into WWT.

        Returns
        -------
        None.

        """


# The `InputImage` ABC and implementation

class InputImage(ABC):
    """An abstract base class representing an image to be processed by the
    pipeline. Such an "image" need not correspond to a single RGB image, but
    it does have to be convertible into some kind of WWT-compatible format
    expressible as a :class:`wwt_data_formats.imageset.ImageSet` item.

    Parameters
    ----------
    unique_id : str
        The unique ID returned by the :class:`CandidateInput` instance that created
        the cached data for this input image.
    cachedir : str
       A path pointing to a local directory inside of which the
       image source data were cached locally.

    """
    def __init__(self, unique_id, cachedir):
        self._unique_id = unique_id
        self._cachedir = cachedir

    @abstractmethod
    def _process_image_data(self, imgset, outdir):
        """Convert the image data into a WWT-compatible format.

        Parameters
        ----------
        imgset : :class:`wwt_data_formats.imageset.ImageSet`
           An object representing metadata about the resulting WWT-compatible
           imagery. Fields inside this object should be filled in as
           appropriate to correspond to the data processing done here. Data URLs
           should be filled in as URLs relative to *outdir*.
        outdir : str
           A path pointing to a local directory inside of which the
           WWT-compatible output data files should be written.

        Returns
        -------
        None.

        Notes
        -----
        This function should also take care of creating the thumbnail.

        """

    @abstractmethod
    def _process_image_coordinates(self, imgset, place):
        """Fill the ImageSet object with sky coordinate information.

        Parameters
        ----------
        imgset : :class:`wwt_data_formats.imageset.ImageSet`
           An object representing metadata about the resulting WWT-compatible
           imagery. Fields inside this object should be filled in as
           appropriate to correspond to sky positioning of this image.
        place : :class:`wwt_data_formats.place.Place`
           A "Place" object that will contain the imgset.

        Returns
        -------
        None.

        """

    @abstractmethod
    def _process_image_metadata(self, imgset, place):
        """Fill the ImageSet object with metadata.

        Parameters
        ----------
        imgset : :class:`wwt_data_formats.imageset.ImageSet`
           An object representing metadata about the resulting WWT-compatible
           imagery. Fields inside this object should be filled in as
           appropriate to correspond to the image metadata.
        place : :class:`wwt_data_formats.place.Place`
           A "Place" object that will contain the imgset.

        Returns
        -------
        None.

        """

    def process_image(self, baseoutdir):
        """Convert the image into WWT-compatible data and metadata.

        Parameters
        ----------
        baseoutdir : str
           A path pointing to a local directory inside of which the
           WWT-compatible data files will be written. The data for
           this particular image will be written inside a subdirectory
           corresponding to this image's unique ID.

        Returns
        -------
        A :class:`wwt_data_formats.place.Place` object containing a single
        "foreground image set" with data about the processed image. URLs for
        any locally-generated data will be relative to the image-specific
        subdirectory.

        """
        place = Place()
        imgset = ImageSet()
        place.foreground_image_set = imgset

        outdir = os.path.join(baseoutdir, self._unique_id)
        os.makedirs(outdir, exist_ok=True)

        self._process_image_data(imgset, outdir)
        self._process_image_coordinates(imgset, place)
        self._process_image_metadata(imgset, place)

        place.name = imgset.name
        place.data_set_type = imgset.data_set_type
        place.thumbnail = imgset.thumbnail_url

        return place


class BitmapInputImage(InputImage):
    """An abstract base class for an input image whose data are stored as an RGB
    bitmap that we will read into memory all at once using the ``PIL``
    module.

    This ABC implements the :meth:`_process_image_data` method on the parent
    :class:`InputImage` ABC but adds a new abstract method :meth:`_load_bitmap`

    """
    _bitmap = None

    @abstractmethod
    def _load_bitmap(self):
        """Load the image data as a :class:`PIL.Image`.

        Returns
        -------
        A :class:`PIL.Image` of the image data.

        Notes
        -----
        This function will only be called once. It can assume that
        :meth:`InputImage.ensure_input_cached` has already been called.

        """

    def _ensure_bitmap(self):
        """Ensure that ``self._bitmap`` is loaded."""
        if self._bitmap is None:
            self._bitmap = self._load_bitmap()
        return self._bitmap

    def _process_image_data(self, imgset, outdir):
        from ..image import Image, ImageMode
        self._ensure_bitmap()

        needs_tiling = self._bitmap.width > 2048 or self._bitmap.height > 2048

        if not needs_tiling:
            dest_path = os.path.join(outdir, 'image.jpg')
            self._bitmap.save(dest_path, format='JPEG')
            imgset.url = 'image.jpg'
            imgset.file_type = '.jpg'
        else:
            from ..study import tile_study_image
            from ..pyramid import PyramidIO
            from ..merge import averaging_merger, cascade_images

            # Create the base layer
            pio = PyramidIO(outdir, scheme='LXY')
            image = Image.from_pil(self._bitmap)
            tiling = tile_study_image(image, pio)
            tiling.apply_to_imageset(imgset)

            # Cascade to create the coarser tiles
            cascade_images(pio, imgset.tile_levels, averaging_merger)

            imgset.url = pio.get_path_scheme() + '.png'
            imgset.file_type = '.png'

        # Deal with the thumbnail
        thumb = Image.from_pil(self._bitmap).make_thumbnail_bitmap()
        thumb.save(os.path.join(outdir, 'thumb.jpg'), format='JPEG')
        imgset.thumbnail_url = 'thumb.jpg'


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

    def fetch_inputs(self):
        src = self.get_image_source()
        n_cand = 0
        n_cached = 0

        for cand in src.query_candidates():
            n_cand += 1
            uniq_id = cand.get_unique_id()
            if self._pipeio.check_exists(uniq_id, 'index.wtml'):
                continue  # skip already-done inputs
            if self._pipeio.check_exists(uniq_id, 'skip.flag'):
                continue  # skip inputs that are explicitly flagged

            cachedir = self._ensure_dir('cache_todo', uniq_id)

            # XXX printing is lame
            try:
                print(f'caching candidate input {uniq_id} ...')
                cand.cache_data(cachedir)
                n_cached += 1
            except NotActionableError as e:
                print(f'skipping {uniq_id}: not ingestible into WWT: {e}')
                shutil.rmtree(cachedir)

        print(f'queued {n_cached} images for processing, out of {n_cand} candidates')

    def process_todos(self):
        src = self.get_image_source()
        self._ensure_dir('cache_done')
        baseoutdir = self._ensure_dir('out_todo')

        pub_url_prefix = self._config.get('publish_url_prefix')
        if pub_url_prefix:
            if pub_url_prefix[-1] != '/':
                pub_url_prefix += '/'

        for uniq_id in os.listdir(self._path('cache_todo')):
            cachedir = self._path('cache_todo', uniq_id)
            inp_img = src.open_input(uniq_id, cachedir)
            print(f'processing {uniq_id} ...')
            place = inp_img.process_image(baseoutdir)

            folder = Folder()
            folder.name = uniq_id
            folder.children = [place]

            # We potentially generate two WTML files. `index_rel.wtml` may
            # contain URLs that are relative to the `index_rel.wtml` file for
            # local data. `index.wtml` contains only absolute URLs, which
            # requires us to use some configuration data. The `place` that we
            # get out of the processing stage has relative URLs.

            with open(self._path('out_todo', uniq_id, 'index_rel.wtml'), 'wt', encoding='utf8') as f:
                write_xml_doc(folder.to_xml(), dest_stream=f)

            if pub_url_prefix:
                pfx = pub_url_prefix + uniq_id + '/'
                place.foreground_image_set.url = maybe_prefix_url(place.foreground_image_set.url, pfx)
                place.foreground_image_set.credits_url = maybe_prefix_url(place.foreground_image_set.credits_url, pfx)
                place.foreground_image_set.thumbnail_url = maybe_prefix_url(place.foreground_image_set.thumbnail_url, pfx)
                place.thumbnail = maybe_prefix_url(place.thumbnail, pfx)

                with open(self._path('out_todo', uniq_id, 'index.wtml'), 'wt', encoding='utf8') as f:
                    write_xml_doc(folder.to_xml(), dest_stream=f)

            # All done here.

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
