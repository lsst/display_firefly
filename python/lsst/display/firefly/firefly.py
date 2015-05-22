#
# LSST Data Management System
# Copyright 2008, 2009, 2010, 2015 LSST Corporation.
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
## \file
## \brief Definitions to talk to firefly from python

from __future__ import absolute_import, division, print_function

import re
import sys
import tempfile
import cStringIO

import lsst.afw.display.interface as interface
import lsst.afw.display.virtualDevice as virtualDevice
import lsst.afw.display.ds9Regions as ds9Regions
import lsst.afw.display.displayLib as displayLib

try:
    import FireflyClient
except ImportError, e:
    print("Cannot import firefly: %s" % (e), file=sys.stderr)

class FireflyError(Exception):
    def __init__(self, str):
        Exception.__init__(self, str)

#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-

def fireflyVersion():
    """Return the version of firefly in use, as a string"""
    raise NotImplementedError("fireflyVersion")

#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-

def __handleCallbacks(event):
    return

    data = dict((_.split('=') for _ in event.get('data', {}).split('&')))
    if data.get('type') == "POINT":
        print("Event Received: %s" % data.get('id'))
        sys.stdout.flush()

try:
    self_client
except NameError:
    try:
        host="localhost"
        port=8080
        name="afw"

        self_client = FireflyClient.FireflyClient("%s:%d" % (host, port), name)
        self_client.launchBrowser()
        self_client.addListener(__handleCallbacks)
    except Exception as e:
        raise RuntimeError("Unable to connect to client: %s" % e)

class DisplayImpl(virtualDevice.DisplayImpl):
    """Device to talk to a firefly display"""

    def __init__(self, display, verbose=False, *args, **kwargs):
        virtualDevice.DisplayImpl.__init__(self, display, verbose)

        if self.verbose:
            print("Opening firefly device %s" % (self.display.frame if self.display else "[None]"))

        self._regionLayerId = None
        self._fireflyFitsID = None
        self._additionalParams = {}

        self._scale('Linear', 1, 99, 'Percent')

    def _getRegionLayerId(self):
        return "lsstRegions%s" % self.display.frame if self.display else "None"

    def _mtv(self, image, mask=None, wcs=None, title=""):
        """Display an Image and/or Mask on a Firefly display
        """

        if self._regionLayerId:
            self_client.removeRegion(self._regionLayerId) # clear overlays
            self._regionLayerId = None

        with tempfile.TemporaryFile() as fd:
            displayLib.writeFitsImage(fd.fileno(), image, wcs, title)
            fd.flush()
            fd.seek(0, 0)

            self._fireflyFitsID = self_client.uploadFitsData(fd)
            self._additionalParams=dict(RangeValues=self.__getRangeString(),
                                        Title=title,
                                        )
            ret = self_client.showFits(self._fireflyFitsID, plotID=self.display.frame,
                                       additionalParams=self._additionalParams)

        if not ret["success"]:
            raise RuntimeError("Display failed")

    def _uploadTextData(self, regions):
        self._regionLayerId = self._getRegionLayerId()
        self_client.overlayRegionData(regions, # plotID=self.display.frame,
                                      regionLayerId=self._regionLayerId)

    def _close(self):
        """Called when the device is closed"""
        if self.verbose:
            print("Closing firefly device %s" % (self.display.frame if self.display else "[None]"))
        self_client.disconnect()
        self_client.session.close()

    def _dot(self, symb, c, r, size, ctype, fontFamily="helvetica", textAngle=None):
        """Draw a symbol onto the specified DS9 frame at (col,row) = (c,r) [0-based coordinates]
    Possible values are:
            +                Draw a +
            x                Draw an x
            *                Draw a *
            o                Draw a circle
            @:Mxx,Mxy,Myy    Draw an ellipse with moments (Mxx, Mxy, Myy) (argument size is ignored)
            An object derived from afwGeom.ellipses.BaseCore Draw the ellipse (argument size is ignored)
    Any other value is interpreted as a string to be drawn. Strings obey the fontFamily (which may be extended
    with other characteristics, e.g. "times bold italic".  Text will be drawn rotated by textAngle (textAngle is
    ignored otherwise).

    N.b. objects derived from BaseCore include Axes and Quadrupole.
    """
        if False:                       # firefly doesn't (currently) default to image
            self._uploadTextData(ds9Regions.dot(symb, c, r, size, ctype, fontFamily, textAngle))
        else:
            regions = []
            for reg in ds9Regions.dot(symb, c, r, size, ctype, fontFamily, textAngle):
                regions.append(re.sub(r"(circle|line|point|text) ", r"image; \1 ", reg))

            self._uploadTextData(regions)

    def _drawLines(self, points, ctype):
        """Connect the points, a list of (col,row)
        Ctype is the name of a colour (e.g. 'red')"""

        if False:                       # firefly doesn't (currently) default to image
            self._uploadTextData(ds9Regions.drawLines(points, ctype))
        else:
            regions = []
            for reg in ds9Regions.drawLines(points, ctype):
                regions.append(re.sub(r"line ", r"image; line ", reg))

            self._uploadTextData(regions)

    def _erase(self):
        """Erase the specified DS9 frame"""
        if self._regionLayerId:
            self_client.removeRegion(self._regionLayerId)
            self._regionLayerId = None

    def _setCallback(self, what, func):
        status = self_client.addExtension('POINT', what,
                                          plotId=self.display.frame,
                                          extensionId=what)
        if not status['success']:
            pass

    def _getEvent(self):
        """Return an event generated by a keypress or mouse click
        """
        from interface import Event

        ev = Event("q")

        if self.verbose:
            print("virtual[%s]._getEvent() -> %s" % (self.display.frame, ev))

        return ev
    #
    # Set gray scale
    #
    def _scale(self, algorithm, min, max, unit=None, *args, **kwargs):
        stretchAlgorithms = ("Linear", "Log", "LogLog", "Equal", "Squared", "Sqrt")
        #
        # Normalise algorithm's case
        #
        if algorithm:
            algorithm = dict((a.lower(), a) for a in stretchAlgorithms).get(algorithm.lower(), algorithm)

            if not algorithm in stretchAlgorithms:
                raise FireflyError('Algorithm %s is invalid; please choose one of "%s"' %
                                   (algorithm, '", "'.join(stretchAlgorithms)))
            self._stretchAlgorithm = algorithm

        if min == "minmax":
            unit = "Percent"
            min, max = 0, 100
        elif min == "zscale":
            pass

        if not unit:
            unit = "Absolute"

        units = ("Percent", "Absolute", "Sigma")
        if not unit in units:
            raise FireflyError('Unit %s is invalid; please choose one of "%s"' % (unit, '", "'.join(units)))

        self._stretchMin = min
        self._stretchMax = max
        self._stretchUnit = unit

        self._additionalParams["RangeValues"] = self.__getRangeString()

        if self._fireflyFitsID:
            self_client.showFits(self._fireflyFitsID, plotID=self.display.frame,
                                 additionalParams=self._additionalParams)

    def __getRangeString(self):
        if self._stretchMin == "zscale":
            return self_client.createRangeValuesZScale(self._stretchAlgorithm,
                                           zscaleContrast=25, zscaleSamples=600, zscaleSamplesPerLine=120)
        else:
            return self_client.createRangeValuesStandard(self._stretchAlgorithm,
                                                     self._stretchUnit, self._stretchMin, self._stretchMax)

    def _show(self):
        """Show the requested window"""
        pass
    #
    # Zoom and Pan
    #
    def _zoom(self, zoomfac):
        """Zoom frame by specified amount"""

        self._additionalParams["InitType"] = "STANDARD"
        self._additionalParams["InitZoomLevel"] = zoomfac

        if self._fireflyFitsID:
            self_client.showFits(self._fireflyFitsID, plotID=self.display.frame,
                                 additionalParams=self._additionalParams)
