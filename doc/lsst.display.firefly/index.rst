.. py:currentmodule:: lsst.display.firefly

.. _lsst.display.firefly:

####################
lsst.display.firefly
####################

The ``lsst.display.firefly`` package provides a backend for the lsst.afw.display,
display abstraction, allowing the Firefly visualization framework to be used
for displaying data objects from the stack.

Firefly is a web framework for astronomical data access and visualization,
developed at Caltech/IPAC and deployed for the archives of several major
facilities including Spitzer, WISE, Plank and others. Firefly is a part
of the LSST Science Platform. Its client-server architecture is designed
to enable a user to easily visualize images and catalog data from a remote
site.

The ``lsst.display.firefly`` backend is a client that can connect to a Firefly
server and visualize data objects from an LSST stack session. It is best
used with a Python session and Firefly server that are both remote and
situated close to the data.

A user typically will not import ``lsst.display.firefly`` directly. Instead,
the ``lsst.afw.display`` interface will commonly be used with `backend=firefly`.
The Firefly backend is based upon the Python API in
:class:`firefly_client.FireflyClient`.

.. _lsst-display-firefly-using:

Using lsst.display.firefly
==========================

.. toctree::
    :maxdepth: 1

    getting-started-lsp
    defining-displays-lsp
    displaying-images
    interactive-tables-charts
    viewing-footprints
    using-firefly-standalone


.. _lsst-display-firefly-installing:


.. _lsst.display.firefly-contributing:

Contributing
============

``lsst.display.firefly`` is developed at https://github.com/lsst/display_firefly.
You can find Jira issues for this module under the
`display_firefly <https://jira.lsstcorp.org/issues/?jql=project%20%3D%20DM%20AND%20component%20%3D%20display_firefly>`_
component.

.. _lsst.display_firefly-pyapi:

.. Python API reference
.. ====================

.. .. automodapi:: lsst.display.firefly
..     :no-main-docstr
..     :no-inheritance-diagram:
