==============================================
toasty: Creating TOAST tile pyramids in Python
==============================================

toasty_ is a Python library that helps you create “tile pyramids” from
astronomical image data, as used in the TOAST_ format. These multi-resolution
maps can be viewed in software such as the AAS_ `WorldWide Telescope`_.

.. _toasty: https://toasty.readthedocs.io/
.. _TOAST: https://arxiv.org/abs/1812.03926
.. _AAS: https://aas.org/
.. _WorldWide Telescope: http://www.worldwidetelescope.org/home

.. toctree::
   :maxdepth: 2

   manual
   cli


Python API Reference
====================

.. toctree::
   :maxdepth: 1

   api/toasty
   api/toasty.builder
   api/toasty.cli
   api/toasty.collection
   api/toasty.fits_tiler
   api/toasty.image
   api/toasty.merge
   api/toasty.multi_tan
   api/toasty.openexr
   api/toasty.par_util
   api/toasty.pipeline
   api/toasty.pipeline.astropix
   api/toasty.pipeline.azure_io
   api/toasty.pipeline.cli
   api/toasty.pipeline.djangoplicity
   api/toasty.pipeline.local_io
   api/toasty.progress
   api/toasty.pyramid
   api/toasty.samplers
   api/toasty.study
   api/toasty.toast


Getting help
============

If you run into any issues when using toasty_, please open an issue `on its
GitHub repository <https://github.com/WorldWideTelescope/toasty/issues>`_.


Acknowledgments
===============

The first version of toasty_ was written by Chris Beaumont.

toasty_ is part of the `AAS`_ `WorldWide Telescope`_ system, a `.NET
Foundation`_ project managed by the non-profit `American Astronomical
Society`_ (AAS). Work on WWT has been supported by the AAS, the US `National
Science Foundation`_ (grants 1550701_ and 1642446_), the `Gordon and Betty
Moore Foundation`_, and `Microsoft`_.

.. _.NET Foundation: https://dotnetfoundation.org/
.. _American Astronomical Society: https://aas.org/
.. _National Science Foundation: https://www.nsf.gov/
.. _1550701: https://www.nsf.gov/awardsearch/showAward?AWD_ID=1550701
.. _1642446: https://www.nsf.gov/awardsearch/showAward?AWD_ID=1642446
.. _Gordon and Betty Moore Foundation: https://www.moore.org/
.. _Microsoft: https://www.microsoft.com/
