.. toasting:

===============================
“TOASTing”: Tiling full spheres
===============================

To view full-sphere data in `AAS WorldWide Telescope`_ — either all-sky maps or
all-planet maps — the input imagery needs to be tiled into the special TOAST
projection. It is not necessary to use this projection for images that may
contain many pixels but do not cover a substantial fraction of the sphere. In
those cases, you should prepare a :ref:`study <studies>` instead.

.. _AAS WorldWide Telescope: http://worldwidetelescope.org/

The intent of the toasty package is to make it so that most tiling workflows can
be executed on the command line using the ``toasty`` program. This section will
demonstrate this way of using the software.


Toasting a single full-sphere image
===================================

Sometimes, you already have a large image mapping the entire sphere — it just
needs to be reprojected, broken into tiles, and described in a `WTML`_ file. The
workflow in this case is as follows:

.. _WTML: https://docs.worldwidetelescope.org/data-guide/1/data-file-formats/collections/

1. Choose and/or create a directory on your computer in which you’ll be working.

2. Download the source image to your work directory. For concreteness, we’ll
   call it ``fullsize.tif`` here, but multiple image formats are supported.

3. Determine the *projection* used by the source image. This is the mechanism by
   which the curved surface of the sphere is mapped onto a 2D image. For
   full-sphere imagery, only a few choices are ever used: probably the main
   thing to check is whether your image is in equatorial (RA/Dec) or galactic
   (l/b) coordinates. Consult the :ref:`cli-tile-allsky` documentation (or
   :ref:`cli-tile-healpix`) for the supported choices. If your image uses an
   unsupported projection, please `file a request`_ with the developers.

4. Determine the *tiling depth* appropriate for your use case. The depth is a
   number that specifies the highest resolution that your final map will attain.
   Consult the :ref:`cli-tile-allsky` documentation for the quantitative
   definition. The best choice will depend on your individual circumstances. But
   as a general guideline, you should probably choose the depth that yields a
   number of pixels equal to, or just greater than, the number of pixels in your
   source image.

5. Do the initial tiling with:

   .. code-block:: shell

      $ toasty tile-allsky --projection={PROJECTION} \
          --outdir=tiled fullsize.tif {DEPTH}

   where ``{PROJECTION}`` and ``{DEPTH}`` should be replaced by the values you
   determined in the previous steps. (Here, the backslashes are used because the
   command spans multiple lines of the shell prompt. If you type it all on one
   line, no backslashes should be used.)

   It might make sense to use some of the :ref:`cli-std-image-options` to
   control how the source image is processed. Along with the tiles, this command
   will generate a file ``tiled/index_rel.wtml`` that describes the imagery.

6. Generate the higher-level tiles with:

   .. code-block:: shell

      $ toasty cascade --start={DEPTH} tiled

   where ``{DEPTH}`` is the same value as used in the previous command.

7. Examine the image ``tiled/0/0/0_0.png`` to see if it looks like a reasonable
   TOAST-ification of your source image. The equator of your map will be
   translated to a diamond touching the midpoints of the edges of the square
   tile.

8. Review the appearance of your image in WWT. Use the ``wwtdatatool`` command
   provided by the `wwt_data_formats`_ Python package to start up an HTTP server
   that will make your WTML and tile data accessible to WWT (either Windows or
   web clients):

   .. code-block:: shell

      $ wwtdatatool serve tiled

   This command will print a URL to a synthetic ``index.wtml`` file that you can
   open up in WWT to view your tiled image. Hopefully everything will be fine,
   but at this point you can tune and/or fix the tiling procedure if something
   isn’t right.

9. Fill in proper metadata in the ``index_rel.wtml`` file. Items to consider are:

   - The ``<Credits>`` XML element with proper credit text.

   - The ``<CreditsUrl>`` XML element with a link to the image source and/or
     more information about it.

   - The ``<Description>`` XML element with text describing the image. If editing
     the XML manually, make sure to properly escape the magic XML characters
     ``&`` (to ``&amp;``), ``<`` (to ``&lt;``) and ``>`` (to ``&gt;``).

   - The ``Name`` attributes of the ``<ImageSet>``, ``<Place>``, and ``<Folder>``
     elements. These should generally all be the same.

   - Other metadata like the ``Bandpass``, etc.

10. When the ``index_rel.wtml`` file is all finalized, it needs to be transformed
    to have absolute rather than relative URLs. To do this transformation, you need
    to know the URL from which users will be accessing your data. When you know that
    base URL, the command to use is of this form:

    .. code-block:: shell

       $ wwtdatatool wtml rewrite-urls \
           tiled/index_rel.wtml \
           http://myserver.org/datasetname/ \
           tiled/index.wtml

    (Here, the backslashes are used because the command spans multiple lines of
    the shell prompt. If you type it all on one line, no backslashes should be
    used.)

11. Finally, upload the complete contents of your ``tiled`` subdirectory to your
    web server. In this case, the upload location should be such that the url
    ``http://myserver.org/datasetname/index.wtml`` will yield the
    ``index.wtml`` file created in the previous step.

.. _file a request: https://github.com/WorldWideTelescope/toasty/issues/
.. _wwt_data_formats: https://wwt-data-formats.readthedocs.io/
