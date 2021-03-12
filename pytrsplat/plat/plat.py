# Copyright (c) 2020, James P. Imes. All rights reserved.

"""
pytrsplat -- A module to generate land plat images of full townships
(6x6 grid) or single sections from PLSS land descriptions ('legal
descriptions'), using the pytrs parsing module.
"""

# TODO: Give the option to depict `.unhandled_lots` on plats somewhere.
#  i.e. warn users that certain lots were not incorporated onto the plat

from pathlib import Path
import os

# Packages from this project.
from pytrsplat.grid import TownshipGrid, SectionGrid
from pytrsplat.grid import LotDefinitions, TwpLotDefinitions, LotDefDB
from pytrsplat.grid import plssdesc_to_twp_grids
from pytrsplat.utils import filter_tracts_by_twprge, confirm_file_ext, cull_list
from pytrsplat.platsettings import Settings
from pytrsplat.platsettings.platsettings import _rel_path_to_abs
from pytrsplat.platqueue import PlatQueue, MultiPlatQueue

# For drawing the plat images, and coloring / writing on them.
from PIL import Image, ImageDraw, ImageFont

# piltextbox.TextBox gets customized into TractTextBox class here, for
# optionally writing pytrs.Tract info at the bottom of each Plat.
# More info at <https://github.com/JamesPImes/piltextbox>
from piltextbox import TextBox

# For parsing text of PLSS land descriptions into its component parts.
# More info at <https://github.com/JamesPImes/pyTRS>
import pytrs
from pytrs import version as pytrs_version


########################################################################
# Plat Objects
########################################################################

class Plat:
    """
    A configurable projection of land within a single PLSS 'township'
    (i.e. a standard 6x6 grid of 'sections', which in turn are a 4x4
    grid of aliquot quarter-quarters or 'QQs'). Can be output as a
    PIL.Image object or saved as a .png or .pdf file.

    NOTE: Optionally plat a single section (rather than the defafult 6x6
    grid of sections), with init parameter `only_section=<int>`.
    (Be sure to choose settings that are appropriate for a single-
    section plat. See pytrsplat.platsettings docs for more info.)

    Plat objects can be configured (size, font, colors, margins, etc.)
    at init, thus:
        -- Plat init parameter `settings=` takes either of these types:
            -- any `pytrsplat.Settings` object
            -- the name (i.e. a string) of a saved preset
                -- Get a current list of available presets:
                    `pytrsplat.Settings.list_presets()`
                -- View / edit / create presets with this GUI tool:
                    `pytrsplat.settingseditor.launch_settings_editor()`
    NOTE: Changes to settings after a Plat has been initialized will not
    necessarily have any effect. It is therefore best practice to
    configure a Settings object prior to initializing a Plat object.

    Plat objects can incorporate and/or be created from these objects:
        -- pytrs.Tract (created externally via the pytrs module)
            `.plat_tract()` -- to project a pytrs.Tract object onto an
                existing Plat object
            `Plat.from_tract()` -- to create a new Plat object from an
                an existing pytrs.Tract object
        -- pytrsplat.SectionGrid
            `.plat_section_grid()` -- to project a SectionGrid onto an
                existing Plat.
            `Plat.from_section_grid()` -- to create a new Plat object
                from an existing SectionGrid object.
        -- pytrsplat.TownshipGrid
            `.plat_township_grid()` -- to project a TownshipGrid onto an
                existing Plat.
            `Plat.from_township_grid()` -- to create a new Plat object
                from an existing TownshipGrid object.
        -- pytrsplat.PlatQueue
            `.process_queue()` -- to project each of the objects in a
                PlatQueue object onto an existing Plat.
            `.queue_add()` -- to add an object to an existing PlatQueue
                (stored in the Plat's `.pq` attribute)
            `Plat.from_queue()` -- to create a new Plat object from an
                existing PlatQueue object

    Plat objects can be output with this method:
        `.output()` -- Return a flattened PIL.Image.Image object of the
            plat, and optionally saves to file (currently supports .png
            and .pdf formats)

    For better results, pass an optional pytrsplat.TwpLotDefinition
    object (usually abbreviated 'tld') at init with parameter `tld=`, to
    specify which lots correspond with which QQ(s) in each respective
    section. (See more info in `pytrsplat.TwpLotDefinition` docs and
    `pytrsplat.LotDefDB` docs.)
    Also specify at init (parameter `allow_ld_defaults=<bool>`) whether
    'default' lot definitions are allowed as a fall-back option, when
    lots have not been explicitly defined for a given section.
    (Default lots are the 'usual' lots in Sections 1 - 7, 18, 19, 30,
    and 31 of a 'standard' township -- i.e. along the northern and
    western boundaries of a township. Potentially useful as a 'better-
    than-nothing' option, but not as reliable as user-specified lot
    definitions.)
    NOTE: All lots that were not defined but which the user tried to
    plat get added to a dict stored as the `.unhandled_lots_by_sec`
    attribute (keyed by section number integers).

    A pytrsplat.PlatQueue object is initialized for each Plat as `.pq`
    attribute. It can be added to with `.queue_add()` and processed with
    `.process_queue()`.
    """

    # TODO: Wherever TLD or LD is referenced in a kwarg, allow it
    #   to pull from self.tld or self.ld.

    def __init__(self, twp='', rge='', only_section=None, settings=None,
                 tld=None, allow_ld_defaults=False):
        """
        A 6x6 grid of sections (which are a 4x4 grid of QQs). Limit to
        only a 1x1 grid of a single section with init parameter
        `only_section=<int>`.

        :param twp: Township number and N/S (ex: '154n' or '7s')
        :param rge: Range number and E/W (ex: '97w' or '8e')
        :param only_section: To plat only a single section rather than
        the standard 6x6 grid, pass an integer (representing section
        number) here. Defaults to None.
        :param settings: How the Plat should be configured. May be
        passed as either:
            -- any `pytrsplat.Settings` object
            -- the name (i.e. a string) of a saved preset
                -- Get a current list of available presets:
                    `pytrsplat.Settings.list_presets()`
                -- View / edit / create presets with this GUI tool:
                    `pytrsplat.settingseditor.launch_settings_editor()`
        :param tld: A `pytrsplat.TwpLotDefinitions` object, which
        defines how each lot should be interpreted (in terms of its
        corresponding QQ or QQs).
        NOTE: If param `only_section=<int>` was passed (i.e. platting
        a single section, rather than the standard 6x6 grid), this will
        alternatively accept a `pytrsplat.LotDefinitions` object (which
        defines lots for a single section).
        :param allow_ld_defaults: Whether 'default' lot definitions are
        allowed as a fall-back option, when lots have not been
        explicitly defined for a given section. (Default lots are the
        'usual' lots in Sections 1 - 7, 18, 19, 30, and 31 of a
        'standard' township -- i.e. along the northern and western
        boundaries of a township. Potentially useful as a 'better-than-
        nothing' option, but not as reliable as user-specified lot
        definitions.)
        """
        self.twp = twp
        self.rge = rge
        self.twprge = twp + rge

        # NOTE: settings can be specified as a Settings object, or by
        # passing the name of an already saved preset (as a string).
        # Alternatively, to load settings data from a DIFFERENT source
        # (i.e. a '.txt' file saved somewhere OTHER than the presets
        # directory), first use the `Settings.from_file()` method, or
        # something like:
        #      `... settings=Settings.from_file(<whatever filepath>)...`
        if isinstance(settings, str):
            settings = Settings(preset=settings)

        # If settings was not specified, create a default Settings object.
        if settings is None:
            settings = Settings()
        elif isinstance(settings, str):
            # If passed as a string, it may be a preset or filepath to a
            # file that can be imported as a Settings object. Create
            # that Settings object now. (If that fails, it will be a
            # defualt Settings object anyway.)
            settings = Settings(settings)
        self.settings = settings

        # The main Image of the plat, and an ImageDraw object for it.
        self.image = Image.new('RGBA', settings.dim, Settings.RGBA_WHITE)
        self.draw = ImageDraw.Draw(self.image, 'RGBA')

        # Overlay on which we'll plat QQ's, and an ImageDraw object for it
        self.overlay = Image.new('RGBA', settings.dim, (255, 255, 255, 0))
        self.overlay_draw = ImageDraw.Draw(self.overlay, 'RGBA')

        # A dict of the sections and the (x,y) coords of their NWNW corner:
        self.sec_coords = {}

        # Draw the standard 36 sections, or the `only_section` (an int).
        # (If `only_section` is None, then will draw all 36 in 6x6 grid.
        # If specified, will draw only that section.)
        self._draw_all_sections(only_section=only_section)
        self.header = self._gen_header(only_section=only_section)

        if self.settings.write_header:
            self._write_header()

        # Text box for writing tract info (or other custom text)
        self.text_box = None
        # Create the TractTextBox (if possible with the provided
        # settings)
        # NOTE: `.text_box` might remain None, depending on settings!
        self.new_textbox()

        # A PlatQueue object holding elements/tracts that will be platted.
        self.pq = PlatQueue()

        # LotDefinitions and/or TwpLotDefinitions, in case we want to
        # call `.plat_tract()`.  The appropriate one will be set
        # shortly, depending on whether `only_section` was specified
        # (LD's apply to single sections, whereas TLD's apply to whole
        # townships).
        self.ld = None
        self.tld = None

        # If a LotDefDB object was passed instead of a TLD or LD object,
        # get the appropriate TLD from it (per twp+rge key); and if none
        # exists, then use the init-specified `allow_ld_defaults` to
        # determine whether to get a default TLD object, or an empty TLD
        # object.  Also then get the LD from it if `only_section` was
        # init-specified; and if no LD exists, also rely on
        # `allow_ld_defaults` to determine whether we get back a default
        # LD object, or an empty LD object.
        # (`force_tld_return=True` and `force_ld_return=True` ensure
        # that the returned objects are not None, but will be at least
        # an empty version of the respective TLD or LD objects.)
        if isinstance(tld, LotDefDB):
            tld = tld.get_tld(
                twp + rge, allow_ld_defaults=allow_ld_defaults,
                force_tld_return=True)
            if only_section is not None:
                ld = tld.get_ld(
                    only_section, allow_ld_defaults=allow_ld_defaults,
                    force_ld_return=True)
            else:
                ld = None
        elif isinstance(tld, LotDefinitions):
            ld = tld
            tld = None
        elif isinstance(tld, TwpLotDefinitions):
            ld = None
        else:
            # Fall back on default LD and TLD objects.
            ld = LotDefinitions()
            tld = TwpLotDefinitions()

        # And finally set the appropriate ld or tld.
        if only_section is not None:
            self.ld = ld
        else:
            self.tld = tld

        # Whether or not to pull default TLD's (and LD's) when undefined
        self.allow_ld_defaults = allow_ld_defaults

        # A dict to track all unhandled lots, keyed by section number (int)
        self.unhandled_lots_by_sec = {}

    @staticmethod
    def from_twprge(
            twprge='', only_section=None, settings=None, tld=None,
            allow_ld_defaults=False):
        """
        Generate a Plat object by specifying `twprge` as a single
        string, rather than as `twp` and `rge` separately.

        All other parameters have the same effect as vanilla __init__().
        """
        twp, rge, _ = pytrs.break_trs(twprge)

        return Plat(
            twp=twp, rge=rge, only_section=only_section, settings=settings,
            tld=tld, allow_ld_defaults=allow_ld_defaults)

    @staticmethod
    def from_queue(
            pq, twp='', rge='', only_section=None, settings=None, tld=None,
            allow_ld_defaults=False):
        """
        Generate and return a filled-in Plat object from a PlatQueue
        object (see: pytrsplat.queue.PlatQueue).


        All parameters have the same effect as vanilla __init__(),
        except arg `pq`.
        :arg pq: pytrsplat.queue.PlatQueue object to process at init.
        """
        sp_obj = Plat(
            twp=twp, rge=rge, only_section=only_section, settings=settings,
            tld=tld, allow_ld_defaults=allow_ld_defaults)
        sp_obj.process_queue(pq)
        return sp_obj

    def queue_add(self, plattable, tracts=None):
        """
        Queue up an object for platting in the PlatQueue stored in this
        Plat's `.pq` attribute -- i.e. pass through the arguments to the
        `.queue_add()` method of the PlatQueue object.

        NOTE: A PlatQueue can contain any number of plattable objects,
        but only one may be added via this method at a time. However,
        the list passed as `tracts=` (if any) can contain any number of
        pytrs.Tract objects.

        IMPORTANT: Passing an object in `tracts` does NOT add it to the
        queue to be platted -- only to the tracts whose text will be
        written at the bottom of the plat(s), if so configured.

        :param plattable: The object to be added to the queue. (Must be
        a type acceptable to PlatQueue -- see docs for those objects.)
        :param tracts: A list of pytrs.Tract objects whose text should
        eventually be written at the bottom of the Plat (assuming the
        Plat is configured in settings to write Tract text).
        NOTE: Objects added to `tracts` do NOT get drawn on the plat --
        only written at the bottom. But pytrs.Tract objects passed here
        as arg `plattable` are automatically added to `tracts`.
        :return: None
        """
        self.pq.queue_add(plattable, tracts)

    def process_queue(self, queue=None, allow_ld_defaults=None):
        """
        Process all objects in a PlatQueue object. If `queue=None` (the
        default), the PlatQueue object that will be processed is the one
        stored in this Plat's `.pq` attribute.
        """

        if allow_ld_defaults is None:
            allow_ld_defaults = self.allow_ld_defaults

        # If a different PlatQueue isn't otherwise specified, use the
        # Plat's own `.pq` from init.
        if queue is None:
            queue = self.pq

        for itm in queue:
            if isinstance(itm, pytrs.PLSSDesc):
                raise TypeError(
                    f"Cannot process pytrs.PLSSDesc objects in a PlatQueue "
                    f"object into a Plat object. "
                    f"Use MultiPlatQueue and MultiPlat objects instead.")
            elif not isinstance(itm, PlatQueue.SINGLE_PLATTABLES):
                raise TypeError(f"Cannot process type in PlatQueue: "
                                f"{type(itm)}")
            if isinstance(itm, SectionGrid):
                self.plat_section_grid(itm)
            elif isinstance(itm, TownshipGrid):
                self.plat_township_grid(itm)
            elif isinstance(itm, pytrs.Tract):
                self.plat_tract(
                    itm, write_tract=False, allow_ld_defaults=allow_ld_defaults)

        if self.settings.write_tracts and self.text_box is not None:
            self.text_box.write_all_tracts(queue.tracts)

    def _gen_header(self, only_section=None):
        """
        INTERNAL USE:
        Generate the text of a header containing the T&R and/or
        Section number.
        :param only_section: Specify with the appropriate integer when
        platting only a single section (rather than the usual 6x6 grid).
        """

        twp = str(self.twp)
        rge = str(self.rge)
        NS = 'undefined'
        EW = 'undefined'

        # Check that directions for twp and rge were appropriately specified.
        # If no direction was specified, then also check if (only) digits were
        # specified for twp and rge. If that's the case, arbitrarily assign 'n'
        # and 'w' as their directions (only for purposes of
        # `pytrs.decompile_twprge()` -- will be cut off before the header
        # itself is compiled).
        if not twp.lower().endswith(('n', 's')):

            if twp != '':
                try:
                    twp = str(int(twp))
                    twp = twp + 'n'
                except ValueError:
                    pass
        if not rge.lower().endswith(('e', 'w')):
            EW = 'undefined'
            if rge != '':
                try:
                    rge = str(int(rge))
                    rge = rge + 'w'
                except ValueError:
                    pass

        twpNum, try_NS, rgeNum, try_EW = pytrs.decompile_twprge(twp + rge)

        if try_NS == 'n':
            NS = 'North'
        elif try_NS == 's':
            NS = 'South'

        if try_EW == 'e':
            EW = 'East'
        elif try_EW == 'w':
            EW = 'West'

        if twp + rge == '':
            # If neither twp nor rge have been set, we will not write T&R in header.
            twptxt = ''
        elif 'TRerr' in [twpNum, rgeNum]:
            # If N/S or E/W were not specified, or if there's some other T&R error
            twptxt = '{Township/Range Error}'
        else:
            twptxt = f'Township {twpNum} {NS}, Range {rgeNum} {EW}'

        if only_section is not None:
            # If we're platting a single section.
            return f"{twptxt}{', ' * (len(twptxt) > 0)}Section {only_section}"
        else:
            return twptxt

    def _draw_all_sections(self, only_section=None):
        """
        INTERNAL USE:
        Draw the lines for 36 sections in the standard 6x6 grid; or draw
        a single section if `only_section=<int>` is specified.
        """

        # Saving some line space shortly by setting this variable:
        settings = self.settings

        w, h = settings.dim

        # Our township (a square) will either be a 6x6 grid of sections,
        # or a single section (i.e. 1x1).
        sections_per_side = 6
        if only_section is not None:
            sections_per_side = 1

        # Number of QQ divisions per section -- i.e. a 4x4 grid of QQ's,
        # or a square of 4 units (QQ's) by 4 units.
        qqs_per_sec_side = 4

        # Multiplying `settings.qq_side` (an int representing how long
        # we draw a QQ side) by `qq_per_sec_side` (an int representing
        # how many QQ's per section side) gets us the number of px per
        # section side.
        section_length = settings.qq_side * qqs_per_sec_side

        # We'll horizontally center our plat on the page. (4 is the number
        # of QQ's drawn per section)
        x_start = (w - (section_length * sections_per_side)) // 2

        # The plat will start this many px below the top of the page.
        y_start = settings.y_top_marg

        # PLSS sections "snake" from the NE corner of the township west
        # then down, then they cut back east, then down and west again,
        # etc., thus:
        #           6   5   4   3   2   1
        #           7   8   9   10  11  12
        #           18  17  16  15  14  13
        #           19  20  21  22  23  24
        #           30  29  28  27  26  25
        #           31  32  33  34  35  36
        #
        # ...so accounting for this is a little trickier:
        sec_nums = list(range(6, 0, -1))
        sec_nums.extend(list(range(7, 13)))
        sec_nums.extend(list(range(18, 12, -1)))
        sec_nums.extend(list(range(19, 25)))
        sec_nums.extend(list(range(30, 24, -1)))
        sec_nums.extend(list(range(31, 37)))

        # If drawing only one section, override that list with a
        # single-element list.
        if only_section is not None:
            sec_nums = [int(only_section)]

        # Generate section(s) on the plat, and number them.
        #
        # For each section, we start at (x_start, y_start) and move
        # `j` section-lengths over, and `i` section-lengths down,
        # at which point we are at the NW corner of the section,
        # from which we'll draw our 4x4 grid for that section and
        # mark the coord in the `.sec_coords` dict.
        #
        # Remember that sections_per_side is `1` if we're platting only
        # a single section, in which case i and j will only be 0.
        for i in range(sections_per_side):
            for j in range(sections_per_side):
                sec_num = sec_nums.pop(0)
                cur_x = x_start + section_length * j
                cur_y = y_start + section_length * i
                self._draw_sec((cur_x, cur_y), sec_num=sec_num)
                self.sec_coords[sec_num] = (cur_x, cur_y)

    def _write_header(self, text=None):
        """
        Write the header at the top of the page.
        :param text: The text to write as header. If not specified, will
        use the text stored in `self.header`.
        """

        if text is None:
            text = self.header

        W = self.image.width
        w, h = self.draw.textsize(text, font=self.settings.headerfont)

        # Center horizontally and write `settings.y_header_marg` px
        # above top section
        text_x = (W - w) / 2
        text_y = self.settings.y_top_marg - h - self.settings.y_header_marg
        self.draw.text(
            (text_x, text_y),
            text,
            font=self.settings.headerfont,
            fill=self.settings.headerfont_RGBA)

    def write_all_tracts(self, tracts):
        """
        Pass the list of pytrs.Tract objects onto the TractTextBox (if
        it exists), where they will be written.
        :param tracts: A list of pytrs.Tract objects that should be
        written to the TractTextBox (i.e. at the bottom of the Plat).
        :return: None
        """
        if self.text_box is not None:
            self.text_box.write_all_tracts(tracts)

    def write_tract(self, tract):
        """
        Pass the pytrs.Tract object onto the TractTextBox (if it
        exists), where they will be written.
        :param tract: A pytrs.Tract object that should be written to the
        TractTextBox (i.e. at the bottom of the Plat)
        :return: None
        """
        if self.text_box is not None:
            self.text_box.write_all_tracts([tract])

    def new_textbox(self):
        """
        INTERNAL USE:
        Create a TractTextBox object per the Plat's settings, for
        writing text at the bottom of the Plat.
        """

        x0, y0 = self.first_text_xy()
        # Bottom / right-most available x and y
        y1 = self.settings.dim[1] - self.settings.y_bottom_marg
        x1 = self.settings.dim[0] - self.settings.x_text_right_marg

        if x0 >= x1 or y0 >= y1:
            self.text_box = None
        else:
            self.text_box = TractTextBox(
                size=(x1 - x0, y1 - y0),
                bg_RGBA=(255, 255, 255, 255),
                typeface=self.settings.tractfont_typeface,
                font_size=self.settings.tractfont_size,
                font_RGBA=self.settings.tractfont_RGBA,
                settings=self.settings)

    def first_text_xy(self, settings=None):
        """
        INTERNAL USE:
        Get the top/left-most pixel available for writing text (i.e.
        top/left corner of where we can create and place a textbox), per
        Plat settings.
        """

        if settings is None:
            settings = self.settings

        # Number of QQ divisions per section -- i.e. a 4x4 grid of QQ's,
        # or a square of 4 units (QQ's) by 4 units.
        qqs_per_sec_side = 4

        # Multiplying `settings.qq_side` (an int representing how long
        # we draw a QQ side) by `qq_per_sec_side` (an int representing
        # how many QQ's per section side) gets us the number of px per
        # section side.
        sec_len = settings.qq_side * qqs_per_sec_side

        # If we platted all 36 sections, there are 6 per side (6x6 grid)
        secs_per_twp_side = 6
        if len(self.sec_coords.keys()) == 1:
            # But if we only platted one, it's a 1x1 grid.
            secs_per_twp_side = 1

        # First available x (i.e. the left margin)
        x0 = settings.x_text_left_marg

        # First available y below the plat...
        #   Starting at the top of the image, move down to the top of
        #   the plat itself...
        y0 = settings.y_top_marg
        #   Then go to the bottom of the plat...
        y0 += sec_len * secs_per_twp_side
        #   And then finally add the settings-specified buffer between
        #   the plat and the first line of text
        y0 += settings.y_px_before_tracts

        return (x0, y0)

    def output(self, filepath=None):
        """
        Merge the drawn overlay (i.e. filled QQ's) onto the base
        township plat image and return an Image object. Also include
        TractTextBox if it exists. Optionally save the image to file if
        `filepath=<filepath>` is specified (must be either '.png' or
        '.pdf' file).
        """
        merged = Image.alpha_composite(self.image, self.overlay)

        if self.text_box is not None:
            merged.paste(self.text_box.im, self.first_text_xy())

        # TODO: Add the option with *args to specify which layers get
        #   included in the output. That also will require me to have
        #   separate layers for QQ's, the grid, labels, etc.
        #   And that, in turn, will require me to change methods to
        #   /plat/ onto multiple layers.

        if filepath is not None:
            merged.save(filepath)

        return merged

    def show(self):
        """
        Flatten and display the plat PIL.Image.Image object (WARNING:
        will hang the program until the image is closed).
        """
        self.output().show()

    def plat_section_grid(
            self, sec_grid: SectionGrid, tracts=None, qq_fill_RGBA=None):
        """
        Project a pytrsplat.SectionGrid object onto an existing Plat
        object (i.e. fill any QQ hits per the `SectionGrid.qq_grid`
        values). Add any lot names in the `.unhandled_lots` list of the
        SectionGrid object to the Plat's `.unhandled_lots_by_sec` dict.

        :param sec_grid: The SectionGrid object whose `.qq_grid` values
        should be projected onto the Plat.
        :param tracts: A list of pytrs.Tract objects whose text should
        be written at the bottom of the Plat (if the Plat settings are
        configured to write Tract text).
        :param qq_fill_RGBA: The color with which to fill the QQs. (If
        not specified, uses whatever is configured in Plat's `.settings`
        attribute.)
        """
        sec_num = int(sec_grid.sec)
        if sec_num not in self.sec_coords.keys():
            # Direct section numbers that are not yet keys into 'section
            # 0', i.e. the meaningless 'junk drawer' section. (This
            # should only happen to section numbers > 36 or < 0.)
            sec_num = 0

        for coord in sec_grid.filled_coords():
            self.fill_qq(sec_num, coord, qq_fill_RGBA=qq_fill_RGBA)
        if self.settings.write_lot_numbers:
            self.write_lots(sec_grid)
        self.unhandled_lots_by_sec[sec_num] = sec_grid.unhandled_lots

        # Write the Tract data to the bottom of the plat (or not, per settings).
        if self.settings.write_tracts and self.text_box is not None:
            self.text_box.write_all_tracts(tracts)

    @staticmethod
    def from_section_grid(
            sec_grid: SectionGrid, single_sec=False, tracts=None,
            settings=None, tld=None, allow_ld_defaults=False):
        """
        Generate and return a new Plat object from a
        pytrsplat.SectionGrid object.

        All parameters have the same effect as vanilla __init__(),
        except:
        :arg sec_grid: pytrsplat.SectionGrid object to project at init.
        NOTE: `twp` and `rge` are pulled from the SectionGrid object,
        rather than specified as parameter.
        :param single_sec: Replaces `only_section=<int>` from __init__()
        in that it takes a bool, rather than an integer -- i.e. specify
        `single_sec=True` to plat a single section (with the section
        number pulled from the `.sec` attribute of the SectionGrid obj),
        or `False` (the default) to plat the full 6x6 grid of sections.
        :param tracts: A list of pytrs.Tract objects whose text should
        be written at the bottom of the Plat (if the Plat settings are
        configured to write Tract text).
        """

        only_section = None
        if single_sec:
            only_section = sec_grid.sec

        platObj = Plat(
            twp=sec_grid.twp, rge=sec_grid.rge, settings=settings, tld=tld,
            allow_ld_defaults=allow_ld_defaults, only_section=only_section)
        platObj.plat_section_grid(sec_grid)
        if platObj.settings.write_tracts:
            platObj.write_all_tracts(tracts)
        return platObj

    @staticmethod
    def from_township_grid(twp_grid, tracts=None, settings=None, tld=None,
            allow_ld_defaults=False):
        """
        Generate and return a new Plat object from a
        pytrsplat.TownshipGrid object.
        NOTE: `only_section` parameter is NOT allowed with this method.

        All parameters have the same effect as vanilla __init__(),
        except:
        :arg twp_grid: pytrsplat.TownshipGrid object to project at init.
        NOTE: `twp` and `rge` are pulled from the TownshipGrid object,
        rather than specified as parameter.
        :param tracts: A list of pytrs.Tract objects whose text should
        be written at the bottom of the Plat (if the Plat settings are
        configured to write Tract text).
        """
        twp = twp_grid.twp
        rge = twp_grid.rge
        platObj = Plat(
            twp=twp, rge=rge, settings=settings, tld=tld,
            allow_ld_defaults=allow_ld_defaults)
        platObj.plat_township_grid(twp_grid=twp_grid, tracts=tracts)
        return platObj

    def plat_township_grid(self, twp_grid, tracts=None, qq_fill_RGBA=None):
        """
        Project a pytrsplat.TownshipGrid object onto an existing Plat
        object (i.e. fill any QQ hits per all `SectionGrid.qq_grid`
        values in the TownshipGrid). Add any lot names in the
        `.unhandled_lots` list of each SectionGrid to the Plat's
        `.unhandled_lots_by_sec` dict.

        :param twp_grid: The TownshipGrid object whose subordinate
        SectionGrid objects should be projected onto the Plat (i.e.
        their `.qq_grid` attributes).
        :param tracts: A list of pytrs.Tract objects whose text should
        be written at the bottom of the Plat (if the Plat settings are
        configured to write Tract text).
        :param qq_fill_RGBA: The color with which to fill the QQs. (If
        not specified, uses whatever is configured in Plat's `.settings`
        attribute.)
        """

        # Generate the list of SectionGrid objs that have anything in them.
        # We use `include_pinged=True` to also include any sections
        # that were 'pinged' by a setter method, but may not have had
        # any values actually set (e.g., perhaps for a Tract object that
        # failed to generate any lots/QQ's when parsed by pytrs).
        sec_grid_list = twp_grid.filled_section_grids(include_pinged=True)

        # Plat each SectionGrid's filled QQ's onto our new overlay.
        for sec_grid in sec_grid_list:
            if self.settings.write_lot_numbers:
                # If so configured in settings, write lot numbers onto QQ's
                self.write_lots(sec_grid)
            self.plat_section_grid(sec_grid, qq_fill_RGBA=qq_fill_RGBA)

        # Write the Tract data to the bottom of the plat (or not, per settings).
        if self.settings.write_tracts and self.text_box is not None:
            self.text_box.write_all_tracts(tracts)

    @staticmethod
    def from_tract(
            tract: pytrs.Tract, settings=None, single_sec=False, ld=None,
            allow_ld_defaults=False):
        """
        Generate and return a new Plat object from a parsed pytrs.Tract
        object.

        :arg tract: pytrs.Tract object to project at init.
        NOTE: `twp` and `rge` are pulled from the Tract object, rather
        than specified as parameter.
        :param single_sec: Replaces `only_section=<int>` from __init__()
        in that it takes a bool, rather than an integer -- i.e. specify
        `single_sec=True` to plat a single section (with the section
        number pulled from the `.sec` attribute of the Tract obj), or
        `False` (the default) to plat the full 6x6 grid of sections.
        """
        twp = tract.twp
        rge = tract.rge

        only_sec = None
        if single_sec:
            sec = tract.sec
            if sec == 'secError':
                sec = 0
            only_sec = str(int(sec))

        platObj = Plat(
            twp=twp, rge=rge, settings=settings, only_section=only_sec,
            allow_ld_defaults=allow_ld_defaults)
        platObj.plat_tract(tract, ld=ld)
        return platObj

    def plat_tract(
            self, tract: pytrs.Tract, write_tract=None, ld=None,
            allow_ld_defaults=None):
        """
        Project a parsed pytrs.Tract object onto an existing Plat.

        :arg tract: pytrs.Tract object to project.
        :parameter write_tract: Whether to write the Tract text at the
        bottom of the Plat. If not specified, defaults to whatever the
        Plat settings are (in `.settings.write_tracts` attribute).
        :param ld: A pytrsplat.LotDefinitions object, for defining how
        each lot should be interpreted in terms of QQ's (i.e. 'L1'
        corresponds with 'NENE' in Sec 1, T154N-R97W).
        :param allow_ld_defaults: Whether to allow 'default' lot
        definitions where lots have not been explicitly defined for this
        section.
        """

        if allow_ld_defaults is None:
            allow_ld_defaults = self.allow_ld_defaults

        twp, rge = tract.twp, tract.rge
        sec = tract.sec
        if sec == 'secError':
            sec = 0
        sec = str(int(sec)).rjust(2, '0')

        # If the user fed in a LDDB or TwpLD, rather than a LotDefinitions
        # object, get the appropriate LD from the LDDB or TLD.
        if isinstance(ld, LotDefDB):
            ld = ld.trs(
                twp + rge + sec, allow_ld_defaults=allow_ld_defaults)
        elif isinstance(ld, TwpLotDefinitions):
            ld = ld.get_ld(
                int(sec), allow_ld_defaults=allow_ld_defaults,
                force_ld_return=True)

        # TODO: Check this block, maybe delete:
        # If the user requested default LotDefs (based on a 'standard'
        # township) by passing 'default' for `ld`, create that LD obj.
        if ld == 'default':
            ld = LotDefinitions(int(sec))

        # Or if not specified when `.plat_tract()` was called, pull from
        # the Plat object's attributes, as long as they were set.
        if ld is None:
            if self.ld is not None:
                ld = self.ld
            elif self.tld is not None:
                ld = self.tld.get_ld(
                    int(sec), allow_ld_defaults=allow_ld_defaults,
                    force_ld_return=True)
            else:
                # Otherwise, fall back to an empty LD.
                ld = LotDefinitions()

        # Generate a SectionGrid from the Tract, and plat it.
        secGrid = SectionGrid.from_tract(tract, ld=ld)
        self.plat_section_grid(secGrid)

        # If not specified whether to write tract, default to settings
        if write_tract is None:
            write_tract = self.settings.write_tracts

        if write_tract and self.text_box is not None:
            self.text_box.write_all_tracts([tract])

    def write_lots(self, sec_grid: SectionGrid):
        """
        Write lot numbers in the top-left corner of the respective QQs,
        according to the lots defined (or assumed) in a
        pytrsplat.SectionGrid object.

        (Location of the lot text, and font typeface, color, and size
        are all as dictated in this Plat's `.settings` attributes.)
        :param sec_grid: a pytrsplat.SectionGrid object whose lot
        numbers should be written into the Plat (regardless whether any
        of the lots are actually filled).
        """

        def write_lot(lots_within_this_QQ: list, grid_location: tuple):

            # Get the pixel location of the NWNW corner of the section:
            xy_start = self.sec_coords[int(sec_grid.sec)]
            x_start, y_start = xy_start

            # Break out the grid location of the QQ into x, y
            x_grid, y_grid = grid_location

            # Calculate the pixel location of the NWNW corner of the QQ.
            # (Remember that qq_side is the length of each side of a QQ square.)
            x_start = x_start + self.settings.qq_side * x_grid
            y_start = y_start + self.settings.qq_side * y_grid

            # Offset x and y, as configured in settings.
            x_start += self.settings.lot_num_offset_px
            y_start += self.settings.lot_num_offset_px

            # And lastly, join the lots into a string, and write the text.
            self.draw.text(
                (x_start, y_start),
                text=', '.join(lots_within_this_QQ),
                font=self.settings.lotfont,
                fill=self.settings.lotfont_RGBA
            )

        # Each qq_coords[y][x] contains a list of which lot(s) are at
        # (x,y) in this particular section.  For example, 'L1' thru 'L4'
        # in a standard Section 1 correspond to the N2N2 QQ's,
        # respectively -- so...
        #       qq_coords[0][0] -> ['L4']    # i.e. (0, 0), or the NWNW
        #       qq_coords[0][1] -> ['L3']    # i.e. (1, 0), or the NENW
        #       qq_coords[0][2] -> ['L2']    # i.e. (2, 0), or the NWNE
        #       qq_coords[0][3] -> ['L1']    # i.e. (3, 0), or the NENE
        # ... and all other coords would be an empty list...
        #       qq_coords[2][1] -> []    # i.e. (1,2), or the NESW
        #       qq_coords[3][3] -> []    # i.e. (3,3), or the SESE
        #       ...etc.
        qq_coords = sec_grid.lots_by_grid()

        for y in range(len(qq_coords)):
            for x in range(len(qq_coords[y])):
                lots = qq_coords[y][x]
                if lots == []:
                    continue
                clean_lots = []
                for lot in lots:
                    # Delete leading 'L' from each lot, leaving only the digit,
                    # and append to clean_lots
                    clean_lots.append(lot.replace('L', ''))
                write_lot(clean_lots, (x, y))

    def fill_qq(self, sec_num: int, grid_location: tuple, qq_fill_RGBA=None):
        """
        Fill in a single QQ on the plat.

        :param sec_num: An integer, being the number of a section that
        is already depicted on the plat (i.e. 1 - 36 for a standard 6x6
        plat; or the only section, if only one section is platted).
        NOTE: When 0 is passed as `sec_num`, this method returns
        immediately without filling any QQ's and without raising any
        errors. This is to handle flawed parses where the section number
        could not be identified in the original text (by the pytrs
        module), which typically sets the section number to 'secError'.
        Where this method gets called by other methods/functions in this
        module, 'secError' should first get converted to int 0 prior to
        passing it as `sec_num` in this method.
        :param grid_location: A coord value (0, 0) to (3, 3), which
        represents the QQ to be filled in the 4x4 grid -- i.e. the same
        coord system as SectionGrid objects, where (0, 0) is the NWNW
        and (3, 3) is the SESE.
            ex:  (0, 0) -> 'NWNW'
                 (1, 0) -> 'NENW'
                 (2, 2) -> 'NWSE'
        :param qq_fill_RGBA: The color with which to fill the QQs. (If
        not specified, uses whatever is configured in Plat's `.settings`
        attribute.)
        :return: None
        """

        if sec_num == 0:
            return

        if qq_fill_RGBA is None:
            # If not specified, pull from plat settings.
            qq_fill_RGBA = self.settings.qq_fill_RGBA

        # Get the pixel location of the NWNW corner of the sec_num:
        xy_start = self.sec_coords[sec_num]
        x_start, y_start = xy_start

        # Break out the grid location of the QQ into x, y
        x_grid, y_grid = grid_location

        # Calculate the pixel location of the NWNW corner of the QQ. (Remember
        # that qq_side is the length of each side of a QQ square.)
        x_start = x_start + self.settings.qq_side * x_grid
        y_start = y_start + self.settings.qq_side * y_grid

        # Draw the QQ
        self.overlay_draw.polygon(
            [(x_start, y_start),
             (x_start + self.settings.qq_side, y_start),
             (x_start + self.settings.qq_side, y_start + self.settings.qq_side),
             (x_start, y_start + self.settings.qq_side)],
            qq_fill_RGBA
        )

    def _draw_sec(self, top_left_corner, sec_num=None):
        """
        INTERNAL USE:
        Draw the 4x4 grid of a section with an ImageDraw object, at the
        specified `top_left_corner` (i.e. px coord). Optionally specify
        the section number with `sec_num=<int>`.
        (Pulls sizes, lengths, etc. from this Plat's `.settings`)
        """

        x_start, y_start = top_left_corner

        settings = self.settings

        # Set this attribute to a shorter-named variable, just to save line space.
        qqs = settings.qq_side

        # We'll draw QQ lines, then Q lines, then Section boundary -- in
        # that order, so that the color of the higher-order lines overrules
        # the lower-order lines.

        # Draw the quarter-quarter lines.
        qq_lines = [
            [(x_start + qqs * 1, y_start), (x_start + qqs * 1, y_start + qqs * 4)],
            [(x_start + qqs * 3, y_start), (x_start + qqs * 3, y_start + qqs * 4)],
            [(x_start, y_start + qqs * 1), (x_start + qqs * 4, y_start + qqs * 1)],
            [(x_start, y_start + qqs * 3), (x_start + qqs * 4, y_start + qqs * 3)]
        ]

        for qq_line in qq_lines:
            self.draw.line(
                qq_line,
                fill=settings.qql_RGBA,
                width=settings.qql_stroke)

        # Draw the quarter lines (which divide the section in half).
        q_lines = [
            [(x_start + qqs * 2, y_start), (x_start + qqs * 2, y_start + qqs * 4)],
            [(x_start, y_start + qqs * 2), (x_start + qqs * 4, y_start + qqs * 2)]
        ]

        for q_line in q_lines:
            self.draw.line(
                q_line,
                fill=settings.ql_RGBA,
                width=settings.ql_stroke)

        # Draw a white box in the center of the section.
        x_center, y_center = (x_start + qqs * 2, y_start + qqs * 2)
        cbwh = settings.centerbox_wh
        centerbox = [
            (x_center - (cbwh // 2), y_center - (cbwh // 2)),
            (x_center - (cbwh // 2), y_center + (cbwh // 2) + 3),
            (x_center + (cbwh // 2), y_center + (cbwh // 2)),
            (x_center + (cbwh // 2), y_center - (cbwh // 2)),
        ]
        self.draw.polygon(centerbox, Settings.RGBA_WHITE)

        # Draw the outer bounds of the section.
        sec_sides = [
            [(x_start, y_start), (x_start + qqs * 4, y_start)],
            [(x_start + qqs * 4, y_start), (x_start + qqs * 4, y_start + qqs * 4)],
            [(x_start + qqs * 4, y_start + qqs * 4), (x_start, y_start + qqs * 4)],
            [(x_start, y_start + qqs * 4), (x_start, y_start)],
        ]

        for side in sec_sides:
            self.draw.line(
                side,
                fill=settings.sec_line_RGBA,
                width=settings.sec_line_stroke)

        # If requested, write in the section number
        if sec_num is not None and settings.write_section_numbers:
            # TODO: DEBUG -- Section numbers are printing very slightly
            #   farther down than they should be. Figure out why.
            w, h = self.draw.textsize(str(sec_num), font=settings.secfont)
            self.draw.text(
                (x_center - (w // 2), y_center - (h // 2)),
                str(sec_num),
                fill=settings.secfont_RGBA,
                font=settings.secfont)


########################################################################
# MultiPlat objects - for creating / processing a collection of Plat objects
########################################################################

class MultiPlat:
    """
    An object to create, process, hold, and output one or multiple Plat
    objects, all using identical settings and general parameters. For
    example, generating one or more Plat objects from a parsed
    pytrs.PLSSDesc object (which can cover one or multiple townships).

    MultiPlat objects can be configured (size, font, colors, margins,
    etc.) at init, thus:
        -- MultiPlat init parameter `settings=` accepts anything that
            is also acceptable to Plat init parameter `settings=`.
    NOTE: Changes to settings after a MultiPlat has been initialized
    will not necessarily have any effect. It is therefore best practice
    to configure a Settings object prior to initializing a MultiPlat
    object.

    MultiPlat objects can incorporate and/or be created from these
    objects directly:
        -- pytrs.PLSSDesc (created externally via the pytrs module)
            `.plat_plssdesc()` -- to process a pytrs.PLSSDesc object
                into an existing MultiPlat object
            `MultiPlat.from_plssdesc()` -- to create a new MultiPlat
                object from an an existing pytrs.PLSSDesc object
            NOTE: To process more than one PLSSDesc object, use the
                MultiPlatQueue options, which filter the data in
                PLSSDesc objects into respective Twp/Rge before platting
                them, so that only one Plat object is generated per
                township. Calling `.plat_plssdesc()` repeatedly on a
                single MultiPlat object will create new Plat objects
                every time.
        -- pytrsplat.MultiPlatQueue
            `.process_queue()` -- to process all of the objects in a
                MultiPlatQueue object into an existing MultiPlat
            `.queue_add()` -- to add an object to an existing
                MultiPlatQueue (stored in the MultiPlat's `.mpq`
                attribute)
            `.queue_add_text()` -- to parse the raw text of a PLSS
                land description, then add it to an existing
                MultiPlatQueue (stored in the MultiPlat's `.mpq`
                attribute)
            `MultiPlat.from_queue()` -- to create a new MultiPlat object
                from an existing MultiPlatQueue object
        -- Raw text of a PLSS land description (i.e. a string):
            `MultiPlat.from_unparsed_text()` -- to create a new
                MultiPlat object from the raw text of a PLSS land
                description (i.e. parse the text into a pytrs.PLSSDesc
                object behind-the-scenes, and generate a MultiPlat from
                that)

        In addition to the above, MultiPlat objects can *indirectly*
        process any of the following object types, by first adding them
        to a MultiPlatQueue object and then using any of the above
        options for processing MultiPlatQueue objects:
                -- pytrs.PLSSDesc
                -- pytrs.Tract
                -- pytrsplat.SectionGrid
                -- pytrsplat.TownshipGrid
                -- pytrsplat.PlatQueue

    For better results, optionally pass a pytrsplat.LotDefDB object (or
    the filepath to a .csv file that can be read into a LotDefDB object)
    to init parameter `lddb=`, to specify how to handle lots -- i.e.
    which QQ's are intended by which lots. (See more info in docs for
    `pytrsplat.LotDefDB`.)
    Also specify at init (parameter `allow_ld_defaults=<bool>`) whether
    'default' lot definitions are allowed as a fall-back option, when
    lots have not been explicitly defined for a given section.
    (Default lots are the 'usual' lots in Sections 1 - 7, 18, 19, 30,
    and 31 of a 'standard' township -- i.e. along the northern and
    western boundaries of a township. Potentially useful as a 'better-
    than-nothing' option, but not as reliable as user-specified lot
    definitions.)
    NOTE: All lots that were not defined but which the user tried to
    plat are compiled into a nested dict via the `.all_unhandled_lots`
    property (keyed by twprge).

    MultiPlat objects can be output with these methods:
        `.output()` -- Return a list of a flattened PIL.Image.Image
            object for each Plat generated.
        `.output_to_pdf()` -- Save the images as a PDF
        `.output_to_png()` -- Save each image as a separate PNG
        NOTE: The subordinate Plat objects are stored in `.plats`, where
            they remain pytrsplat.Plat objects but not yet 'flattened'
            images. They get flattened via the above output methods.

    A pytrsplat.MultiPlatQueue object is initialized for each MultiPlat
    as `.mpq` attribute. It can be added to with `.queue_add()` and
    `.queue_add_text()`, and processed with `.process_queue()`.
    """

    # TODO: Wherever LDDB, TLD, or LD is referenced in a kwarg, allow it
    #   to pull from self.lddb.

    # TODO: Figure out a good way to organize the plats. I'm thinking a
    #  dict, keyed by T&R. Currently, it's a list.

    def __init__(self, settings=None, lddb=None, allow_ld_defaults=False):
        """
        An object to create, process, hold, and output one or multiple
        Plat objects, all using identical settings and general
        parameters.

        :param settings: How each subordinate Plat should be configured.
        May be passed as either:
            -- any `pytrsplat.Settings` object
            -- the name (i.e. a string) of a saved preset
                -- Get a current list of available presets:
                    `pytrsplat.Settings.list_presets()`
                -- View / edit / create presets with this GUI tool:
                    `pytrsplat.settingseditor.launch_settings_editor()`
        :param lddb: A `pytrsplat.LotDefDB` object, which defines how
        each lot should be interpreted (in terms of its corresponding QQ
        or QQs). May also pass the filepath to a .csv file containing
        appropriately formatted lot definitions. (See documentation on
        `pytrsplat.LotDefDB` objects for acceptable .csv formatting.)
        :param allow_ld_defaults: Whether 'default' lot definitions are
        allowed as a fall-back option, when lots have not been
        explicitly defined for a given section. (Default lots are the
        'usual' lots in Sections 1 - 7, 18, 19, 30, and 31 of a
        'standard' township -- i.e. along the northern and western
        boundaries of a township. Potentially useful as a 'better-than-
        nothing' option, but not as reliable as user-specified lot
        definitions.)
        """
        # If settings was not specified, create a default Settings object.
        if settings is None:
            settings = Settings()
        elif isinstance(settings, str):
            # If passed as a string, it should be the name of a preset.
            # Create that Settings object now. (Will throw off an error
            # if not an existing preset name.)
            settings = Settings(preset=settings)
        self.settings = settings

        # A list of generated plats
        self.plats = []

        # A MultiPlatQueue object holding PlatQueue objects (which in
        # turn hold elements/tracts that will be platted).
        self.mpq = MultiPlatQueue()

        # Try converting lddb to a pathlib.Path object (e.g., if it was
        # passed as a string). If unsuccessful, it seems the user has
        # NOT tried to pass a filepath as `lddb`.
        try:
            lddb = Path(lddb)
        except TypeError:
            pass

        # LotDefDB object for defining lots in subordinate plats (if not
        # specified when platting objects).
        if isinstance(lddb, Path):
            # If a string is passed, we assume it's a filepath to a file
            # that can be read into a LDDB object (e.g., a .csv file).
            # Convert to LDDB object now. (Will throw off errors if it
            # does not lead to a '.csv' file.)
            lddb = LotDefDB(from_csv=lddb)
        if not isinstance(lddb, LotDefDB):
            # If there's no valid LDDB by now, default to an empty LDDB.
            lddb = LotDefDB()
        self.lddb = lddb

        # Whether or not to pull default TLD's when they are not set
        # in our LotDefDB. (See `Grid.LotDefDB.get_tld()` for more info)
        self.allow_ld_defaults = allow_ld_defaults

    @property
    def all_unhandled_lots(self):
        """
        Get a nested dict of all of the unhandled lots in each plat,
        keyed by T&R.
        """
        uhl = {}
        for pl_obj in self.plats:
            uhl[pl_obj.twprge] = pl_obj.unhandled_lots_by_sec
        return uhl

    @staticmethod
    def from_queue(mpq, settings=None, lddb=None, allow_ld_defaults=False):
        """
        Generate and return a MultiPlat object from a MultiPlatQueue
        object.

        All parameters are identical to vanilla __init__() except:
        :param mpq: a pytrsplat.MultiPlatQueue object whose contents
        should be processed immediately at init.
        """

        mp_obj = MultiPlat(
            settings=settings, lddb=lddb, allow_ld_defaults=allow_ld_defaults)
        mp_obj.process_queue(mpq)
        return mp_obj

    def queue_add(self, plattable, twprge='', tracts=None):
        """
        Queue up an object for platting -- i.e. pass through the
        arguments to the `.queue_add()` method in the MultiPlat's
        MultiPlatQueue object (its `.mpq` attribute).

        NOTE: If a pytrs.PLSSDesc object is passed as the `plattable`,
        then `twprge` and `tracts` are ignored, but rather are deduced
        automatically (because there can be more than one T&R from a
        single PLSSDesc object).

        NOTE ALSO: If a pytrs.Tract object is passed as the `plattable`,
        then `twprge` is optional (as long as the Tract object has a
        specified `.twp` and `.rge`), and `tracts` is always optional.
        However, the Tract object's `.twp` and `.rge` will NOT overrule
        a kwarg-specified `twprge=` (if any).

        :param plattable: The object to be added to the queue. (Must be
        a type acceptable to MultiPlatQueue -- see docs for those
        objects.)
        :param twprge: A string of the Twp/Rge (e.g., '154n97w' or
        '1s8e') to which the plattable object belongs.
            ex: If queuing up a pytrs.SectionGrid object for Section 1,
                T154N-R97W, then `twprge` should be '154n97w'.
        NOTE: `twprge` is ignored when a pytrs.PLSSDesc object is passed
            as `plattable`.
        NOTE ALSO: `twprge` is optional when a pytrs.Tract object is
            passed as `plattable`, as long as the Tract object has
            appropriate `.twp` and `.rge` attributes. If `twprge=` is
            specified in this method, that will control over whatever is
            in the Tract object's `.twp` and `.rge` attributes.
        :param tracts: A list of pytrs.Tract objects whose text should
        eventually be written at the bottom of the appropriate Plat
        (assuming the MultiPlat is configured in settings to write Tract
        text).
        NOTE: Objects added to `tracts` do NOT get drawn on the plat --
        only written at the bottom. But pytrs.Tract objects passed here
        as arg `plattable` are automatically added to `tracts`.
        """
        self.mpq.queue_add(plattable=plattable, twprge=twprge, tracts=tracts)

    def queue_add_text(self, text, config=None):
        """
        Parse the raw text of a PLSS land description (optionally using
        `config=` parameters -- see pytrs docs), and add the resulting
        pytrs.PLSSDesc object to this MultiPlat's queue (`.mpq`) -- by
        passing through the arguments to the `.queue_add_text()` method
        in the Plat's MultiPlatQueue object.
        """
        self.mpq.queue_add_text(text=text, config=config)

    def process_queue(self, queue=None, allow_ld_defaults=None):
        """Process all objects in a MultiPlatQueue object. If `queue=None`,
        the MultiPlatQueue object that will be processed is this
        MultiPlat's `.mpq` attribute."""

        if allow_ld_defaults is None:
            allow_ld_defaults = self.allow_ld_defaults

        # If a different MultiPlatQueue isn't otherwise specified, use
        # the MultiPlat's own `.mpq` from init.
        if queue is None:
            queue = self.mpq

        for twprge, pq in queue.items():
            tld = self.lddb.get_tld(twprge, allow_ld_defaults=allow_ld_defaults)
            pl_obj = Plat.from_twprge(
                twprge, settings=self.settings, tld=tld,
                allow_ld_defaults=allow_ld_defaults)
            pl_obj.process_queue(pq)
            self.plats.append(pl_obj)

    @staticmethod
    def from_plssdesc(
            plssdesc_obj: pytrs.PLSSDesc, settings=None, lddb=None,
            allow_ld_defaults=False):
        """
        Generate a MultiPlat from a parsed pytrs.PLSSDesc object.
        (lots/QQs must be parsed within the pytrs.Tract objects in the
        PLSSDesc object's `.parsedDesc` attribute for any QQ's to be
        filled on the resulting plats -- see pytrs docs for more info.)
        """

        mp_obj = MultiPlat(
            settings=settings, lddb=lddb, allow_ld_defaults=allow_ld_defaults)

        mp_obj.plat_plssdesc(
            plssdesc_obj, lddb=lddb, allow_ld_defaults=allow_ld_defaults)

        return mp_obj

    def plat_plssdesc(
            self, plssdesc_obj: pytrs.PLSSDesc, lddb=None,
            allow_ld_defaults=False):
        """
        Process a parsed pytrs.PLSSDesc object into an existing
        MultiPlat.

        :arg plssdesc_obj: a pytrs.PLSSDesc object (whose subordinate
        pytrs.Tract objects have also been parsed into lots/QQs) to
        process into this MultiPlat.
        :param lddb: A pytrsplat.LotDefDB object, for defining how
        each lot should be interpreted in terms of QQ's (i.e. 'L1'
        corresponds with 'NENE' in Sec 1, T154N-R97W).
        :param allow_ld_defaults: Whether to allow 'default' lot
        definitions where lots have not been explicitly defined for this
        section.
        """
        # Generate a dict of TownshipGrid objects from the PLSSDesc object,
        # keyed by T&R ('000x000y' or fewer digits)
        twp_grids = plssdesc_to_twp_grids(
            plssdesc_obj, lddb=lddb, allow_ld_defaults=allow_ld_defaults)

        # Get a dict linking the this PLSSDesc's parsed Tracts to their
        # respective T&R's (keyed by T&R -- same as twp_grids dict)
        twp_to_tract = filter_tracts_by_twprge(plssdesc_obj.parsed_tracts)

        # Generate Plat object of each township, and append it to `self.plats`
        for k, v in twp_grids.items():
            pl_obj = Plat.from_township_grid(
                v, tracts=twp_to_tract[k], settings=self.settings)
            self.plats.append(pl_obj)

    @staticmethod
    def from_unparsed_text(
            text, config=None, settings=None, lddb=None, allow_ld_defaults=False):
        """Parse the text of a PLSS land description (optionally using
        `config=` parameters -- see pytrs docs), and generate Plat(s)
        for the lands described. Returns a MultiPlat object."""

        descObj = pytrs.PLSSDesc(text, config=config, init_parse_qq=True)
        return MultiPlat.from_plssdesc(
            descObj, settings=settings, lddb=lddb,
            allow_ld_defaults=allow_ld_defaults)

    def show(self, index: int):
        """
        Flatten and display the plat PIL.Image.Image object,
        specifically the one in the `.plats` list at the specified
        `index`.
        (WARNING: will hang the program until the image is closed).

        :param index: An integer, specifying which Plat object to view
        (i.e. the index of the list stored in the `.plats` attribute.)
        """
        self.plats[index].output().show()

    def output_to_pdf(self, filepath, pages=None):
        """
        Save all of the Plat images to a single PDF, optionally limiting
        to only some of the pages.

        :param filepath: The filepath to which to save the .pdf file.
        Must end in '.pdf'.
        IMPORTANT: Will NOT prompt before overwriting.
        :param pages: Which pages to include (indexed to 0), passed as
        a single int, or a list of ints. If not specified, will output
        all pages.
        """
        # TODO: Use a better module for generating PDF's.

        if not confirm_file_ext(filepath, '.pdf'):
            raise ValueError('filepath must end with \'.pdf\'')

        output_list = self.output(pages=pages)

        if len(output_list) == 0:
            return

        im1 = output_list.pop(0)
        im1.save(filepath, save_all=True, append_images=output_list)

    def output_to_png(self, filepath, pages=None):
        """
        Save the Plat images to .png (or multiple .png files, if there
        is more than one Plat in `.plats`), optionally limiting to only
        some of the pages.

        :param filepath: The filepath to which to save the .png file(s).
        Must end in '.png'.
        IMPORTANT: If multiple plats are output, then numbers (from
        '_000') will be added to the end of each, before the file
        extension.
        ALSO IMPORTANT: Will NOT prompt before overwriting.
        :param pages: Which pages to include (indexed to 0), passed as
        a single int, or a list of ints. If not specified, will output
        all pages.
        """

        if not confirm_file_ext(filepath, '.png'):
            raise ValueError('filepath must end with \'.png\'')

        output_list = self.output(pages=pages)

        if len(output_list) == 0:
            return
        elif len(output_list) == 1:
            output_list[0].save(filepath)
        else:
            i = 0
            ext = '.png'
            fp = filepath[:-len(ext)]
            while len(output_list) > 0:
                filepath = f"{fp}_{str(i).rjust(3,'0')}{ext}"
                output_list.pop(0).save(filepath)
                i += 1

    def output(self, pages=None) -> list:
        """
        Return a list of flattened Image objects from the Plat objects
        in the `.plats` attribute.

        :param pages: Which pages to include (indexed to 0), passed as
        a single int, or a list of ints. If not specified, will output
        all pages.
        :return: A list of PIL.Image.Image objects, being flattened
        images of the Plat objects.
        """
        plat_ims = []
        for p in self.plats:
            plat_ims.append(p.output().convert('RGB'))

        # Cull our list of plat images to only the pages requested
        # (if not specified -- i.e. `pages=None` -- returns all images)
        output_list = cull_list(plat_ims, pages)

        return output_list


class TractTextBox(TextBox):
    """
    INTERNAL USE:
    A piltextbox.TextBox object, with additional methods for writing
    pytrs.Tract data at the bottom of the Plat.

    IMPORTANT: After init, any changes to font in the Settings object
    will have NO EFFECT on the TractTextBox.
    """

    def __init__(
            self, size: tuple, typeface=None, font_size=None,
            bg_RGBA=Settings.RGBA_WHITE, font_RGBA=Settings.RGBA_BLACK,
            paragraph_indent=None, new_line_indent=None, spacing=None,
            settings=None):
        """
        :param size: 2-tuple of (width, height).
        :param typeface: Which typeface to use, passed either as the
        filepath to a .ttf font (absolute path, or relative to the
        'pytrsplat/platsettings/' directory), or as a key for the
        Settings.TYPEFACES dict (i.e. as the name of a stock font, such
        as 'Mono (Bold)').
        :param font_size: The size of the font to create.
        :param bg_RGBA: 4-tuple of the background color. (Defaults to
        white, full opacity.)
        :param font_RGBA: 4-tuple of the font color. (Defaults to black,
        full opacity.)
        :param paragraph_indent: How many spaces (i.e. characters, not
        px) to write before the first line of a new paragraph.
        :param new_line_indent: How many spaces (i.e. characters, not
        px) to write before every subsequent line of a paragraph.
        :param spacing: How many px above each new line.
        :param settings: A pytrsplat.Settings object (or the name of a
        preset, i.e. a string), which can specify various relevant
        attribs for this TractTextBox object. (In the event that an
        attribute was set in the Settings object but ALSO specified as
        init parameters here; the init parameters will control.)
        """
        # If settings is not specified, get a default Settings object.
        if settings is None:
            settings = Settings()
        elif isinstance(settings, str):
            settings = Settings(preset=settings)
        # If these are not specified, pull them from settings
        if typeface is None:
            typeface = settings.tractfont_typeface
        if font_size is None:
            font_size = settings.tractfont_size
        if paragraph_indent is None:
            paragraph_indent = settings.paragraph_indent
        if new_line_indent is None:
            new_line_indent = settings.new_line_indent
        if spacing is None:
            spacing = settings.y_px_between_tracts

        # Check if `typeface` is the *name* of a stock font name (i.e. a
        # key in Settings.TYPEFACES), and if so, get the corresponding
        # absolute filepath.
        # If not a font name, then check if `typeface` is a valid
        # filepath.
        # If not a valid filepath, check if it is a relative filepath
        # (relative to 'pytrsplat/platsettings/' dir -- i.e. a stock
        # font), and if so, convert to that absolute path.
        if typeface in Settings.TYPEFACES.keys():
            typeface = Settings.TYPEFACES[typeface]
        elif not os.path.isfile(typeface):
            candidate_fp = _rel_path_to_abs(typeface)
            if os.path.isfile(candidate_fp):
                typeface = candidate_fp

        TextBox.__init__(
            self, size=size, typeface=typeface, font_size=font_size,
            bg_RGBA=bg_RGBA, font_RGBA=font_RGBA, spacing=spacing,
            paragraph_indent=paragraph_indent, new_line_indent=new_line_indent)

        self.settings = settings

    def write_all_tracts(self, tracts=None, cursor='text_cursor',
            justify=None):
        """
        Write the descriptions of each parsed pytrs.Tract object at the
        current coord of the specified `cursor`. Updates the coord of
        the `cursor` used.

        :param tracts: A list of pytrs.Tract objects, whose descriptions
        should be written.
        :param cursor: The name of an existing cursor, at whose coord
        the text should be written. (Defaults to 'text_cursor')
        :param justify: Whether to justify the tract text, if it breaks
        onto multiple lines. (Defaults to whatever is set in
        `self.settings.justify_tract_text`)
        :return:
        """

        if tracts is None:
            return

        # Copy tracts, because we'll pop elements from it.
        ctracts = tracts.copy()

        def write_warning(num_unwritten_tracts, tracts_written):
            """
            Could not fit all tracts on the page. Write a warning to
            that effect at the bottom of the page.
            """

            # If we wrote at least one tract, we want to include the word
            # 'other', to avoid any confusion.
            other = ''
            if tracts_written > 0:
                other = ' other'

            plural = ''
            if num_unwritten_tracts > 1:
                plural = 's'

            warning = (f'[No space to write {num_unwritten_tracts}{other} '
                       f'tract{plural}]')

            self.write_line(
                text=warning, cursor=cursor, override_legal_check=True,
                font_RGBA=self.settings.warningfont_RGBA)

        pull_ejector = False
        tracts_written = 0

        while len(ctracts) > 0:

            if pull_ejector or self.on_last_line(cursor=cursor):
                # We either failed to write the last full tract because it would
                # have gone outside our textbox, or the next line is the last
                # available within our textbox, and we have at least one more
                # tract yet to write. So write a warning now.
                num_unwritten = len(ctracts)
                write_warning(num_unwritten, tracts_written)
                break

            tract = ctracts.pop(0)

            # We will reserve_last_line so we can write a warning,
            # unless this is the last tract to write.
            reserve_last_line = len(ctracts) != 0

            font_RGBA = self.font_RGBA
            if len(tract.lots_qqs) == 0 or tract.sec == 'secError':
                # If no lots/QQs were identified, or if this tract has a
                # 'secError' (i.e. it was a flawed parse where the section
                # number could not be successfully deduced -- in which case it
                # could not have been projected onto this plat), then we'll
                # write the tract in the configured warning color
                font_RGBA = self.settings.warningfont_RGBA
            # Any lines that could not be written will be returned and stored
            # in list `unwrit_lines` (i.e. empty if all successful)
            unwrit_lines = self.write_tract(
                cursor=cursor, tract=tract, font_RGBA=font_RGBA,
                reserve_last_line=reserve_last_line, justify=justify)
            if unwrit_lines is not None:
                # We couldn't write all of our lines, so let's bail.
                pull_ejector = True

            tracts_written += 1

    def write_tract(
            self, tract: pytrs.Tract, cursor='text_cursor', font_RGBA=None,
            override_legal_check=False, reserve_last_line=False,
            justify=None):
        """
        Write the description of the parsed pytrs.Tract object at the
        current coord of the specified `cursor`. First confirms that
        writing the text would not go past margins; and if so, will not
        write it. Updates the coord of the `cursor` used.

        :param tract: a pytrs.Tract object, whose description should be
        written.
        :param cursor: The name of an existing cursor, at whose coord
        the text should be written. (Defaults to 'text_cursor')
        :param font_RGBA: A 4-tuple containing RGBA value to use
        (defaults to configuration in settings)
        :param override_legal_check: Ignore whether it is past the
        margins. (`False` by default)
        :param reserve_last_line: A bool, whether or not the last line
        (before the margins are broken) should be reserved -- i.e., if
        a tract will be written all the way to the end of the margin,
        this will dictate whether or not to stop before writing that
        last line, perhaps to write a warning message instead. (Defaults
        to `False`)
        :param justify: Whether to justify the tract text, if it breaks
        onto multiple lines. (Defaults to whatever is set in
        `self.settings.justify_tract_text`)
        :return: Returns None if the entire tract text was written, but
        returns a piltextbox.UnwrittenLines object if at least one line
        of text could not be written.
        """

        # Extract the text of the TRS+description from the Tract object.
        text = tract.quick_desc()

        # If font color not otherwise specified, pull from settings.
        if font_RGBA is None:
            font_RGBA = self.settings.tractfont_RGBA

        if justify is None:
            justify = self.settings.justify_tract_text

        # Write all lines in the description. If any lines could not be written,
        # store them in list `unwrit_lines`. We reserve_last_line here, because
        # we want to write an ellipses if more than 1 line remains.
        unwrit_lines = self.write_paragraph(
            text=text, cursor=cursor, font_RGBA=font_RGBA, justify=justify,
            reserve_last_line=True, override_legal_check=override_legal_check)

        if reserve_last_line or unwrit_lines is None:
            return unwrit_lines

        # If we had only one more line to write, write it; otherwise,
        # write an ellipses in red
        if unwrit_lines.remaining == 1:
            final_line = unwrit_lines._stage_next_line()
            single_unwrit = self.write_line(final_line, justify=justify)
        else:
            font_RGBA = self.settings.warningfont_RGBA
            single_unwrit = self.write_line(
                text="[...]", indent=self.new_line_indent, font_RGBA=font_RGBA)

        if single_unwrit is not None:
            # If that last line couldn't be written, unstage it, and
            # return the full unwrit_lines
            unwrit_lines._unstage()
            return unwrit_lines
        else:
            # Otherwise, if it was successfully written, pop it off, and
            # return the remaining unwrit_lines (if any)
            unwrit_lines._successful_write()
            if unwrit_lines.remaining == 0:
                return None
            return unwrit_lines


########################################################################
# Public / Convenience Methods
########################################################################

def text_to_plats(
        text, config=None, settings=None, lddb=None,
        output_filepath=None, allow_ld_defaults=False) -> list:
    """
    (A convenience function, for simplified interaction with MultiPlat
    objects.) Parse the raw text of a PLSS land description (optionally
    using `config=` parameters -- see pytrs.Config docs), and generate
    plat(s) for the lands described (i.e. PIL.Image.Image objects.
    Configure the plats with `settings=` parameter (see
    ``pytrsplat.Settings`` docs). Optionally output to .png or .pdf with
    `output_filepath=` (end with '.png' or '.pdf' to specify the output
    file type).  Returns a list of PIL.Image.Image objects of the plats.

    All parameters have the same effect as for init of MultiPlat objects
    except:
    :param text: The raw text of a PLSS land description to be platted.
    :param config: Optional configurable parameters for how the raw
    description should be parsed (see pytrs docs, especially
    pytrs.Config).
    :param output_filepath: If specified, the generated images will be
    saved to file(s). Defaults to None.
    NOTE: Must end in either '.pdf' or '.png'.
    IMPORTANT: If '.png' is used and multiple plats are output, then
    numbers (from '_000') will be added to the end of each, before the
    file extension. (This does not apply for '.pdf' files.)
    ALSO IMPORTANT: Will NOT prompt before overwriting.
    :return: A list of PIL.Image.Image objects, being flattened images
    of the generated plats.
    """

    mp = MultiPlat.from_unparsed_text(
        text=text, config=config, settings=settings, lddb=lddb,
        allow_ld_defaults=allow_ld_defaults)
    if output_filepath is not None:
        if confirm_file_ext(output_filepath, '.pdf'):
            mp.output_to_pdf(output_filepath)
        elif confirm_file_ext(output_filepath, '.png'):
            mp.output_to_png(output_filepath)
    return mp.output()
