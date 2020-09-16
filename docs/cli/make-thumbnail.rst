.. _cli-make-thumbnail:

=========================
``toasty make-thumbnail``
=========================

The ``make-thumbnail`` command takes a single input image and reduces it to a
96×45 pixel WWT thumbnail.

Usage
=====

.. code-block:: shell

   toasty make-thumbnail
      [standard image-loading options]
      {INPUT-IMAGE-PATH}
      {OUTPUT-IMAGE-PATH}

See the :ref:`cli-std-image-options` section for documentation on those options.

The ``INPUT-IMAGE-PATH`` argument gives the filename of the input image.

The ``OUTPUT-IMAGE-PATH`` argument gives the filename of the thumbnail to be
created. It is always saved in JPEG format, regardless of the filename
extension.


Example
=======

When tiling a very large input image, the thumbnailing step may actually use too
much memory or yield bad results. You can use this command to create a better
thumbnail.

.. code-block:: shell

  $ toasty tile-allsky --placeholder-thumbnail --outdir tiled allsky_64k.exr 8
  $ toasty make-thumbnail allsky_2k.jpg tiled/thumb.jpg


Details
=======

The built-in tiling commands will attempt to create a thumbnail for you, but the
results can be mediocre and the step can actually consume a great deal of memory
for large input images. In conjunction with the ``--placeholder-thumbnail``
option to the tiling commands, this command can make it a bit easier to create a
better-quality thumbnail by deriving it from a different, more task-appropriate
source image.

The thumbnailing process crops the image to the required aspect ratio and then
downsamples it using `PIL`_. This algorithm isn’t always the best. If your
high-resolution source image is “sparse” (i.e., mostly black), it may be useful
to generate the thumbnail from a version of it that has already been downscaled.
Because the final thumbnail size is so small, you can work from very modest
source images if needed.

.. _PIL: https://pillow.readthedocs.io/en/stable/reference/Image.html#PIL.Image.Image.thumbnail
