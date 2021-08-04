.. _cli-pipeline-ignore-rejects:

==================================
``toasty pipeline ignore-rejects``
==================================

The ``ignore-rejects`` :ref:`pipeline command <pipeline>` marks all of the
rejected images in a workspace to be ignored by future processing runs.


Usage
=====

.. code-block:: shell

   toasty pipeline ignore-rejects [--workdir=WORKDIR]

The ``WORKDIR`` argument optionally specifies the location of the pipeline
workspace directory. The default is the current directory.


Example
=======

Ignore every image in the ``rejects`` directory:

.. code-block:: shell

   toasty pipeline ignore-rejects

Subsequent invocations of :ref:`cli-pipeline-refresh` will ignore these images
when searching for new processing candidates.


Notes
=====

This command will ignore every image in the “reject” state.  That is, each file
inside the ``rejects`` subfolder of the pipeline workspace will be taken to be
an image ID that should be ignored. If you have rejects that should *not* be
permanently ignored (maybe you can't solve their coordinates right now, but will
be able to later), delete their files from the ``rejects`` subfolder before
running this command.


See Also
========

- :ref:`The toasty pipeline processing overview <pipeline>`
- :ref:`cli-pipeline-refresh`
