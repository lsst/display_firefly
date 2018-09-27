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

def create_footprint_dict(catalog, contents='all', xy0 = afwGeom.Point2I(0,0),
                          pixelsys='zero-based'):
    """Create footprint structure from SourceCatalog

    Parameters:
    -----------
    catalog : `lsst.afw.table.SourceCatalog`
        Source catalog from which to generate footprints
    contents: `str`, default 'all'
        Include 'all', 'parents', or 'children' footprints
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
    def selector(x, contents):
        if contents == 'all':
            return True
        elif contents == 'parents':
            return (x > 0)
        elif contents == 'children':
            return (x == 0)
        else:
            raise RuntimeError('invalid contents: {}'.format(contents))
    for record in scarletCat:
        if selector(record.get('deblend_nChild')):
            footprint = record.getFootprint()
            footid = str(footprint.getId())
            spans = footprint.getSpans()
            scoords = [(s.getY()-y0, s.getX0()-x0, s.getX1()-x0) for s in spans]
            peaks = footprint.getPeaks()
            pcoords = [(p.getFx()-x0, p.getFy()-y0) for p in peaks]
            footd['feet'][footid] = dict(corners=corners, spans=scoords, peaks=pcoords)
    return footd

