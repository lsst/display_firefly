.. currentmodule:: lsst.display.firefly

.. _display_firefly:

########################################################
lsst.display.firefly — visualization backend for Firefly
########################################################

`lsst.display.firefly` is a backend for the lsst.afw.display interface, allowing
the Firefly visualization framework to be used for displaying data objects
from the stack.

.. _lsst-display_firefly-intro

Introduction
============

.. _lsst-display-firefly-getting-started

Getting Started
===============

This short example uses data that has been run through the `LSST stack demo` _.

.. _LSST stack demo: https://pipelines.lsst.io/install/demo.html

At a shell prompt:

.. code-block:: shell
   :name: shell-setup

   setup obs_sdss
   setup display_firefly


Start a Python session of some kind.

.. code-block

.. _lsst-display-firefly-tutorials

Tutorials
=========

.. _lsst-display-firefly-using

Using lsst.display.firefly
==========================

.. _lsst-display-firefly-installing

Installing lsst.display.firefly
===============================

Since `display_firefly` is not yet included in the `lsst_distrib` set of stack
packages, this section outlines several installation scenarios.

.. _lsst-display_firefly-eups-distrib-install

Installing with eups distrib install
------------------------------------

To check for published distributions of `display_firefly`:

.. code-block:: shell
    :name: eups-distrib-list

    eups distrib list display_firefly -s https://sw.lsstcorp.org/eupspkg

This command will return the published versions of `display_firefly`, with
the third item displayed as the EUPS version. Provide that version to
`eups distrib install display_firefly`, e.g.:

.. code-block:: shell

    eups distrib install display_firefly master-g05bec400a4

The version may not be compatible with the version of the stack you are
using. This will be fixed when `display_firefly` is included in the
`lsst_distrib` distribution.


Developer installation from source code
---------------------------------------

Using lsstsw
^^^^^^^^^^^^

If using `lsstsw` to develop with the stack, simply rebuild the package:

.. code-block:: shell

   rebuild display_firefly

Note the build number that is output by the rebuild process, then:

.. code-block:: shell

    eups tags --clone bNNNN current


.. _lsst-display-firefly-servers

Firefly Servers
===============

.. _lsst-display-firefly-py-ref

Python API reference
====================

.. automodapi:: lsst.display.firefly

.. automodapi:: lsst.afw.display
:no-inheritance-diagram:

.. _Firefly: https://firefly.lsst.codes

.. _firefly_client: https://firefly_client.lsst.codes
