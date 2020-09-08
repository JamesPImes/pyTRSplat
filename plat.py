# Copyright (c) 2020, James P. Imes. All rights reserved.

"""Generate plat images of full Townships (6x6 grid) or single Sections
and incorporate parsed pyTRS PLSSDesc and Tract objects."""

# TODO: Add kwarg for specifying LotDefinitions for Tracts, and
#  maybe TwpLotDefinitions where appropriate. (Have already implemented
#  LDDB in at least some places.)

# TODO: `platObj.text_cursor` (or other specified cursor) should be
#  updated while tracts are being written.

# TODO: Give the option to depict `.unhandled_lots` on plats somewhere.
#  i.e. warn users that certain lots were not incorporated onto the plat

from PIL import Image, ImageDraw, ImageFont
from pyTRS import version as pyTRS_version
from pyTRS.pyTRS import PLSSDesc, Tract, decompile_tr
from grid import TownshipGrid, SectionGrid, plss_to_grids, filter_tracts_by_twprge
from grid import LotDefinitions, TwpLotDefinitions, LotDefDB, confirm_file
from platsettings import Settings
from platqueue import PlatQueue, MultiPlatQueue

__version__ = '0.0.1'
__versionDate__ = '8/31/2020'
__author__ = 'James P. Imes'
__email__ = 'jamesimes@gmail.com'


class Plat:
    """An object containing an PIL.Image object of a 36-section (in
    `.image`), as well as various attributes for platting on top of it.
    Notably, `.sec_coords` is a dict of the pixel coordinates for the
    NWNW corner of each of the 36 sections (keyed by integers 1 - 36,
    inclusive).

    NOTE: May plat a single section, with `only_section=<int>` at init,
    in which case, `.sec_coords` will have only a single key.

    Plat objects can process these types of objects:
        pyTRS.Tract**, SectionGrid, TownshipGrid
    (**pyTRS.Tract objects are imported in this module as `Tract`.)

    At init, configure the look, size, fonts, etc. of the Plat by
    passing a Settings object to `settings=`. (Can also pass the name of
    a preset -- see Settings docs for more details.)

    For better results, optionally pass a TwpLotDefinition (or 'tld' for
    short) to `tld=` at init, to specify which lots correspond with
    which QQ in each respective section. (See more info in
    `grid.TwpLotDefinition` docs and `grid.LotDefDB` docs.)"""

    # TODO: Wherever TLD or LD is referenced in a kwarg, allow it
    #   to pull from self.tld or self.ld.

    def __init__(self, twp='', rge='', only_section=None, settings=None,
                 tld=None):
        self.twp = twp
        self.rge = rge
        self.TR = twp+rge

        # NOTE: settings can be specified as a Settings object, as a
        # filepath (str) to a settings data .txt (which are created via
        # the `.save_to_file()` on a Settings object), or by passing the
        # name of an already saved preset (also as a string).
        if isinstance(settings, str):
            if settings.lower().endswith('.txt'):
                try:
                    settings = Settings.from_file(settings)
                except:
                    settings = None
            else:
                try:
                    settings = Settings.preset(settings)
                except:
                    settings = None

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

        # Keeping track of the current position where text (e.g., tracts
        # etc.) can be written -- i.e. where we've written up to, and
        # where we can still write at in x,y pixel coordinates
        self.text_cursor = self.reset_cursor()
        # NOTE: Other cursors can also be created
        #   ex: This would create a new cursor at the original x,y
        #       coords (per settings) and accessed as `platObj.highlighter`:
        #           >>> platObj.reset_cursor(cursor='highlighter')
        #   ex: This would create a new cursor at the specified x,y
        #       coords (120,180) and accessed as `platObj.underliner`:
        #           >>> platObj.set_cursor(120, 180, cursor='underliner')

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
        # get the appropriate TLD from it (per twp+rge); and if none
        # exists, then use a default TLD object. Also then get the LD
        # from it, if `only_section` was specified; and if none exists,
        # then get a default LotDefinitions obj.
        if isinstance(tld, LotDefDB):
            tld = tld.get(twp + rge, TwpLotDefinitions())
            if only_section is not None:
                ld = tld.get(only_section, LotDefinitions())
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

    @staticmethod
    def from_twprge(twprge='', only_section=None, settings=None, tld=None):
        """Generate a Plat object by specifying twprge as a single string,
        rather than as twp and rge separately."""
        t, ns, r, ew = decompile_tr(twprge)
        twp = t + ns
        rge = r + ew
        # TODO: Handle error twprge's.
        return Plat(twp=twp, rge=rge, only_section=only_section,
                    settings=settings, tld=tld)

    @staticmethod
    def from_queue(pq, twp='', rge='', only_section=None, settings=None, tld=None):
        """Generate and return a Plat object from a PlatQueue object."""
        sp_obj = Plat(
            twp=twp, rge=rge, only_section=only_section,
            settings=settings, tld=tld)
        sp_obj.process_queue(pq)
        return sp_obj

    def queue(self, plattable, tracts=None):
        """Queue up an object for platting -- i.e. pass through the
        arguments to the `.queue()` method in the Plat's PlatQueue
        object."""
        self.pq.queue(plattable, tracts)

    def process_queue(self, queue=None):
        """Process all objects in a PlatQueue object. If `queue=None`,
        the PlatQueue object that will be processed is the one stored in
        this Plat's `.pq` attribute."""

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
                self.plat_tract(itm, write_tract=False)

        if self.settings.write_tracts:
            self.write_all_tracts(queue.tracts)

    def _gen_header(self, only_section=None):
        """Generate the text of a header containing the T&R and/or
        Section number."""

        twptxt = ''
        if '' not in [self.twp, self.rge]:
            # If twp and rge were specified
            twptxt = '{Township/Range Error}'

            twp = str(self.twp)
            rge = str(self.rge)

            twpNum = '0'
            rgeNum = '0'
            NS = 'undefined'
            EW = 'undefined'
            twprge_fail = False

            if twp[-1].lower() == 'n':
                NS = 'North'
                twpNum = twp[:-1]
            elif twp[-1].lower() == 's':
                NS = 'South'
                twpNum = twp[:-1]
            else:
                twprge_fail = True

            if rge[-1].lower() == 'e':
                EW = 'East'
                rgeNum = rge[:-1]
            elif rge[-1].lower() == 'w':
                EW = 'West'
                rgeNum = rge[:-1]
            else:
                twprge_fail = True

            if 'TRerr' in [twp, rge]:
                twptxt = '{Township/Range Error}'
            elif twprge_fail:
                twptxt = ''
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
        w, h = self.settings.dim

        # We'll horizontally center our plat on the page.
        x_start = (w - (self.settings.qq_side * 4 * 6)) // 2

        # The plat will start this many px below the top of the page.
        y_start = self.settings.y_top_marg

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

        # Generate section(s) on the plat, and number them.
        if only_section is not None:
            # If drawing only one section
            self._draw_sec((x_start, y_start), section=only_section)
            self.sec_coords[int(only_section)] = (x_start, y_start)
        else:
            # If drawing all 36 sections
            for i in range(6):
                for j in range(6):
                    sec_num = sec_nums.pop(0)
                    cur_x = x_start + self.settings.qq_side * 4 * j
                    cur_y = y_start + self.settings.qq_side * 4 * i
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

    def reset_cursor(self, cursor='text_cursor', commit=True) -> tuple:
        """Return the original coord (x,y) of where bottom text may be
        written, per settings. If `commit=True` (on by default), the
        coord will be stored to the appropriate Plat object attribute.
        Specifically, if a string is NOT passed as `cursor=`, the
        committed coord will be set to the default `.text_cursor`.
        However, if the particular cursor IS specified, it will save the
        resulting coord to that attribute name (so long as
        `commit=True`).
            ex: 'setObj.reset_cursor()
                -> setObj.text_cursor == (100, 800) #because commit=True
                -> and returns (100,800)
            ex: 'setObj.reset_cursor(cursor='highlight', commit=True)
                -> setObj.highlight == (100, 800)  #because commit=True
                -> and returns (100,800)
            (Note that (100, 800) as starting coords were arbitrarily
                chosen for the purposes of this example. It depends on
                the Settings object stored in `.settings` attribute.)
        Be careful not to overwrite other required attributes."""

        stngs = self.settings
        x = stngs.bottom_text_indent
        y = stngs.y_top_marg + stngs.qq_side * 4 * 6 + stngs.y_px_before_tracts
        coord = (x, y)

        # Only if `commit=True` do we set this.
        if commit:
            self.set_cursor(x, y, cursor)

        # And return the coord.
        return coord

    def set_cursor(self, x, y, cursor='text_cursor'):
        """Set the cursor to the specified x and y coords. If a string
        is NOT passed as `cursor=`, the committed coord will be set to
        the default `.text_cursor`. However, if the particular cursor
        IS specified, it will save the resulting coord to that attribute
        name.
            ex: 'setObj.set_cursor()
                -> setObj.text_cursor == (200, 1200)
            ex: 'setObj.set_cursor(200, 1200, cursor='highlight')
                -> setObj.highlight == (200, 1200)
        Be careful not to overwrite other required attributes."""

        setattr(self, cursor, (x, y))

    def update_cursor(
            self, x_delta, y_delta, cursor='text_cursor', commit=True) -> tuple:
        """Update the coord of the cursor, by adding the `x_delta` and
        `y_delta` to the pre-existing coord. Returns the updated coord,
        and optionally store it to the attribute with `commit=True` (on
        by default).

        If a string is NOT passed as `cursor=`, the committed coord will
        be set to the default `.text_cursor`. However, if the particular
        cursor IS specified, it will save the resulting coord to that
        attribute name (so long as `commit=True`).

        Further, if the cursor is specified but does not yet exist, this
        will read from `.text_cursor` (to calculate the updated coord)
        but save to the specified cursor.

        Be careful not to overwrite other required attributes."""

        # Pull the specified cursor. If it does not already exist as an
        # attribute in this object, it will fall back to `.text_cursor`,
        # which exists for every Settings object, per init.
        x0, y0 = getattr(self, cursor, getattr(self, 'text_cursor'))
        coord = (x0 + x_delta, y0 + y_delta)

        # Only if `commit=True` do we set this.
        if commit:
            setattr(self, cursor, coord)

        return coord

    def output(self, filepath=None):
        """Merge the drawn overlay (i.e. filled QQ's) onto the base
        township plat image and return an Image object. Optionally save
        the image to file if `filepath=<filepath>` is specified."""
        merged = Image.alpha_composite(self.image, self.overlay)

        # TODO: Add the option with *args to specify which layers get
        #   included in the output. That also will require me to have
        #   separate layers for QQ's, the grid, labels, etc.
        #   And that, in turn, will require me to change methods to
        #   /plat/ onto multiple layers.

        if filepath is not None:
            merged.save(filepath)

        return merged

    def plat_section_grid(self, secGrid: SectionGrid, qq_fill_RGBA=None):
        """Project a SectionGrid object onto an existing Plat Object
        (i.e. fill in any QQ hits per the `SectionGrid.QQgrid` values)."""
        secNum = int(secGrid.sec)
        # TODO: Handle secError
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
        sec_list = twpGrid.filled_sections()

        # Plat each Section's filled QQ's onto our new overlay.
        for sec in sec_list:
            if self.settings.write_lot_numbers:
                # If so configured in settings, write lot numbers onto QQ's
                self.write_lots(sec)
            self.plat_section_grid(sec)

        # Write the Tract data to the bottom of the plat (or not, per settings).
        if self.settings.write_tracts:
            self.write_all_tracts(tracts)

        return self.output()

    @staticmethod
    def from_tract(tractObj, settings=None, single_sec=True, ld=None):
        """Return a Plat object generated from a Tract object."""
        twp = tractObj.twp
        rge = tractObj.rge
        sec = tractObj.sec
        only_sec = None
        if single_sec:
            only_sec = str(int(sec))

        platObj = Plat(twp=twp, rge=rge, settings=settings, only_section=only_sec)
        platObj.plat_tract(tractObj, ld=ld)
        return platObj

    def plat_tract(self, tractObj, write_tract=None, ld=None):
        """Project a Tract object onto an existing Plat object. Optionally,
        write the tract description at the bottom with `write_tract=True`.
        If `write_tract` is unspecified, it will default to whatever the
        Plat settings say (i.e. in `platObject.settings.write_tracts`)."""

        twp, rge = tractObj.twp, tractObj.rge
        sec = str(int(tractObj.sec)).rjust(2, '0')

        # If the user fed in a LDDB or TwpLD, rather than a LotDefinitions
        # object, get the appropriate LD from the LDDB or TLD.
        if isinstance(ld, LotDefDB):
            ld = ld.trs(twp + rge + sec)
        elif isinstance(ld, TwpLotDefinitions):
            ld = ld[int(sec)]

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
                ld = self.tld[int(sec)]
            else:
                # Otherwise, fall back to an empty LD.
                ld = LotDefinitions()

        # Generate a SectionGrid from the Tract, and plat it.
        secGrid = SectionGrid.from_tract(tractObj, ld=ld)
        self.plat_section_grid(secGrid)

        # If not specified whether to write tract, default to settings
        if write_tract is None:
            write_tract = self.settings.write_tracts

        if write_tract:
            self.write_all_tracts([tractObj])

    def write_all_tracts(self, tracts=None):
        """Write all the tract descriptions at the bottom of the plat."""
        if tracts is None:
            return

        # Save line space later in by setting this variable:
        settings = self.settings

        y_spacer = 10  # This many px between tracts.
        total_px_written = 0

        # starting coord for the first tract.
        start_x, start_y = self.text_cursor
        x, y = (start_x, start_y)

        max_px = self.image.height - start_y - settings.y_bottom_marg

        tracts_written = 0
        for tract in tracts:
            # x and y are returned from write_tract(); x stays the same, but y is updated
            last_y = y
            font_RGBA = self.settings.tractfont_RGBA
            if len(tract.lotQQList) == 0:
                # If no lots/QQs were identified, we'll write the tract in red
                font_RGBA = Settings.RGBA_RED
            x, y = self._write_tract((x, y), tract, font_RGBA=font_RGBA)
            y += y_spacer
            total_px_written = y - start_y
            tracts_written += 1
            if total_px_written >= max_px:
                if tracts_written + 1 >= len(tracts):
                    # No more or only 1 more tract to write.
                    continue
                else:
                    # Write a warning that we ran out of space to write tracts.
                    warning = '[AND OTHER TRACTS]'
                    self.draw.text(
                        (x, y),
                        warning,
                        font=self.settings.tractfont,
                        fill=Settings.RGBA_RED)
                    break

    def _write_tract(self, start_xy, tractObj, font_RGBA=None):
        """Write the description of the parsed Tract object on the page."""

        if font_RGBA is None:
            font_RGBA = self.settings.tractfont_RGBA

        x, y = start_xy
        tract_text = tractObj.quick_desc()
        w, h = self.draw.textsize(tract_text, font=self.settings.tractfont)
        self.draw.text(
            start_xy,
            tract_text,
            font=self.settings.tractfont,
            fill=font_RGBA)
        return x, y + h

    #TODO: def write_custom_text(self, start_xy, text, font_RGBA)

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


class MultiPlat:
    """An object to create, process, hold, and output one or more Plat
    objects -- e.g., when there are multiple T&R's from a PLSSDesc obj.

    At init, configure the look, size, fonts, etc. of all subordinate
    Plats by passing a Settings object to `settings=`. (Can also pass
    the name of a preset -- see Settings docs for more details.)

    For better results, optionally pass a LotDefDB object (or the path
    to a .csv file that can be read into a LotDefDB object) to `lddb=`,
    to specify how to handle lots -- i.e. which QQ's are intended by
    which lots. (See more info in `grid.LotDefDB` docs.)

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

    def __init__(self, settings=None, lddb=None):

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

        # A list of generated plats
        self.plats = []

        # A MultiPlatQueue object holding PlatQueue objects (which in
        # turn hold elements/tracts that will be platted).
        self.mpq = MultiPlatQueue()

        # LotDefDB object for defining lots in subordinate plats (if not
        # specified when platting objects).
        if isinstance(lddb, str):
            # If a string is passed, we assume it's a filepath to a file
            # that can be read into a LDDB object (e.g., a .csv file).
            # Convert to LDDB object now.
            lddb = LotDefDB(lddb)
        if not isinstance(lddb, LotDefDB):
            # If there's no valid LDDB by now, default to an empty LDDB.
            lddb = LotDefDB()
        self.lddb = lddb

    @staticmethod
    def from_queue(mpq, settings=None, lddb=None):
        """Generate and return a MultiPlat object from a MultiPlatQueue
        object."""

        mp_obj = MultiPlat(settings=settings, lddb=lddb)
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

    def process_queue(self, queue=None):
        """Process all objects in a MultiPlatQueue object. If `queue=None`,
        the MultiPlatQueue object that will be processed is this
        MultiPlat's `.mpq` attribute."""

        # If a different MultiPlatQueue isn't otherwise specified, use
        # the Plat's own `.mpq` from init.
        if queue is None:
            queue = self.mpq

        stngs = self.settings
        for twprge, pq in queue.items():
            tld = self.lddb.get(twprge, None)
            pl_obj = Plat.from_twprge(twprge, settings=stngs, tld=tld)
            pl_obj.process_queue(pq)
            self.plats.append(pl_obj)

    @staticmethod
    def from_PLSSDesc(PLSSDesc_obj, settings=None, lddb=None):
        """Generate a MultiPlat from a parsed PLSSDesc object.
        (lots/QQs must be parsed within the Tracts for any QQ's to be
        filled on the resulting plats.)"""

        mp_obj = MultiPlat(settings=settings, lddb=lddb)

        # Generate a dict of TownshipGrid objects from the PLSSDesc object.
        twp_grids = plss_to_grids(PLSSDesc_obj, lddb=lddb)

        # Get a dict linking the the PLSSDesc object's parsed Tracts to their
        # respective T&R's (keyed by T&R '000x000y' -- same as the twp_grids dict)
        twp_to_tract = filter_tracts_by_twprge(PLSSDesc_obj.parsedTracts)

        # Generate Plat object of each township, and append it to mp_obj.plats
        for k, v in twp_grids.items():
            pl_obj = Plat.from_township_grid(v, tracts=twp_to_tract[k], settings=settings)
            mp_obj.plats.append(pl_obj)

        return mp_obj

    @staticmethod
    def from_text(text, config=None, settings=None, lddb=None):
        """Parse the text of a PLSS land description (optionally using
        `config=` parameters -- see pyTRS docs), and generate Plat(s)
        for the lands described. Returns a MultiPlat object."""

        # If the user passed a filepath to a .csv file as `lddb`, create a
        # LotDefDB object from that file now, and then pass that forward.
        if confirm_file(lddb, '.csv'):
            lddb = LotDefDB.from_csv(lddb)

        descObj = PLSSDesc(text, config=config, initParseQQ=True)
        return MultiPlat.from_PLSSDesc(descObj, settings=settings, lddb=lddb)

    def show(self, index: int):
        """Display one of the plat Image objects, specifically the one
        in the `.plats` list at the specified `index`."""
        try:
            self.plats[index].output().show()
        except:
            return None

    def output_to_pdf(self, filepath):
        """Save all of the Plat images to a PDF at the specified
        `filepath`."""
        if not filepath.lower().endswith('.pdf'):
            raise Exception('Error: filepath should end with `.pdf`')
            return
        plat_ims = self.output()
        if len(plat_ims) == 0:
            return
        im1 = plat_ims.pop(0)
        im1.save(filepath, save_all=True, append_images=plat_ims)

    def output_to_png(self, filepath):
        """Save all of the Plat images to .png (or multiple .png files,
        if there is more than one Plat in `.plats`) at the specified
        `filepath`. IMPORTANT: If there are multiple plats, then numbers
        (from '_000') will be added to the end of each, before the file
        extension."""
        if not filepath.lower().endswith('.png'):
            raise Exception('Error: filepath should end with `.png`')
            return
        plat_ims = self.output()

        if len(plat_ims) == 0:
            return
        elif len(plat_ims) == 1:
            plat_ims[0].save(filepath)
        else:
            i = 0
            ext = '.png'
            fp = filepath[:-len(ext)]
            while len(plat_ims) > 0:
                filepath = f"{fp}_{str(i).rjust(3,'0')}{ext}"
                plat_ims.pop(0).save(filepath)
                i += 1

    def output(self) -> list:
        """Return a list of flattened Image objects from all of the Plat
        objects in `.plats`."""
        plat_ims = []
        for p in self.plats:
            plat_ims.append(p.output().convert('RGB'))
        return plat_ims


########################################################################
# Platting text directly
########################################################################

def text_to_plats(
        text, config=None, settings=None, lddb=None,
        output_filepath=None) -> list:
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

    mp = MultiPlat.from_text(text=text, config=config, settings=settings, lddb=lddb)
    if output_filepath is not None:
        if output_filepath.lower().endswith('.pdf'):
            mp.output_to_pdf(output_filepath)
        elif output_filepath.lower().endswith('.png'):
            mp.output_to_png(output_filepath)
    return mp.output()
