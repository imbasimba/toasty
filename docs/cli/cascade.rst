.. _cli-cascade:

==================
``toasty cascade``
==================

The ``cascade`` operation computes lower-resolution tiles from higher-resolution
tiles. The same algorithms apply to either studies or all-sky TOAST pyramids.

Usage
=====

.. code-block:: shell

   toasty cascade {--start DEPTH} PYRAMID-DIR

The ``PYRAMID-DIR`` argument gives the location of a directory containing tile
pyramid data files. The ``--start DEPTH`` argument gives the depth at which
tiles *already exist*. For instance, with ``--start 5``, the pyramid should
contain level-5 tiles, and the cascade will fill in tiles between levels 4 and
0, inclusive.
