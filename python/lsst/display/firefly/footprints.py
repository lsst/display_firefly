#
# LSST Data Management System
# Copyright 2018 LSST Corporation.
#
# This product includes software developed by the
# LSST Project (http://www.lsst.org/).
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the LSST License Statement and
# the GNU General Public License along with this program.  If not,
# see <http://www.lsstcorp.org/LegalNotices/>.
#

##
# @file
# @brief Support for LSST footprints, specific to Firefly

import numpy as np
import lsst.afw.geom as afwGeom
from firefly_client import plot


def record_selector(record, selection):
    """Select records from source catalog

    Parameters:
    -----------
    record : `lsst.afw.detect.SourceRecord`
        record to select
    selection : `str`
        'all' to select all records. 'parents' to select records with
        more than zero children. 'children' to select records with
        non-zero parents. 'isolated' to select records that are not blended,
        meaning zero parents and zero children.
        Values to check for sel
    """
    nChildren = record.get('deblend_nChild')
    parentId = record.getParent()
    if selection == 'all':
        return True
    elif selection == 'parents':
        return (nChildren > 0)
    elif selection == 'children':
        return (parentId > 0)
    elif selection == 'isolated':
        return ((parentId == 0) and (nChildren == 0))
    else:
        raise RuntimeError('invalid selection: {}'.format(selection))

def create_footprint_dict(catalog, selection='all', xy0 = afwGeom.Point2I(0,0),
                          pixelsys='zero-based'):
    """Create footprint structure from SourceCatalog

    Parameters:
    -----------
    catalog : `lsst.afw.table.SourceCatalog`
        Source catalog from which to generate footprints
    selection: `str`, default 'all'
        Include 'all', 'parents','children', or 'isolated' footprints
    xy0 : `lsst.afw.geom.Point2I`, default afwGeom.Point2I(0,0)
        Pixel origin to subtract off from the footprint coordinates
    pixelsys : `str`, default 'zero-based'
        Coordinate string to include in the dictionary / JSON

    Returns:
    --------
    `dict` : Dictionary to turn into JSON
    """
    x0, y0 = xy0
    footd = dict(pixelsys=pixelsys, feet=dict())
    for record in catalog:
        if record_selector(record, selection):
            footprint = record.getFootprint()
            footid = str(record.getId())
            fpbbox = footprint.getBBox()
            corners = [(c.getX()-x0,c.getY()-y0) for c in fpbbox.getCorners()]
            spans = footprint.getSpans()
            scoords = [(s.getY()-y0, s.getX0()-x0, s.getX1()-x0) for s in spans]
            peaks = footprint.getPeaks()
            pcoords = [(p.getFx()-x0, p.getFy()-y0) for p in peaks]
            footd['feet'][footid] = dict(corners=corners, spans=scoords, peaks=pcoords)
    return footd

def browse_sources(catalog, display, dataId, butler, bbox, image=True,
                   imageType='deepCoadd_calexp', footprints=True,
                   selection='all', reset_display=True):
    """browse sources from a catalog using Firefly

    Parameters:
    -----------
    catalog : `lsst.afw.table.SourceCatalog`
        Table of sources
    display : `lsst.afw.display.Display`
        Display using the Firefly backend
    dataId : `dict`
        Data ID used to retrieve the catalog, used for retrieving the image
    butler : `lsst.daf.persistence.Butler`
        Butler instance used to retrieve the catalog
    bbox : `lsst.afw.geom.Box2I`
        Bounding box for the catalog, image and the footprints
    image : `bool`
        If True (default), retrieve and display the subimage corresponding to
        the dataId and the bounding box
    imageType : `str`
        DatasetType for the image to retrieve from the butler instance, if
        image is True. '_sub' will be appended to retrieve a subimage.
    footprints: `bool`
        If True (default), overlay footprints from the catalog
    selection: `str`, default 'all'
        Include 'all', 'parents', 'children', or 'isolated' footprints
    reset_display: `bool`
        If True (default) and image is True, reset the display
    """
    fc = display._client

    if image:
        if reset_display:
            fc.reinit_viewer()
            fc.add_cell(row=2, col=0, width=4, height=2, element_type='tables',
                cell_id='main')
            fc.add_cell(row=0, col=0, width=2, height=3, element_type='images',
                cell_id='image-%s' % str(display.frame))
            fc.add_cell(row=0, col=2, width=2, height=3, element_type='xyPlots',
                cell_id='plots')
        calexp = butler.get(imageType + '_sub', bbox=bbox, dataId=dataId)
        # currently need to zero out the xy0 for overlay to work
        calexp.setXY0(afwGeom.Point2I(0,0))
        display.mtv(calexp)

    cat_select = np.array([(bbox.contains(afwGeom.Point2I(r.getX(), r.getY())) and
                            record_selector(r, selection))
                          for r in catalog])
    cat_subset = catalog.subset(cat_select)
    plot.upload_table(cat_subset, 'Sources_%s_%s' % (selection, str(display.frame)))

    if footprints:
        fpdata = create_footprint_dict(cat_subset, selection=selection,
                                       xy0=bbox.getBegin())
        fc.overlay_footprints(fpdata,
                              'catalog footprints %s %s' % (selection, str(display.frame)),
                              'footprints_%s_%s'%(selection,
                                        str(display.frame)))

