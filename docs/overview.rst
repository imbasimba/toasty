=================================
Overview: Tile Pyramids and TOAST
=================================

The toasty_ package can be used to create “tile pyramids” of astronomical
image data, particularly ones targeting the “TOAST” format. What does that
even mean?

.. _toasty: https://toasty.readthedocs.io/


The first problem
=================

Say that you are writing a piece of software that aims to let users
interactively explore high-resolution imagery. The user may want to zoom out
and view large swathes of an image all at once, or they may want to zoom way
in and see extremely fine detail. The user will probably be accessing the
images over a network, and the images may be far too large to transmit in over
the network in their entirety. How do we provide a smooth user experience?


The first solution
==================

Pretty much everyone who has faced the above problem — say, the engineers of
Google Maps — has converged on a common solution. You process your
high-resolution image to create a “tile pyramid.” First, the full-resolution
image is broken into a set of modestly-sized sub-images, “tiles.” Then, you
create lower-resolution tiles by downsampling clusters of these tiles, and you
downsample *those* tiles until the entire image is downsampled into a small
number of base tiles. As a user zooms in or out, or pans around the image,
their computer is sent the tiles needed to produce a visually acceptable view.
Each individual tile file is small enough that the data transfer remains
tractable. If you group the tiles by their resolutions and think of them as
forming a layered stack, there are fewer tiles in each layer as you move
towards lower resolutions — hence the “pyramid.”

In toasty_, a few invariants are maintained. Each tile is 256 pixels on a
side. The number of tiles on each side of the full-resolution map must be a
power of 2. Tiles are downsampled in 2×2 pixel blocks, yielding derived images
that are half as large as their parents along each axis. (Each downsampled
image therefore has 1/4 as many pixels as its parent.) By construction, each
lower-resolution map can also be broken into 256×256 tiles. This process
continues until a “level 0” map is created consisting of a single tile.


The second problem
==================

If you’re writing a piece of software that aims to let users interactively
explore a map of the Earth, the sky, or another planet, you have another
problem. These are all spherical entities, and there is no unique best way to
map the curved surface of a sphere into a two-dimensional representation; in
particular, many common projections perform poorly at the poles. If you want
to apply the tile-pyramid approach to spherical map data, you have to choose a
projection that meshes well with the tiling scheme.


The second solution
===================

The Tesselated Octahedral Adaptive Spherical Transformation (TOAST) projection
does exactly this: it maps the entire sphere onto a square 2D image. While
TOAST is not perfect for all applications, it performs well at the poles and
maintains approximately uniform resolution at all locations on the sphere. If
you’re familiar with this topic, you may know that the HEALPix_ projection
also operates in this problem space. We won’t go into details here, but
suffice it to say that TOAST has some nice technical properties that make it
the preferred choice for software such as the AAS_ `WorldWide Telescope`_. In
particular, TOAST maps the sphere onto a square image, rather than the jagged
shape required by HEALPix, and pixels at different resolutions share common
great-circle edges, allowing gap-free rendering when tiles of varying
resolutions are available.

.. _HEALPix: https://healpix.jpl.nasa.gov/
.. _AAS: https://aas.org/
.. _WorldWide Telescope: http://www.worldwidetelescope.org/home

Currently, the best detailed TOAST reference is `McGlynn et al. 2019`_. See
also the `WorldWide Telescope Data Guide`_, although that document
is a bit out of date. (Which shouldn’t matter, in principle, but its current
Web expression may be a bit busted.)

.. _McGlynn et al. 2019: https://ui.adsabs.harvard.edu/abs/2019ApJS..240...22M/abstract
.. _WorldWide Telescope Data Guide: https://docs.worldwidetelescope.org/data-guide/1/spherical-projections/

A high-resolution full-sphere TOAST map may weigh in at a million pixels *on a
side*, or a trillion pixels total, which is why tiling is essential. With a
full sphere having a solid angle of 4π steradians, each pixel in a level-0
TOAST map (256×256 pixels) map covers about 0.0002 steradians or 0.6 square
degrees.


The role of toasty
==================

The toasty_ module helps create these tile pyramids from astronomical image
data, with special support for the TOAST projection. There are essentially
three problems that it tackles:

1. Breaking large image assets into tiles, potentially transforming them into
   the TOAST projection.
2. Mapping scalar data values into RGB color images for user display.
3. Downsampling a set of tiles all the way down to a level-0 root tile.

The process of creating TOAST tile pyramids from some input data is
colloquially referred to as “toasting.” While toasty_ was originally written
to target only all-sky maps in the TOAST projection, it now also supports
other kinds of tile pyramids as well.
