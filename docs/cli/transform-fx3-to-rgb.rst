.. _cli-transform-fx3-to-rgb:

===============================
``toasty transform fx3-to-rgb``
===============================

The ``transform fx3-to-rgb`` command transform a pyramid in an “Fx3” format —
three planes of floating-point data — and converts them to RGB(A) image files.

Usage
=====

.. code-block:: shell

   toasty transform fx3-to-rgb
      [--parallelism FACTOR]
      [--start DEPTH]
      [--clip NUMBER]
      {PYRAMID-DIR}

See the :ref:`cli-std-image-options` section for documentation on those options.

The ``PYRAMID-DIR`` argument gives the name of a tile pyramid. It should contain
Numpy data files in one of the supported Toasty “Fx3” formats. One potential
source of such data is tiling an `OpenEXR`_ file.

.. _OpenEXR: https://www.openexr.com/

The ``--clip NUMBER`` argument specifies the point at which the floating-point
values will be clipped. By default, the input floating-point data are expected
to range between 0 and 1, which will be mapped to the range 0–255 in the
standard 8-bit RGB color scheme. If, for example, you specify ``--clip=0.1``,
then floating-point values of 0.1 will be mapped to 255 (i.e. full brightness).
Values greater than this cutoff will be clipped and appear equally bright in the
output RGB images.

The ``--parallelism FACTOR`` argument specifies the level of parallism to use.
On operating systems that support parallel processing, the default is to use
all CPUs. To disable parallel processing, explicitly specify a factor of 1.

Notes
=====

After the clip is applied, the floating-point data have a square-root transform
applied before being mapped to RGB values. This could/should be made
configurable, but this hasn't yet been done.
