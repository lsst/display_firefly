#
# LSST Data Management System
# Copyright 2016 LSST Corporation.
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

"""Test for imports of display_firefly backend

Note that interactive user tests are in afw/tests/test_display.py
"""
from __future__ import absolute_import, division, print_function

import unittest

import lsst.utils.tests
import lsst.display.firefly
import lsst.afw.display as afw_display
import ws4py


class InvalidHostTestCase1(lsst.utils.tests.TestCase):
    """Test for invalid host (not a Firefly server)"""

    def testConnect(self):
        with self.assertRaises(ws4py.websocket.HandshakeError):
            lsst.display.firefly.firefly_client.FireflyClient(
                                    'http://google.com')

    def testMakeDisplay(self):
        with self.assertRaises(RuntimeError):
            afw_display.Display(backend='firefly',
                                url='http://google.com')


class MemoryTester(lsst.utils.tests.MemoryTestCase):
    pass


def setup_module(module):
    lsst.utils.tests.init()


if __name__ == "__main__":
    lsst.utils.tests.init()
    unittest.main()
