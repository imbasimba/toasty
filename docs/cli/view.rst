.. _cli-view:

=======================
``toasty view``
=======================

The ``view`` command allows you view one or more FITS files using the `WWT
research app`_.

.. _WWT research app: https://docs.worldwidetelescope.org/research-app/latest/


Example
=======

View a FITS file:

.. code-block:: shell

   toasty view myfile.fits


Detailed Usage
==============

.. code-block:: shell

   toasty view
      [--tunnel HOST, -t HOST]
      [--appurl URL]
      [--blankval NUMBER]
      [--browser BROWSER, -b BROWSER]
      [--hdu-index INDEX[,INDEX,...]]
      [--parallelism COUNT, -j COUNT]
      [--tile-only]
      {FITS [FITS ...]}

The ``FITS`` argument(s) give the path(s) of one or more input FITS files. These
will be automatically tiled if necessary, then made available on a local web
server so that the WWT viewer can access the data.

The ``-t HOST`` or ``--tunnel HOST`` option can be used to view an image stored
on the remote machine named ``HOST``, using `SSH`_. In order for this work, SSH
`connection sharing`_ must be enabled, and Toasty must be installed on the
destination machine. See more in :ref:`cli-view-tunneled` below.

.. _SSH: https://en.wikipedia.org/wiki/Secure_Shell
.. _connection sharing: https://en.wikibooks.org/wiki/OpenSSH/Cookbook/Multiplexing

The ``-b`` or ``--browser`` option specifies which web browser to use, using an
identifier as understood by the `Python "webbrowser" module`_. Typical choices
might be ``firefox``, ``safari``, or ``google-chrome``. If unspecified, a
sensible default will be used.

.. _Python "webbrowser" module: https://docs.python.org/3/library/webbrowser.html

The ``--hdu-index`` argument, if specified, fixes the index number of the FITS
HDU to load from the input file(s). If one value is provided, that index will be
used for every FITS file. If a comma-separated list is provided, the index
corresponding to each index path will be used.

The ``--blankval`` argument, if specified, gives a data value to be treated as
undefined data when processing the FITS data.

The ``--parallelism COUNT`` (or ``-j COUNT``) argument specifies the level of
parallism to use in the tiling and downsampling process. On operating systems
that support parallel processing, the default is to use all CPUs. To disable
parallel processing, explicitly specify a factor of 1.

The ``--appurl`` option can be used to override the base URL for the preview app
that will be used. This can be helpful when developing new features in one of
these apps.

If the ``--tile-only`` option is specified, the data are tiled but no web
browser is launched. This can be useful when automating Toasty workflows.


Details
=======

This command provides similar functionality as the ``wwtdatatool preview``
command `provided by the wwt_data_formats package`_, but automatically tiles its
inputs and generates the needed ``index_rel.wtml`` file.

.. _provided by the wwt_data_formats package: https://wwt-data-formats.readthedocs.io/en/latest/cli/preview.html

If tiling is required and the tile output directory already exists, the tool
assumes that the image was already successfully tiled, and skips straight to
launching the viewer without rerunning the tiling process.

The FITS data will be tiled either onto a common tangential projection, or into
a TOAST, depending on the angular size subtended by the data. If any of the
FITS image corners are separated by more than 20 degrees, the TOAST format will
be used. Otherwise, Toasty will reproject the input data into a tangential
(gnomonic) projection if necessary.



.. _cli-view-tunneled:

Tunneled Image Viewing
======================

The “tunneled” mode of this command allows you to view images that live on
another machine.

The basic usage of this mode is


.. code-block:: shell

   toasty view -t HOST FITS1 [FITS2...]

where ``HOST`` is the hostname of the machine with the image(s), and the
``FITSn`` values are the paths of the images on the machine relative to the
destination user's home directory. Or, absolute paths are also OK.

Here, ``HOST`` is any hostname that will be accepted by your ``ssh`` program.
This means that it can be a “virtual” host alias set up in your ``.ssh/config``
file, for instance.

In order for this functionality to work, it is necessary that the SSH commands
will not need to prompt you interactively in order to log in. This requires that
either you have key-based SSH authentication set up, with passphrase-less keys
or a key agent running, *or* that SSH connection reuse is activated for the
target host, and you have an existing SSH connection to the host open. The
program `stund`_ can be helpful for setting up long-lived connections to avoid
password prompts.

.. _stund: https://github.com/pkgw/stund

The target host must also have Toasty installed, such that if you log in to a
terminal over SSH, the command ``toasty`` is available.

In tunneled mode, the following sequence of events happens:

1. SSH is used to run a ``toasty view`` command on the target host to tile the
   requested data sets. Relevant flags such as ``-j`` / ``--parallelism`` are
   forwarded to the remote host.
2. SSH is used to run a ``wwtdatatool serve`` command on the target host,
   starting an HTTP-based data server.
3. A local SSH port forward is created so that the HTTP server can be accessed
   from the local machine.
4. A local web browser is launched with the proper setup to view the data via
   the port forward.
5. When the local command is stopped, the remote HTTP server is shut down, and
   the port forward is cancelled.

The remote HTTP server is set up in a way where it should shut down
automatically if the SSH connection is dropped for any reason.


See Also
========

- :ref:`cli-tile-study`
