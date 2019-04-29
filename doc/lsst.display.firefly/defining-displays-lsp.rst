
This page assumes you are working inside a notebook or console
in the LSST Science Platform. To use Firefly elsewhere, see
:ref:`the page on standalone use <lsst-display-firefly-standalone>`.

##############################################
Defining Displays in the LSST Science Platform
##############################################


You must have a viewer tab or window open before sending commands to
render images, tables or charts.

Defining a Display with default settings
========================================

To initialize a Firefly display, define a Display object with the
``lsst.afw.display`` interface.

.. code-block:: py
    :name: construct-display

    import lsst.afw.display as afwDisplay
    afwDisplay.setDefaultBackend('firefly')
    display1 = afwDisplay.Display(frame=1)

A Firefly tab opens showing a toolbar at the top, and "Firefly Ready"
in large letters in the center. You can drag the tab to the right
side of your Jupyterlab session to allow you to see notebooks and the
Firefly display side-by-side.

Defining subsequent displays
============================

You can create additional Display objects by specifying a different value
of the ``frame`` parameter. The subsequent displays will not open a tab;
they will display to the same one created

Making a display tab reopen after closing it
============================================

If you have closed your Firefly tab, you can bring it back with

.. code-block:: py

    display1.show()

Reinitializing a display tab
============================

You can reinitialize a Firefly viewer tab with

.. code-block:: py

    display1.clearViewer()

This command is specific to the Firefly backend of the afwDisplay framework.

Defining a Display to open a browser tab
========================================

The first time that a Display object is instantiated in your Python or notebook
session, you can specify that a browser tab be opened. You will need to allow
pop-ups for the science platform site.

.. code-block:: py

    import lsst.afw.display as afwDisplay
    afwDisplay.setDefaultBackend('firefly')
    display1 = afwDisplay.Display(frame=1)


Displaying a clickable link
===========================

A more reliable method of opening another browser tab or window is to display
a clickable link to the Firefly viewer.

.. code-block:: py

    display1.getClient().display_url()

Click on the link to bring up a browser tab or window. Your browser or system
settings determine whether the link brings up a tab, or a window.


Authorizing a Display
=====================

When working inside the LSST Science Platform with default settings,
authorization of the connection to the Firefly server will be handled
automatically. If you encounter a need to pass a token for authorization,
you can pass it to the first Display instance you create, with
the ``token=`` keyword parameter.

Embedding the Firefly viewer in a notebook
==========================================

The Firefly tab or browser tab options are the recommended ways to bring up
the Firefly viewer. That said, you can embed the Firefly viewer in the output
of a notebook cell.

Using the SlateWidget
---------------------

.. code-block:: py

    from ipywidgets import Layout
    from jupyter_firefly_extensions import SlateWidget
    slate= SlateWidget(layout=Layout(width='1100px', height='700px'))
    slate._render_tree_id = display1.getClient().render_tree_id
    slate

The SlateWidget appears in the output part of the cell and is ready to 
receive display commands from ``display1``.

Using an IFrame
---------------

.. code-block:: py

    from IPython.display import IFrame
    IFrame(display1.getClient().get_firefly_url(), 1100, 700)

The Firefly viewer appears in the output part of the cell.


