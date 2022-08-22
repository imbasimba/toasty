.. _cli-show-version-doi:

===========================
``toasty show version-doi``
===========================

The ``show version-doi`` command prints the `DOI`_ associated with
the current version of the Toasty software package.

.. _DOI: https://help.zenodo.org/

Usage
=====

.. code-block:: shell

   toasty show version-doi

Prints out the DOI of the current version of Toasty.

Notes
=====

While the version DOI in and of itself does not provide any information that
isn’t already provided more clearly by the :ref:`cli-show-version` command, the
version DOI can be used to properly cite your use of the Toasty software in an
academic context.

While each release of Toasty has its own version DOI, all releases of toasty
share the same “concept DOI”, which can be obtained with the
:ref:`cli-show-concept-doi` command. Unless you specifically know that you need the
concept DOI for a particular application, you should use the version DOI.


See Also
========

- :ref:`cli-show-concept-doi`
- :ref:`cli-show-version`
