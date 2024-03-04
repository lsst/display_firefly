This page assumes you are working inside a notebook or console
in the LSST Science Platform. To use Firefly elsewhere, see
:ref:`the page on standalone use <lsst-display-firefly-standalone>`.

.. _lsst-display-firefly-getting-started:

#######################################################
Getting started with the Firefly backend for afwDisplay
#######################################################


Initialize a Display instance
=============================

Start a Firefly viewer tab by defining a Display.

.. code-block:: py
    :name: getting-started-init

    import lsst.afw.display as afwDisplay
    afwDisplay.setDefaultBackend('firefly')
    display1 = afwDisplay.Display(frame=1)

A Firefly tab opens showing a toolbar at the top, and "Firefly Ready"
in large letters in the center. You can drag the tab to the right
side of your Jupyterlab session to allow you to see notebooks and the
Firefly display side-by-side.

Retrieve and display an image
=============================

Retrieve a simulated LSST image.

.. code-block:: py
    :name: getting-started-getimage

    from lsst.daf.butler import Butler
    butler = Butler('/repo/main', collectiions='output_data_v2')
    dataId = {'physical_filter': 'r', 'raft': 'R01', 'name_in_raft': 'S01', 'visit': 235}
    calexp = butler.get('calexp', **dataId)

Set the scaling and mask transparency, and display the image.

.. code-block:: py
    :name: getting-started-showimage

    display1.scale("asinh", "zscale")
    display1.setMaskTransparency(90)
    display1.image(calexp)

Overlay symbols from a catalog
==============================

Retrieve a source catalog corresponding to the image.

.. code-block:: py
    :name: getting-started-fetch-catalog

    src = butler.get('src', **dataId)

Overlay non-interactive circles at the source positions.

.. code-block:: py
    :name: getting-started-regions

    with display1.Buffering():
        for record in src:
            display1.dot('o', record.getX(), record.getY(), size=20, ctype='orange')

Erase the regions while leaving the image and masks displayed.

.. code-block:: py
    :name: getting-started-erase

    display1.erase()
