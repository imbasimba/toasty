.. _cli-pipeline-approve:

===========================
``toasty pipeline approve``
===========================

The ``approve`` :ref:`pipeline command <pipeline>` marks one or more images
as ready for publication. It creates the ``index.wtml`` file for each image.


Usage
=====

.. code-block:: shell

   toasty pipeline approve [--workdir=WORKDIR] {IMAGE-IDs...}

The ``IMAGE-IDs`` argument specifies one or more images by their unique
identifiers.

The ``WORKDIR`` argument optionally specifies the location of the pipeline
workspace directory. The default is the current directory.


Example
=======

Before approving an image, it should be validated. First, check the astrometry
with the help of ``wwtdatatool`` command. To check a group of images all at once,
it can be convenient to merge the individual image files into a temporary index:

.. code-block:: shell

   wwtdatatool wtml merge processed/*/index_rel.wtml processed/index_rel.wtml
   wwtdatatool preview processed/index_rel.wtml

(Change the forward slashes to backslashes if you’re using Windows.) The first
command merges the individual image WTMLs into a new file,
``processed/index_rel.wtml``. The second command opens up this combined file in
the WWT webclient, running an internal webserver to make the data available.

Next, get a metadata report and check for any issues:

.. code-block:: shell

   wwtdatatool wtml report processed/noao0201b/index_rel.wtml

If everything is OK, you can mark the image as approved:

.. code-block:: shell

   toasty pipeline approve noao0201b

After approval of a batch of images, the next step is to :ref:`cli-pipeline-publish`.


Notes
=====

The specified images must be in the “processed” state.  That is, each image ID
specified must correspond to a directory inside the ``processed`` subfolder of
the pipeline workspace. After processing, the specified images will be moved to
the “approved” state.

The approval stage will create a ``index.wtml`` file in the data directory,
which will derive from the ``index_rel.wtml`` file but insert the final absolute
URLs paths to be used by the published data.


See Also
========

- :ref:`The toasty pipeline processing overview <pipeline>`
- :ref:`cli-pipeline-publish`
