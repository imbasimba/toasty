===================================
``toasty study-sample-image-tiles``
===================================

The ``study-sample-image-tiles`` command takes a single large :ref:`study
<studies>` image and samples it into a high-resolution layer of tiles.

Usage
=====

.. code-block:: shell

   toasty study-sample-image-tiles
      [standard image-loading options]
      [--outdir DIR]
      IMAGE-PATH

See the :ref:`cli-std-image-options` section for documentation on those options.

The ``IMAGE-PATH`` argument gives the filename of the input image. For this
usage, the input image is typically a very large astrophotography or data image
that needs to be tiled to be displayed usefully in AAS WorldWide Telescope.

The ``--outdir DIR`` option specifies where the output data should be written.
If unspecified, the data root will be the current directory.
