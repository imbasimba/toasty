.. _studies:

========================================
“Studies”: Tiling high-resolution images
========================================

In the `AAS WorldWide Telescope`_ framework, “studies” are high-resolution sky
images projected on the sky in a tangential (`gnomonic`_) projection. Due to the
properties of this projection, the “study” format is best suited for images that
are large in terms of pixels, but not necessarily large in terms of angular
area. Examples of this kind of imagery include nearly all astrophotography
images and typical scientific observations. Mosaics that cover *extremely* large
regions of the sky (multiple steradians) are better represented in the all-sky
TOAST format.

.. _AAS WorldWide Telescope: http://worldwidetelescope.org/
.. _gnomonic: https://en.wikipedia.org/wiki/Gnomonic_projection

The intent of the toasty package is to make it so that most tiling workflows can
be executed on the command line using the ``toasty`` program. This section will
demonstrate this way of using the software.


Astrometry
==========

Tiling study images should generally be easy, and in many circumstances the
process can be completely automatic. If there’s one part of the process most
likely to cause problems, it is generating the “astrometric” information that
specifies where the image should be placed on the sky.

When creating a new WWT study dataset, you need to determine how or where the
necessary astrometric information will come from. Your options are:

- `AVM`_ tags in the source image. **Except we haven’t wired this up for basic
  study processing! Fix this!!!**

- Pre-positioning in the WWT Windows client and exporting as a WWTL file. If you
  have a large image that you can load in the WWT Windows client, you can use its
  interactive placement feature to set its position, and then save the image with
  that placement as an “image layer” in a WWTL “layers file”, then can load the
  image and its astrometry using the :ref:`cli-wwtl-sample-image-tiles` command.

- If all else fails, the :ref:`cli-tile-study` command will insert
  default astrometric information and place your image at RA = Dec = 0 and make
  it 1° across. You can then manually edit the WTML to properly place the image
  against a reference. This can be less horrible than it sounds, but it’s
  definitely not good.

.. _AVM: https://www.virtualastronomy.org/avm_metadata.php
