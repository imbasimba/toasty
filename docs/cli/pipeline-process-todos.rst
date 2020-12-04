.. _cli-pipeline-process-todos:

=================================
``toasty pipeline process-todos``
=================================

The ``process-todos`` :ref:`pipeline command <pipeline>` processes images into
WWT’s data formats.


Usage
=====

.. code-block:: shell

   toasty pipeline process-todos [--workdir=WORKDIR]

The ``WORKDIR`` argument optionally specifies the location of the pipeline
workspace directory. The default is the current directory.


Example
=======

Process every image in the ``cache_todo`` directory:

.. code-block:: shell

   toasty pipeline process-todos

After processing, the next step is to review the results, correct any issues,
and eventually :ref:`cli-pipeline-approve`.


Notes
=====

The specified images must be in the “cache-todo” state.  That is, each image ID
specified must correspond to a directory inside the ``cache_todo`` subfolder of
the pipeline workspace. After successful procesing, the *source* image data will
be moved to the ``cache_done`` directory, and the processed data will be
populated inside a subfolder of the ``processed`` directory. So, to *reprocess*
an image, all you have to do is move its data folder from the ``cache_done``
directory back to ``cache_todo``.

The intention is that pipeline processing can be almost entirely automated, such
that this command doesn’t need arguments.


See Also
========

- :ref:`The toasty pipeline processing overview <pipeline>`
- :ref:`cli-pipeline-approve`
