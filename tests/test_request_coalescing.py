#
# LSST Data Management System
# Copyright 2026 LSST Corporation.
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

"""Tests for the request-traffic mitigations: coalescing of region
uploads and reuse of identical FITS uploads.  Rapid-fire small
requests have been mistaken for denial-of-service attacks by site
security, so the batching behavior matters beyond efficiency.
"""

import threading
import time
import unittest
from io import BytesIO
from types import SimpleNamespace
from unittest import mock

import lsst.utils.tests
from lsst.display.firefly import firefly as firefly_mod


def _make_impl(frame=0, buffered=False):
    """Construct a ``DisplayImpl`` without running ``__init__``.

    ``DisplayImpl.__init__`` requires a live Firefly server; we sidestep
    it via ``__new__`` and inject only the attributes the methods under
    test read.
    """
    impl = firefly_mod.DisplayImpl.__new__(firefly_mod.DisplayImpl)
    impl.display = SimpleNamespace(
        frame=frame,
        getMaskPlaneColor=lambda name: "red",
        _defaultMaskPlaneColor={},
    )
    impl.verbose = False
    impl._client = None
    impl._isBuffered = buffered
    impl._regions = []
    impl._regionLock = threading.Lock()
    impl._regionFlushTimer = None
    impl._regionLayerId = f"lsstRegions{frame}"
    return impl


def _flushDelay(margin=0.4):
    """Sleep long enough for a scheduled deferred flush to have fired."""
    time.sleep(firefly_mod._REGION_FLUSH_DELAY + margin)


class RegionCoalescingTest(unittest.TestCase):
    """Unbuffered region uploads (``dot()`` in a loop) must be batched
    into a small number of requests instead of one request per call."""

    def test_rapid_dots_coalesce_into_one_request(self):
        impl = _make_impl()
        with mock.patch.object(firefly_mod, "_fireflyClient") as client:
            for i in range(100):
                impl._uploadTextData([f"region {i}"])
            # Nothing is sent synchronously; a deferred flush is pending.
            self.assertEqual(client.add_region_data.call_count, 0)
            _flushDelay()
            self.assertEqual(client.add_region_data.call_count, 1)
            regions = client.add_region_data.call_args.kwargs["region_data"]
        self.assertEqual(len(regions), 100)

    def test_explicit_flush_sends_pending_and_cancels_timer(self):
        impl = _make_impl()
        with mock.patch.object(firefly_mod, "_fireflyClient") as client:
            impl._uploadTextData(["r1"])
            impl._uploadTextData(["r2"])
            impl._flush()
            self.assertEqual(client.add_region_data.call_count, 1)
            self.assertEqual(client.add_region_data.call_args.kwargs["region_data"], ["r1", "r2"])
            # The deferred flush was canceled: nothing arrives later.
            _flushDelay()
            self.assertEqual(client.add_region_data.call_count, 1)

    def test_buffering_defers_until_flush(self):
        impl = _make_impl(buffered=True)
        with mock.patch.object(firefly_mod, "_fireflyClient") as client:
            impl._uploadTextData(["r1"])
            self.assertIsNone(impl._regionFlushTimer)
            _flushDelay()
            self.assertEqual(client.add_region_data.call_count, 0)
            impl._flush()
            self.assertEqual(client.add_region_data.call_count, 1)

    def test_oversized_buffer_flushes_immediately(self):
        impl = _make_impl()
        with mock.patch.object(firefly_mod, "_fireflyClient") as client, \
                mock.patch.object(firefly_mod, "_MAX_PENDING_REGIONS", 10):
            impl._uploadTextData([f"r{i}" for i in range(10)])
            self.assertEqual(client.add_region_data.call_count, 1)
            self.assertEqual(impl._regions, [])

    def test_erase_discards_pending_regions(self):
        # Pending unbuffered regions would be deleted by the erase
        # anyway; they must be dropped, not sent after the delete.
        impl = _make_impl()
        with mock.patch.object(firefly_mod, "_fireflyClient") as client:
            impl._uploadTextData(["r1"])
            impl._erase()
            client.delete_region_layer.assert_called_once()
            _flushDelay()
            self.assertEqual(client.add_region_data.call_count, 0)
        self.assertEqual(impl._regions, [])


class UploadCacheTest(unittest.TestCase):
    """Identical FITS data must not be re-uploaded within the reuse
    window; distinct or expired data must be."""

    def setUp(self):
        firefly_mod._uploadCache.clear()

    def tearDown(self):
        firefly_mod._uploadCache.clear()

    def test_identical_upload_reused(self):
        impl = _make_impl()
        with mock.patch.object(firefly_mod, "_fireflyClient") as client:
            client.upload_fits_data.return_value = "${upload}/file1.fits"
            path1 = impl._uploadFitsCached(BytesIO(b"FITS data"))
            path2 = impl._uploadFitsCached(BytesIO(b"FITS data"))
            self.assertEqual(client.upload_fits_data.call_count, 1)
        self.assertEqual(path1, path2)

    def test_different_data_uploads_again(self):
        impl = _make_impl()
        with mock.patch.object(firefly_mod, "_fireflyClient") as client:
            client.upload_fits_data.side_effect = ["${upload}/a.fits", "${upload}/b.fits"]
            path1 = impl._uploadFitsCached(BytesIO(b"FITS data A"))
            path2 = impl._uploadFitsCached(BytesIO(b"FITS data B"))
            self.assertEqual(client.upload_fits_data.call_count, 2)
        self.assertNotEqual(path1, path2)

    def test_expired_entry_is_reuploaded(self):
        impl = _make_impl()
        with mock.patch.object(firefly_mod, "_fireflyClient") as client, \
                mock.patch.object(firefly_mod, "_UPLOAD_CACHE_TTL", 0):
            client.upload_fits_data.return_value = "${upload}/file1.fits"
            impl._uploadFitsCached(BytesIO(b"FITS data"))
            impl._uploadFitsCached(BytesIO(b"FITS data"))
            self.assertEqual(client.upload_fits_data.call_count, 2)

    def test_cache_size_is_bounded(self):
        impl = _make_impl()
        with mock.patch.object(firefly_mod, "_fireflyClient") as client, \
                mock.patch.object(firefly_mod, "_UPLOAD_CACHE_MAXSIZE", 2):
            client.upload_fits_data.side_effect = [f"${{upload}}/{i}.fits" for i in range(3)]
            for i in range(3):
                impl._uploadFitsCached(BytesIO(b"FITS data %d" % i))
        self.assertLessEqual(len(firefly_mod._uploadCache), 2)


class TestMemory(lsst.utils.tests.MemoryTestCase):
    pass


def setup_module(module):
    lsst.utils.tests.init()


if __name__ == "__main__":
    lsst.utils.tests.init()
    unittest.main()
