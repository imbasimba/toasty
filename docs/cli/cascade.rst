.. _cli-cascade:

==================
``toasty cascade``
==================

The ``cascade`` operation computes lower-resolution tiles from higher-resolution
tiles. The same algorithms apply to either studies or all-sky TOAST pyramids.

Usage
=====

.. code-block:: shell

   toasty cascade [--parallelism FACTOR] {--start DEPTH} PYRAMID-DIR

The ``PYRAMID-DIR`` argument gives the location of a directory containing tile
pyramid data files. The ``--start DEPTH`` argument gives the depth at which
tiles *already exist*. For instance, with ``--start 5``, the pyramid should
contain level-5 tiles, and the cascade will fill in tiles between levels 4 and
0, inclusive.

The ``--parallelism FACTOR`` argument specifies the level of parallism to use.
On operating systems that support parallel processing, the default is to use
all CPUs. To disable parallel processing, explicitly specify a factor of 1.

Notes
=====

Currently, parallel processing is only supported on the Linux operating system,
because ``fork()``-based multiprocessing is required. MacOS should support this,
but there is currently (as of Python 3.8) `a bug`_ preventing that.

.. _a bug: https://bugs.python.org/issue33725
