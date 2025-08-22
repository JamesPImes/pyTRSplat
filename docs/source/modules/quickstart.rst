Quickstart
==========

To get up and running ASAP, the simplest option is to use a
:doc:`PlatGroup <platgroup>`. This will accept any number of Twp/Rges,
and you can output to a single PDF or separate image files.

Reference the section on :ref:`default lots <default_lots>`,
which might be enough for handling lots in 'typical' sections.

If your land description has unpredictable lots, you'll probably want to define
lots in a :ref:`csv file and load them <lot_defs_csv>`.


Typical Workflow
----------------

.. note::

    The docs for ``Plat``, ``PlatGroup``, and ``MegaPlat`` each contain
    an example block of code that shows this workflow. The next section
    contains example code for a ``PlatGroup``.


1. Load a ``Settings`` preset (or create one yourself, if you're ambitious).

    * Adjust the settings however you want.

2. Create a ``Plat``, ``PlatGroup``, or ``MegaPlat`` with those settings.

3. Optionally, write lot definitions to a :ref:`csv file <lot_defs_csv>` and load
   them into the plat with ``.lot_definer.read_csv('some_file.csv')``.

    * Alternatively / additionally, assume :ref:`'default' lots <default_lots>`
      in those sections along the north and west boundaries of the township,
      with ``.lot_definer.assume_defaults = True``.

4. Add lands to the plat's queue with ``.add_description()``,
   ``.add_tracts()``, or ``.add_tract()``.

5. Call ``.execute_queue()`` to fill in the plats.

6. Output the results with ``.output()``, optionally saving them to file(s).


Example Code
------------

We will generate plats for the following lands::

    T154N-R97W
    Sec 14: NE/4
    T153N-R96W
    Sec 1: Lots 1 - 3
    Sec 18: ALL

The code below will generate two plat pages, one for lands in T153N-R96W
and another for T154N-R97W.


.. code-block:: python

    import pytrsplat

    # Choose the 'letter' settings preset (8.5x11" paper, at 300ppi).
    letter_preset = pytrsplat.Settings.preset('letter')
    plat_group = pytrsplat.PlatGroup(settings=letter_preset)

    # If we've written lot definitions to .csv, we load them here.
    plat_group.lot_definer.read_csv('some_lot_definitions.csv')
    # Otherwise / additionally, we can assume 'default' lots.
    plat_group.lot_definer.allow_defaults = True
    plat_group.lot_definer.standard_lot_size = 40

    land_desc = """T154N-R97W
    Sec 14: NE/4
    T153N-R96W
    Sec 1: Lots 1 - 3
    Sec 18: ALL"""

    # Add the land description to the queue.
    # (`config` gets passed to pytrs for parsing.)
    plat_group.add_description(land_desc, config='clean_qq')

    # <Use `.add_description()` for any other lands that we want to add.>

    # Executing the queue will fill in the plat.
    plat_group.execute_queue()

    # Save to a ZIP file containing multiple PNG images.
    plat_group.output(fp=r'some\path\results.zip', image_format='png')

    # Or save to a single PDF, with each plat on its own page.
    plat_group.output(fp=r'some\path\results.pdf')
