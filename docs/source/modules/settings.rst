``Settings``
============

This class controls the appearance and behavior of a plat.

Example Code
------------

.. code-block:: python

    import pytrsplat
    letter_preset = pytrsplat.Settings.preset('letter')
    letter_preset.write_lot_numbers = True
    plat = pytrsplat.Plat(settings=letter_preset)
    # Change settings within the plat's `.settings` attribute.
    # Here, changing the header font to the included 'Mono Bold' typeface.
    plat.settings.set_font(purpose='header', typeface='Mono (Bold)')

Configure the ``.settings`` attribute of a ``Plat``, ``MegaPlat``, or
``PlatGroup``, or pass it as ``settings=<some Settings object>`` when
initializing one.


.. code-block:: python

    import pytrsplat
    plat_group = pytrsplat.PlatGroup()
    plat_group.settings = pytrsplat.Settings.preset('square_s')

    mp_default_settings = pytrsplat.Settings.preset('megaplat_default')
    mega_plat = pytrsplat.MegaPlat(settings=mp_default_settings)


.. important::
    If you want to change any of the fonts, be sure to use the
    ``.set_font()`` method.


.. autoclass:: pytrsplat.Settings
    :members:

