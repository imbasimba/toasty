.. _cli-tile-healpix:

=======================
``toasty tile-healpix``
=======================

The ``tile-healpix`` command transforms all-sky FITS images in the HEALPix_
format into WWT’s FITS TOAST format.

.. _HEALPix: https://healpix.jpl.nasa.gov/

Usage
=====

.. code-block:: shell

   toasty tile-healpix
      [--galactic]
      [--outdir DIR]
      [--parallelism FACTOR] [-j FACTOR]
      {FITS-PATH}
      {TOAST-DEPTH}

The ``FITS-PATH`` argument gives the filename of the input image, which should
be a single FITS file storing data in the HEALPix_ format.

The ``TOAST-DEPTH`` argument specifies the resolution level of the TOAST
pixelization that will be generated. A depth of 0 means that the input will be
sampled onto a single 256×256 tile, a depth of 1 means that the input will be
sampled onto four tiles for a total resolution of 512×512, and so on. When
converting from HEALPix, the appropriate TOAST depth can be derived from the
HEALPix ``N_side`` parameter as approximately::

  depth = log2(N_side) - 6.2

One should typically round up to the next larger integer to err on the side of
higher resolution, although the best policy will depend on the sampling of the
input HEALPix map.

The ``--outdir DIR`` option specifies where the output data should be written.
If unspecified, the data root will be the current directory.

The ``--galactic`` option forces the tiling to assume that the input map is in
Galactic coordinates, even if the FITS headers do not specify that. This has
been observed in some data sets in the wild.

The ``--parallelism FACTOR`` argument (or ``-j FACTOR``) specifies the level of
parallism to use. On operating systems that support parallel processing, the
default is to use all CPUs. To disable parallel processing, explicitly specify a
factor of 1.

Notes
=====

This command requires that the healpy_ Python module is installed.

.. _healpy: https://healpy.readthedocs.io/

This command will create FITS files for the highest-resolution tile layer,
corresponding to the ``DEPTH`` argument, and emit an ``index_rel.wtml`` file
containing projection information and template metadata.

The WWT rendering engine can also display datasets in the hierarchical HiPS_
FITS format, which addresses about the same use case as TOAST. If a HiPS FITS
dataset already exists, it is probably a wiser choice to use it rather than
creating a new TOAST pyramid. However, TOAST provides noticeably better
performance for the initial data display and avoiding positional shifts as the
user zooms in.

.. _HiPS: https://aladin.unistra.fr/hips/

Currently, parallel processing is only supported on the Linux operating system,
because ``fork()``-based multiprocessing is required. MacOS should support this,
but there is currently (as of Python 3.8) `a bug`_ preventing that.

.. _a bug: https://bugs.python.org/issue33725


See Also
========

- :ref:`cli-tile-allsky`