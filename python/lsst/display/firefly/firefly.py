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
    _fireflyClient = None
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

class DisplayImpl(virtualDevice.DisplayImpl):
    """Device to talk to a firefly display"""

    @staticmethod
    def __handleCallbacks(event):
        if 'type' in event['data']:
            if event['data']['type']=='AREA_SELECT':
                print('*************area select')
                pParams= { 'URL' : 'http://web.ipac.caltech.edu/staff/roby/demo/wise-m51-band2.fits','ColorTable' : '9'}
                plotId = 3
                global _fireflyClient
                status= _fireflyClient.showFits(fileOnServer=None, plotId=plotId, additionalParams=pParams)


        print("RHL", event)
        return
        data = dict((_.split('=') for _ in event.get('data', {}).split('&')))
        if data.get('type') == "POINT":
            print("Event Received: %s" % data.get('id'))
            sys.stdout.flush()

    def __init__(self, display, verbose=False, host="localhost", port=8080, name="afw", *args, **kwargs):
        virtualDevice.DisplayImpl.__init__(self, display, verbose)

        if self.verbose:
            print("Opening firefly device %s" % (self.display.frame if self.display else "[None]"))

        global _fireflyClient
        if not _fireflyClient:
            try:
                _fireflyClient = FireflyClient.FireflyClient("%s:%d" % (host, port), name)
                _fireflyClient.launchBrowser()
                _fireflyClient.addListener(self.__handleCallbacks)
            except Exception as e:
                raise RuntimeError("Unable to connect to client: %s" % e)

        self._isBuffered = False
        self._regions = []
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
            _fireflyClient.removeRegion(self._regionLayerId) # plotId=self.display.frame
            self._regionLayerId = None

        with tempfile.TemporaryFile() as fd:
            displayLib.writeFitsImage(fd.fileno(), image, wcs, title)
            fd.flush()
            fd.seek(0, 0)

            self._fireflyFitsID = _fireflyClient.uploadFitsData(fd)
            self._additionalParams=dict(RangeValues=self.__getRangeString(),
                                        Title=title,
                                        )
            ret = _fireflyClient.showFits(self._fireflyFitsID, plotId=self.display.frame,
                                          additionalParams=self._additionalParams)

        if not ret["success"]:
            raise RuntimeError("Display failed")

    def _buffer(self, enable=True):
        """!Enable or disable buffering of writes to the display
        \param enable  True or False, as appropriate
        """
        self._isBuffered = enable

    def _flush(self):
        """!Flush any I/O buffers
        """
        if not self._regions:
            return
        
        if self.verbose:
            print("Flushing %d regions" % len(self._regions))

        self._regionLayerId = self._getRegionLayerId()
        _fireflyClient.overlayRegionData(self._regions, # plotId=self.display.frame,
                                         regionLayerId=self._regionLayerId)
        self._regions = []

    def _uploadTextData(self, regions):
        self._regions += regions
        
        if not self._isBuffered:
            self._flush()

    def _close(self):
        """Called when the device is closed"""
        if self.verbose:
            print("Closing firefly device %s" % (self.display.frame if self.display else "[None]"))
        _fireflyClient.disconnect()
        _fireflyClient.session.close()

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
        self._uploadTextData(ds9Regions.dot(symb, c, r, size, ctype, fontFamily, textAngle))

    def _drawLines(self, points, ctype):
        """Connect the points, a list of (col,row)
        Ctype is the name of a colour (e.g. 'red')"""

        self._uploadTextData(ds9Regions.drawLines(points, ctype))

    def _erase(self):
        """Erase the specified DS9 frame"""
        if self._regionLayerId:
            _fireflyClient.removeRegion(self._regionLayerId) # plotId=self.display.frame
            self._regionLayerId = None

    def _setCallback(self, what, func):
        if func != interface.noop_callback:
            status = _fireflyClient.addExtension('POINT' if False else 'AREA_SELECT', what,
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
            
        if False:
            if self._fireflyFitsID:
                _fireflyClient.showFits(self._fireflyFitsID, plotId=self.display.frame,
                                        additionalParams=self._additionalParams)
        else:
            if self.display:
                print("RHL stretch", self.display.frame, self.__getRangeString())
                _fireflyClient.stretch(self.display.frame, self.__getRangeString())

    def __getRangeString(self):
        if self._stretchMin == "zscale":
            return _fireflyClient.createRangeValuesZScale(
                self._stretchAlgorithm, zscaleContrast=25, zscaleSamples=600, zscaleSamplesPerLine=120)
        else:
            return _fireflyClient.createRangeValuesStandard(
                self._stretchAlgorithm, self._stretchUnit, self._stretchMin, self._stretchMax)

    def _show(self):
        """Show the requested window"""
        pass
    #
    # Zoom and Pan
    #
    def _zoom(self, zoomfac):
        """Zoom frame by specified amount"""

        _fireflyClient.zoom(plotId=self.display.frame, factor=zoomfac)

    def _pan(self, colc, rowc):
        _fireflyClient.pan(plotId=self.display.frame, x=colc, y=rowc)

            
