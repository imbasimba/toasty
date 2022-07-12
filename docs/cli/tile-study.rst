.. _cli-tile-study:

=====================
``toasty tile-study``
=====================

The ``tile-study`` command takes a single large :ref:`study <studies>` image and
breaks it into a high-resolution layer of tiles.

Usage
=====

.. code-block:: shell

   toasty tile-study
      [standard image-loading options]
      [--placeholder-thumbnail]
      [--outdir DIR]
      [--name NAME]
      [--avm]
      [--avm-from PATH]
      [--fits-wcs PATH]
      IMAGE-PATH

See the :ref:`cli-std-image-options` section for documentation on those options.

The ``IMAGE-PATH`` argument gives the filename of the input image. For this
usage, the input image is typically a very large astrophotography or data image
that needs to be tiled to be displayed usefully in AAS WorldWide Telescope.

The ``--outdir DIR`` option specifies where the output data should be written.
If unspecified, the data root will be the current directory.

The ``--name NAME`` option specifies the descriptive name for the imagery to be
embedded inside the output WTML file. It defaults to "Toasty".

If the ``--placeholder-thumbnail`` argument is given, an all-black placeholder
thumbnail will be created. Otherwise, the thumbnail will be created by
downsampling the input image. This operation can actually be the most
memory-intensive part of the process, and can yield poor results with
mostly-empty images. You can avoid this by using this argument and then invoking
:ref:`cli-make-thumbnail` with a better-suited input image.

If the ``--avm`` argument is given, Toasty will attempt to load world-coordinate
information from AVM (`Astronomy Visualization Metadata`_) tags in the input
image’s metadata. This isn’t checked automatically because this functionality
requires the `pyavm`_ package to be installed on your system.

.. _Astronomy Visualization Metadata: https://virtualastronomy.org/avm_metadata.php

.. _pyavm: https://astrofrog.github.io/pyavm/

The ``--avm-from PATH`` argument is like ``--avm``, but loads the AVM
information from a *different* image file. This can be useful if you have
multiple files with different versions of the same image, and the one that you
want to tile has broken or missing AVM. It is up to you to ensure that
information contained in the AVM file corresponds to the main input image.

If the ``--fits-wcs`` argument is given, Toasty will attempt to load
world-coordinate information from the headers of the named `FITS`_ file. It is
up to you to ensure that information contained in that file corresponds to the
main input image. This argument can be useful with the output from
`Astrometry.Net`_, which generates WCS FITS files for the images it solves.

.. _FITS: https://en.wikipedia.org/wiki/FITS
.. _Astrometry.Net: https://astrometry.net/

Notes
=====

For correct results the source image must be in a tangential (gnomonic)
projection on the sky. For images that are small in an angular sense, you might
be able to get away with fudging the projection type.

If the input image does not contain any useful astrometric information, the
emited ``index_rel.wtml`` file will contain generic information that makes the
image 1° wide and places it at RA = Dec = 0.


See Also
========

- :ref:`cli-check-avm`
- :ref:`cli-view`
