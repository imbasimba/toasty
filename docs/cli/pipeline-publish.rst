.. _cli-pipeline-publish:

===========================
``toasty pipeline publish``
===========================

The ``publish`` :ref:`pipeline command <pipeline>` publishes approved images to
the destination data store.


Usage
=====

.. code-block:: shell

   toasty pipeline publish [--workdir=WORKDIR]

The ``WORKDIR`` argument optionally specifies the location of the pipeline
workspace directory. The default is the current directory.


Notes
=====

In usual usage, this command will upload a bunch of image data to the cloud, so
it may take a while to run.

All images in the “approved” state will be uploaded. After publication, the
specified image data directories will be moved from the “approved” state to the
“published” state. This will only happen if the image uploads fully, so if the
command fails due to a transient network issue, you should just try rerunning
it.


See Also
========

- :ref:`The toasty pipeline processing overview <pipeline>`