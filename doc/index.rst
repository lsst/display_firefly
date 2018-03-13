.. currentmodule:: lsst.display.firefly

.. default-domain:: py

.. _display_firefly:

########################################################
lsst.display.firefly — visualization backend for Firefly
########################################################

`lsst.display.firefly` is a backend for the `lsst.afw.display` interface, allowing
the Firefly visualization framework to be used for displaying data objects
from the stack.

.. _lsst-display_firefly-intro:

Introduction
============

Firefly is a web framework for astronomical data access and visualization,
developed at Caltech/IPAC and deployed for the archives of several major
facilities including Spitzer, WISE, Plank and others. Firefly is a part
of the LSST Science User Platform. Its client-server architecture is designed
to enable a user to easily visualize images and catalog data from a remote
site.

The `lsst.display.firefly` backend is a client that can connect to a Firefly
server and visualize data objects from an LSST stack session. It is best
used with a Python session and Firefly server that are both remote and
situated close to the data.

A user typically will not import `lsst.display.firefly` directly. Instead,
the `lsst.afw.display` interface will commonly be used with `backend=firefly`.

.. _lsst-display-firefly-getting-started:

Getting Started
===============

This short example uses data that has been run through the
`LSST stack demo <https://pipelines.lsst.io/install/demo.html>`_.


At a shell prompt:

.. code-block:: shell
   :name: gs-shell-setup

   setup obs_sdss
   setup display_firefly


Start a Python session of some kind in the directory where the demo was run.
Then these statements will create a Butler instance for the processed data
and then retrieve an exposure.

.. code-block:: py
   :name: gs-butler-get

   from lsst.daf.persistence import Butler
   butler = Butler('./output')
   calexp = butler.get('calexp', run=4192, camcol=4, field=300, filter='g')

The next lines will set up the display, using a public Firefly server.

.. code-block:: py
   :name: gs-setup-display

   import lsst.afw.display as afw_display
   afw_display.setDefaultBackend('lsst.display.firefly')
   display1 = afw_display.getDisplay(frame=1,
      host='https://lsst-demo.ncsa.illinois.edu',
      name='mychannel')

Open a browser window to
`http://lsst-demo.ncsa.illinois.edu/firefly?__wsch=mychannel <http://lsst-demo.ncsa.illinois.edu/firefly?__wsch=mychannel>`_.
Then display the exposure:

.. code-block:: py
   :name: gs-display-calexp

   display1.mtv(calexp)

The displayed exposure will appear in your browser.

Subsequent displays can be opened more simply:

.. code-block:: py
   :name: gs-additional-display

   display2 = afw_display.getDisplay(frame=2)

.. _lsst-display-firefly-using:

Using lsst.display.firefly
==========================

The `lsst.display.firefly` package is not used directly. Instead, instances
of `lsst.afw.display` are created with parameters passed to the backend.
The Firefly backend is based upon the Python API in
:class:`firefly_client.FireflyClient`.

Setup
-----

Before a Python session or Jupyter notebook is started, setup of stack
packages must be completed. Use :command:`setup display_firefly` to enable
the Firefly backend.

Initializing with lsst.afw.display
----------------------------------

The recommended way to create a display object for Firefly is using
the :meth:`getDisplay` method from `lsst.afw.display`:

.. code-block:: py
    :name: construct-display

    import lsst.afw.display as afw_display
    afw_display.setDefaultBackend('lsst.display.firefly')
    display1 = afw_display.getDisplay(frame=1, host='http://localhost:8080',
                                   basedir='firefly', name='afw')

The parameters shown above (besides ``frame``) are the defaults and will
apply when running a Firefly server locally with default settings.

If a Firefly server has been provided to you, set ``host`` and
``basedir`` according to the information provided. You should set ``name``
to a unique string to avoid another user from writing to your display.

.. warning::

   Once a :class:`Display` instance is made, within your Python session
   it will not be possible to define another display pointing to a different
   server.

Opening a browser window
------------------------

A browser window or tab must be opened before any data are displayed.

When using a Firefly server on ``localhost``, creating the display object
will cause a browser window to open to the correct location. If using
another server (as in the above example), the ``display1.show()`` method
opens the browser window, if your Python session is on your local machine.

When running a remote Python session, or one inside a container, you will
need to
open a browser window or tab on your local machine yourself. For example,
for ``host=http://lsst-dev:8085``, ``basedir=firefly``, ``name=mine``,
use the url ``http://lsst-dev:8085/firefly?__wsch=mine``.


Displaying an image
-------------------

The :meth:`mtv` method of your display is used to display Exposures,
MaskedImages and Images from the stack. Assuming that your session
includes an Exposure named ``calexp``:

.. code-block:: py
    :name: display-mtv

    display1.mtv(calexp)

Mask display and manipulation
-----------------------------

If the data object passed to :meth:`mtv` contains masks, these will
automatically be overlaid on the image. A layer control icon at the
top of the browser window can be used to turn mask layers on and off.

The :meth:`display1.setMaskPlaneColor` and
:meth:`display1.setMaskTransparency` methods can be used to programmatically
change the mask display. :meth:`display1.setMaskPlaneColor` must be used before
the image is displayed, while the transparency may be changed at any time.

.. code-block:: py
    :name: mask-manipulation

    display1.setMaskPlaneColor('DETECTED', afw_display.GREEN)
    display1.mtv(calexp)
    display1.setMaskTransparency(30)

Image scale, zoom, pan
----------------------

The ``display1`` object includes methods for setting the image scale or
stretch, the zoom and the pan position.

.. code-block:: py
    :name: scale-zoom-pan

    display1.scale('log', -1, 10, 'sigma')
    display1.zoom(4)
    display1.pan(1064, 890)

Overlaying symbols
------------------

The :meth:`display1.dot` method will overlay a symbol at a point.

.. code-block:: py
    :name: ff-dot

    display1.dot('x', 1064, 890, size=8, ctype=afw_display.RED)


.. _lsst-display-firefly-installing:

Installing lsst.display.firefly
===============================

Now that `display_firefly` is included in the `lsst_distrib` set of stack
packages, the `setup lsst_distrib` command will set up this package and
its dependecies. See methods for installing `lsst_distrib` at
`pipelines.lsst.io <https://pipelines.lsst.io>`_.

.. _lsst-display-firefly-servers:

Firefly Servers
===============

Ideally, a Firefly server sitting close to your data and your Python workspace
will have been provided to you. In some cases you may want to run your own
Firefly server.

Firefly server using Docker
---------------------------

With Docker installed, you can start a Firefly server with 8 GB of memory on
port 8080:

.. code-block:: shell

    docker run -p 8080:8080 -e "MAX_JVM_SIZE=8G" --rm ipac/firefly

To run it on port 8090, in the background and saving logging information
to a file:

.. code-block:: shell

    docker run -p 8090:8080  -e "MAX_JVM_SIZE=8G" --rm ipac/firefly >& my.log &

Useful Docker commands may be found `in this cheat sheet <https://github.com/wsargent/docker-cheat-sheet>`_.

Standalone Firefly using Java
-----------------------------

A Firefly server may be run from a single file using Java 8.

- Point your web browser to the Firefly release page at
  `https://github.com/Caltech-IPAC/firefly/releases <https://github.com/Caltech-IPAC/firefly/releases>`_

- Download the latest ``firefly-exec.war``

- Start Firefly with :command:`java -jar firefly-exec.war`

   - Use option ``-httpPort 9080`` to run on port 9080 instead of the
     default 8080
   - Use option ``-extractDirectory <dirname>`` to extract the contents to a
     different directory instead of the default ``./extract``
   - On Mac OS X, it may be necessary to add the option
     ``-Djava.net.preferIPv4Stack=true``. If using this server locally, you
     may need to use host ``127.0.0.1`` instead of ``localhost``



.. .. _lsst-display-firefly-py-ref:

.. Python API reference
.. ====================

.. .. automodapi:: lsst.display.firefly
..      :no-inheritance-diagram:
