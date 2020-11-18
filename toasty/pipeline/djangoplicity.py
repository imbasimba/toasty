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
import json
import requests
import yaml

from ..image import ImageLoader
from . import CandidateInput, ImageSource, NotActionableError


class DjangoplicityImageSource(ImageSource):
    """
    An ImageSource that obtains its inputs from a query to a Djangoplicity website.
    """

    _base_url = None

    @classmethod
    def get_config_key(cls):
        return 'djangoplicity'


    @classmethod
    def deserialize(cls, data):
        inst = cls()
        inst._base_url = data['base_url']
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
        pass


    def process(self, unique_id, cand_data_stream, cachedir, builder):
        pass


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
