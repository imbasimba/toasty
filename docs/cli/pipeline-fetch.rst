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
identifiers. You can specify exact ID’s, or `glob patterns`_ as processed by the
Python ``fnmatch`` module. See examples below.

.. _glob patterns: https://docs.python.org/3/library/fnmatch.html#module-fnmatch

The ``WORKDIR`` argument optionally specifies the location of the pipeline
workspace directory. The default is the current directory.


Example
=======

Fetch two images:

.. code-block:: shell

   toasty pipeline fetch noao0201b noao0210a

After fetching, the next step is to :ref:`cli-pipeline-process-todos`.


Example
=======

You can use `glob patterns`_ to match candidate names. For instance,

.. code-block:: shell

   toasty pipeline fetch "rubin-*" "soar?"

will match every candidate whose name begins with ``rubin-``,  as well as those
whose names are exactly five letters long and start with ``soar``. You generally
must make sure to encase glob arguments in quotation marks, as shown above, to
prevent your shell from attempting to process them before Toasty gets a chance
to.


Notes
=====

Candidate names may be found by looking at the filenames contained in the
``candidates`` subdirectory of your workspace.

During the fetch process, the candidates are analyzed. Some of them may be
deemed “not actionable” — a common reason being that an image may not have
sufficient astrometric information attached for it to be placed on the sky as
WWT requires. Such candidates will be discarded, with their information files
moved into the ``rejects`` subdirectory.

For each candidate that is successfully fetched and validated, a
sub-subdirectory is created in the ``cache_todo`` subdirectory with a name
corresponding to the unique candidate ID.


See Also
========

- :ref:`The toasty pipeline processing overview <pipeline>`
- :ref:`cli-pipeline-process-todos`
