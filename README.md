# display_firefly

Implementation of the `afw.display` interface for the Firefly backend.

Firefly is IPAC's toolkit for construction of astronomical data user interfaces.

## Pointers to more information

* Full documentation is available at https://display-firefly.lsst.io/ .
* Within the Rubin Science Platform environment, suitable Firefly servers
  are provided by default, so that in many cases the user need not be aware
  of the identity or URL of the server.
* `display_firefly` works with the RSP's
  [Firefly extension for JupyterLab](https://github.com/Caltech-IPAC/jupyter_firefly_extensions)
  for displays within the JupyterLab environment (the default), but also with
  Firefly servers in separate browser tabs/windows.
* See http://github.com/Caltech-IPAC/firefly for the core Firefly code base.
* The RSP Portal Aspect is constructed from
  the http://github.com/lsst/suit package, as an application of Firefly.
  Portal Aspect application.
* Standalone Firefly servers for individual use may be obtained from
  [this Dockerhub repository](https://hub.docker.com/r/ipac/firefly/).

## Dependencies

In addition to its `eups`-declared dependencies, `display_firefly` requires
the [`firefly_client`](https://github.com/Caltech-IPAC/firefly_client) Python
module to be available.
In the Rubin build environment, this is treated as an external dependency,
managed via Conda and supplied via the `rubin-env` mechanism.

* See https://github.com/conda-forge/rubinenv-feedstock
  and [DMTN-174](https://dmtn-174.lsst.io).

## Usage

Usage is described in detail in 
the [documentation](https://display-firefly.lsst.io/).
However, in many cases the following is sufficient to set up a Firefly
display for use with the back-end-agnostic `afw.display` interface:

```
import lsst.afw.display as afwDisplay
afwDisplay.setDefaultBackend('firefly')
afw_display = afwDisplay.Display(frame=1)
```
