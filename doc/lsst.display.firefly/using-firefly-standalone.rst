This page assumes you are working standalone on your own laptop or desktop.
To get started using Firefly inside the LSST Science Platform,
see :ref:`Getting Started <lsst-display-firefly-getting-started>`.

.. _lsst-display-firefly-standalone:

#########################################
Using Firefly in a standalone environment
#########################################

Using ``lsst.display.firefly`` in a standalone environment, such as your
laptop or desktop, is a supported use case. This page lays out how to
use Docker to set up a fully functional environment to use the LSST
Science Pipelines together with Firefly on your own machine.

Installing a Docker image of Science Pipelines
==============================================

Instructions for using Docker images of the LSST Science Pipelines are
available on the `pipelines.lsst.io site <https://pipelines.lsst.io>`_.
These images contain the Science Pipelines software (known colloquially
as "the stack") but do not contain Jupyterlab or the Firefly extension
for Jupyterlab. This section shows how to install all these pieces
for the example of the sixth weekly build of 2019, assuming you have already
installed Docker and have it available on your machine.

First, change your directory to one that you want to mount inside your Docker
container. Then, install the weekly build, taking care to leave ports open for Jupyterlab
and optionally for other services.

.. code-block:: shell

    docker run -itd -p 9888:9888 -p 9889:9889 -p 9890:9890 -v `pwd`:/home/vagrant/mnt --name lsst_w_2019_06 lsstsqre/centos:7-stack-lsst_distrib-w_2019_06

You will be able to use `docker stop` and `docker start` together with the name
`lsst_w_2019_06` to start and stop your Science Pipelines container.

Second, in a terminal window on your machine, open a shell inside the container.

.. code-block:: shell

    docker exec -it lsst_w_2019_06 /bin/bash

From the container's shell, set up Science Pipelines which includes Python and
the `conda` distribution manager.

.. code-block:: shell

    source /opt/lsst/software/stack/loadLSST.bash
    setup lsst_distrib

This third step is needed only the first time you are setting up a Science
Pipelines container, to install Jupyterlab and the Firefly Jupyterlab
extension.

.. code-block:: shell

    conda install jupyterlab nodejs ipywidgets
    npm install —global babel-cli
    jupyter labextension install @jupyter-widgets/jupyterlab-manager
    jupyter labextension install jupyter_firefly_extensions
    pip install jupyter_firefly_extensions
    jupyter serverextension enable --py jupyter_firefly_extensions

Running a Docker image of Firefly
=================================

The commands in this section are run in a terminal on your machine, and not inside
the container's shell.

Start a Firefly server with 8 GB of memory on
port 8080:

.. code-block:: shell

    docker run -p 8080:8080 -e "MAX_JVM_SIZE=8G" --rm ipac/firefly:lsst-dev

In this case, the URL for Firefly will be `http://localhost:8080/firefly`.

Alternatively, to run it in the background on port 8090, saving logging information
to a file:

.. code-block:: shell

    docker run -p 8090:8080  -e "MAX_JVM_SIZE=8G" --rm ipac/firefly:lsst-dev >& my.log &

Useful Docker commands may be found `in this cheat sheet <https://github.com/wsargent/docker-cheat-sheet>`_.

Starting Jupyterlab
===================

The commands in this section are to be used in your container's shell.
-
For the Firefly Jupyter extension to work, you must set an environment variable or
edit a configuration file to indicate how to connect to your Firefly server.
To enable callbacks to work properly, it is recommended to find the network address
of your machine and use that to set the `FIREFLY_URL` environment variable. On
a Macintosh computer, that is found in System Preferences under Network.

.. code-block:: shell

    export FIREFLY_URL=http://10.8.12.110:8080/firefly

Typically you will want to start Jupyterlab from the directory that you mounted
inside your container, `/home/vagrant/mnt`.

.. code-block:: shell

    cd /home/vagrant/mnt
    jupyter lab --ip 0.0.0.0 --port 9888

Jupyterlab prints a long URL to copy and paste into a browser window on your
machine. Typically what is printed needs some editing to start with `127.0.0.1`.
After pointing your web browser to the Jupyterlab URL, your Jupyterlab session will
appear.

Removing the Firefly Jupyterlab extension
=========================================

The Firefly Jupyterlab extension has not been extensively tested with this standalone
setup with two Docker containers, one for the Science Pipelines and Jupyterlab, and
one for Firefly. You may find it desirable or even necessary to disable the extension
to use `lsst.display.firefly`. 

To disable and uninstall the extension, issue these commands in your Science
Platform container's shell.


.. code-block:: shell

    jupyter serverextension disable --py jupyter_firefly_extensions
    pip uninstall jupyter_firefly_extensions
    jupyter labextension uninstall jupyter_firefly_extensions

Listing installed extensions
============================

Inside your Science Pipeline container's shell, you can list the extensions
that are installed for Jupyterlab.

.. code-block:: shell

    jupyter labextension list
    jupyter serverextension list

The server extension list will also indicate whether the extension is enabled.

