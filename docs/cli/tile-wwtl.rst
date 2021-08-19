.. _cli-tile-wwtl:

==================================
``toasty tile-wwtl``
==================================

The ``tile-wwtl`` command is like :ref:`cli-tile-study`, but loads
up ``.wwtl`` WWT “layers” files, from which it can load preexisting astrometric
information and convert it to the format needed for its tiled output. The
purpose of this specialized command is to enable an easy workflow where you can
interactively position a large image file on the sky in the AAS WorldWide
Telescope Windows application, then tile it for web viewing while preserving the
astrometric alignment.

Usage
=====

.. code-block:: shell

   toasty tile-wwtl
      [standard image-loading options]
      [--placeholder-thumbnail]
      [--outdir DIR]
      [--name NAME]
      WWTL-PATH

See the :ref:`cli-std-image-options` section for documentation on those options.
Note that options that deal with image processing will process the image
contained in the input WWTL file. Other options might not make sense for this
command.

The ``WWTL-PATH`` argument gives the filename of the input WWTL file. This file
should contain one layer, which should be an image-set layer. The WWTL file will
include the contents of the associated image as well. The source image should be
in a tangential (gnomonic) projection on the sky.

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
