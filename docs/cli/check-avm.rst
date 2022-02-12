.. _cli-check-avm:

====================
``toasty check-avm``
====================

The ``check-avm`` command checks whether an image file contains AVM (`Astronomy
Visualization Metadata`_) tags in its metadata. AVM metadata often include
spatial positioning data that specify how an astronomical image maps onto the
sky, similar to `WCS`_ headers in FITS files.

.. _Astronomy Visualization Metadata: https://virtualastronomy.org/avm_metadata.php

Usage
=====

.. code-block:: shell

   toasty check-avm
      [--print] [-p]
      [--exitcode]
      IMAGE-PATH

The ``IMAGE-PATH`` argument gives the filesystem path of an image to check. This
should typically be an RGB bitmap image such as a JPEG, PNG, or TIFF file. The
tool will try to load AVM data from the file and report whether it is
successful.

.. _WCS: https://fits.gsfc.nasa.gov/fits_wcs.html

By default, the presence of AVM data is reported along with some information
about the agreement between the AVM and the image shape. If the ``--print`` or
``-p`` option is given, the actual AVM data will be dumped out.

If the ``--exitcode`` option is given, the exit code of the command line tool
will reflect whether spatial AVM data were found. Zero (success) means that
spatial data were found, while nonzero (failure) indicates that no data were
present, the data were corrupt, or that some other failure occurred. Without
this option, the exit code will be zero if the image can be opened but contains
no AVM data.


Notes
=====

This functionality requires that the `pyavm`_ Python package has been installed.

.. _pyavm: https://astrofrog.github.io/pyavm/


See Also
========

- :ref:`cli-tile-study`
