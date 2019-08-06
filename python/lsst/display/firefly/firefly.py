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

from __future__ import absolute_import, division, print_function
from past.builtins import long

from io import BytesIO
from socket import gaierror
import tempfile

import lsst.afw.display.interface as interface
import lsst.afw.display.virtualDevice as virtualDevice
import lsst.afw.display.ds9Regions as ds9Regions
import lsst.afw.display.displayLib as displayLib
import lsst.afw.math as afwMath
import lsst.log

from .footprints import createFootprintsTable

try:
    import firefly_client
    _fireflyClient = None
except ImportError as e:
    raise RuntimeError("Cannot import firefly_client: %s" % (e))
from ws4py.client import HandshakeError


class FireflyError(Exception):

    def __init__(self, str):
        Exception.__init__(self, str)


def firefly_version():
    """Return the version of firefly_client in use, as a string"""
    return(firefly_client.__version__)


class DisplayImpl(virtualDevice.DisplayImpl):
    """Device to talk to a firefly display"""

    @staticmethod
    def __handleCallbacks(event):
        if 'type' in event['data']:
            if event['data']['type'] == 'AREA_SELECT':
                lsst.log.debug('*************area select')
                pParams = {'URL': 'http://web.ipac.caltech.edu/staff/roby/demo/wise-m51-band2.fits',
                           'ColorTable': '9'}
                plot_id = 3
                global _fireflyClient
                _fireflyClient.show_fits(fileOnServer=None, plot_id=plot_id, additionalParams=pParams)

        lsst.log.debug("Callback event info: {}".format(event))
        return
        data = dict((_.split('=') for _ in event.get('data', {}).split('&')))
        if data.get('type') == "POINT":
            lsst.log.debug("Event Received: %s" % data.get('id'))

    def __init__(self, display, verbose=False, url=None,
                 name=None, *args, **kwargs):
        virtualDevice.DisplayImpl.__init__(self, display, verbose)

        if self.verbose:
            print("Opening firefly device %s" % (self.display.frame if self.display else "[None]"))

        global _fireflyClient
        if not _fireflyClient:
            import os
            start_tab = None
            html_file = kwargs.get('html_file',
                                   os.environ.get('FIREFLY_HTML', 'slate.html'))
            if url is None:
                if (('fireflyLabExtension' in os.environ) and
                        ('fireflyURLLab' in os.environ)):
                    url = os.environ['fireflyURLLab']
                    start_tab = kwargs.get('start_tab', True)
                    start_browser_tab = kwargs.get('start_browser_tab', False)
                    if (name is None) and ('fireflyChannelLab' in os.environ):
                        name = os.environ['fireflyChannelLab']
                elif 'FIREFLY_URL' in os.environ:
                    url = os.environ['FIREFLY_URL']
                else:
                    raise RuntimeError('Cannot determine url from environment; you must pass url')

            token = kwargs.get('token',
                               os.environ.get('ACCESS_TOKEN', None))

            try:
                if start_tab:
                    if verbose:
                        print('Starting Jupyterlab client')
                    _fireflyClient = firefly_client.FireflyClient.make_lab_client(
                        start_tab=True, start_browser_tab=start_browser_tab,
                        html_file=kwargs.get('html_file'), verbose=verbose,
                        token=token)

                else:
                    if verbose:
                        print('Starting vanilla client')
                    _fireflyClient = firefly_client.FireflyClient.make_client(
                        url=url, html_file=html_file, launch_browser=True,
                        channel_override=name, verbose=verbose,
                        token=token)

            except (HandshakeError, gaierror) as e:
                raise RuntimeError("Unable to connect to %s: %s" % (url or '', e))

            try:
                _fireflyClient.add_listener(self.__handleCallbacks)
            except Exception as e:
                raise RuntimeError("Cannot add listener. Browser must be connected" +
                                   "to %s: %s" %
                                   (_fireflyClient.get_firefly_url(), e))

        self._isBuffered = False
        self._regions = []
        self._regionLayerId = self._getRegionLayerId()
        self._fireflyFitsID = None
        self._fireflyMaskOnServer = None
        self._client = _fireflyClient
        self._channel = _fireflyClient.channel
        self._url = _fireflyClient.get_firefly_url()
        self._maskIds = []
        self._maskDict = {}
        self._maskPlaneColors = {}
        self._maskTransparencies = {}
        self._lastZoom = None
        self._lastPan = None
        self._lastStretch = None

    def _getRegionLayerId(self):
        return "lsstRegions%s" % self.display.frame if self.display else "None"

    def _clearImage(self):
        """Delete the current image in the Firefly viewer
        """
        self._client.dispatch(action_type='ImagePlotCntlr.deletePlotView',
                              payload=dict(plotId=str(self.display.frame)))

    def _mtv(self, image, mask=None, wcs=None, title=""):
        """Display an Image and/or Mask on a Firefly display
        """
        if title == "":
            title = str(self.display.frame)
        if image:
            if self.verbose:
                print('displaying image')
            self._erase()

            with tempfile.NamedTemporaryFile() as fd:
                displayLib.writeFitsImage(fd.name, image, wcs, title)
                fd.flush()
                fd.seek(0, 0)
                self._fireflyFitsID = _fireflyClient.upload_data(fd, 'FITS')

            try:
                viewer_id = ('image-' + str(_fireflyClient.render_tree_id) + '-' +
                             str(self.frame))
            except AttributeError:
                viewer_id = 'image-' + str(self.frame)
            extraParams = dict(Title=title,
                               MultiImageIdx=0,
                               PredefinedOverlayIds=' ',
                               viewer_id=viewer_id)
            # Firefly's Javascript API requires a space for parameters;
            # otherwise the parameter will be ignored

            if self._lastZoom:
                extraParams['InitZoomLevel'] = self._lastZoom
                extraParams['ZoomType'] = 'LEVEL'
            if self._lastPan:
                extraParams['InitialCenterPosition'] = '{0:.3f};{1:.3f};PIXEL'.format(
                    self._lastPan[0], self._lastPan[1])
            if self._lastStretch:
                extraParams['RangeValues'] = self._lastStretch

            ret = _fireflyClient.show_fits(self._fireflyFitsID, plot_id=str(self.display.frame),
                                           **extraParams)

            if not ret["success"]:
                raise RuntimeError("Display of image failed")

        if mask:
            if self.verbose:
                print('displaying mask')
            with tempfile.NamedTemporaryFile() as fdm:
                displayLib.writeFitsImage(fdm.name, mask, wcs, title)
                fdm.flush()
                fdm.seek(0, 0)
                self._fireflyMaskOnServer = _fireflyClient.upload_data(fdm, 'FITS')

            maskPlaneDict = mask.getMaskPlaneDict()
            for k, v in maskPlaneDict.items():
                self._maskDict[k] = v
                self._maskPlaneColors[k] = self.display.getMaskPlaneColor(k)
            usedPlanes = long(afwMath.makeStatistics(mask, afwMath.SUM).getValue())
            for k in self._maskDict:
                if (((1 << self._maskDict[k]) & usedPlanes) and
                        (k in self._maskPlaneColors) and
                        (self._maskPlaneColors[k] is not None) and
                        (self._maskPlaneColors[k].lower() != 'ignore')):
                    _fireflyClient.add_mask(bit_number=self._maskDict[k],
                                            image_number=0,
                                            plot_id=str(self.display.frame),
                                            mask_id=k,
                                            title=k + ' - bit %d'%self._maskDict[k],
                                            color=self._maskPlaneColors[k],
                                            file_on_server=self._fireflyMaskOnServer)
                    if k in self._maskTransparencies:
                        self._setMaskTransparency(self._maskTransparencies[k], k)
                    self._maskIds.append(k)

    def _remove_masks(self):
        """Remove mask layers"""
        for k in self._maskIds:
            _fireflyClient.remove_mask(plot_id=str(self.display.frame), mask_id=k)
        self._maskIds = []

    def _buffer(self, enable=True):
        """!Enable or disable buffering of writes to the display
        param enable  True or False, as appropriate
        """
        self._isBuffered = enable

    def _flush(self):
        """!Flush any I/O buffers
        """
        if not self._regions:
            return

        if self.verbose:
            print("Flushing %d regions" % len(self._regions))
            print(self._regions)

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
        if _fireflyClient is not None:
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
        """Erase all overlays on the image"""
        if self.verbose:
            print('region layer id is {}'.format(self._regionLayerId))
        if self._regionLayerId:
            _fireflyClient.delete_region_layer(self._regionLayerId, plot_id=str(self.display.frame))

    def _setCallback(self, what, func):
        if func != interface.noop_callback:
            try:
                status = _fireflyClient.add_extension('POINT' if False else 'AREA_SELECT', title=what,
                                                      plot_id=str(self.display.frame),
                                                      extension_id=what)
                if not status['success']:
                    pass
            except Exception as e:
                raise RuntimeError("Cannot set callback. Browser must be (re)opened " +
                                   "to %s%s : %s" %
                                   (_fireflyClient.url_bw,
                                    _fireflyClient.channel, e))

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
        """Scale the image stretch and limits

        Parameters:
        -----------
        algorithm : `str`
            stretch algorithm, e.g. 'linear', 'log', 'loglog', 'equal', 'squared',
            'sqrt', 'asinh', powerlaw_gamma'
        min : `float` or `str`
            lower limit, or 'minmax' for full range, or 'zscale'
        max : `float` or `str`
            upper limit; overrriden if min is 'minmax' or 'zscale'
        unit : `str`
            unit for min and max. 'percent', 'absolute', 'sigma'.
            if not specified, min and max are presumed to be in 'absolute' units.

        *args, **kwargs : additional position and keyword arguments.
            The options are shown below:

            **Q** : `float`, optional
                The asinh softening parameter for asinh stretch.
                Use Q=0 for linear stretch, increase Q to make brighter features visible.
                When not specified or None, Q is calculated by Firefly to use full color range.
            **gamma**
                The gamma value for power law gamma stretch (default 2.0)
            **zscale_contrast** : `int`, optional
                Contrast parameter in percent for zscale algorithm (default 25)
            **zscale_samples** : `int`, optional
                Number of samples for zscale algorithm (default 600)
            **zscale_samples_perline** : `int`, optional
                Number of samples per line for zscale algorithm (default 120)
        """
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

        # Translate parameters for asinh and powerlaw_gamma stretches
        if 'Q' in kwargs:
            kwargs['asinh_q_value'] = kwargs['Q']
            del kwargs['Q']

        if 'gamma' in kwargs:
            kwargs['gamma_value'] = kwargs['gamma']
            del kwargs['gamma']

        if min == 'minmax':
            interval_type = 'percent'
            unit = 'percent'
            min, max = 0, 100
        elif min == 'zscale':
            interval_type = 'zscale'
        else:
            interval_type = None

        if not unit:
            unit = 'absolute'

        units = ('percent', 'absolute', 'sigma')
        if unit not in units:
            raise FireflyError('Unit %s is invalid; please choose one of "%s"' % (unit, '", "'.join(units)))

        if unit == 'sigma':
            interval_type = 'sigma'
        elif unit == 'absolute' and interval_type is None:
            interval_type = 'absolute'
        elif unit == 'percent':
            interval_type = 'percent'

        self._stretchMin = min
        self._stretchMax = max
        self._stretchUnit = unit

        if interval_type not in interval_methods:
            raise FireflyError('Interval method %s is invalid' % interval_type)

        rval = {}
        if interval_type != 'zscale':
            rval = _fireflyClient.set_stretch(str(self.display.frame), stype=interval_type,
                                              algorithm=algorithm, lower_value=min,
                                              upper_value=max, **kwargs)
        else:
            if 'zscale_contrast' not in kwargs:
                kwargs['zscale_contrast'] = 25
            if 'zscale_samples' not in kwargs:
                kwargs['zscale_samples'] = 600
            if 'zscale_samples_perline' not in kwargs:
                kwargs['zscale_samples_perline'] = 120
            rval = _fireflyClient.set_stretch(str(self.display.frame), stype='zscale',
                                              algorithm=algorithm, **kwargs)

        if 'rv_string' in rval:
            self._lastStretch = rval['rv_string']

    def _setMaskTransparency(self, transparency, maskName):
        """Specify mask transparency (percent); or None to not set it when loading masks"""
        if maskName is not None:
            masklist = [maskName]
        else:
            masklist = set(self._maskIds + list(self.display._defaultMaskPlaneColor.keys()))
        for k in masklist:
            self._maskTransparencies[k] = transparency
            _fireflyClient.dispatch(action_type='ImagePlotCntlr.overlayPlotChangeAttributes',
                                    payload={'plotId': str(self.display.frame),
                                             'imageOverlayId': k,
                                             'attributes': {'opacity': 1.0 - transparency/100.},
                                             'doReplot': False})

    def _getMaskTransparency(self, maskName):
        """Return the current mask's transparency"""
        transparency = None
        if maskName in self._maskTransparencies:
            transparency = self._maskTransparencies[maskName]
        return transparency

    def _setMaskPlaneColor(self, maskName, color):
        """Specify mask color """
        _fireflyClient.remove_mask(plot_id=str(self.display.frame),
                                   mask_id=maskName)
        self._maskPlaneColors[maskName] = color
        if (color.lower() != 'ignore'):
            _fireflyClient.add_mask(bit_number=self._maskDict[maskName],
                                    image_number=1,
                                    plot_id=str(self.display.frame),
                                    mask_id=maskName,
                                    color=self.display.getMaskPlaneColor(maskName),
                                    file_on_server=self._fireflyFitsID)

    def _show(self):
        """Show the requested window"""
        if self._client.render_tree_id is not None:
            # we are using Jupyterlab
            self._client.dispatch(self._client.ACTION_DICT['StartLabWindow'],
                                  {})
        else:
            localbrowser, url = _fireflyClient.launch_browser(verbose=self.verbose)
            if not localbrowser and not self.verbose:
                _fireflyClient.display_url()

    #
    # Zoom and Pan
    #

    def _zoom(self, zoomfac):
        """Zoom display by specified amount

        Parameters:
        -----------
        zoomfac: `float`
            zoom level in screen pixels per image pixel
        """
        self._lastZoom = zoomfac
        _fireflyClient.set_zoom(plot_id=str(self.display.frame), factor=zoomfac)

    def _pan(self, colc, rowc):
        """Pan to specified pixel coordinates

        Parameters:
        -----------
        colc, rowc : `float`
            column and row in units of pixels (zero-based convention,
              with the xy0 already subtracted off)
        """
        self._lastPan = [colc+0.5, rowc+0.5]  # saved for future use in _mtv
        # Firefly's internal convention is first pixel is (0.5, 0.5)
        _fireflyClient.set_pan(plot_id=str(self.display.frame), x=colc, y=rowc)

    # Extensions to the API that are specific to using the Firefly backend

    def getClient(self):
        """Get the instance of FireflyClient for this display

        Returns:
        --------
        `firefly_client.FireflyClient`
            Instance of FireflyClient used by this display
        """
        return self._client

    def clearViewer(self):
        """Reinitialize the viewer
        """
        self._client.reinit_viewer()

    def resetLayout(self):
        """Reset the layout of the Firefly Slate browser

        Clears the display and adds Slate cells to display image in upper left,
        plot area in upper right, and plots stretch across the bottom
        """
        self.clearViewer()
        try:
            tables_cell_id = 'tables-' + str(_fireflyClient.render_tree_id)
        except AttributeError:
            tables_cell_id = 'tables'
        self._client.add_cell(row=2, col=0, width=4, height=2, element_type='tables',
                              cell_id=tables_cell_id)
        try:
            image_cell_id = ('image-' + str(_fireflyClient.render_tree_id) + '-' +
                             str(self.frame))
        except AttributeError:
            image_cell_id = 'image-' + str(self.frame)
        self._client.add_cell(row=0, col=0, width=2, height=3, element_type='images',
                              cell_id=image_cell_id)
        try:
            plots_cell_id = 'plots-' + str(_fireflyClient.render_tree_id)
        except AttributeError:
            plots_cell_id = 'plots'
        self._client.add_cell(row=0, col=2, width=2, height=3, element_type='xyPlots',
                              cell_id=plots_cell_id)

    def overlayFootprints(self, catalog, color='rgba(74,144,226,0.60)',
                          highlightColor='cyan', selectColor='orange',
                          style='fill', layerString='detection footprints ',
                          titleString='catalog footprints '):
        """Overlay outlines of footprints from a catalog

        Overlay outlines of LSST footprints from the input catalog. The colors
        and style can be specified as parameters, and the base color and style
        can be changed in the Firefly browser user interface.

        Parameters:
        -----------
        catalog : `lsst.afw.table.SourceCatalog`
            Source catalog from which to display footprints.
        color : `str`
            Color for footprints overlay. Colors can be specified as a name
            like 'cyan' or afwDisplay.RED; as an rgb value such as
            'rgb(80,100,220)'; or as rgb plus alpha (transparency) such
            as 'rgba('74,144,226,0.60)'.
        highlightColor : `str`
            Color for highlighted footprints
        selectColor : `str`
            Color for selected footprints
        style : {'fill', 'outline'}
            Style of footprints display, filled or outline
        insertColumn : `int`
            Column at which to insert the "family_id" and "category" columns
        layerString: `str`
            Name of footprints layer string, to concatenate with the frame
            Re-using the layer_string will overwrite the previous table and
            footprints
        titleString: `str`
            Title of catalog, to concatenate with the frame
        """
        footprintTable = createFootprintsTable(catalog)
        with BytesIO() as fd:
            footprintTable.to_xml(fd)
            tableval = self._client.upload_data(fd, 'UNKNOWN')
        self._client.overlay_footprints(footprint_file=tableval,
                                        title=titleString + str(self.display.frame),
                                        footprint_layer_id=layerString + str(self.display.frame),
                                        plot_id=str(self.display.frame),
                                        color=color,
                                        highlightColor=highlightColor,
                                        selectColor=selectColor,
                                        style=style)
