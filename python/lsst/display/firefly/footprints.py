# This file is part of {{ cookiecutter.package_name }}.
#
# Developed for the LSST Data Management System.
# This product includes software developed by the LSST Project
# (https://www.lsst.org).
# See the COPYRIGHT file at the top-level directory of this distribution
# for details of code ownership.
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
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

from copy import deepcopy
import tempfile

import numpy as np
from astropy.io.votable.tree import VOTableFile, Resource, Field, Info
from astropy.io.votable import from_table
from astropy.table import Table
import astropy.units as u

import lsst.afw.geom as afwGeom
import lsst.afw.table as afwTable


def recordSelector(record, selection):
    """Select records from source catalog

    Parameters:
    -----------
    record : `lsst.afw.detect.SourceRecord`
        record to select
    selection : `str`
        'all' to select all records. 'blended parents' to select records with
        more than zero children. 'deblended children' to select records with
        non-zero parents. 'isolated' to select records that are not blended,
        meaning zero parents and zero children.
        Values to check for sel
    """
    nChildren = record.get('deblend_nChild')
    parentId = record.getParent()
    if selection == 'all':
        return True
    elif selection == 'blended parents':
        return (nChildren > 0)
    elif selection == 'deblended children':
        return (parentId > 0)
    elif selection == 'isolated':
        return ((parentId == 0) and (nChildren == 0))
    else:
        raise RuntimeError('invalid selection: {}'.format(selection) +
                           '\nMust be one of "all", "blended parents", ' +
                           '"deblended children", "isolated"')


def createFootprintsTable(catalog, xy0=None,
                            insertColumn=6):
    """make a VOTable of SourceData table and footprints

    Parameters:
    -----------
    catalog : `lsst.afw.table.SourceCatalog`
            Source catalog from which to display footprints.
    xy0 : tuple or list or None
        Pixel origin to subtract off from the footprint coordinates.
        If None, the value used is (0,0)
    insertColumn : `int`
        Column at which to insert the "family_id" and "category" columns

    Returns:
    --------
    `astropy.io.votable.voTableFile`
        VOTable object to upload to Firefly
    """
    if xy0 is None:
        xy0 = afwGeom.Point2I(0, 0)

    _catalog = afwTable.SourceCatalog(catalog.table.clone())
    _catalog.extend(catalog, deep=True)
    sourceTable = _catalog.asAstropy()

    # Fix invalid unit strings of "seconds"
    # Ticket DM-16411 has been filed to fix this upstream
    for colName in ['modelfit_CModel_dev_time', 'modelfit_CModel_initial_time',
                     'modelfit_CModel_exp_time']:
        if colName in sourceTable.colnames:
            sourceTable[colName].unit = u.s

    # Change int64 dtypes so they convert to VOTable
    for colName in sourceTable.colnames:
        if sourceTable[colName].dtype.num == 9:
            sourceTable[colName].dtype = np.dtype('long')

    # Convert the astropy.table.Table to astropy.vo.voTableFile
    inputVoFile = from_table(sourceTable)
    # Extract first (only) table
    inputVoTable = inputVoFile.get_first_table()
    # Make a copy of the table, because adding columns will cause the data
    # to be destroyed, and we will have to copy the data back from the input
    outTable = deepcopy(inputVoTable)

    voTableFile = VOTableFile()
    resource = Resource()
    voTableFile.resources.append(resource)
    resource.tables.append(outTable)
    outTable.fields.insert(insertColumn, Field(voTableFile, name='family_id',
                                                datatype='long', arraysize='1'))
    outTable.fields.insert(insertColumn+1, Field(voTableFile, name='category',
                                                  datatype='unicodeChar', arraysize='*'))
    outTable.fields.extend([
        Field(voTableFile, name="spans", datatype="int", arraysize="*"),
        Field(voTableFile, name="peaks", datatype="float", arraysize="*"),
        Field(voTableFile, name='footprint_corner1_x', datatype="int", arraysize="1"),
        Field(voTableFile, name='footprint_corner1_y', datatype="int", arraysize="1"),
        Field(voTableFile, name='footprint_corner2_x', datatype="int", arraysize="1"),
        Field(voTableFile, name='footprint_corner2_y', datatype="int", arraysize="1")])

    # This next step destroys the existing data
    outTable.create_arrays(nrows=len(sourceTable))

    x0, y0 = xy0
    spanList = []
    peakList = []
    familyList = []
    categoryList = []
    fpxll = []
    fpyll = []
    fpxur = []
    fpyur = []
    for record in catalog:
        footprint = record.getFootprint()
        recordId = record.getId()
        spans = footprint.getSpans()
        scoords = [(s.getY()-y0, s.getX0()-x0, s.getX1()-x0) for s in spans]
        fpbbox = footprint.getBBox()
        corners = [(c.getX()-x0, c.getY()-y0) for c in fpbbox.getCorners()]
        fpxll.append(corners[0][0])
        fpyll.append(corners[0][1])
        fpxur.append(corners[2][0])
        fpyur.append(corners[2][1])
        peaks = footprint.getPeaks()
        pcoords = [(p.getFx()-x0, p.getFy()-y0) for p in peaks]
        parentId = record.getParent()
        nChild = record.get('deblend_nChild')
        if parentId == 0:
            familyList.append(recordId)
            if nChild > 0:
                # blended parent
                categoryList.append('blended parent')
            else:
                # isolated
                categoryList.append('isolated')
        else:
            # deblended child
            familyList.append(parentId)
            categoryList.append('deblended child')
        spanList.append(scoords)
        peakList.append(pcoords)

    for i, row in enumerate(inputVoTable.array):
        startList = [row.item(0)[k] for k in range(len(row))]
        startList.insert(insertColumn, familyList[i])
        startList.insert(insertColumn+1, categoryList[i])
        startList = startList + [spanList[i], peakList[i],
                                 fpxll[i], fpyll[i], fpxur[i], fpyur[i]]
        outTable.array[i] = tuple(startList)

    outTable.infos.append(Info(name='contains_lsst_footprints', value='true'))
    outTable.infos.append(Info(name='contains_lsst_measurements', value='true'))
    outTable.infos.append(Info(name='FootPrintColumnNames',
                               value='id;footprint_corner1_x;footprint_corner1_y;' +
                               'footprint_corner2_x;footprint_corner2_y;spans;peaks'))
    outTable.infos.append(Info(name='pixelsys', value='zero-based'))
    # Check whether the coordinates are included and are valid
    if (('coord_ra' in sourceTable.colnames) and
            ('coord_dec' in sourceTable.colnames) and
            np.isfinite(sourceTable['coord_ra']).any() and
            np.isfinite(sourceTable['coord_dec']).any()):
        coord_column_string = 'coord_rafla;coord_dec;EQ_J2000'
    elif (('base_SdssCentroid_x' in sourceTable.colnames) and
            ('base_SdssCentroid_y' in sourceTable.colnames) and
            np.isfinite(sourceTable['base_SdssCentroid_x']).any() and
            np.isfinite(sourceTable['base_SdssCentroid_y']).any()):
        coord_column_string = 'base_SdssCentroid_x;base_SdssCentroid_y;ZERO_BASED'
    elif (('base_NaiveCentroid_x' in sourceTable.colnames) and
            ('base_NaiveCentroid_y' in sourceTable.colnames) and
            np.isfinite(sourceTable['base_NaiveCentroid_x']).any() and
            np.isfinite(sourceTable['base_NaiveCentroid_y']).any()):
        coord_column_string = 'base_NaiveCentroid_x;base_NaiveCentroid_y;ZERO-BASED'
    else:
        raise RuntimeError('No valid coordinate columns in catalog')
    outTable.infos.append(Info(name='CatalogCoordColumns',
                               value=coord_column_string))

    outTable.format = 'tabledata'

    return(voTableFile)
