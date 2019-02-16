
##########################################
Working with interactive tables and charts
##########################################



Upload a catalog to an interactive table
========================================

Firefly provides sophisticated capabilities for viewing and overlaying tables.
The `firefly_client`  Python package underlies the Firefly backend for
`lsst.afw.display`. The `firefly_client.plot` module includes convenience
functions for uploading tables.

Accessing the underlying FireflyClient instance
-----------------------------------------------

The underlying instance of `~firefly_client.FireflyClient` can be accessed
with the `getClient` method.

.. code-block:: py
    :name: client-attribute

    fc = display1.getClient()

Uploading a SourceTable
-----------------------

For uploading a table it is convenient to use the `firefly_client.plot` module.
Import it and ensure it is using the same `~firefly_client.FireflyClient` instance.

.. code-block:: py

    import firefly_client.plot as ffplt
    ffplt.use_client(fc)

Upload a SourceCatalog to Firefly. By default, the catalog is shown in an
interactive table viewer.

.. code-block:: py

    tbl_id = ffplt.upload_table(src, title='Source Catalog')

The catalog appears in an interactive table viewer. Since the catalog contains
coordinate columns recognized by Firefly, the source locations are overlaid on
the images (if one is displayed).


Charts from tables
------------------

Firefly includes plotting capabilities using the Plotly.js library.

Make a histogram of cell values.

.. code-block:: py

    ffplt.hist('log10(base_PsfFlux_flux)')

`firefly_client.plot.scatter` can be used to make a scatter plot of two columns
for a table. These functions use the table ID of the last uploaded table by
default; the `tbl_id` we saved in the last cell can be passed as an optional argument.

References
==========

See the `firefly_client documentation <https://firefly-client.lsst.io>`_ for
more information about using `FireflyClient`.
