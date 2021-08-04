.. _cli-pipeline-refresh:

===========================
``toasty pipeline refresh``
===========================

The ``refresh`` :ref:`pipeline command <pipeline>` connects to the data source
and fetches information about candidate images that are potentially available
for processing.


Usage
=====

.. code-block:: shell

   toasty pipeline refresh [--workdir=WORKDIR]

The ``WORKDIR`` argument optionally specifie the location of the pipeline
workspace directory. The default is the current directory.


Notes
=====

The configuration for connecting to the data source must be already set up. See
:ref:`the toasty pipeline processing overview <pipeline>`.

The command will print out a report of what it discovered. For each candidate
image, a file will be created in the ``candidates`` subdirectory. The next step
is to select candidates for processing and download them using
:ref:`cli-pipeline-fetch`.

If there are candidates that should *never* be processed, they can be marked to
be ignored by subsequent refreshes. Currently you can only do this with images
that are rejected during processing, using :ref:`cli-pipeline-ignore-rejects`.


See Also
========

- :ref:`The toasty pipeline processing overview <pipeline>`
- :ref:`cli-pipeline-fetch`
- :ref:`cli-pipeline-ignore-rejects`
