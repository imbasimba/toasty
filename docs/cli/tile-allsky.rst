.. _cli-tile-allsky:

======================
``toasty tile-allsky``
======================

The ``tile-allsky`` command takes a single image representing a full sphere and
samples it into a TOAST tiling.

Usage
=====

.. code-block:: shell

   toasty tile-allsky
      [standard image-loading options]
      [--placeholder-thumbnail]
      [--outdir DIR]
      [--name NAME]
      [--projection TYPE]
      [--parallelism FACTOR]
      {IMAGE-PATH}
      {TOAST-DEPTH}

See the :ref:`cli-std-image-options` section for documentation on those options.

The ``IMAGE-PATH`` argument gives the filename of the input image. Its
projection onto the sphere should be specified with the ``--projection`` option.

The ``TOAST-DEPTH`` argument specifies the resolution level of the TOAST
pixelization that will be generated. A depth of 0 means that the image will be
sampled onto a single 256×256 tile, each pixel in the tile having an angular
size of about 0.6 deg². A depth of 1 means that the image will be sampled onto
four tiles, for a total resolution of 512×512 and an average pixel area of
0.16 deg². A depth of 8 means that there will be 65,536 tiles and 4.3 billion
pixels, with an average pixel area of about (11 arcsec)². The appropriate choice
of the depth depends on your application.

The ``--outdir DIR`` option specifies where the output data should be written.
If unspecified, the data root will be the current directory.

The ``--name NAME`` option specifies the descriptive name for the imagery to be
embedded inside the output WTML file. It defaults to "Toasty".

The ``--projection TYPE`` option specifies how the surface of the sphere is
mapped on to the image. Allowed types are:

- ``plate-carree`` (the default) — the image uses a “plate carrée”, AKA
  `equirectangular`_ or geographic, projection. The image will typically be
  about twice as wide as it is tall. Interpreted as a sky image, the north
  celestial pole is at the top of the image, RA = Dec = 0 is at the image
  center, and RA increases to the left.

- ``plate-carree-galactic`` — like the above, but the image is in Galactic
  coordinates rather than (celestial) equatorial. This is often the case for
  all-sky astronomical press release images.

- ``plate-carree-ecliptic`` — like the above, but the image is in barycentric
  true ecliptic coordinates rather than (celestial) equatorial.

- ``plate-carree-planet`` — like the above, but the image is that of a planet
  and so the sense of the longitude/RA axis is inverted. Longitude increases to
  the right. This is the format in which planetary maps are typically
  represented. If you use this option when you should have used
  ``plate-carree``, or vice versa, your map come out flipped horizontally.

.. _equirectangular: https://en.wikipedia.org/wiki/Equirectangular_projection

If the ``--placeholder-thumbnail`` argument is given, an all-black placeholder
thumbnail will be created. Otherwise, the thumbnail will be created by
downsampling the input image. This operation can actually be the most
memory-intensive part of the process, and can yield poor results with
mostly-empty images. You can avoid this by using this argument and then invoking
:ref:`cli-make-thumbnail` with a better-suited input image.

The ``--parallelism FACTOR`` argument specifies the level of parallism to use.
On operating systems that support parallel processing, the default is to use
all CPUs. To disable parallel processing, explicitly specify a factor of 1.

Notes
=====

This command will create the highest-resolution tile layer, corresponding to the
``DEPTH`` argument, and emit an ``index_rel.wtml`` file containing projection
information and template metadata.

Currently, parallel processing is only supported on the Linux operating system,
because ``fork()``-based multiprocessing is required. MacOS should support this,
but there is currently (as of Python 3.8) `a bug`_ preventing that.

.. _a bug: https://bugs.python.org/issue33725
