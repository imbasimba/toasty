# -*- mode: python; coding: utf-8 -*-
# Copyright 2013-2019 Chris Beaumont and the AAS WorldWide Telescope team
# Licensed under the MIT License

from __future__ import absolute_import, division, print_function

import os
from setuptools import setup, Extension

def get_long_desc():
    in_preamble = True
    lines = []

    with open('README.md') as f:
        for line in f:
            if in_preamble:
                if line.startswith('<!--pypi-begin-->'):
                    in_preamble = False
            else:
                if line.startswith('<!--pypi-end-->'):
                    break
                else:
                    lines.append(line)

    lines.append('''

For more information, including installation instructions, please visit [the
project homepage].

[the project homepage]: https://toasty.readthedocs.io/
''')
    return ''.join(lines)


setup_args = dict(
    name = 'toasty',
    version = '0.1.0',  # also update docs/conf.py
    description = 'Generate TOAST image tile pyramids from existing image data',
    long_description = get_long_desc(),
    long_description_content_type = 'text/markdown',
    url = 'https://toasty.readthedocs.io/',
    license = 'MIT',
    platforms = 'Linux, Mac OS X',

    author = 'Chris Beaumont, AAS WorldWide Telescope Team',
    author_email = 'wwt@aas.org',

    classifiers = [
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Topic :: Scientific/Engineering :: Astronomy',
        'Topic :: Scientific/Engineering :: Visualization',
    ],

    packages = [
        'toasty',
        'toasty.tests',
    ],
    include_package_data = True,

    entry_points = {
        'console_scripts': [
            'toasty=toasty.cli:entrypoint',
        ],
    },

    install_requires = [
        'cython>=0.20',
        'numpy>=1.7',
        'pillow>=7.0',
        'wwt_data_formats>=0.2.0',
    ],

    extras_require = {
        'test': [
            'coveralls',
            'pytest-cov',
        ],
        'docs': [
            'astropy-sphinx-theme',
            'numpydoc',
            'sphinx',
            'sphinx-automodapi',
        ],
    },

    ext_modules = [
        Extension('toasty._libtoasty', ['toasty/_libtoasty.pyx']),
    ],
)


# When we build on ReadTheDocs, there seems to be no way to ensure that Cython
# and Numpy are installed before this file is evaluated (yes, I tried all
# sorts of requirements.txt tricks and things). So, we allow these imports to
# fail in that environment, since we can make things work out for the docs
# build in the end.

ON_READTHEDOCS = 'READTHEDOCS' in os.environ

try:
    import numpy as np
except ImportError:
    if not ON_READTHEDOCS:
        raise
else:
    setup_args['include_dirs'] = [
        np.get_include(),
    ]

try:
    from Cython.Distutils import build_ext
except ImportError:
    if not ON_READTHEDOCS:
        raise
else:
    setup_args['cmdclass'] = {
        'build_ext': build_ext,
    }

# That was fun.

if __name__ == '__main__':
    setup(**setup_args)
