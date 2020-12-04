.. _cli-pipeline-init:

========================
``toasty pipeline init``
========================

The ``init`` :ref:`pipeline command <pipeline>` creates a pipeline workspace.

Usage
=====

.. code-block:: shell

   toasty pipeline init
     [--azure-conn-env VARNAME]
     [--azure-container CONTAINERNAME]
     [--azure-path-prefix PREFIX]
     [--local PATH]
     [WORKDIR]

The ``WORKDIR`` argument is the name of a directory that will be created as the
pipeline workspace.

The ``--azure-*`` arguments configure the workspace to connect to an Azure
storage account for publishing data. The ``--local`` argument indicates that
“publishing” should happen by copying files elsewhere on the local filesystem.
One of these two storage options must be activated.

Examples
========

To set up a workspace connected to Azure storage:

.. code-block:: shell

   toasty pipeline init \
     --azure-conn-env=AZURE_STORAGE_CONNECTION_STRING \
     --azure-container=feeds \
     --azure-path-prefix=noirlab \
     workspace

After running this command, a new directory ``workspace`` will be created.

Note that the ``--azure-conn-env`` argument takes the *name of an environment
variable*. The *value* of *that* environment variable should then contain an
Azure storage “connection string”. This indirect approach avoids the security
issues that would happen if you just passed the the connection string directly
to the program.

To set up a workspace using local storage (likely for testing):

.. code-block:: shell

   toasty pipeline init \
     --local=/tmp/pipetest \
     testspace

In order for subsequent commands to work, you will need to place a
``toasty-pipeline-config.yaml`` file in the local directory (``/tmp/pipetest``
in this example).


Notes
=====

After initialization, the named ``WORKDIR`` directory will be created and will
contain a file name ``toasty-store-config.yaml`` that records the storage
configuration options used when this command is called. The next step is to
invoke the :ref:`cli-pipeline-refresh` command to query for candidate imags to
process.


See Also
========

- :ref:`The toasty pipeline processing overview <pipeline>`
- :ref:`cli-pipeline-refresh`
