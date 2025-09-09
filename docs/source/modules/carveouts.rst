Using Carve-Outs
================

It is possible to "carve out" a portion of the lands already added to
the plat, so that some portion does not get filled in on the plat.

Each layer (if using layers) will have its own carve-outs that do not
affect other layers.

The methods for carving out lands are ``.carve_description()``,
``.carve_tracts()``, and ``.carve_tract()``, found in every plat-generating
class (``Plat``, ``PlatGroup``, and ``MegaPlat``).
These mirror their counterpart methods for adding lands: ``.add_description()``,
``.add_tracts()``, and ``.add_tract()``.

Example Code
------------

In the following code, we add the ``'N/2'`` of Section 14, but only the
NE/4 will be depicted on the plat, because we "carve out" the NW/4.

.. code-block:: python

    plat = pytrsplat.Plat()

    # If `layer=<name>` isn't specified, will use default.
    plat.add_description('T154N-R97W Sec 14: N/2', layer='some_layer')
    plat.carve_description('T154N-R97W Sec 14: NW/4', layer='some_layer')

    plat.execute_queue()
    plat.output(fp=r"some/file/path.png")

If the settings are configured to write tracts to the footer
(``.settings.write_tracts=True``), the entirety of ``'154n97w14: N/2'``
would still be written to the footer. The carve-outs will only affect
what gets **colored** onto the plat.


.. important::

    It does not matter whether lands are added first or carved out first.
    Regardless of the order, all carve-outs override the queue for a
    given layer. In other words, when the queue is executed, all added
    lands will be platted for that layer, then all carved-out
    lands will be removed from that layer. This means that carved-out
    lands **cannot** be re-added to the queue for that same
    layer. They **can** be added to the queue for a different
    layer.

    Carve-outs for any given layer can be cleared with
    ``.clear_layer_carveouts(layer=<name>)``.

    All carve-outs must be added prior to calling ``.execute_queue()``.

.. warning::

    **Any** lots or aliquots identified in this tract will be
    removed from the layer. Be careful to use a 'clean'
    description that will not remove lands that should be kept.


Example Code (multiple layers)
------------------------------

Each layer has its own carve-outs that do not affect one another.

.. code-block:: python

    plat = pytrsplat.Plat()

    # This layer will show only the NE/4.
    plat.add_description('T154N-R97W Sec 14: N/2', layer='some_layer')
    plat.carve_description('T154N-R97W Sec 14: NW/4', layer='some_layer')

    # This will show the entire W/2, because it is on a different layer
    # than the carved-out 'NW/4' above.
    plat.add_description('T154N-R97W Sec 14: W/2', layer='other_layer')

    # Use different color for each layer.
    plat.settings.set_layer_fill('some_layer', qq_fill_rgba=(255, 0, 0, 100))
    plat.settings.set_layer_fill('other_layer', qq_fill_rgba=(0, 255, 0, 100))

    plat.execute_queue()
    plat.output(fp=r"some/file/path.png")
