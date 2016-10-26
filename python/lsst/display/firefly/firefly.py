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
from past.builtins import long

import re
import sys
import tempfile

import lsst.afw.display.interface as interface
import lsst.afw.display.virtualDevice as virtualDevice
import lsst.afw.display.ds9Regions as ds9Regions
import lsst.afw.image as afwImage
import lsst.afw.math as afwMath

try:
    import firefly_client
    _fireflyClient = None
except ImportError as e:
    print("Cannot import firefly_client: %s" % (e), file=sys.stderr)


class FireflyError(Exception):

    def __init__(self, str):
        Exception.__init__(self, str)

#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-


def firefly_version():
    """Return the version of firefly in use, as a string"""
    raise NotImplementedError("firefly_version")

#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-


class DisplayImpl(virtualDevice.DisplayImpl):
    """Device to talk to a firefly display"""

    @staticmethod
    def __handleCallbacks(event):
        if 'type' in event['data']:
            if event['data']['type'] == 'AREA_SELECT':
                print('*************area select')
                pParams = {'URL': 'http://web.ipac.caltech.edu/staff/roby/demo/wise-m51-band2.fits',
                           'ColorTable': '9'}
                plot_id = 3
                global _fireflyClient
                _fireflyClient.show_fits(fileOnServer=None, plot_id=plot_id, additionalParams=pParams)

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
                _fireflyClient = firefly_client.FireflyClient("%s:%d" % (host, port), name)
                _fireflyClient.launch_browser()
                _fireflyClient.add_listener(self.__handleCallbacks)
            except Exception as e:
                raise RuntimeError("Unable to connect to client: %s" % e)

        self._isBuffered = False
        self._regions = []
        self._regionLayerId = None
        self._fireflyFitsID = None
        self._maskIds = []

        #self._scale('linear', 1, 99, 'percent')

    def _getRegionLayerId(self):
        return "lsstRegions%s" % self.display.frame if self.display else "None"

    def _mtv(self, image, mask=None, wcs=None, title=""):
        """Display an Image and/or Mask on a Firefly display
        """

        if re.search("ImageF", repr(image)):
            mskimg = afwImage.MaskedImageF(image, mask)
            exp = afwImage.ExposureF(mskimg, wcs)
        elif re.search("ImageU", repr(image)):
            mskimg = afwImage.MaskedImageU(image, mask)
            exp = afwImage.ExposureF(mskimg, wcs)
        elif re.search("ImageD", repr(image)):
            mskimg = afwImage.MaskedImageD(image, mask)
            exp = afwImage.ExposureF(mskimg, wcs)
        elif re.search("ImageI", repr(image)):
            mskimg = afwImage.MaskedImageI(image, mask)
            exp = afwImage.ExposureF(mskimg, wcs)
        elif re.search("ImageL", repr(image)):
            mskimg = afwImage.MaskedImageL(image, mask)
            exp = afwImage.ExposureF(mskimg, wcs)
        else:
            raise RuntimeError("Unknown image type")

        if title == "":
            title=str(self.display.frame)
        if image:
            self._erase()

            with tempfile.NamedTemporaryFile() as fd:
                exp.writeFits(fd.name)
                fd.flush()

                self._fireflyFitsID = _fireflyClient.upload_file(fd.name)
                ret = _fireflyClient.show_fits(self._fireflyFitsID, plot_id=str(self.display.frame),
                                               Title=title, MultiImageIdx=0)
            if not ret["success"]:
                raise RuntimeError("Display of image failed")

        if mask:
                mdict = mask.getMaskPlaneDict()
                usedPlanes = long(afwMath.makeStatistics(mask, afwMath.SUM).getValue())
                for k in mdict:
                    if ((1 << mdict[k]) & usedPlanes):
                        _fireflyClient.add_mask(bit_number=mdict[k], image_number=1,
                                                plot_id=str(self.display.frame),
                                                mask_id=k, 
                                                color=self.display.getMaskPlaneColor(k),
                                                file_on_server=self._fireflyFitsID)
                        self._maskIds.append(k)

    def _remove_masks(self):
        """Remove mask layers"""
        for k in self._maskIds:
            _fireflyClient.remove_mask(plot_id=str(self.display.frame), mask_id=k)
        self._maskIds = []

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
        _fireflyClient.add_region_data(region_data=self._regions, plot_id=str(self.display.frame),
                                       region_layer_id=self._regionLayerId)
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
    with other characteristics, e.g. "times bold italic".  Text will be drawn rotated by textAngle (textAngle
    is ignored otherwise).

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
            _fireflyClient.delete_region_layer(self._regionLayerId, plot_id=str(self.display.frame))
            self._regionLayerId = None
        self._remove_masks()
        _fireflyClient.dispatch_remote_action(channel=_fireflyClient.channel,
                                              action_type='ImagePlotCntlr.deletePlotView',
                                              payload={'plotId': str(self.display.frame)})

    def _setCallback(self, what, func):
        if func != interface.noop_callback:
            status = _fireflyClient.add_extension('POINT' if False else 'AREA_SELECT', title=what,
                                                  plot_id=str(self.display.frame),
                                                  extension_id=what)
            if not status['success']:
                pass

    def _getEvent(self):
        """Return an event generated by a keypress or mouse click
        """
        ev = interface.Event("q")

        if self.verbose:
            print("virtual[%s]._getEvent() -> %s" % (self.display.frame, ev))

        return ev
    #
    # Set gray scale
    #

    def _scale(self, algorithm, min, max, unit=None, *args, **kwargs):
        stretch_algorithms = ('linear', 'log', 'loglog', 'equal', 'squared', 'sqrt',
                              'asinh', 'powerlaw_gamma')
        interval_methods = ('percent', 'maxmin', 'absolute', 'zscale', 'sigma')
        #
        #
        # Normalise algorithm's case
        #
        if algorithm:
            algorithm = dict((a.lower(), a) for a in stretch_algorithms).get(algorithm.lower(), algorithm)

            if algorithm not in stretch_algorithms:
                raise FireflyError('Algorithm %s is invalid; please choose one of "%s"' %
                                   (algorithm, '", "'.join(stretch_algorithms)))
            self._stretchAlgorithm = algorithm
        else:
            algorithm = 'linear'

        if min == 'minmax':
            interval_type = 'percent'
            unit = 'percent'
            min, max = 0, 100
        elif min == 'zscale':
            interval_type = 'zscale'

        if not unit:
            unit = 'absolute'

        units = ('percent', 'absolute', 'sigma')
        if unit not in units:
            raise FireflyError('Unit %s is invalid; please choose one of "%s"' % (unit, '", "'.join(units)))

        if unit == 'sigma':
            interval_type = 'sigma'
        if unit == 'absolute' and interval_type is None:
            interval_type = 'absolute'
        if unit == 'percent':
            interval_type = 'percent'

        self._stretchMin = min
        self._stretchMax = max
        self._stretchUnit = unit

        if interval_type not in interval_methods:
            raise FireflyError('Interval method %s is invalid' % interval_type)

        if interval_type is not 'zscale':
            _fireflyClient.set_stretch(str(self.display.frame), stype=interval_type, algorithm=algorithm,
                                       lower_value=min, upper_value=max)
        else:
            if 'zscale_constrast' not in kwargs:
                kwargs['zscale_contrast'] = 25
            if 'zscale_samples' not in kwargs:
                kwargs['zscale_samples'] = 600
            if 'zscale_samples_perline' not in kwargs:
                kwargs['zscale_samples_perline'] = 120
            _fireflyClient.set_stretch(str(self.display.frame), stype='zscale', algorithm=algorithm,
                                       zscale_contrast=kwargs['zscale_contrast'],
                                       zscale_samples=kwargs['zscale_samples'],
                                       zscale_samples_perline=kwargs['zscale_samples_perline'])

    def _setMaskTransparency(self, transparency, maskplane):
        """Specify mask transparency (percent); or None to not set it when loading masks"""
        if maskplane is not None:
            masklist = [maskplane]
        else:
            masklist = self._maskIds
        for k in masklist:
            _fireflyClient.dispatch_remote_action(channel=_fireflyClient.channel,
                                                  action_type='ImagePlotCntlr.overlayPlotChangeAttributes',
                                                  payload={'plotId': str(self.display.frame),
                                                           'imageOverlayId': k,
                                                           'attributes': {'opacity': transparency/100.},
                                                           'doReplot': False})

    def _getMaskTransparency(self, maskplane):
        """Return the current mask's transparency"""

        pass

    def _show(self):
        """Show the requested window"""
        _fireflyClient.launch_browser(force=True)
    #
    # Zoom and Pan
    #

    def _zoom(self, zoomfac):
        """Zoom frame by specified amount"""

        _fireflyClient.set_zoom(plot_id=str(self.display.frame), factor=zoomfac)

    def _pan(self, colc, rowc):
        _fireflyClient.set_pan(plot_id=str(self.display.frame), x=colc, y=rowc)
