=================
Installing toasty
=================

Installing toasty with pip
==========================

You can also install the latest release of toasty using pip_::

  pip install toasty

.. _pip: https://pip.pypa.io/en/stable/


Dependencies
============

If you install toasty using pip_ as described above, any required dependencies
will get installed automatically. The `README in the Git repository`_ lists the
current dependencies if you would like to see an explict list.

.. _README in the Git repository: https://github.com/WorldWideTelescope/toasty/#readme


Installing the developer version
================================

If you want to use the very latest developer version, you should clone `this
repository <https://github.com/WorldWideTelescope/toasty/>`_ and manually
install the package in “editable” mode::

  git clone https://github.com/WorldWideTelescope/toasty.git
  cd toasty
  pip install -e .

You will need to have Numpy_ and Cython_ installed on order to build the extension
module that toasty uses to speed up its core operations.

.. _Numpy: https://cython.org/
.. _Cython: https://numpy.org/

You can run the test suite with the command::

  pytest toasty
