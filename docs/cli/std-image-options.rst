.. _cli-std-image-options:

==============================
Standard image-loading options
==============================

Various ``toasty`` subcommands that load images accept a standard set of options
that allow you to customize the loading process. These options are listed below.


``--black-to-transparent``
==========================

If this option is specified, pure black values in the source image will be
converted to be completely transparent. This is useful because in image formats
that do not support transparency, like JPEG, pure black is often used for
data-free regions that should be marked as transparent when possible.


``--colorspace-processing=MODE``
================================

This option specifies how to handle the color profile of the source image.

- ``srgb`` (the default): the image color profile will be converted to the
  Web-standard sRGB profile. This is almost definitely what you want.
- ``none``: no color profile conversions will be performed.


``--crop=TOP,RIGHT,BOTTOM,LEFT``
================================

If this option is provided, the input image will have its edges cropped before
further processing. The argument should be a list of four non-negative integers,
each representing how many pixels to crop off from the specified edge of the
image. For instance, ``--crop=0,10,0,0`` indicates that 10 pixels should be
cropped off the right edge of the image, while other edges should remain
unmodified.

As a shorthand, ``--crop=X``, means to crop off X pixels from all edges of the
image. Writing ``--crop=V,H`` is shorthand for ``--crop=V,H,V,H``.


``--psd-single-layer=NUMBER``
=============================

*If* the input image is an Adobe Photoshop PSD or PSB file, this option will
tell toasty to only load the specified layer from the file. The numbering starts
with zero. Even if the image contains only one layer, this option will save a
factor of a few in memory, so it is useful for extremely large images, which are
sometimes distributed in Photoshop formats.
