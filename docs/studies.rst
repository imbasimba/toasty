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
  image and its astrometry using the :ref:`cli-tile-wwtl` command.

- If all else fails, the :ref:`cli-tile-study` command will insert
  default astrometric information and place your image at RA = Dec = 0 and make
  it 1° across. You can then manually edit the WTML to properly place the image
  against a reference. This can be less horrible than it sounds, but it’s
  definitely not good.

.. _AVM: https://www.virtualastronomy.org/avm_metadata.php


Standard workflow 1: manual positioning in the Windows client
=============================================================

In the typical study workflow, you have a single source image, potentially very
large, that needs to be broken into tiles and described in a `WTML`_ file. If
you have access to the Windows client and can position the image manually, the
standard workflow proceeds as follows:

.. _WTML: https://docs.worldwidetelescope.org/data-guide/1/data-file-formats/collections/

1. Choose and/or create a directory on your computer in which you’ll be working.

2. Download the source image to your work directory. For concreteness, we’ll
   call it ``fullsize.tif`` here, but multiple image formats are supported.

3. Open the image in the WWT Windows client, position it interactively, and
   export the positioned image layer as a WWTL layer file. We’ll call that
   ``fullsize.wwtl``.

4. Do the initial tiling and astrometry extraction with:

   .. code-block:: shell

      $ toasty tile-wwtl --outdir=tiled fullsize.wwtl

   Here it might make sense to use some of the :ref:`cli-std-image-options` to
   control how the source image is processed. Along with the tiles, this command
   will generate a file ``tiled/index_rel.wtml`` that describes the image data,
   including their astrometry.

5. Generate the higher-level tiles with:

   .. code-block:: shell

      $ toasty cascade --start=5 tiled

   where the number passed to the ``--start`` argument will change depending on
   the characteristics of your image. The ``tile-wwtl`` command will tell you
   what value to use.

6. Examine the image ``tiled/0/0/0_0.png`` to see if it looks like a reasonable
   reduction of your large source image.

7. Review the appearance of your image in WWT. Use the ``wwtdatatool`` command
   provided by the `wwt_data_formats`_ Python package to start up an HTTP server
   that will make your WTML and tile data accessible to WWT (either Windows or
   web clients):

   .. code-block:: shell

      $ wwtdatatool serve tiled

   This command will print a URL to a synthetic ``index.wtml`` file that you can
   open up in WWT to view your tiled image. Hopefully everything will be fine,
   but at this point you can tune and/or fix the tiling procedure if something
   isn’t right.

8. Fill in proper metadata in the ``index_rel.wtml`` file. Items to consider are:

   - The ``<Credits>`` XML element with proper credit text.

   - The ``<CreditsUrl>`` XML element with a link to the image source and/or
     more information about it.

   - The ``<Description>`` XML element with text describing the image. If editing
     the XML manually, make sure to properly escape the magic XML characters
     ``&`` (to ``&amp;``), ``<`` (to ``&lt;``) and ``>`` (to ``&gt;``).

   - The ``Name`` attributes of the ``<ImageSet>``, ``<Place>``, and ``<Folder>``
     elements. These should generally all be the same.

   - The ``ZoomLevel`` attribute of the ``<Place>`` element, specifying the zoom
     level that the client should seek to when viewing the image. It can be a bit
     subjective as to what zoom level is best, and the numbers are measured oddly
     so choosing the right value is generally a matter of trial and error.

   - Other metadata like the ``Classification``, ``Constellation``, etc.

9. When the ``index_rel.wtml`` file is all finalized, it needs to be transformed
   to have absolute rather than relative URLs. To do this transformation, you need
   to know the URL from which users will be accessing your data. When you know that
   base URL, the command to use is of this form:

   .. code-block:: shell

      $ wwtdatatool wtml rewrite-urls \
          tiled/index_rel.wtml \
          http://data1.wwtassets.org/packages/2020/07_phat_m31/ \
          tiled/index.wtml

   (Here, the backslashes are used because the command spans multiple lines of
   the shell prompt. If you type it all on one line, no backslashes should be
   used.)

10. Finally, upload the complete contents of your ``tiled`` subdirectory to your
    web server. In this case, the upload location should be such that the url
    `<http://data1.wwtassets.org/packages/2020/07_phat_m31/index.wtml>`_ will
    yield the ``index.wtml`` file created in the previous step.

.. _wwt_data_formats: https://wwt-data-formats.readthedocs.io/

And that’s it, your image has been tiled and published!
