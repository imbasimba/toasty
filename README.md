# toasty

[![PyPI version](https://badge.fury.io/py/toasty.svg)](https://badge.fury.io/py/toasty)
[![Build Status](https://dev.azure.com/aasworldwidetelescope/WWT/_apis/build/status/WorldWideTelescope.toasty?branchName=master)](https://dev.azure.com/aasworldwidetelescope/WWT/_build/latest?definitionId=23&branchName=master)
[![codecov](https://codecov.io/gh/WorldWideTelescope/toasty/branch/master/graph/badge.svg?token=63Lgd07mGn)](https://codecov.io/gh/WorldWideTelescope/toasty)
[![Documentation Status](https://readthedocs.org/projects/toasty/badge/?version=latest)](https://toasty.readthedocs.io/en/latest/?badge=latest)

<!--pypi-begin-->
[toasty] is a Python library that helps you create “tile pyramids” from
astronomical image data as used in the [TOAST] format. These multi-resolution
maps can be viewed in software such as the [AAS] [WorldWide Telescope].

[toasty]: https://toasty.readthedocs.io/
[TOAST]: https://doi.org/10.3847/1538-4365/aaf79e
[AAS]: https://aas.org/
[WorldWide Telescope]: http://www.worldwidetelescope.org/

[toasty] was originally written by [Chris Beaumont] and is currently maintained
as part of the AAS [WorldWide Telescope] project.

[Chris Beaumont]: https://chrisbeaumont.org/
<!--pypi-end-->


## Installation

The easiest way to install [toasty] is through [pip]:

```
pip install toasty
```

[pip]: https://pip.pypa.io/

For more information, please see the full [toasty installation instructions].

[toasty installation instructions]: https://toasty.readthedocs.io/en/latest/installation.html


## Documentation, Examples, etc.

For documentation and examples, go to:

https://toasty.readthedocs.io/


## Contributions

Contributions to [toasty] are welcome! See
[the WorldWide Telescope contributors’ guide] for applicable information. We
use a standard workflow with issues and pull requests. All participants in
[toasty] and the WWT communities must abide by the [WWT Code of Conduct].

[the WorldWide Telescope contributors’ guide]: https://worldwidetelescope.github.io/contributing/
[WWT Code of Conduct]: https://worldwidetelescope.github.io/code-of-conduct/


## Release History

Releases of [toasty] are logged in the file
[CHANGELOG.md](https://github.com/WorldWideTelescope/toasty/blob/release/CHANGELOG.md)
on the `release` branch of this repository, as well as release listings
maintained by [GitHub](https://github.com/WorldWideTelescope/toasty/releases)
and [PyPI](https://pypi.org/project/toasty/#history).


## Dependencies

[toasty] is a Python package so, yes, Python is required.

- [astropy] if using FITS files or WCS coordinates
- [azure-storage-blob] >= 12.0 if using the Azure storage backend for pipeline processing
- [cython]
- [filelock]
- [healpy] if using [HEALPix] maps
- [numpy]
- [pillow]
- [pytest] to run the test suite
- [PyYAML]
- [tqdm]
- [wwt_data_formats] >= 0.7

[astropy]: https://www.astropy.org/
[azure-storage-blob]: https://github.com/Azure/azure-sdk-for-python/tree/master/sdk/storage/azure-storage-blob
[cython]: https://cython.org/
[filelock]: https://github.com/benediktschmitt/py-filelock
[healpy]: https://healpy.readthedocs.io/
[HEALPix]: https://healpix.jpl.nasa.gov/
[numpy]: https://numpy.org/
[pillow]: https://pillow.readthedocs.io/
[pytest]: https://docs.pytest.org/
[PyYAML]: https://github.com/yaml/pyyaml
[tqdm]: https://tqdm.github.io/
[wwt_data_formats]: https://github.com/WorldWideTelescope/wwt_data_formats


## Legalities

[toasty] is copyright Chris Beaumont, Clara Brasseur, and the AAS WorldWide
Telescope Team. It is licensed under the [MIT License](./LICENSE).


## Acknowledgments

[toasty] is part of the AAS WorldWide Telescope system, a [.NET Foundation]
project managed by the non-profit [American Astronomical Society] (AAS). Work
on WWT has been supported by the AAS, the US [National Science Foundation]
(grants [1550701] and [1642446]), the [Gordon and Betty Moore Foundation], and
[Microsoft].

[.NET Foundation]: https://dotnetfoundation.org/
[American Astronomical Society]: https://aas.org/
[National Science Foundation]: https://www.nsf.gov/
[1550701]: https://www.nsf.gov/awardsearch/showAward?AWD_ID=1550701
[1642446]: https://www.nsf.gov/awardsearch/showAward?AWD_ID=1642446
[Gordon and Betty Moore Foundation]: https://www.moore.org/
[Microsoft]: https://www.microsoft.com/
