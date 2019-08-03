===========================
Overview: What is Toasting?
===========================

So, toasty_ is for toasting. What does that even mean?

.. _toasty: https://toasty.readthedocs.io/

This documentation will *not* go into detail because there are plans to
provide comprehensive information in a separate document that is not specific
to this particular library.

Alas, that documentation has not been written yet. In the meantime, the best
detailed reference is `McGlynn et al. 2019`_, which explains and justifies the
Tesselated Octahedral Adaptive Spherical Transformation (TOAST) projection
that toasty_ is concerned with. See also the `WorldWide Telescope Projection
Reference`_, although that document is a bit out of date. (Which shouldn’t
matter, in principle, but its current Web expression may be a bit busted.) The
following text aims to give a quick overview of the concepts that these
documents work out in detail.

.. _McGlynn et al. 2019: https://ui.adsabs.harvard.edu/abs/2019ApJS..240...22M/abstract
.. _WorldWide Telescope Projection Reference: https://worldwidetelescope.gitbook.io/projection-reference/


The problem(s)
==============

Say that you are writing a piece of software that aim to let users
interactively explore a map of the Earth, the sky, or another planet. For the
purposes of this discussion, the key thing is that these are all spherical
entities. The user may want to zoom out and view large swathes of these
spheres at once, or they may want to zoom way in and see extremely fine
detail. The user will probably be accessing the maps over a network, and the
maps may be far too large to transmit in over the network in their entirety.

There are two problems to solve here. First, we need some way to store image
data covering an entire sphere. There is no unique best way to map the curved
surface of a sphere into a two-dimensional representation; in particular, many
common projections perform poorly at the poles.

Second, once we have some image data that we can map onto a sphere in some
satisfactory way, we need a way to transmit pieces of it to the user
incrementally. If they zoom out, it won't be practical to send them a huge
chunk of the full-resolution map.


The solution(s)
===============

Our solution to the above problems is to construct “tile pyramids” using the
TOAST spherical projection.

The TOAST projection does exactly what we need for the first problem: it maps
the entire sphere onto a 2D image that can easily be represented digitally.
While TOAST is not perfect in every way, it performs well at the poles and
maintains approximately uniform resolution at all locations on the sphere. If
you’re familiar with this topic, you may know that the HEALPix_ projection
also operates in this problem space. We won’t go into details here, but
suffice it to say that TOAST has some nice technical properties that make it
the preferred choice for software such as the AAS_ `WorldWide Telescope`_. In
particular, TOAST maps the sphere onto a square image, rather than the jagged
shape required by HEALPix.

.. _HEALPix: https://healpix.jpl.nasa.gov/
.. _AAS: https://aas.org/
.. _WorldWide Telescope: http://www.worldwidetelescope.org/home

A high-resolution full-sphere TOAST map may weigh in at a million pixels *on a
side*, or a trillion pixels total — far too large to manipulate in a
user-facing scenario. Creating a “tile pyramid” of the image makes it possible
to actually do useful things with a full-scale TOAST map. First, the
high-resolution map is broken into a set of square sub-images, “tiles,” each
256 pixels on a side. By the requirements of the TOAST standard, the number of
tiles on each side must be a power of 2. Then, lower-resolution maps are
created by downsampling the high-resolution map in 2×2 pixel blocks, yielding
derived images that are half as large as their parents along each axis. (Each
downsampled image therefore has 1/4 as many pixels as its parent.) By
construction, each of these lower-resolution maps can also be broken into
256×256 tiles. This process continues until a “level 0” map is created
consisting of a single tile that represents the full sphere. With a full
sphere having a solid angle of 4π steradians, each pixel in this level-0 map
covers about 0.0002 steradians or 0.6 square degrees. As a user zooms in or
out, or pans around the sphere, their computer is sent the tiles needed to
produce a visually acceptable view. Each individual tile file is small enough
that the data transfer remains tractable.


The role of toasty
==================

The toasty_ module helps create these TOAST tile pyramids from astronomical
image data. There are essentially three problems that it tackles:

1. Transforming image data from their native projection to the TOAST one.
2. Mapping scalar data values into RGB color images for user display.
3. Downsampling the high-resolution TOAST map all the way down to the level-0
   map.

The process of creating TOAST tile pyramids from some input data is
colloquially referred to as “toasting.”
