# Copyright (c) 2020, James P. Imes. All rights reserved.

"""
pyTRSplat -- A module to generate land plat images of full townships
(6x6 grid) or single sections from PLSS land descriptions ('legal
descriptions'), using the pyTRS parsing module.
"""

# TODO: Give the option to depict `.unhandled_lots` on plats somewhere.
#  i.e. warn users that certain lots were not incorporated onto the plat

from pathlib import Path

# Submodules from this project.
from Grid import TownshipGrid, SectionGrid, LotDefinitions, TwpLotDefinitions, LotDefDB
from Grid import plssdesc_to_grids, filter_tracts_by_twprge, confirm_file_ext
from PlatSettings import Settings
from PlatQueue import PlatQueue, MultiPlatQueue
# TODO: Note: TextBox is being spun off into its own project, but is
#   kept here for the moment. Shouldn't change any functionality, beyond
#   the import.
from TextBox import TextBox

# For drawing the plat images, and coloring / writing on them.
from PIL import Image, ImageDraw, ImageFont

# For parsing text of PLSS land descriptions into its component parts.
from pyTRS.pyTRS import PLSSDesc, Tract
from pyTRS.pyTRS import decompile_twprge, break_trs
from pyTRS import version as pyTRS_version

import _constants

__version__ = _constants.__version__
__versionDate__ = _constants.__versionDate__
__author__ = _constants.__author__
__email__ = _constants.__email__


def version():
    """Return the current version and version date as a string."""
    return f'v{__version__} - {__versionDate__}'


########################################################################
# Plat Objects
########################################################################

class Plat:
    """An object containing an PIL.Image object of a 36-section (in
    `.image`), as well as various attributes for platting on top of it.
    Notably, `.sec_coords` is a dict of the pixel coordinates for the
    NWNW corner of each of the 36 sections (keyed by integers 1 - 36,
    inclusive).

    NOTE: We can plat a single section, with `only_section=<int>` at
    init, in which case, `.sec_coords` will have only a single key. (Be
    sure to choose settings that are appropriate for a single-section
    plat.)

    Plat objects can process these types of objects:
        pyTRS.Tract**, SectionGrid, TownshipGrid
    (**pyTRS.Tract objects are imported in this module as `Tract`.)

    At init, configure the look, size, fonts, etc. of the Plat by
    passing a Settings object to `settings=`. (Can also pass the name of
    a preset -- see Settings docs for more details.)

    For better results, optionally pass a TwpLotDefinition (or 'tld' for
    short) to `tld=` at init, to specify which lots correspond with
    which QQ in each respective section. (See more info in
    `grid.TwpLotDefinition` docs and `grid.LotDefDB` docs.)
    # TODO: :param: allow_ld_defaults

    """

    # TODO: Wherever TLD or LD is referenced in a kwarg, allow it
    #   to pull from self.tld or self.ld.

    def __init__(self, twp='', rge='', only_section=None, settings=None,
                 tld=None, allow_ld_defaults=False):
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
        # an empty version of the respective TLD and LD objects.)
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

    @staticmethod
    def from_twprge(
            twprge='', only_section=None, settings=None, tld=None,
            allow_ld_defaults=False):
        """Generate an empty Plat object by specifying twprge as a single
        string, rather than as twp and rge separately."""
        twp, rge, _ = break_trs(twprge)

        return Plat(
            twp=twp, rge=rge, only_section=only_section, settings=settings,
            tld=tld, allow_ld_defaults=allow_ld_defaults)

    @staticmethod
    def from_queue(
            pq, twp='', rge='', only_section=None, settings=None, tld=None,
            allow_ld_defaults=False):
        """Generate and return a filled-in Plat object from a PlatQueue
        object."""
        sp_obj = Plat(
            twp=twp, rge=rge, only_section=only_section, settings=settings,
            tld=tld, allow_ld_defaults=allow_ld_defaults)
        sp_obj.process_queue(pq)
        return sp_obj

    def queue(self, plattable, tracts=None):
        """Queue up an object for platting -- i.e. pass through the
        arguments to the `.queue()` method in the Plat's PlatQueue
        object."""
        self.pq.queue(plattable, tracts)

    def process_queue(self, queue=None, allow_ld_defaults=None):
        """Process all objects in a PlatQueue object. If `queue=None`,
        the PlatQueue object that will be processed is the one stored in
        this Plat's `.pq` attribute."""

        if allow_ld_defaults is None:
            allow_ld_defaults = self.allow_ld_defaults

        # If a different PlatQueue isn't otherwise specified, use the
        # Plat's own `.pq` from init.
        if queue is None:
            queue = self.pq

        for itm in queue:
            if not isinstance(itm, PlatQueue.SINGLE_PLATTABLES):
                raise TypeError(f"Cannot process type in PlatQueue: "
                                f"{type(itm)}")
            if isinstance(itm, SectionGrid):
                self.plat_section_grid(itm)
            elif isinstance(itm, TownshipGrid):
                self.plat_township_grid(itm)
            elif isinstance(itm, Tract):
                self.plat_tract(itm, write_tract=False,
                                allow_ld_defaults=allow_ld_defaults)

        if self.settings.write_tracts and self.text_box is not None:
            self.text_box.write_all_tracts(queue.tracts)

    def _gen_header(self, only_section=None):
        """Generate the text of a header containing the T&R and/or
        Section number."""

        twp = str(self.twp)
        rge = str(self.rge)
        NS = 'undefined'
        EW = 'undefined'

        # Check that directions for twp and rge were appropriately specified.
        # If no direction was specified, then also check if (only) digits were
        # specified for twp and rge. If that's the case, arbitrarily assign 'n'
        # and 'w' as their directions (only for purposes of `decompile_twprge()`
        # -- will be cut off before the header itself is compiled).
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

        twpNum, try_NS, rgeNum, try_EW = decompile_twprge(twp + rge)

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
        """Draw the 36 sections in the standard 6x6 grid; or draw a
        single section if `only_section=<int>` is specified."""

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
                self._draw_sec((cur_x, cur_y), section=sec_num)
                self.sec_coords[sec_num] = (cur_x, cur_y)

    def _write_header(self, text=None):
        """Write the header at the top of the page."""

        if text is None:
            text = self.header

        W = self.image.width
        w, h = self.draw.textsize(text, font=self.settings.headerfont)

        # Center horizontally and write `settings.y_header_marg` px above top section
        text_x = (W - w) / 2
        text_y = self.settings.y_top_marg - h - self.settings.y_header_marg
        self.draw.text(
            (text_x, text_y),
            text,
            font=self.settings.headerfont,
            fill=self.settings.headerfont_RGBA)

    def write_all_tracts(self, tracts):
        """
        Pass the list of pyTRS.Tract objects onto the TractTextBox (if
        it exists) and write them.
        :param tract_list: A list of pyTRS.Tract objects that should be
        written to the TextBox.
        :return: None
        """
        if self.text_box is not None:
            self.text_box.write_all_tracts(tracts)

    def write_tract(self, tract):
        """
        Pass the pyTRS.Tract object onto the TractTextBox (if it exists)
        and write it.
        :param tract: A pyTRS.Tract object that should be written to the
        TextBox.
        :return: None
        """
        if self.text_box is not None:
            self.text_box.write_all_tracts([tract])

    def new_textbox(self):
        """Create a textbox Image per the Plat's settings."""

        x0, y0 = self.first_text_xy()
        # Bottom / right-most available x and y
        y1 = self.settings.dim[1] - self.settings.y_bottom_marg
        x1 = self.settings.dim[0] - self.settings.x_text_right_marg

        if x0 >= x1 or y0 >= y1:
            self.text_box = None
        else:
            stngs = self.settings
            self.text_box = TractTextBox(
                size=(x1 - x0, y1 - y0),
                bg_RGBA=(255, 255, 255, 255),
                typeface=stngs.tractfont_typeface,
                font_size=stngs.tractfont_size,
                font_RGBA=stngs.tractfont_RGBA)

    def first_text_xy(self, settings=None):
        """Get the top/left-most pixel available for writing text (i.e.
        top/left corner of where we can create and place a textbox), per
        Plat settings."""

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
        """Merge the drawn overlay (i.e. filled QQ's) onto the base
        township plat image and return an Image object. Optionally save
        the image to file if `filepath=<filepath>` is specified."""
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
        """Flatten and display the plat Image."""
        self.output().show()

    def plat_section_grid(self, secGrid: SectionGrid, qq_fill_RGBA=None):
        """Project a SectionGrid object onto an existing Plat Object
        (i.e. fill in any QQ hits per the `SectionGrid.QQgrid` values)."""
        secNum = int(secGrid.sec)
        for coord in secGrid.filled_coords():
            self.fill_qq(secNum, coord, qq_fill_RGBA=qq_fill_RGBA)
        if self.settings.write_lot_numbers:
            self.write_lots(secGrid)

    @staticmethod
    def from_section_grid(secGrid: SectionGrid, tracts=None, settings=None):
        """Return a section-only Plat object generated from a
        SectionGrid object."""
        platObj = Plat(
            twp=secGrid.twp,
            rge=secGrid.rge,
            settings=settings,
            only_section=secGrid.sec)
        platObj.plat_section_grid(secGrid)
        if platObj.settings.write_tracts:
            platObj.write_all_tracts(tracts)
        return platObj

    @staticmethod
    def from_township_grid(twpGrid, tracts=None, settings=None):
        """Return a Plat object generated from a TownshipGrid object."""
        twp = twpGrid.twp
        rge = twpGrid.rge
        platObj = Plat(twp=twp, rge=rge, settings=settings)
        platObj.plat_township_grid(twpGrid=twpGrid, tracts=tracts)
        return platObj

    def plat_township_grid(self, twpGrid, tracts=None):
        """Project a TownshipGrid object onto an existing Plat object."""

        # Generate the list of sections that have anything in them.
        # We use `include_pinged=True` to also include any sections
        # that were 'pinged' by a setter method, but may not have had
        # any values actually set (e.g., perhaps for a Tract object that
        # failed to generate any lots/QQ's when parsed by pyTRS).
        sec_list = twpGrid.filled_sections(include_pinged=True)

        # Plat each Section's filled QQ's onto our new overlay.
        for sec in sec_list:
            if self.settings.write_lot_numbers:
                # If so configured in settings, write lot numbers onto QQ's
                self.write_lots(sec)
            self.plat_section_grid(sec)

        # Write the Tract data to the bottom of the plat (or not, per settings).
        if self.settings.write_tracts and self.text_box is not None:
            self.text_box.write_all_tracts(tracts)

        return self.output()

    @staticmethod
    def from_tract(
            tractObj, settings=None, single_sec=False, ld=None,
            allow_ld_defaults=False):
        """Return a Plat object generated from a Tract object. Specify
        `single_sec=True` to plat only one section, or `False` (the
        default) to show the entire township."""
        twp = tractObj.twp
        rge = tractObj.rge
        sec = tractObj.sec
        only_sec = None
        if single_sec:
            only_sec = str(int(sec))

        platObj = Plat(
            twp=twp, rge=rge, settings=settings, only_section=only_sec,
            allow_ld_defaults=allow_ld_defaults)
        platObj.plat_tract(tractObj, ld=ld)
        return platObj

    def plat_tract(
            self, tractObj, write_tract=None, ld=None,
            allow_ld_defaults=None):
        """Project a Tract object onto an existing Plat object. Optionally,
        write the tract description at the bottom with `write_tract=True`.
        If `write_tract` is unspecified, it will default to whatever the
        Plat settings say (i.e. in `platObject.settings.write_tracts`)."""

        if allow_ld_defaults is None:
            allow_ld_defaults = self.allow_ld_defaults

        twp, rge = tractObj.twp, tractObj.rge
        sec = tractObj.sec
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
        secGrid = SectionGrid.from_tract(tractObj, ld=ld)
        self.plat_section_grid(secGrid)

        # If not specified whether to write tract, default to settings
        if write_tract is None:
            write_tract = self.settings.write_tracts

        if write_tract and self.text_box is not None:
            self.text_box.write_all_tracts([tractObj])

    def _write_text(
            self, draw_obj: ImageDraw.Draw, coord: tuple, text: str,
            font, font_RGBA) -> tuple:
        """
        Write `text` at the specified `coord`. Returns a tuple of the
        width and height of the written text. Does NOT update a cursor.
        NOTE: This method does not care whether it goes past margins, so
            be sure to handle `._check_legal_textwrite()` before calling
            this method.
        """

        w, h = draw_obj.textsize(text, font=font)
        draw_obj.text(coord, text, font=font, fill=font_RGBA)
        return (w, h)

    def write_lots(self, secObj):
        """Write lot numbers in the top-left corner of the respective QQs."""

        def write_lot(lots_within_this_QQ: list, grid_location: tuple):

            # Get the pixel location of the NWNW corner of the section:
            xy_start = self.sec_coords[int(secObj.sec)]
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

        # Each coords[y][x] contains a list of which lot(s) are at (x,y)
        # in this particular section.  For example, 'L1' through 'L4' in
        # a standard Section 1 correspond to the N2N2 QQ's, respectively
        # -- so...
        #       coords[0][0] -> ['L4']    # i.e. (0, 0), or the NWNW
        #       coords[0][1] -> ['L3']    # i.e. (1, 0), or the NENW
        #       coords[0][2] -> ['L2']    # i.e. (2, 0), or the NWNE
        #       coords[0][3] -> ['L1']    # i.e. (3, 0), or the NENE
        # ... and all other coords would be an empty list...
        #       coords[2][1] -> []    # i.e. (1,2), or the NESW
        #       coords[3][3] -> []    # i.e. (3,3), or the SESE
        #       ...etc.
        coords = secObj.lots_by_grid()

        for y in range(len(coords)):
            for x in range(len(coords[y])):
                lots = coords[y][x]
                if lots == []:
                    continue
                clean_lots = []
                for lot in lots:
                    # Delete leading 'L' from each lot, leaving only the digit,
                    # and append to clean_lots
                    clean_lots.append(lot.replace('L', ''))
                write_lot(clean_lots, (x, y))

    def fill_qq(self, section: int, grid_location: tuple, qq_fill_RGBA=None):
        """Fill in the QQ on the plat, in the specified `section`, at the
        appropriate `grid_location` coord (x, y) within that section,
        with the color specified in `qq_fill_RGBA`. If `qq_fill_RGBA` is
        not specified, it will pull from the Plat object's settings."""

        if section == 0:
            return

        if qq_fill_RGBA is None:
            # If not specified, pull from plat settings.
            qq_fill_RGBA = self.settings.qq_fill_RGBA

        # Get the pixel location of the NWNW corner of the section:
        xy_start = self.sec_coords[section]
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

    def _draw_sec(self, top_left_corner, section=None):
        """Draw the 4x4 grid of a section with an ImageDraw object, at the
        specified coordinates. Optionally specify the section number
        with `section=<int>`. (Pulls sizes, lengths, etc. from `.settings`)"""

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
        if section is not None and settings.write_section_numbers:
            # TODO: DEBUG -- Section numbers are printing very slightly
            #   farther down than they should be. Figure out why.
            w, h = self.draw.textsize(str(section), font=settings.secfont)
            self.draw.text(
                (x_center - (w // 2), y_center - (h // 2)),
                str(section),
                fill=settings.secfont_RGBA,
                font=settings.secfont)


########################################################################
# MultiPlat objects - for creating / processing a collection of Plat objects
########################################################################

class MultiPlat:
    """An object to create, process, hold, and output one or more Plat
    objects -- e.g., when there are multiple T&R's from a PLSSDesc obj.

    At init, configure the look, size, fonts, etc. of all subordinate
    Plats by passing a Settings object to `settings=`. (Can also pass
    the name of a preset -- see Settings docs for more details.)

    For better results, optionally pass a LotDefDB object (or the
    filepath to a .csv file that can be read into a LotDefDB object) to
    `lddb=`, to specify how to handle lots -- i.e. which QQ's are
    intended by which lots. (See more info in `grid.LotDefDB` docs.)
    Use `allow_ld_defaults=True` to allow any townships for which lots
    have not been defined in the lddb, to instead use the default lot
    definitions for Sections 1 - 7, 18, 19, 30, and 31 (inits as `False`
    unless specified otherwise).

    MultiPlat objects can process these types of objects:
        pyTRS.PLSSDesc**, pyTRS.Tract**, SectionGrid, TownshipGrid
    (**pyTRS.Tract objects are imported in this module as `Tract`, and
    pyTRS.PLSSDesc objects are imported as `PLSSDesc`.)

    Generated Plat objects are stored in `.plats`. They are Plat objects
    but not flattened images. To get a list of flattened images from all
    of the plats, use the `.output()` method. And see `.output_to_pdf()`
    and `.output_to_png()` methods for saving to files.

    A MultiPlatQueue object is stored for each MultiPlat as `.mpq`,
    which can be added to with the `.queue()` method (or `.queue_text()`
    method), and processed with the `.process_queue()` method."""

    # TODO: Wherever LDDB, TLD, or LD is referenced in a kwarg, allow it
    #   to pull from self.lddb.

    # TODO: Figure out a good way to organize the plats. I'm thinking a
    #  dict, keyed by T&R. Currently, it's a list.

    def __init__(self, settings=None, lddb=None, allow_ld_defaults=False):

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

    @staticmethod
    def from_queue(mpq, settings=None, lddb=None, allow_ld_defaults=False):
        """Generate and return a MultiPlat object from a MultiPlatQueue
        object."""

        mp_obj = MultiPlat(
            settings=settings, lddb=lddb, allow_ld_defaults=allow_ld_defaults)
        mp_obj.process_queue(mpq)
        return mp_obj

    def queue(self, plattable, twprge='', tracts=None):
        """Queue up an object for platting -- i.e. pass through the
        arguments to the `.queue()` method in the Plat's MultiPlatQueue
        object."""
        self.mpq.queue(plattable=plattable, twprge=twprge, tracts=tracts)

    def queue_text(self, text, config=None):
        """Parse the text of a PLSS land description (optionally using
        `config=` parameters -- see pyTRS docs), and add the resulting
        PLSSDesc object to this MultiPlat's queue (`.mpq`) -- by passing
        through the arguments to the `.queue_text()` method in the
        Plat's MultiPlatQueue object."""
        self.mpq.queue_text(text=text, config=config)

    def process_queue(self, queue=None, allow_ld_defaults=None):
        """Process all objects in a MultiPlatQueue object. If `queue=None`,
        the MultiPlatQueue object that will be processed is this
        MultiPlat's `.mpq` attribute."""

        if allow_ld_defaults is None:
            allow_ld_defaults = self.allow_ld_defaults

        # If a different MultiPlatQueue isn't otherwise specified, use
        # the Plat's own `.mpq` from init.
        if queue is None:
            queue = self.mpq

        stngs = self.settings
        for twprge, pq in queue.items():
            tld = self.lddb.get(twprge, None)
            pl_obj = Plat.from_twprge(
                twprge, settings=stngs, tld=tld,
                allow_ld_defaults=allow_ld_defaults)
            pl_obj.process_queue(pq)
            self.plats.append(pl_obj)

    @staticmethod
    def from_plssdesc(
            PLSSDesc_obj, settings=None, lddb=None, allow_ld_defaults=False):
        """Generate a MultiPlat from a parsed PLSSDesc object.
        (lots/QQs must be parsed within the Tracts for any QQ's to be
        filled on the resulting plats.)"""

        mp_obj = MultiPlat(
            settings=settings, lddb=lddb, allow_ld_defaults=allow_ld_defaults)

        # Generate a dict of TownshipGrid objects from the PLSSDesc object.
        twp_grids = plssdesc_to_grids(
            PLSSDesc_obj, lddb=lddb, allow_ld_defaults=allow_ld_defaults)

        # Get a dict linking the the PLSSDesc object's parsed Tracts to their
        # respective T&R's (keyed by T&R '000x000y' -- same as the twp_grids dict)
        twp_to_tract = filter_tracts_by_twprge(PLSSDesc_obj.parsedTracts)

        # Generate Plat object of each township, and append it to mp_obj.plats
        for k, v in twp_grids.items():
            pl_obj = Plat.from_township_grid(v, tracts=twp_to_tract[k], settings=settings)
            mp_obj.plats.append(pl_obj)

        return mp_obj

    @staticmethod
    def from_text(
            text, config=None, settings=None, lddb=None, allow_ld_defaults=False):
        """Parse the text of a PLSS land description (optionally using
        `config=` parameters -- see pyTRS docs), and generate Plat(s)
        for the lands described. Returns a MultiPlat object."""

        descObj = PLSSDesc(text, config=config, initParseQQ=True)
        return MultiPlat.from_plssdesc(
            descObj, settings=settings, lddb=lddb,
            allow_ld_defaults=allow_ld_defaults)

    def show(self, index: int):
        """Display one of the plat Image objects, specifically the one
        in the `.plats` list at the specified `index`."""
        self.plats[index].output().show()

    @staticmethod
    def _cull_list_to_requested_pages(list_to_cull: list, pages: list) -> list:
        """Take a list, and return a list of the same objects, but
        limited to the specified `pages`. Discards any page requests
        that do not exist (i.e. below 0 or above the total page count in
        `list_to_cull`). If `pages` is None, will return the original
        list intact (i.e. all pages)."""

        if pages is None:
            # If not specified, output all.
            return list_to_cull
        elif isinstance(pages, int):
            pages = [pages]
        else:
            pages = list(pages)

        output_list = []
        for page_num in pages:
            if page_num >= len(list_to_cull) or page_num < 0:
                pass
            else:
                output_list.append(list_to_cull[page_num])
        return output_list

    def output_to_pdf(self, filepath, pages=None):
        """Save all of the Plat images to a PDF at the specified
        `filepath`. If `pages=` is specified as an int, or list / tuple
        of ints, only the specified pages will be included. Otherwise,
        will output all pages."""

        if not confirm_file_ext(filepath, '.pdf'):
            raise ValueError('filepath must end with \'.pdf\'')

        output_list = self.output(pages=pages)

        if len(output_list) == 0:
            return

        im1 = output_list.pop(0)
        im1.save(filepath, save_all=True, append_images=output_list)

    def output_to_png(self, filepath, pages=None):
        """Save all of the Plat images to .png (or multiple .png files,
        if there is more than one Plat in `.plats`) at the specified
        `filepath`. If `pages=` is specified as an int, or list / tuple
        of ints, only the specified pages will be included. Otherwise,
        will output all pages.
        IMPORTANT: If multiple plats are output, then numbers (from
        '_000') will be added to the end of each, before the file
        extension."""

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
        """Return a list of flattened Image objects from all of the Plat
        objects in `.plats`. If `pages=` is specified as an int, or list
        or tuple of ints, only the specified pages will be included.
        Otherwise, will output all pages."""
        plat_ims = []
        for p in self.plats:
            plat_ims.append(p.output().convert('RGB'))

        output_list = MultiPlat._cull_list_to_requested_pages(plat_ims, pages)

        return output_list


class TractTextBox(TextBox):
    """
    A TextBox object, with additional methods for writing pyTRS.Tract
    data at the bottom of the Plat.

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
        :param typeface: The filepath to a truetype font (.ttf file)
        :param font_size: The size of the font to create.
        :param bg_RGBA: 4-tuple of the background color. (Defaults to
        white, full opacity.)
        :param font_RGBA: 4-tuple of the font color. (Defaults to black,
        full opacity.)
        :param paragraph_indent: How many spaces (i.e. characters, not
        px) to write before the first line of a new paragraph.
        :param new_line_indent: How many spaces (i.e. characters, not
        px) to write before every subsequent line of a paragraph.
        :param spacing: How many px between each line.
        :param settings: A pyTRSplat.Settings object (or the name of a
        preset, i.e. a string), which can specify various relevant
        attribs for this TractTextBox object. (In the event that an
        attributes was set in the Settings object but ALSO specified as
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

        TextBox.__init__(
            self, size=size, typeface=typeface, font_size=font_size,
            bg_RGBA=bg_RGBA, font_RGBA=font_RGBA, spacing=spacing,
            paragraph_indent=paragraph_indent, new_line_indent=new_line_indent)

        self.settings = settings

    def write_all_tracts(self, tracts=None, cursor='text_cursor'):
        """Write all the tract descriptions at the bottom of the plat,
        starting at the current coord of the specified `cursor`. If a
        string is NOT passed as `cursor=` (or a non-existent cursor is
        specified), it will begin at the default `.text_cursor`. The
        coord in `cursor` will also be updated as text gets written."""

        if tracts is None:
            return

        # Copy tracts, because we'll pop elements from it.
        ctracts = tracts.copy()

        # Save line space later in by setting this variable:
        settings = self.settings

        def write_warning(num_unwritten_tracts, tracts_written):
            """Could not fit all tracts on the page. Write a warning to
            that effect at the bottom of the page."""

            # If we wrote at least one tract, we want to include the word
            # 'other', to avoid any confusion.
            other = ''
            if tracts_written > 0:
                other = ' other'

            plural = ''
            if num_unwritten_tracts > 1:
                plural = 's'

            warning = f'[No space to write {num_unwritten_tracts}{other} tract{plural}]'

            self.write_line(
                text=warning, cursor=cursor, font_RGBA=Settings.RGBA_RED,
                override_legal_check=True)

        pull_ejector = False
        tracts_written = 0

        while len(ctracts) > 0:

            if pull_ejector or self.on_last_line:
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
            if len(tract.lotQQList) == 0 or tract.sec == 'secError':
                # If no lots/QQs were identified, or if this tract has a
                # 'secError' (i.e. it was a flawed parse where the section
                # number could not be successfully deduced -- in which case it
                # could not have been projected onto this plat), then we'll
                # write the tract in red
                font_RGBA = Settings.RGBA_RED
            # Any lines that could not be written will be returned and stored
            # in list `unwrit_lines` (i.e. empty if all successful)
            unwrit_lines = self.write_tract(
                cursor=cursor, tractObj=tract, font_RGBA=font_RGBA,
                reserve_last_line=reserve_last_line)
            if len(unwrit_lines) > 0:
                # We couldn't write all of our lines, so let's bail.
                pull_ejector = True

            tracts_written += 1

    def write_tract(
            self, tractObj: Tract, cursor='text_cursor', font_RGBA=None,
            override_legal_check=False, reserve_last_line=False) -> list:
        """
        Write the description of the parsed pyTRS.Tract object at the
        current coord of the specified `cursor`. First confirms that
        writing the text would not go past margins; and if so, will not
        write it. Updates the coord of the `cursor` used.

        :param tractObj: a pyTRS.Tract object, whose description should
        be written.
        :param cursor: The name of an existing cursor, at whose coords
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
        :return: Returns a list of all of the lines that were not
        written (i.e. an empty list, if all were written successfully).
        """

        # Extract the text of the TRS+description from the Tract object.
        text = tractObj.quick_desc()

        # If font color not otherwise specified, pull from settings.
        if font_RGBA is None:
            font_RGBA = self.settings.tractfont_RGBA

        # Pull font from settings.
        font = self.settings.tractfont

        # Break description into lines
        lines = self._wrap_text(text)

        # Write all lines in the description. If any lines could not be written,
        # store them in list `unwrit_lines`. We reserve_last_line here, because
        # we want to write an ellipses if more than 1 line remains.
        unwrit_lines = self.write_paragraph(
            text=text, cursor=cursor, font_RGBA=font_RGBA,
            reserve_last_line=True, override_legal_check=override_legal_check)

        if reserve_last_line or len(unwrit_lines) == 0:
            return unwrit_lines

        # If we had only one more line to write, write it; otherwise,
        # write an ellipses in red
        if len(unwrit_lines) == 1:
            final_text = unwrit_lines[0]
        else:
            final_text = "[...]"
            font_RGBA = Settings.RGBA_RED
        single_unwrit = self.write_line(
            text=final_text, indent=self.new_line_indent, font_RGBA=font_RGBA)

        if len(single_unwrit) > 0:
            # If that last line couldn't be written, return the full
            # unwrit_lines list (which still includes that line)
            return unwrit_lines
        else:
            # Otherwise, if it was successfully written, pop it off, and
            # return the remaining unwrit_lines
            unwrit_lines.pop(0)
            return unwrit_lines


########################################################################
# Public / Convenience Methods
########################################################################

def text_to_plats(
        text, config=None, settings=None, lddb=None,
        output_filepath=None, allow_ld_defaults=False) -> list:
    """Parse the text of a PLSS land description (optionally using
    `config=` parameters -- see pyTRS docs), and generate plat(s) for
    the lands described. Optionally output to .png or .pdf with
    `output_filepath=` (end with '.png' or '.pdf' to specify the output
    file type).  Returns a list of Image objects of the plats.

    Configure the look, size, fonts, etc. of the Plat by passing a
    Settings object to `settings=`. (Can also pass the name of a preset
    -- see Settings docs for more details.)

    Optionally pass a LotDefDB object (or path to .csv file that can be
    read into a LotDefDB object) into `lddb=` for better results. (See
    more info in `grid.LotDefDB` docs."""

    mp = MultiPlat.from_text(
        text=text, config=config, settings=settings, lddb=lddb,
        allow_ld_defaults=allow_ld_defaults)
    if output_filepath is not None:
        if confirm_file_ext(output_filepath, '.pdf'):
            mp.output_to_pdf(output_filepath)
        elif confirm_file_ext(output_filepath, '.png'):
            mp.output_to_png(output_filepath)
    return mp.output()