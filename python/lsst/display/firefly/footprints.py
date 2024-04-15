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


import numpy as np
from astropy.io.votable.tree import Info
from astropy.io.votable import from_table
from astropy.table import Column

import lsst.geom as geom
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


def createFootprintsTable(catalog, xy0=None, insertColumn=4):
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
        xy0 = geom.Point2I(0, 0)

    _catalog = afwTable.SourceCatalog(catalog.table.clone())
    _catalog.extend(catalog, deep=True)
    sourceTable = _catalog.asAstropy()

    # Change int64 dtypes so they convert to VOTable
    for colName in sourceTable.colnames:
        if sourceTable[colName].dtype.num == 9:
            sourceTable[colName].dtype = np.dtype('long')

    inputColumnNames = sourceTable.colnames

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
        scoords = np.array(scoords).flatten()
        scoords = np.ma.MaskedArray(scoords, mask=np.zeros(len(scoords),
                                                           dtype=np.bool))
        fpbbox = footprint.getBBox()
        corners = [(c.getX()-x0, c.getY()-y0) for c in fpbbox.getCorners()]
        fpxll.append(corners[0][0])
        fpyll.append(corners[0][1])
        fpxur.append(corners[2][0])
        fpyur.append(corners[2][1])
        peaks = footprint.getPeaks()
        pcoords = [(p.getFx()-x0, p.getFy()-y0) for p in peaks]
        pcoords = np.array(pcoords).flatten()
        pcoords = np.ma.MaskedArray(pcoords, mask=np.zeros(len(pcoords),
                                                           dtype=np.bool))
        fpbbox = footprint.getBBox()
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

    sourceTable.add_column(Column(np.array(familyList)),
                           name='family_id',
                           index=insertColumn)
    sourceTable.add_column(Column(np.array(categoryList)),
                           name='category',
                           index=insertColumn+1)
    sourceTable.add_column(Column(np.array(spanList)), name='spans')
    sourceTable.add_column(Column(np.array(peakList)), name='peaks')
    sourceTable.add_column(Column(np.array(fpxll)), name='footprint_corner1_x')
    sourceTable.add_column(Column(np.array(fpyll)), name='footprint_corner1_y')
    sourceTable.add_column(Column(np.array(fpxur)), name='footprint_corner2_x')
    sourceTable.add_column(Column(np.array(fpyur)), name='footprint_corner2_y')

    outputVO = from_table(sourceTable)
    outTable = outputVO.get_first_table()

    outTable.infos.append(Info(name='contains_lsst_footprints', value='true'))
    outTable.infos.append(Info(name='contains_lsst_measurements', value='true'))
    outTable.infos.append(Info(name='FootPrintColumnNames',
                               value='id;footprint_corner1_x;footprint_corner1_y;' +
                               'footprint_corner2_x;footprint_corner2_y;spans;peaks'))
    outTable.infos.append(Info(name='pixelsys', value='zero-based'))
    # Check whether the coordinates are included and are valid
    if (('slot_Centroid_x' in inputColumnNames) and
            ('slot_Centroid_y' in inputColumnNames) and
            np.isfinite(outTable.array['slot_Centroid_x']).any() and
            np.isfinite(outTable.array['slot_Centroid_y']).any()):
        coord_column_string = 'slot_Centroid_x;slot_Centroid_y;ZERO_BASED'
    elif (('coord_ra' in inputColumnNames) and
            ('coord_dec' in inputColumnNames) and
            np.isfinite(outTable.array['coord_ra']).any() and
            np.isfinite(outTable.array['coord_dec']).any()):
        coord_column_string = 'coord_ra;coord_dec;EQ_J2000'
    elif (('base_SdssCentroid_x' in inputColumnNames) and
            ('base_SdssCentroid_y' in inputColumnNames) and
            np.isfinite(outTable.array['base_SdssCentroid_x']).any() and
            np.isfinite(outTable.array['base_SdssCentroid_y']).any()):
        coord_column_string = 'base_SdssCentroid_x;base_SdssCentroid_y;ZERO_BASED'
    else:
        raise RuntimeError('No valid coordinate columns in catalog')
    outTable.infos.append(Info(name='CatalogCoordColumns',
                               value=coord_column_string))

    for f in outTable.fields:
        if f.datatype == 'bit':
            f.datatype = 'boolean'

    outTable._config['version_1_3_or_later'] = True
    outputVO.set_all_tables_format('binary2')

    return outputVO
