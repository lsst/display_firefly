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

"""Tests that mask overlays sent to the Firefly server are keyed by both
frame and plane name, so that multiple frames carrying same-named planes
(e.g. ``DETECTED`` on three different exposures) do not overwrite each
other on the server.
"""

import unittest
from types import SimpleNamespace
from unittest import mock

import lsst.utils.tests
from lsst.display.firefly import firefly as firefly_mod


def _make_impl(frame, mask_ids=None, mask_dict=None, mask_plane_colors=None,
               default_mask_plane_color=None, mask_transparencies=None):
    """Construct a ``DisplayImpl`` without running ``__init__``.

    ``DisplayImpl.__init__`` requires a live Firefly server; we sidestep it
    via ``__new__`` and inject only the attributes the methods under test
    read.  ``display`` is stubbed as a SimpleNamespace exposing the small
    surface those methods touch (``frame``, ``getMaskPlaneColor``,
    ``_defaultMaskPlaneColor``).
    """
    impl = firefly_mod.DisplayImpl.__new__(firefly_mod.DisplayImpl)
    impl.display = SimpleNamespace(
        frame=frame,
        getMaskPlaneColor=lambda name: (mask_plane_colors or {}).get(name, "red"),
        _defaultMaskPlaneColor=default_mask_plane_color or {},
    )
    impl._maskIds = list(mask_ids) if mask_ids is not None else []
    impl._maskDict = dict(mask_dict) if mask_dict is not None else {}
    impl._maskPlaneColors = dict(mask_plane_colors) if mask_plane_colors is not None else {}
    impl._maskTransparencies = dict(mask_transparencies) if mask_transparencies is not None else {}
    impl._fireflyFitsID = "fits-id-stub"
    # ``__del__`` -> ``_close()`` reads these attributes; satisfy it
    # since we are bypassing ``__init__``.
    impl.verbose = False
    impl._client = None
    return impl


class ScopedMaskIdTest(unittest.TestCase):
    """The helper itself is pure -- verify it produces distinct ids per
    frame while remaining human-readable in the layer panel."""

    def test_distinct_per_frame(self):
        self.assertNotEqual(firefly_mod.DisplayImpl._scoped_mask_id(0, "DETECTED"),
                            firefly_mod.DisplayImpl._scoped_mask_id(1, "DETECTED"))

    def test_includes_plane_name(self):
        self.assertIn("DETECTED", firefly_mod.DisplayImpl._scoped_mask_id(0, "DETECTED"))
        self.assertIn("0", firefly_mod.DisplayImpl._scoped_mask_id(0, "DETECTED"))


class RemoveMasksTest(unittest.TestCase):
    """``_remove_masks`` is invoked when a new image is loaded into a
    frame; it must only clear *that* frame's overlays."""

    def test_only_removes_current_frame(self):
        impl = _make_impl(
            frame=1,
            mask_ids=[(0, "DETECTED"), (1, "DETECTED"), (1, "BAD"), (2, "SAT")],
        )
        with mock.patch.object(firefly_mod, "_fireflyClient") as client:
            impl._remove_masks()
            removed = [(c.kwargs["plot_id"], c.kwargs["mask_id"])
                       for c in client.remove_mask.call_args_list]
        # Frame 1 layers removed, frames 0 and 2 left alone.
        self.assertEqual(set(removed),
                         {("1", "f1__DETECTED"), ("1", "f1__BAD")})
        self.assertEqual(set(impl._maskIds), {(0, "DETECTED"), (2, "SAT")})


class SetMaskPlaneColorTest(unittest.TestCase):
    """``setMaskPlaneColor`` should retarget only the current frame's
    layer, leaving sibling frames' layers in place."""

    def test_scopes_mask_id(self):
        impl = _make_impl(
            frame=2,
            mask_dict={"DETECTED": 5},
            mask_plane_colors={"DETECTED": "red"},
        )
        with mock.patch.object(firefly_mod, "_fireflyClient") as client:
            impl._setMaskPlaneColor("DETECTED", "cyan")
            (remove_call,) = client.remove_mask.call_args_list
            (add_call,) = client.add_mask.call_args_list
        self.assertEqual(remove_call.kwargs["plot_id"], "2")
        self.assertEqual(remove_call.kwargs["mask_id"], "f2__DETECTED")
        self.assertEqual(add_call.kwargs["plot_id"], "2")
        self.assertEqual(add_call.kwargs["mask_id"], "f2__DETECTED")
        self.assertEqual(impl._maskPlaneColors["DETECTED"], "cyan")

    def test_ignore_color_skips_add(self):
        impl = _make_impl(
            frame=0,
            mask_dict={"DETECTED": 5},
            mask_plane_colors={"DETECTED": "red"},
        )
        with mock.patch.object(firefly_mod, "_fireflyClient") as client:
            impl._setMaskPlaneColor("DETECTED", "ignore")
            self.assertEqual(client.remove_mask.call_count, 1)
            self.assertEqual(client.add_mask.call_count, 0)


class SetMaskTransparencyTest(unittest.TestCase):
    """``setMaskTransparency`` dispatches per-layer attribute changes;
    the dispatched ``imageOverlayId`` must be the frame-scoped id."""

    def test_named_plane_uses_scoped_overlay_id(self):
        impl = _make_impl(frame=3)
        with mock.patch.object(firefly_mod, "_fireflyClient") as client:
            impl._setMaskTransparency(40, "DETECTED")
            (call,) = client.dispatch.call_args_list
        payload = call.kwargs["payload"]
        self.assertEqual(payload["plotId"], "3")
        self.assertEqual(payload["imageOverlayId"], "f3__DETECTED")
        self.assertAlmostEqual(payload["attributes"]["opacity"], 0.6)

    def test_all_planes_filters_by_frame(self):
        # ``maskName=None`` means "all of this frame's planes".  Layers
        # registered against other frames must not be touched.
        impl = _make_impl(
            frame=1,
            mask_ids=[(0, "DETECTED"), (1, "DETECTED"), (1, "BAD")],
            default_mask_plane_color={},
        )
        with mock.patch.object(firefly_mod, "_fireflyClient") as client:
            impl._setMaskTransparency(0, None)
            ids = {c.kwargs["payload"]["imageOverlayId"]
                   for c in client.dispatch.call_args_list}
        self.assertEqual(ids, {"f1__DETECTED", "f1__BAD"})


class TestMemory(lsst.utils.tests.MemoryTestCase):
    pass


def setup_module(module):
    lsst.utils.tests.init()


if __name__ == "__main__":
    lsst.utils.tests.init()
    unittest.main()
