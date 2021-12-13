.. _cli-view:

=======================
``toasty view``
=======================

The ``view`` command allows you view one or more FITS files using the `WWT
research app`_.

.. _WWT research app: https://docs.worldwidetelescope.org/research-app/latest/


Example
=======

View a FITS file:

.. code-block:: shell

   toasty view myfile.fits


Detailed Usage
==============

.. code-block:: shell

   toasty view
      [--appurl URL]
      [--blankval NUMBER]
      [--browser BROWSER, -b BROWSER]
      [--hdu-index INDEX[,INDEX,...]]
      [--parallelism COUNT, -j COUNT]
      {FITS [FITS ...]}

The ``FITS`` argument(s) give the path(s) of one or more input FITS files. These
will be automatically tiled if necessary, then made available on a local web
server so that the WWT viewer can access the data.

The ``-b`` or ``--browser`` option specifies which web browser to use, using an
identifier as understood by the `Python "webbrowser" module`_. Typical choices
might be ``firefox``, ``safari``, or ``google-chrome``. If unspecified, a
sensible default will be used.

.. _Python "webbrowser" module: https://docs.python.org/3/library/webbrowser.html

The ``--hdu-index`` argument, if specified, fixes the index number of the FITS
HDU to load from the input file(s). If one value is provided, that index will be
used for every FITS file. If a comma-separated list is provided, the index
corresponding to each index path will be used.

The ``--blankval`` argument, if specified, gives a data value to be treated as
undefined data when processing the FITS data.

The ``--parallelism COUNT`` (or ``-j COUNT``) argument specifies the level of
parallism to use in the tiling and downsampling process. On operating systems
that support parallel processing, the default is to use all CPUs. To disable
parallel processing, explicitly specify a factor of 1.

The ``--appurl`` option can be used to override the base URL for the preview app
that will be used. This can be helpful when developing new features in one of
these apps.


Details
=======

This command provides similar functionality as the ``wwtdatatool preview``
command `provided by the wwt_data_formats package`_, but automatically tiles its
inputs and generates the needed ``index_rel.wtml`` file.

.. _provided by the wwt_data_formats package: https://wwt-data-formats.readthedocs.io/en/latest/cli/preview.html

If tiling is required and the tile output directory already exists, the tool
assumes that the image was already successfully tiled, and skips straight to
launching the viewer without rerunning the tiling process.

The FITS data will be tiled either onto a common tangential projection, or into
a HiPS format using `hipsgen`_, depending on the angular size subtended by the
data. If any of the FITS image corners are separated by more than 20 degrees and
Java is available, `hipsgen`_ will be used. Otherwise, Toasty's internal
processing will be used, reprojecting the input data into a tangential
(gnomonic) projection if necessary.

.. _hipsgen: https://aladin.u-strasbg.fr/hips/HipsIn10Steps.gml


See Also
========

- :ref:`cli-tile-study`
