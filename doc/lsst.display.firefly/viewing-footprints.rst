
########################################
Viewing LSST Source Detection Footprints
########################################

The Firefly backend for ``lsst.afw.display`` includes specialized functions
for overlaying and interacting with LSST Source Detection Footprints.

Here is an example using HSC-reprocessed data.

Define a Butler instance and an identifier for retrieving the data.

.. code-block:: py

    from lsst.daf.persistence import Butler
    butler = Butler('/datasets/hsc/repo/rerun/RC/w_2018_38/DM-15690/')
    dataId = dict(filter='HSC-R', tract=9813, patch='4,4')

Define bounding boxes for two regions of interest, one for the catalog and
a somewhat larger one for the image. Use these to retrieve a cutout of
the coadd image.

.. code-block:: py

    import lsst.afw.geom as afwGeom
    footprintsBbox = afwGeom.Box2I(corner=afwGeom.Point2I(16900, 18700),
                                   dimensions=afwGeom.Extent2I(600,600))
    imageBbox = afwGeom.Box2I(corner=afwGeom.Point2I(16800, 18600),
                              dimensions=afwGeom.Extent2I(800,800))
    calexp = butler.get('deepCoadd_calexp_sub', dataId=dataId, bbox=imageBbox)

Retrieve the entire catalog and then select only those records with pixel
locations inside the footprints bounding box.

.. code-block:: py

    measCat = butler.get('deepCoadd_meas', dataId=dataId)
    import numpy as np
    catSelect = np.array([footprintsBbox.contains(afwGeom.Point2I(r.getX(), r.getY()))
                       for r in measCat])
    catalogSubset = measCat.subset(catSelect)

Set up the Firefly display and display the image.

.. code-block:: py

    import lsst.afw.display as afwDisplay
    display1 = afwDisplay.Display(frame=1, backend='firefly')
    display1.setMaskTransparency(80)
    display1.scale('asinh', 10, 80, unit='percent', Q=6)
    display1.resetLayout()
    display1.mtv(calexp)

Overlay the footprints and show the accompanying table. Colors can be specified as
a name like "cyan" or "afwDisplay.RED"; as an rgb value such as "rgb(80,100,220";
or as rgb plus alpha (opacity) such as "rgba(74,144,226,0.60)".

.. code-block:: py

    display1.overlayFootprints(catalogSubset, color='rgba(74,144,226,0.50)',
                               highlightColor='yellow', selectColor='orange',
                               style='outline', layerString='detection footprints ',
                               titleString='catalog footprints ')

The `layerString` and `titleString` are concatenated with the frame, to make the
footprint drawing layer name and the table title, respectively. If multiple
footprint layers are desired, be sure to use different values of `layerString`.
