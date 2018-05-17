#!/usr/bin/env python
"""Sphinx configuration file for an LSST stack package.
This configuration only affects single-package Sphinx documenation builds.
"""

from documenteer.sphinxconfig.stackconf import build_package_configs
import lsst.display.firefly


_g = globals()
_g.update(build_package_configs(
    project_name='display_firefly',
    version=lsst.display.firefly.version.__version__))
