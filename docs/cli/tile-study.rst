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
      [--outdir DIR]
      IMAGE-PATH

See the :ref:`cli-std-image-options` section for documentation on those options.

The ``IMAGE-PATH`` argument gives the filename of the input image. For this
usage, the input image is typically a very large astrophotography or data image
that needs to be tiled to be displayed usefully in AAS WorldWide Telescope.

The ``--outdir DIR`` option specifies where the output data should be written.
If unspecified, the data root will be the current directory.

Notes
=====

For correct results the source image must be in a tangential (gnomonic)
projection on the sky. For images that are small in an angular sense, you might
be able to get away with fudging the projection type.

If the input image does not contain any useful astrometric information, the
emited ``index_rel.wtml`` file will contain generic information that makes the
image 1° wide and places it at RA = Dec = 0.
