# -*- mode: python; coding: utf-8 -*-
# Copyright 2020 the AAS WorldWide Telescope project
# Licensed under the MIT License.

"""
Support for loading images from a Djangoplicity database.
"""

__all__ = '''
DjangoplicityImageSource
DjangoplicityCandidateInput
'''.split()

import codecs
from datetime import datetime, timezone
import html
import json
import numpy as np
import os.path
import requests
import shutil
from urllib.parse import urljoin, quote as urlquote
import yaml

from ..image import ImageLoader
from . import CandidateInput, ImageSource, NotActionableError


class DjangoplicityImageSource(ImageSource):
    """
    An ImageSource that obtains its inputs from a query to a Djangoplicity website.
    """

    _base_url = None
    _channel_name = None

    @classmethod
    def get_config_key(cls):
        return 'djangoplicity'


    @classmethod
    def deserialize(cls, data):
        inst = cls()
        inst._base_url = data['base_url']
        inst._channel_name = data['channel_name']
        return inst


    def query_candidates(self):
        page_num = 1

        while True:
            url = self._base_url + f'archive/search/page/{page_num}/?type=Observation'

            # XXX SSL verification fails for noirlab.edu for some reason XXX
            with requests.get(url, stream=True, verify=False) as resp:
                if resp.status_code == 404:
                    break  # all done
                if not resp.ok:
                    raise Exception(f'error fetching url {url}: {resp.status_code}')

                text_stream = codecs.getreader('utf8')(resp.raw)
                json_lines = []

                for line in text_stream:
                    if not len(json_lines):
                        if 'var images = [' in line:
                            json_lines.append('[')
                    elif '];' in line:
                        json_lines.append(']')
                        break
                    else:
                        json_lines.append(line)

            # This is really a JS literal, but YAML is compatible enough.
            # JSON does *not* work because the dict keys here aren't quoted.
            data = yaml.safe_load(''.join(json_lines))

            for item in data:
                yield DjangoplicityCandidateInput(item)

            page_num += 1


    def fetch_candidate(self, unique_id, cand_data_stream, cachedir):
        url = self._base_url + urlquote(unique_id) + '/api/json/'

        # XXX SSL verification fails for noirlab.edu for some reason XXX
        with requests.get(url, verify=False) as resp:
            if not resp.ok:
                raise Exception(f'error fetching url {url}: {resp.status_code}')
            info = json.loads(resp.content)

        # Find the "fullsize original" image URL

        fullsize_url = None

        for resource in info['Resources']:
            if resource.get('ResourceType') == 'Original':
                fullsize_url = resource['URL']
                break

        if fullsize_url is None:
            raise Exception(f'error processing {unique_id}: can\'t identify \"fullsize original\" image URL')

        ext = fullsize_url.rsplit('.', 1)[-1].lower()
        info['toasty_image_extension'] = ext

        # Validate that there's actually WCS we can use

        if not isinstance(info.get('Spatial.CoordsystemProjection', None), str):
            raise NotActionableError('image does not have full WCS')

        # Download it

        # XXX SSL verification fails for noirlab.edu for some reason XXX
        with requests.get(fullsize_url, stream=True, verify=False) as resp:
            if not resp.ok:
                raise Exception(f'error downloading {fullsize_url}: {resp.status_code}')

            with open(os.path.join(cachedir, 'image.' + ext), 'wb') as f:
                shutil.copyfileobj(resp.raw, f)

        with open(os.path.join(cachedir, 'metadata.json'), 'wt') as f:
            json.dump(info, f, ensure_ascii=False, indent=2)


    def process(self, unique_id, cand_data_stream, cachedir, builder):
        # Set up the metadata.

        with open(os.path.join(cachedir, 'metadata.json'), 'rt') as f:
            info = json.load(f)

        img_path = os.path.join(cachedir, 'image.' + info['toasty_image_extension'])
        md = DjangoplicityMetadata(info)

        # Load up the image.

        img = ImageLoader().load_path(img_path)

        # Do the processing.

        builder.tile_base_as_study(img)
        builder.make_thumbnail_from_other(img)

        builder.imgset.set_position_from_wcs(
            md.as_wcs_headers(img.width, img.height),
            img.width,
            img.height,
            place = builder.place,
        )

        builder.set_name(info['Title'])
        builder.imgset.credits_url = info['ReferenceURL']
        builder.imgset.credits = html.escape(info['Credit'])
        builder.place.description = html.escape(info['Description'])

        # Annotation metadata

        pub_dt = datetime.fromisoformat(info['Date'])
        if pub_dt.tzinfo is None:
            pub_dt = pub_dt.replace(tzinfo=timezone.utc)

        amd = {
            'channel': self._channel_name,
            'itemid': unique_id,
            'publishedUTCISO8601': pub_dt.isoformat(),
        }
        builder.place.annotation = json.dumps(amd)

        # Finally, crunch the rest of the pyramid.

        builder.cascade()


class DjangoplicityCandidateInput(CandidateInput):
    """
    A CandidateInput obtained from an AstroPix query.
    """

    def __init__(self, info):
        self._info = info

    def get_unique_id(self):
        return self._info['id']

    def save(self, stream):
        with codecs.getwriter('utf8')(stream) as text_stream:
            json.dump(self._info, text_stream, ensure_ascii=False, indent=2)


class DjangoplicityMetadata(object):
    metadata = None

    def __init__(self, metadata):
        self.metadata = metadata

    def as_wcs_headers(self, width, height):
        headers = {}

        #headers['RADECSYS'] = self.wcs_coordinate_frame  # causes Astropy warnings
        headers['CTYPE1'] = 'RA---' + self.metadata['Spatial.CoordsystemProjection']
        headers['CTYPE2'] = 'DEC--' + self.metadata['Spatial.CoordsystemProjection']
        headers['CRVAL1'] = float(self.metadata['Spatial.ReferenceValue'][0])
        headers['CRVAL2'] = float(self.metadata['Spatial.ReferenceValue'][1])

        # See Calabretta & Greisen (2002; DOI:10.1051/0004-6361:20021327), eqn 186
        crot = np.cos(float(self.metadata['Spatial.Rotation']) * np.pi / 180)
        srot = np.sin(float(self.metadata['Spatial.Rotation']) * np.pi / 180)
        scale0 = float(self.metadata['Spatial.Scale'][0])
        scale1 = float(self.metadata['Spatial.Scale'][1])
        lam = scale1 / scale0

        headers['PC1_1'] = crot
        headers['PC1_2'] = -lam * srot
        headers['PC2_1'] = srot / lam
        headers['PC2_2'] = crot

        # If we couldn't get the original image, the pixel density used for
        # the WCS parameters may not match the image resolution that we have
        # available. In such cases, we need to remap the pixel-related
        # headers. From the available examples, `wcs_reference_pixel` seems to
        # be 1-based in the same way that `CRPIXn` are. Since in FITS, integer
        # pixel values correspond to the center of each pixel box, a CRPIXn of
        # [0.5, 0.5] (the lower-left corner) should not vary with the image
        # resolution. A CRPIXn of [W + 0.5, H + 0.5] (the upper-right corner)
        # should map to [W' + 0.5, H' + 0.5] (where the primed quantities are
        # the new width and height).

        factor0 = width / float(self.metadata['Spatial.ReferenceDimension'][0])
        factor1 = height / float(self.metadata['Spatial.ReferenceDimension'][1])

        headers['CRPIX1'] = (float(self.metadata['Spatial.ReferencePixel'][0]) - 0.5) * factor0 + 0.5
        headers['CRPIX2'] = (float(self.metadata['Spatial.ReferencePixel'][1]) - 0.5) * factor1 + 0.5
        headers['CDELT1'] = scale0 / factor0
        headers['CDELT2'] = scale1 / factor1

        return headers
