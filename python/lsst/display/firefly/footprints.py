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

from copy import deepcopy
import io
import tempfile

import numpy as np
from astropy.io.votable.tree import VOTableFile, Resource, Field, Info
from astropy.io.votable import from_table
from astropy.table import Table, Column
import astropy.units as u

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


def create_footprints_table(catalog, xy0 = afwGeom.Point2I(0,0)):
    """make a VOTable of SourceData table and footprints

    Parameters:
    -----------
    dataId : `dict`
        Data ID used to retrieve the catalog, used for retrieving the image
    butler : `lsst.daf.persistence.Butler`
        Butler instance used to retrieve the catalog
    dataType : `str`
        DatasetType for the catalog to retrieve from the butler instance
    xy0 : `lsst.afw.geom.Point2I`, default afwGeom.Point2I(0,0)
        Pixel origin to subtract off from the footprint coordinates

    Returns:
    --------
    `astropy.io.votable.VOTableFile`
        VOTable object to upload to Firefly
    """
    with tempfile.NamedTemporaryFile() as fd:
        catalog.writeFits(fd.name)
        sourceTable = Table.read(fd.name, hdu=1)

    # Fix invalid unit strings of "seconds"
    sourceTable['modelfit_CModel_dev_time'].unit = u.s
    sourceTable['modelfit_CModel_initial_time'].unit = u.s
    sourceTable['modelfit_CModel_exp_time'].unit = u.s

    inputvofile = from_table(sourceTable)
    inputvotable = inputvofile.get_first_table()
    outtable = deepcopy(inputvotable)

    votablefile = VOTableFile()
    resource = Resource()
    votablefile.resources.append(resource)
    resource.tables.append(outtable)
    outtable.fields.insert(6, Field(votablefile, name='family_id', datatype='long', arraysize='1'))
    outtable.fields.insert(7, Field(votablefile, name='category', datatype='unicodeChar', arraysize='*'))
    for f in [
        Field(votablefile, name="spans", datatype="int", arraysize="*"),
        Field(votablefile, name="peaks", datatype="float", arraysize="*"),
        Field(votablefile, name='footprint_corner1_x', datatype="int", arraysize="1"),
        Field(votablefile, name='footprint_corner1_y', datatype="int", arraysize="1"),
        Field(votablefile, name='footprint_corner2_x', datatype="int", arraysize="1"),
        Field(votablefile, name='footprint_corner2_y', datatype="int", arraysize="1")]:
        outtable.fields.append(f)

    # This next step destroys the existing data
    outtable.create_arrays(nrows=len(sourceTable))

    x0, y0 = xy0
    spanlist = []
    peaklist = []
    familylist = []
    categorylist = []
    fpxll = []
    fpyll = []
    fpxur = []
    fpyur = []
    for record in catalog:
        footprint = record.getFootprint()
        recordid = record.getId()
        spans = footprint.getSpans()
        scoords = [(s.getY()-y0, s.getX0()-x0, s.getX1()-x0) for s in spans]
        fpbbox = footprint.getBBox()
        corners = [(c.getX()-x0,c.getY()-y0) for c in fpbbox.getCorners()]
        fpxll.append(corners[0][0])
        fpyll.append(corners[0][1])
        fpxur.append(corners[2][0])
        fpyur.append(corners[2][1])
        peaks = footprint.getPeaks()
        pcoords = [(p.getFx()-x0, p.getFy()-y0) for p in peaks]
        parentid = record.getParent()
        nchild = record.get('deblend_nChild')
        if (parentid == 0):
            familylist.append(recordid)
            if (nchild > 0):
                # blended parent
                categorylist.append('blended parent')
            else:
                # isolated
                categorylist.append('isolated')
        else:
            # deblended child
            familylist.append(parentid)
            categorylist.append('deblended child')
        spanlist.append(scoords)
        peaklist.append(pcoords)

    for i in range(len(inputvotable.array)):
        row = inputvotable.array[i]
        startlist = [row.item(0)[k] for k in range(len(row))]
        startlist.insert(6, familylist[i])
        startlist.insert(7, categorylist[i])
        startlist = startlist + [spanlist[i], peaklist[i],
                            fpxll[i], fpyll[i], fpxur[i], fpyur[i]]
        outtable.array[i] = tuple(startlist)

    outtable.infos.append(Info(name='contains_lsst_footprints', value='true'))
    outtable.infos.append(Info(name='contains_lsst_measurements', value='true'))

    outtable.format = 'tabledata'

    return(votablefile)

def browse_footprints(catalog, display, dataId, butler, bbox=None, image=True,
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
                cell_id='tables')
            fc.add_cell(row=0, col=0, width=2, height=3, element_type='images',
                cell_id='image-%s' % str(display.frame))
            fc.add_cell(row=0, col=2, width=2, height=3, element_type='xyPlots',
                cell_id='plots')
        if isinstance(bbox, afwGeom.Box2I):
            calexp = butler.get(imageType + '_sub', bbox=bbox, dataId=dataId)
        else:
            calexp = butler.get(imageType, dataId=dataId)
        # currently need to zero out the xy0 for overlay to work
        #calexp.setXY0(afwGeom.Point2I(0,0))
        display.mtv(calexp)

    if isinstance(bbox, afwGeom.Box2I):
        cat_select = np.array([(bbox.contains(afwGeom.Point2I(r.getX(), r.getY())) and
                            record_selector(r, selection))
                          for r in catalog])
        cat_subset = catalog.subset(cat_select)
    else:
        cat_subset = catalog

    if footprints:
        footprint_table = create_footprints_table(cat_subset)
        with tempfile.NamedTemporaryFile() as fd:
            footprint_table.to_xml(fd.name)
            tableval = display._client.upload_file(fd.name)
        fc.overlay_footprints(footprint_file=tableval,
                              title='catalog footprints %s %s' % (selection, str(display.frame)),
                              footprint_layer_id='footprints_%s_%s'%(selection,
                                        str(display.frame)),
                              plot_id=str(display.frame), color='rgba(74,144,226,0.30)')

