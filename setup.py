# -*- mode: python; coding: utf-8 -*-
# Copyright 2013-2019 Chris Beaumont and the AAS WorldWide Telescope team
# Licensed under the MIT License

from __future__ import absolute_import, division, print_function

from setuptools import setup, Extension
import numpy as np

setup_args = dict(
    name = 'toasty',
    version = '0.0.2',  # also update docs/conf.py
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
        'Topic :: Scientific/Engineering :: Astronomy',
        'Topic :: Scientific/Engineering :: Visualization',
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
            'numpydoc',
            'sphinx',
            'sphinx-automodapi',
            'sphinx_rtd_theme',
        ],
    },

    include_dirs = [
        np.get_include(),
    ],
    ext_modules = [
        Extension('toasty._libtoasty', ['toasty/_libtoasty.pyx']),
    ],
)

# When we build on ReadTheDocs, there seems to be no way to ensure that Cython
# is installed before this file is evaluated (yes, I tried all sorts of
# requirements.txt tricks and things). So we allow the Cython import to fail
# in that environment since we can make things work out for the docs build in
# the end.

try:
    from Cython.Distutils import build_ext
except ImportError:
    import os
    if 'READTHEDOCS' not in os.environ:
        raise
else:
    setup_args['cmdclass'] = {
        'build_ext': build_ext,
    }

if __name__ == '__main__':
    setup(**setup_args)
