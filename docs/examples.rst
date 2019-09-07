=============================
Examples of How to Use Toasty
=============================

Here we’ll summarize some of the ways that you can use toasty_.

.. _toasty: https://toasty.readthedocs.io/


Toasting a plate-carrée, all-sky PNG image
==========================================

This script processes an existing all-sky PNG image that uses a `plate carrée
<https://en.wikipedia.org/wiki/Equirectangular_projection>`_ projection, using
scikit-image_ to load the data::

  from toasty.toast import toast
  from toasty.samplers import plate_carree_sampler
  from skimage.io import imread

  data = imread('allsky.png')
  sampler = plate_carree_sampler(data)
  output_directory = 'toast'
  depth = 8  # approximately 0.165"/pixel at highest resolution

  # Make the full toast tile set for the entire sky:
  toast(sampler, depth, output_directory)

.. _scikit-image: https://scikit-image.org/


Toasting subsets of the sky
===========================

You don’t have to build the full pyramid for the full sky all at once::

  # Toast a specific region of the sky defined by RA/Dec bounds
  from toasty.toast import minmax_tile_filter
  ra_range = [0.17, 0.19],  # radians
  dec_range = [1.22, 1.24],  # radians
  filter = minmax_tile_filter(ra_range, dec_range)
  toast(sampler, depth, output_directory, tile_filter=filter)

  # Toast a specific region of the sky defined by a higher-level TOAST tile
  from toasty.toast import nxy_tile_filter
  filter = nxy_tile_filter(4, 5, 9)  # depth=4, ix=5, iy=9
  toast(sampler, depth, output_directory, tile_filter=filter)

  # Create only the bottom layer of toast tiles
  toast(sampler, depth, output_directory,
        base_level_only = True,
  )

  # Merge from a previously created toast layer up to a specified layer
  toast(sampler, depth, output_directory,
        top_layer = 4,
  )


Controlling how data are turned into RGB
========================================

Here we apply a log-stretch to an all sky FITS image::

  from toasty.toast import toast
  from toasty.sampler import plate_carree_sampler, normalizer
  from astropy.io import fits

  data = fits.open('allsky.fits')[0].data

  vmin, vmax = 100, 65535
  scaling = 'log'
  contrast = 1
  sampler = normalizer(
    plate_carree_sampler(data),
    vmin, vmax
    scaling, bias, contrast
  )

  output_directory = 'toast'
  depth = 8
  toast(sampler, depth, output_directory)


Arbitrary coordinate transformations
====================================

A custom “sampler” can be used to tell toasty_ what image values
correspond to what locations on the sky::

  from toasty.toast import toast

  def sampler(x, y):
      """
      x and y are arrays, giving the RA/Dec centers
      (in radians) for each pixel to extract
      """
      ... code to produce pixel values goes here ...

  output_directory = 'toast'
  depth = 8
  toast(sampler, depth, output_directory)

See :meth:`toasty.toast.toast` for documentation on sampler functions.


Previewing toasts with AAS WorldWide Telescope
==============================================

To quickly preview a toast directory named ``mytoast``, run the command::

  python -m toasty.viewer mytoast

This will start a web server, probably at ``http://0.0.0.0:8000``. (Check the
program’s output for the actual address). Open this URL in a browser to get a
quick look at the data.


Example toasty outputs: ADS All-Sky Survey
==========================================

For an example of tiles generated with Toasty, see `the ADS All Sky Survey
<http://adsass.org/wwt>`_. The code used to generate these images is in `the
file toast.py`_ in the `adsass/wwt-frontend`_ repository on GitHub. This tile
pyramid was created by Chris Beaumont.

.. _the file toast.py: https://github.com/adsass/wwt-frontend/blob/master/toast/toast.py
.. _adsass/wwt-frontend: https://github.com/adsass/wwt-frontend/


Example toasty outputs: PanSTARRS in STScI AstroView
====================================================

Another example is a toasting of the “3π” survey of the PanSTARRS_ project,
viewable `here in STScI’s AstroView`_ interface. The code used to generate
these images is in the GitHub repository `ceb8/toastPanstarrs`_. This tile
pyramid was created by Clara Brasseur.

.. _PanSTARRS: https://panstarrs.stsci.edu/
.. _here in STScI’s AstroView: https://mast.stsci.edu/portal/Mashup/Clients/AstroView/AstroView.html?debug&avSurveyType=PANSTARRS
.. _ceb8/toastPanstarrs: https://github.com/ceb8/toastPanstarrs
