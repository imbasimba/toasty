.. _studies:

========================================
“Studies”: Tiling high-resolution images
========================================

In the `AAS WorldWide Telescope`_ framework, “studies” are high-resolution sky
images projected on the sky in a tangential (`gnomonic`_) projection. Due to the
properties of this projection, the “study” format is best suited for images that
are large in terms of pixels, but not necessarily large in terms of angular
area. Examples of this kind of imagery include nearly all astrophotography
images and typical scientific observations. Mosaics that cover extremely large
sections of the sky (multiple steradians) are better represented in the all-sky
TOAST format.

.. _AAS WorldWide Telescope: http://worldwidetelescope.org/
.. _gnomonic: https://en.wikipedia.org/wiki/Gnomonic_projection

The intent of the toasty package is to make it so that most tiling workflows can
be executed on the command line using the ``toasty`` program. This section will
demonstrate this way of using the software.


Astrometry
==========

Tiling study images should, in general, be easy if not completely automatic. If
there’s one part of the process most likely to cause problems, it is generating
the “astrometric” information that specifies where the image should be placed on
the sky.

More here ...
