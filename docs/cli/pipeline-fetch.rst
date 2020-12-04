.. _cli-pipeline-fetch:

=========================
``toasty pipeline fetch``
=========================

The ``fetch`` :ref:`pipeline command <pipeline>` selects and downloads candidate
images for pipeline processing.


Usage
=====

.. code-block:: shell

   toasty pipeline fetch [--workdir=WORKDIR] {IMAGE-IDs...}

The ``IMAGE-IDs`` argument specifies one or more images by their unique
identifiers.

The ``WORKDIR`` argument optionally specifies the location of the pipeline
workspace directory. The default is the current directory.


Example
=======

Fetch two images:

.. code-block:: shell

   toasty pipeline fetch noao0201b noao0210a

After fetching, the next step is to :ref:`cli-pipeline-process-todos`.


Notes
=====

Candidate names may be found by looking at the filenames contained in the
``candidates`` subdirectory of your workspace.

For each candidate that is successfully fetched, a sub-subdirectory is created
in the ``cache_todo`` subdirectory with a name corresponding to the unique
candidate ID.


See Also
========

- :ref:`The toasty pipeline processing overview <pipeline>`
- :ref:`cli-pipeline-process-todos`
