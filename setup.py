# -*- mode: python; coding: utf-8 -*-
# Copyright 2013-2019 Chris Beaumont
# Licensed under the MIT License

from __future__ import absolute_import, division, print_function

from setuptools import setup, Extension
from Cython.Distutils import build_ext
import numpy as np

setup_args = dict(
    name = 'toasty',
    version = '0.0.1',
    description = 'Generate TOAST image tile pyramids from FITS files',
    url = 'https://github.com/WorldWideTelescope/toasty/',
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
        'Topic :: Scientific/Engineering :: Data Visualization'
    ],

    packages = [
        'toasty',
        'toasty.tests',
    ],
    include_package_data = True,

    install_requires = [
        'cython',
        'numpy',
        'pillow',
    ],

    extras_require = {
        'test': [
            'coveralls',
            'pytest-cov',
        ],
        'docs': [
            'sphinx',
            'sphinx_rtd_theme',
        ],
    },

    cmdclass = {
        'build_ext': build_ext,
    },
    include_dirs = [
        np.get_include(),
    ],
    ext_modules = [
        Extension('toasty._libtoasty', ['toasty/_libtoasty.pyx']),
    ],
)


if __name__ == '__main__':
    setup(**setup_args)
