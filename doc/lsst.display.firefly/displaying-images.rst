
########################################
Displaying images and overlaying regions
########################################


Displaying an image
===================

Default display of an Exposure object
-------------------------------------

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

    display1.setMaskPlaneColor('DETECTED', afwDisplay.GREEN)
    display1.setMaskTransparency(30)
    display1.mtv(calexp)

Rescale or restretch the image pixels display
---------------------------------------------

You can rescale or restretch the display of the image pixels
wit the ``scale`` method.

.. code-block:: py
    :name: display-scale

    display1.scale('log', -1, 10, 'sigma')
    display1.scale('asinh', 'zscale')

These settings are "sticky", in the sense that they can be commanded before
an image is displayed, and they will apply to subsequent image displays
on that Display object.

Zooming and panning
-------------------

Use the ``pan`` method with pixel coordinates to center the image at a
new location. The ``zoom`` method can zoom and pan at the same time.

.. code-block:: py
    :name: zoom-pan

    display1.pan(1064, 890)
    display1.zoom(4)
    display1.zoom(2, 500, 800)

These settings are also "sticky" -- they can be issued before an image is
displayed.

Overlay regions
===============

Firefly support for overlaying regions enables symbols and lines to drawn
over an image.

When drawing many items it is best to use `display1.Buffering` to send them
to Firefly in one batch. A good example is drawing circles at the source
positions.

.. code-block:: py
    :name: display-many-dots

    with display1.Buffering():
        for record in src:
            display1.dot('o', record.getX(), record.getY(), size=20, ctype='orange')

You can draw lines, optionally with symbols. Here is how to draw a square.

.. code-block:: py

    display1.line([[100,100], [100,200], [200,200], [200,100], [100,100]], ctype='blue')

Erase the regions while leaving the image and masks displayed.

.. code-block:: py
    :name: region-erase

    display1.erase()

