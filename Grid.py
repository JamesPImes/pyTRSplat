# Copyright (C) 2020, James P. Imes, all rights reserved.

"""A basic interpreter for parsed PLSSDesc and Tract objects, for
converting them to a grid, and basic platting."""

from pyTRS import pyTRS


class SectionGrid:
    """A grid of a single Section, divided into standard PLSS aliquot
    quarter-quarters (QQs) -- i.e. 4x4 for a standard section.
    Takes optional `ld=` argument for specifying a LotDefinitions object
    (defaults to a 'standard' township layout if not specified -- i.e.
    Sections 1 - 7, 18, 19, 30, and 31 have lots, because they are along
    the northern and/or western boundaries of the township). A
    TwpLotDefinitions object may also be passed, so long as `sec`,
    `twp`, and `rge` are also correctly specified.

    If `sec=<int or str>`, `twp=<str>`, and `rge=<str>` are not
    specified at init, the object may not have full functionality in
    conjunction with other modules.
        --example:
            sg_obj = SectionGrid(`sec=14, twp='154n', rge='97w')
        --equivalently:
            sg_obj = SectionGrid.from_trs('154n97w14')
    (Passing `ld=...` in either example is optional, but advisable.)

    If a lot was not defined for this SectionGrid but the lot is
    incorporated into the SectionGrid anyway, it will not set any hits,
    but the lot will be added to the list in the `.unhandled_lots`
    attribute.

    QQ's have been assigned these coordinates, with (0,0) being the NWNW
    and (3,3) being the SESE -- i.e. moving from top-to-bottom and
    left-to-right:
    ------------------------------------------------------------------
    | NWNW -> (0,0) | NENW -> (1,0) || NWNE -> (2,0) | NENE -> (3,0) |
    |---------------+---------------++---------------+---------------|
    | SWNW -> (0,1) | SENW -> (1,1) || SWNE -> (2,1) | SENE -> (3,1) |
    |===============+===============++===============+===============|
    | NWSW -> (0,2) | SESW -> (1,2) || NWSE -> (2,2) | NESE -> (3,2) |
    |---------------+---------------++---------------+---------------|
    | SWSW -> (0,3) | SESW -> (1,3) || SWSE -> (2,3) | SESE -> (3,3) |
    ------------------------------------------------------------------
    """

    def __init__(
            self, sec='', twp='', rge='', ld=None, allow_ld_defaults=False):

        # Note: twp and rge should have their direction specified
        #   ('n' or 's' for twp; and 'e' or 'w' for rge). Without doing
        #   so, various functionality may break.

        twp = twp.lower()
        rge = rge.lower()
        self.twp = twp
        self.rge = rge

        # 'secError' can be returned by pyTRS in the event of a flawed
        # parse, so we handle this by setting to 0 (a meaningless number
        # for a section that can't exist in reality) to avoid causing
        # ValueError when converting to int elsewhere.
        if sec == 'secError':
            sec = 0

        # Ensure sec is formatted as a two digit string -- ex: '01'
        sec = str(int(sec)).rjust(2, '0')

        self.sec = sec
        self.tr = twp+rge
        self.trs = f"{twp}{rge}{sec}".lower()
        self.unhandled_lots = []

        try:
            secNum = int(sec)
        except ValueError:
            secNum = 0

        self.ld = {}
        if ld is None and allow_ld_defaults:
            # If ld was not specified, but the user wants to allow
            # defaults (i.e. for Sections 1 - 7, 18, 19, 30, and 31)
            self.ld = LotDefinitions(default=secNum)
        elif isinstance(ld, LotDefinitions):
            self.ld = ld
        elif isinstance(ld, TwpLotDefinitions):
            # If the user passed a TLD object (which contains LotDefinitions
            # objects), then pull the appropriate LD object (based on the
            # section number); and if it doesn't exist, create a new (empty)
            # LD object
            self.ld = ld.get(int(sec), LotDefinitions())
        else:
            # Otherwise, an empty LD.
            self.ld = LotDefinitions()

        # A dict for the 16 aliquot divisions of a standard section,
        # with (0, 0) being NWNW and (3, 3) being SESE -- i.e. beginning
        # at the NWNW, and running east and south. The nested dict for
        # each QQ contains the x,y coordinates in the grid, and whether
        # that QQ has been switched `on` -- i.e. 'val', which is either
        # 0 ('nothing') or 1 ('something') to track whether the QQ
        # (or equivalent Lot) was identified in the tract description.
        self.QQgrid = {
            'NWNW': {'coord': (0, 0), 'val': 0},
            'NENW': {'coord': (1, 0), 'val': 0},
            'NWNE': {'coord': (2, 0), 'val': 0},
            'NENE': {'coord': (3, 0), 'val': 0},
            'SWNW': {'coord': (0, 1), 'val': 0},
            'SENW': {'coord': (1, 1), 'val': 0},
            'SWNE': {'coord': (2, 1), 'val': 0},
            'SENE': {'coord': (3, 1), 'val': 0},
            'NWSW': {'coord': (0, 2), 'val': 0},
            'NESW': {'coord': (1, 2), 'val': 0},
            'NWSE': {'coord': (2, 2), 'val': 0},
            'NESE': {'coord': (3, 2), 'val': 0},
            'SWSW': {'coord': (0, 3), 'val': 0},
            'SESW': {'coord': (1, 3), 'val': 0},
            'SWSE': {'coord': (2, 3), 'val': 0},
            'SESE': {'coord': (3, 3), 'val': 0}
        }

        # Whether this SectionGrid has been 'pinged' by a setter (e.g.,
        # by `.incorporate_lotList()` -- even if no values were actually
        # set, or if values were later reset to 0).
        self._was_pinged = False

    @staticmethod
    def from_trs(trs='', ld='default'):
        """Create and return a SectionGrid object by passing in a TRS
        (e.g., '154n97w14'), rather than the separate Sec, Twp, Rge
        components. Also takes optional `ld` argument for specifying
        LotDefinitions object."""
        twp, rge, sec = pyTRS.break_trs(trs)
        return SectionGrid(sec, twp, rge, ld)

    def apply_lddb(self, lddb):
        """Apply the appropriate LotDefinitions object from a LotDefDB
        object, if such a LD obj exists. Will not overwrite anything if
        no LD object exists for this section in the LDDB."""
        ld = lddb.trs(self.trs)
        if ld is not None:
            self.ld = ld

    def apply_tld(self, tld):
        """Apply the appropriate LotDefinitions object from a
        TwpLotDefinitions object, if such a LD exists. Will not
        overwrite anything if no LD obj exists for this section in the
        TwpLotDefinitions."""
        ld = tld.get(int(self.sec), None)
        if ld is not None:
            self.ld = ld

    def lots_by_qq_name(self) -> dict:
        """Get a dict, with QQ's as keys, and whose values are each a
        list of the lot(s) that correspond with those QQ's. Note that it
        is possible for more than 1 lot per QQ, so the values are all
        lists."""

        # This functionality is handled by LotDefinitions object.
        return self.ld.lots_by_qq_name()

    def lots_by_grid(self) -> list:
        """Convert the `ld` into a grid (nested list) of
        which lots fall within which coordinate. For example, 'L1'
        through 'L4' in a standard Section 1 correspond to the N2N2
        QQ's, respectively -- so this method would output a grid whose
        (0,0), (1,0), (2,0), and (3,0) are filled with ['L4'], ['L3'],
        ['L2'], and ['L1'], respectively."""
        lots_by_QQname_dict = self.lots_by_qq_name()
        ar = self.output_array()

        for qq_name, dv in self.QQgrid.items():
            x = dv['coord'][0]
            y = dv['coord'][1]
            lots = lots_by_QQname_dict.get(qq_name)
            if lots is not None:
                ar[y][x] = lots
            else:
                ar[y][x] = []

        return ar

    @staticmethod
    def from_tract(tractObj : pyTRS.Tract, ld='default'):
        """Return a SectionGrid object created from a parsed pyTRS.Tract
        object and incorporate the lotList and QQList from that Tract."""
        twp, rge, sec = tractObj.twp, tractObj.rge, tractObj.sec
        secObj = SectionGrid(sec=sec, twp=twp, rge=rge, ld=ld)
        secObj.incorporate_tract(tractObj)

        return secObj

    def incorporate_tract(self, tractObj : pyTRS.Tract):
        """Check the lotList and QQList of a parsed pyTRS.Tract object,
        and incorporate any hits into the grid.
        NOTE: Relies on the LotDefinitions object in `.ld` at the time
        this method is called. Later changes to `.ld` will not
        modify what has already been done here."""
        self._was_pinged = True
        self.incorporate_qq_list(tractObj.QQList)
        self.incorporate_lot_list(tractObj.lotList)

    def incorporate_lot_list(self, lotList : list):
        """Incorporate all lots in the passed lotList into the grid.
        ex: Passing ['L1', 'L3', 'L4', 'L5'] might set 'NENE', 'NENW',
            'NWNW', and 'SWNW' as hits for a hypothetical section,
            depending on the definitions in the LotDefinitions object in
            the `self.ld` attribute.
        NOTE: Relies on the LotDefinitions object in `.ld` at the time
        this method is called. Later changes to `.ld` will not
        modify what has already been done here."""

        self._was_pinged = True

        # QQ equivalents to Lots
        equiv_qq = []

        # Convert each lot to its equivalent QQ, per the ld, and
        # add them to the equiv_qq list.
        for lot in lotList:
            # First remove any divisions in the lot (e.g., 'N2 of L1' -> 'L1')
            lot = _lot_without_div(lot)

            eq_qqs_from_lot = self._unpack_ld(lot)
            if eq_qqs_from_lot is None:
                self.unhandled_lots.append(lot)
                continue
            equiv_qq.extend(eq_qqs_from_lot)

        self.incorporate_qq_list(equiv_qq)

    def incorporate_qq_list(self, QQList : list):
        """Incorporate all QQs in the passed QQList into the grid.
        ex: Passing 'NENE', 'NENW', 'NWNW', and 'SWNW' sets all of those
            QQ's as hits."""

        self._was_pinged = True

        # `qq` can be fed in as 'NENE' or 'NENE,NWNE'. So we need to break it
        # into components before incorporating.
        for qq in QQList:
            for qq_ in qq.replace(' ', '').split(','):
                self.turn_on_qq(qq_)

    def _unpack_ld(self, lot) -> list:
        """Pass a lot number (string 'L1' or int 1), and get a list of the
        corresponding / properly formatted QQ(s) from the `.ld` of this
        SectionGrid object. Returns None if the lot is undefined, or if
        it was defined with invalid QQ's."""

        equiv_aliquots = []
        # Cull lot divisions (i.e. 'N2 of L1' to just 'L1')
        lot = _lot_without_div(lot)

        # Get the raw definition from the LotDefinitions object.
        # If undefined in the LD obj, return None.
        raw_ldef = self.ld.get(lot, None)
        if raw_ldef is None:
            return None

        # Ensure the raw lot definition is in the expected format and is
        # broken out into QQ chunks (e.g., a 'L1' that is defined as
        # 'N2NE4' should be converted to 'NENE' and 'NWNE').  And add
        # the resulting QQ(s) to the list of aliquots.
        equiv_aliquots.extend(_smooth_QQs(raw_ldef))

        if len(equiv_aliquots) == 0:
            return None

        return equiv_aliquots

    def output_text_plat(self, include_header=False) -> str:
        """Output a simple plat (as a string) of the Section grid values."""

        ar = self.output_array()
        total_columns = len(ar[0])
        total_rows = len(ar)
        box_width = 4
        box_height = 1
        total_width = 1 + total_columns * (box_width + 1)

        header = '=' * total_width + '\n' + self.trs.center(total_width)

        plat_txt = '=' * total_width
        rows_written = 0
        for row in ar:
            drawn_row = '|'
            for col in row:
                draw = ' ' * box_width
                if col != 0:
                    draw = 'X' * box_width

                drawn_row = drawn_row + draw + '|'
            plat_txt = plat_txt + ( '\n' + drawn_row ) * box_height
            rows_written += 1
            if rows_written != total_rows:
                plat_txt = plat_txt + '\n' + '|'
                plat_txt = plat_txt + ('-' * box_width + '+') * (total_columns - 1)
                plat_txt = plat_txt + '-' * box_width + '|'

        plat_txt = plat_txt + '\n' + '=' * total_width

        return (header + '\n') * include_header + plat_txt

    def output_array(self) -> list:
        """Convert the grid to an array (oriented from NWNW to SESE),
        with resulting coords formatted (y, x) -- ex:
            ar = sg_obj.output_array()
            ar[y][x]  # Accesses the value at (x, y) in `sg_obj.QQgrid`"""

        max_x = 0
        max_y = 0
        for qq in self.QQgrid.values():
            if qq['coord'][0] > max_x:
                max_x = qq['coord'][0]
            if qq['coord'][1] > max_y:
                max_y = qq['coord'][1]

        # Create an array of all zero-values, with equal dimensions as
        # in the SectionGrid.QQgrid (which is 4x4 in a standard section).
        ar = [[0 for _a in range(max_x + 1)] for _b in range(max_y + 1)]

        for qq in self.QQgrid.values():
            x = qq['coord'][0]
            y = qq['coord'][1]
            if qq['val'] != 0:
                ar[y][x] = qq['val']

        return ar

    def turn_off_qq(self, qq: str):
        """Set the value of the specified QQ (e.g. 'NENE') to 0."""
        qq = qq.upper()
        if qq in self.QQgrid.keys():
            self.QQgrid[qq]['val'] = 0

    def turn_on_qq(self, qq: str, custom_val=1):
        """Set the value of the specified QQ (e.g. 'NENE') to 1."""

        self._was_pinged = True

        # Note: Passing anything other than `1` to `custom_val` will
        # probably cause other current functionality to break. But it
        # might be useful for some purposes (e.g., tracking which
        # PLSS descriptions include that QQ).
        qq = qq.upper()
        if qq in self.QQgrid.keys():
            self.QQgrid[qq]['val'] = custom_val

    def filled_coords(self) -> list:
        """Return a list of coordinates in the SectionGrid that contain
        a hit."""
        ar = self.output_array()
        filled = []
        for y in range(len(ar)):
            for x in range(len(ar[y])):
                if ar[y][x] != 0:
                    filled.append((x,y))
        return filled

    def has_any(self):
        """Return a bool, whether at least one QQ is filled anywhere in
        this SectionGrid."""
        ar = self.output_array()
        for i in ar:
            for j in i:
                if j != 0:
                    return True
        return False

class TownshipGrid:
    """A grid of a single Township/Range, containing in `.sections` a
    dict (keyed by integers 1 - 36, inclusive) a respective SectionGrid
    object for each of its 36 sections.

    At init, optionally use `tld=` to pass in a TwpLotDefinitions object
    wherein lots are given a definition of which QQ(s) they correspond
    to in each respective section. It defaults to passing
    `tld='default'`, which causes Sections 1 - 7, 18, 19, 30, and 31 to
    have their 'expected' lots (i.e. the lots that come from being along
    the northern and/or western boundaries of a standard township)."""

    # Sections 1-6, 13-18, and 25-30 (inclusive) are east-to-west (i.e. right-to-left)
    # -- all other sections are left-to-right.
    RIGHT_TO_LEFT_SECTIONS = list(range(1, 7)) + list(range(13, 19)) + list(range(25, 31))

    def __init__(self, twp='', rge='', tld=None, allow_ld_defaults=False):

        # NOTE: `tld` stands for `TwpLotDefinitions`

        total_sections = 36

        self.twp = twp
        self.rge = rge
        self.twprge = twp + rge

        # A dict of SectionGrid objs for each section, keyed by ints 1 - 36:
        self.sections = {}

        # A dict of (x,y) coords for each section in the Twp, keyed by ints 1 - 36:
        self.section_coords = {}

        if isinstance(tld, TwpLotDefinitions):
            self.tld = tld
        elif tld is None and allow_ld_defaults:
            self.tld = TwpLotDefinitions(list(range(0, 37)))
        else:
            self.tld = TwpLotDefinitions()

        # Sections "snake" from the NE corner of the township west then
        # down, then they cut back east, then down and west again, etc.,
        # thus:
        #           6   5   4   3   2   1
        #           7   8   9   10  11  12
        #           18  17  16  15  14  13
        #           19  20  21  22  23  24
        #           30  29  28  27  26  25
        #           31  32  33  34  35  36
        #
        # ...so accounting for this is a little trickier:
        for secNum in range(1, total_sections + 1):
            x = (secNum - 1) // 6
            if secNum in TownshipGrid.RIGHT_TO_LEFT_SECTIONS:
                y = -secNum % 6
            else:
                y = secNum % 6
            # Pull the LotDefinitions from our TLD, if it's been set for
            # this section. If not set, check with `allow_ld_defaults`
            # whether to pull a default LD, or to pull an empty LD.
            ld = self.tld.get_ld(
                secNum, allow_ld_defaults=allow_ld_defaults,
                force_ld_return=True)
            self.sections[secNum] = SectionGrid(
                sec=secNum, twp=twp, rge=rge, ld=ld)
            self.section_coords[secNum] = (x, y)

        # Also add a nonsense 'Section 0' (which never actually exists
        # for any real-life township). This way, we can handle section
        # errors (e.g., from a flawed parse by pyTRS, which can generate
        # a section number of 'secError') by changing them to Section 0,
        # without crashing the program, but while also being able to
        # check if there were flaws (e.g., if there are any changes made
        # to this SectionGrid object).
        self.sections[0] = SectionGrid(sec=0, twp=twp, rge=rge)
        self.section_coords[0] = (-1, -1)


    def apply_tld(self, tld):
        """Apply a TwpLotDefinitions object (i.e. set the respective
        SectionGrid's LotDefinitions objects)."""
        if not isinstance(tld, TwpLotDefinitions):
            raise TypeError('`tld` must be `TwpLotDefinitions` object.')
        for key, val in tld.items():
            self.apply_ld(key, val)

    def apply_ld(self, section_number : int, ld):
        """Apply a LotDefinitions object for the specified section_number."""
        if not isinstance(ld, LotDefinitions):
            raise TypeError('`ld` must be type `LotDefinitions`')
        self.sections[int(section_number)].ld = ld

    def filled_sections(self, include_pinged=False):
        """Return a list of SectionGrid objects that have at least one
        QQ filled. Optionally, `include_pinged=True` (`False` by
        default) will include SectionGrid objects that were 'pinged' by
        any setter method, even if no values were actually set (e.g., an
        empty list was passed to `secGridObj.incorporate_lotlist()`, so
        no values were actually set -- this is potentially useful if a
        Tract object was parsed but did not have any identifiable lots
        or QQ's and we still want to include the corresponding
        SectionGrid object here)."""
        x_sec = []
        for secNum, val in self.sections.items():
            if val.has_any() or (val._was_pinged and include_pinged):
                x_sec.append(val)
        return x_sec

    def incorporate_tract(self, tractObj, sec=None):
        """Check the lotList and QQList of a parsed pyTRS.Tract object,
        and incorporate any hits into the grid. If `sec=` is not
        specified, it will pull the `.sec` from the Tract object.
        NOTE: Relies on the TwpLotDefinitions object in `.tld` at the
        time this method is called. Later changes to `.tld` will not
        modify what has already been done here."""
        if sec is None:
            sec = tractObj.sec
        # 'secError' can be returned by pyTRS in the event of a flawed
        # parse, so we handle this by setting sec to 0 (a section number
        # that can't exist in reality), before trying to
        # convert `sec` to an int causes a ValueError.
        if sec == 'secError':
            sec = 0
        sec = int(sec)
        secGridObj = self.sections[sec]
        secGridObj.incorporate_tract(tractObj)

    def turn_off_qq(self, secNum: int, qq: str):
        """For the specified section, set the value of the specified QQ
        (e.g. 'NENE') to 0, in the appropriate SectionGrid in the
        `.sections` attribute of this TownshipGrid object."""

        if secNum in self.sections.keys():
            self.sections[int(secNum)].turn_on_qq(qq=qq)

    def turn_on_qq(self, secNum: int, qq: str, custom_val=1):
        """For the specified section, set the value of the specified QQ
        (e.g. 'NENE') to 1, in the appropriate SectionGrid in the
        `.sections` attribute of this TownshipGrid object."""

        # Note: Passing anything other than `1` to `custom_val` will
        # probably cause other current functionality to break. But it
        # might be useful for some purposes (e.g., tracking which
        # PLSS descriptions include that QQ).

        if secNum in self.sections.keys():
            self.sections[int(secNum)].turn_on_qq(qq=qq, custom_val=custom_val)

class LotDefinitions(dict):
    """A dict object (often abbreviated 'ld' or 'LD') for defining which
    lots correspond to which QQ in a given section. At init, pass in an
    int 1 - 36 (inclusive) to set to the /default/ for that section in a
    STANDARD township (i.e. perhaps better than nothing).

    These objects can also be contained within a TwpLotDefinitions
    object for a 36-section collection of such lot-to-QQ definitions.
    In turn, TwpLotDefinitions can be contained within a LotDefDB
    object for definitions of lots in the sections of any number of
    townships.

    See `LotDefDB.from_csv()` or `TwpLotDefinitions.from_csv()` for
    loading larger databases from .csv files, rather than creating
    LotDefinitions objects individually."""

    # Below are defaults for sections in a 'standard' 6x6 Township grid.
    # (Sections along the north and west boundaries of the township have
    # 'expected' lot locations. In practice, these might only RARELY be
    # the only lots in a township, and they are not always consistent,
    # even within these sections. Even so, it is better than nothing.)

    DEF_01_to_05 = {
        'L1': 'NENE',
        'L2': 'NWNE',
        'L3': 'NENW',
        'L4': 'NWNW'
    }

    DEF_06 = {
        'L1': 'NENE',
        'L2': 'NWNE',
        'L3': 'NENW',
        'L4': 'NWNW',
        'L5': 'SWNW',
        'L6': 'NWSW',
        'L7': 'SWSW',
    }

    DEF_07_18_19_30_31 = {
        'L1': 'NWNW',
        'L2': 'SWNW',
        'L3': 'NWSW',
        'L4': 'SWSW'
    }

    # All other sections in a /standard/ Twp have no lots.
    DEF_00 = {}

    def __init__(self, default=None):
        super().__init__()

        # If default is specified, we'll absorb that standard dict for
        # this LD object.
        if isinstance(default, dict):
            self.absorb_ld(default)
        elif default in [1, 2, 3, 4, 5]:
            self.absorb_ld(LotDefinitions.DEF_01_to_05)
        elif default == 6:
            self.absorb_ld(LotDefinitions.DEF_06)
        elif default in [7, 18, 19, 30, 31]:
            self.absorb_ld(LotDefinitions.DEF_07_18_19_30_31)
        else:
            self.absorb_ld(LotDefinitions.DEF_00)

    def set_lot(self, lot, definition):
        """Set definition (value) to lot (key). Overwrite, if already
        exists. Using this method ensures that the resulting format will
        be as expected elsewhere in the program (assuming input format
        is acceptable), by passing definitions through pyTRS parsing."""

        # If no leading 'L' was fed in, add it now (e.g. 1 -> 'L1')
        if str(lot).upper()[0] != 'L':
            lot = 'L' + str(lot).upper()

        # Ensure the definitions are broken down into QQ's by passing them
        # through pyTRS.Tract parsing, and pulling the resulting QQList.
        qq_list = pyTRS.Tract(desc=definition, initParseQQ=True, config='cleanQQ').QQList
        self[lot] = ','.join(qq_list)

    def absorb_ld(self, dct):
        """Absorb another LotDefinitions object. Will overwrite existing
        keys, if any. Using this method ensures that the resulting
        format will be as expected elsewhere in the program (assuming
        input format is acceptable), by passing definitions through
        pyTRS parsing."""
        for lot, definition in dct.items():
            self.set_lot(lot, definition)

    def lots_by_qq_name(self) -> dict:
        """Get a dict, with QQ's as keys (e.g., 'NENE'), and whose
        values are each a list of the lot(s) that correspond with those
        QQ's (e.g., 'L1'). Note that it is possible for more than 1 lot
        per QQ, so each value is a list."""
        ret_dict = {}
        for k, v in self.items():
            list_of_qqs = _smooth_QQs(v)
            for qq in list_of_qqs:
                if qq in ret_dict.keys():
                    ret_dict[qq].append(k)
                else:
                    ret_dict[qq] = [k]
        return ret_dict


class TwpLotDefinitions(dict):
    """A dict of LotDefinition objects (i.e. essentially a nested dict)
    for an entire township. Each key is a section number (an int), whose
    value is a LotDefinition object for that section. If a section
    number or list of section numbers (all ints) are passed at init,
    will use default definitions for those sections.

    These objects can be contained within a LotDefDB object (keyed by
    T&R, formatted '000x000x' or fewer digits -- e.g., '154n97w' for
    T154N-R97W) for definitions of lots in the sections of any number of
    townships.

    See `LotDefDB.from_csv()` or `TwpLotDefinitions.from_csv()` for
    loading larger databases from .csv files, rather than creating
    TwpLotDefinitions objects individually."""

    def __init__(self, default_sections=None):
        super().__init__()
        # for i in range(1,37):
        #     # Initialize an empty LotDef obj for each of the 36 sections
        #     # in a standard Twp.
        #     self[i] = LotDefinitions(None)

        # Initialize an empty LotDef obj for an non-existing 'section 0'
        # (for error-handling purposes only -- will not contain
        # meaningful data)
        self[0] = LotDefinitions(None)

        # If we want to use default dicts for any sections, do so now.
        if isinstance(default_sections, int):
            self[default_sections] = LotDefinitions(default_sections)
        elif isinstance(default_sections, list):
            for sec in default_sections:
                self[sec] = LotDefinitions(sec)

    def set_section(self, sec_num: int, lot_defs: LotDefinitions):
        """Set the LotDefinitions object for a specified section."""
        # This need not be a defined method, but it's more intuitively
        # named, so... why not.
        self[sec_num] = lot_defs

    def get_ld(self, sec_num: int, allow_ld_defaults=False,
               force_ld_return=False):
        """Get the TwpLotDefinitions object for a specified `twprge`
        (formatted '000x000z' or fewer digits, if not needed).

        If no LotDefinitions has been set for the requested sec_num,
        then parameter `allow_ld_defaults=True` (set `False` by default)
        will cause this to return a LotDefinitions object with the lot
        definitions of that section, as though in a 'standard' township
        (i.e. for Sections 1 - 7, 18, 19, 30, and 31 -- the sections
        along the north and/or west boundaries of a standard township).

        If parameter `force_ld_return=True` (set `False` by default),
        then this method will be forced to return a LotDefinitions
        object. This has the effect of returning an (empty) LD object
        when this function otherwise WOULD HAVE returned None (i.e. the
        LotDefinitions was unset for the requested section, but user
        specified `allow_ld_defaults=False`). This would have no effect
        if the LotDefinitions object was set for the requested section,
        and/or the user passed parameter `allow_ld_defaults=True`."""

        #TODO: docstring. Similar to `LotDefDB.get_tld()`.
        sec_num = int(sec_num)
        ld = self.get(sec_num, None)
        if ld is not None:
            return ld
        elif allow_ld_defaults:
            # If there was no LD set for this sec_num, but the user wants
            # to allow default LD's, generate and return a section-default
            # LD now.
            return LotDefinitions(default=sec_num)
        elif force_ld_return:
            # If the LD was not set for this section, and the user
            # prohibited defaults, but the user still wants to receive a
            # LotDefinitions object... we return an empty LD obj.
            return LotDefinitions()
        else:
            return None

    @staticmethod
    def from_csv(fp, twp: str, rge: str):
        """Generate a TwpLotDefinitions object from a properly
        formatted** .csv file at filepath `fp`. Specify `twp=<str>` and
        `rge=<str>` for which rows should match.
            ex: tld_obj = TwpLotDefinitions.from_csv(
                    r'assets\examples\SAMPLE_LDDB.csv',
                    twp='154n', rge='97w')

        **See the docstring for LotDefDB for proper .csv formatting."""

        if None in [twp, rge]:
            raise ValueError('`twp` and `rge` must be specified.')

        twp = twp.lower()
        rge = rge.lower()

        # Load a full LotDefDB object from .csv file, and then pull our
        # twp+rge from it. If our twp+rge does not exist as a key,
        # return an empty TLD object.
        temp_lddb = LotDefDB(from_csv=fp)
        return temp_lddb.get(twp+rge, TwpLotDefinitions())


class LotDefDB(dict):
    """A dict database of TwpLotDefinitions, whose keys are T&R (formatted
    '000a000b' or fewer digits), and each whose values is a
    TwpLotDefinitions object for that T&R.

    NOTE: If a string filepath to a properly formatted** .csv file is
    passed as `from_csv=` at init the object will load the data
    represented in the .csv file.

    By design, it is best to use the `.get_tld()` method to access the
    stored TwpLotDefinitions objects (rather than the native `.get()`
    method), because `allow_ld_defaults=<bool>` in that method will
    decide whether to fall back to default lot definitions for any T&R's
    that have not been set in a given LotDefDB object (i.e. for Sections
    1 - 7, 18, 19, 30, and 31 -- which are along the north and/or west
    boundaries of a standard township). Of course, `.get()` also works
    (as do square brackets for the key), if this functionality isn't
    needed.

    ** For proper .csv formatting, follow these guidelines (and see the
    example `SAMPLE_LDDB.csv` in the documentation):
        1) These 5 headers MUST exist, all lowercase:
                twp, rge, sec, lot, qq
        2) twp must be specified in the format '000x'
            ex: '154n' for Township 154 North; '1s' for Township 7 South
                (without quotation marks)
        3) rge must be specified in the format '000x'
            ex: '97w' for Range 97 West; '6e' for Range 6 East
                (without quotation marks)
        4) sec and lot should integers (non-numeric lots cannot
                currently be handled)
        5) qq should be in the format as follows:
            a) 'NENE' for 'Northeast Quarter of the Northeast Quarter';
                    'W2' for 'West Half'; 'ALL' for 'ALL' ...
                        (These get passed through pyTRS parsing, so
                        reasonable abbreviations SHOULD be captured...)
            b) If a lot comprises more than a single QQ, separate QQs by
                    comma (with no space), and/or use larger aliquot
                    divisions as appropriate.
                        ex: Lot 1 that comprises the N/2NE/4 could be
                            specified under the 'qq' columns as 'N2NE'
                            (without quotation marks)
                        ex: Lot 4 that sprawls across the E/2NW/4 and
                            SW/4NW/4 could be specified under the 'qq'
                            column as 'E2NW,SWNW' (without quotation
                            marks)
        6) Any other columns (e.g., 'COMMENTS') should be acceptable but
                will be ignored.
        7) Duplicate lot entries will result in only the last-entered
                row being effective. If a lot comprises multiple QQ's,
                keep it on a single row, and refer to list item #5 above
                on how to handle it.
        8) Keep in mind that extra long .csv files might conceivably
                take a while to process and/or result in a LotDefDB that
                burdens the system's memory."""

    def __init__(self, from_csv=None):
        super().__init__()
        if from_csv is not None:
            self._import_csv(from_csv)

    def _import_csv(self, fp):
        """Read in a properly formatted** .csv file at filepath `fp`, and
        convert each unique T&R represented in the .csv file into a
        separate TwpLotDefinitions object, keyed by T&R (keys formatted
        '000x000y' or fewer digits -- ex: '154n97w' for T154N-R97W, or
        '1s6e' for T1S-R6E).

        **See the docstring for LotDefDB for proper .csv formatting."""

        from pathlib import Path

        # Confirm that we're going to read '.csv' file.
        if Path(fp).suffix.lower() != '.csv':
            raise ValueError("Filepath must end in '.csv'")

        import csv
        f = open(fp, 'r')
        reader = csv.DictReader(f)

        for row in reader:
            twp, rge = row['twp'].lower(), row['rge'].lower()
            sec = int(row['sec'])
            lot, qq = row['lot'], row['qq']
            # If no TLD has yet been created for this T&R, do it now.
            self.setdefault(twp + rge, TwpLotDefinitions())

            # Add this lot/qq definition for the section/twp/rge on this row.
            self[twp + rge].setdefault(sec, LotDefinitions())
            self[twp + rge][sec].set_lot(lot, qq)

    def set_twp(self, twprge, tld_obj):
        """Set the TwpLotDefinitions object for a specified `twprge`
        (formatted '000x000z' or fewer digits, if not needed)."""
        # This need not be a defined method, but it's more intuitively
        # named, so... why not.
        self[twprge] = tld_obj

    def get_tld(self, twprge, allow_ld_defaults=False,
                force_tld_return=False):
        """Get the TwpLotDefinitions object for a specified `twprge`
        (formatted '000x000z' or fewer digits, if not needed).

        If a requested TLD has not been set, this will return `None` --
        unless the parameter `allow_ld_defaults=True` is set to True, in
        which case, it will return as a TwpLotDefinitions object with
        default lot definitions (i.e. for Sections 1 - 7, 18, 19, 30,
        and 31 -- the sections along the north and/or west boundaries
        of a standard township)."""

        tld = self.get(twprge, None)
        if tld is not None:
            return tld
        elif allow_ld_defaults:
            # If there was no TLD set for this twprge, but the user wants
            # to allow default TLD's, generate and return one now.
            return TwpLotDefinitions(
                default_sections=[i for i in range(0, 37)])
        elif force_tld_return:
            return TwpLotDefinitions()
        else:
            return None

    def trs(self, trs, allow_ld_defaults=None):
        """Access the (section-level) LotDefinitions object for the
        specified `trs`. Returns either the corresponding LotDefinitions
        object -- or None, if none was found**.
            ex: lddb_oj.trs('154n97w14')
        # This would access the LD for Sec 14 of T154N-R97W, if defined
        in the LotDefDB.

        **However, if parameter `allow_ld_defaults=True` is passed, then
        if the LotDefDB does not contain any lot definitions for the
        requested T&R, it will instead create (but not store) a new
        TwpLotDefinitions object with default lot definitions (i.e. for
        Sections 1 - 7, 18, 19, 30, and 31 -- which are along the north
        and/or west boundaries of a standard township), and will pull
        LotDefinitions from that.

        IMPORTANT: If ANY lots are defined in a given T&R, then no
        defaults will be used for that T&R -- i.e. if lots are defined
        in Section 25, T154N-R97W but not in Section 1 of that township,
        then falling back to defaults for Section 1 will have no effect.
        (So if any lots are defined for a T&R, then all lots SHOULD be
        defined, although nothing would break if they are not.)"""

        twp, rge, sec = pyTRS.break_trs(trs)
        twprge = twp + rge
        tld = self.get_tld(twprge, allow_ld_defaults=allow_ld_defaults)
        if tld is None:
            return None
        else:
            return tld[int(sec)]


def plssdesc_to_grids(
        PLSSDescObj: pyTRS.PLSSDesc, lddb=None, allow_ld_defaults=False) -> dict:
    """Generate a dict of TownshipGrid objects (keyed by T&R
    '000x000x') from a parsed pyTRS.PLSSDesc object. Optionally specify
    `lddb=<LotDefDB>` to define lots and get better results."""
    tl = PLSSDescObj.parsedTracts
    return tracts_into_twp_grids(
        tl, lddb=lddb, allow_ld_defaults=allow_ld_defaults)


def tracts_into_twp_grids(
        tract_list, grid_dict=None, lddb=None, allow_ld_defaults=False) -> dict:
    """Incorporate a list of parsed pyTRS.Tract objects into respective
    TownshipGrid objects, and return a dict of those TownshipGrid objs
    (keyed by T&R). If an existing `grid_dict` is passed, it will be
    updated and returned. If not, a new one will be created and
    returned.
    Optionally specify `lddb=<LotDefDB>` to define lots and get better
    results."""
    if grid_dict is None:
        grid_dict = {}

    # If the user passed a filepath (as a str) to a .csv file that can
    # be loaded into a LDDB object, create that.
    if isinstance(lddb, str):
        lddb = LotDefDB(from_csv=lddb)
    # If we do not yet have a valid LotDefDB object, create a default.
    if not isinstance(lddb, LotDefDB):
        lddb = LotDefDB()

    # We'll incorporate each Tract object into a SectionGrid object. If
    # necessary, we'll first create TownshipGrid objects that do not yet
    # exist in the grid_dict.
    for tractObj in tract_list:

        # If there was a T&R error in the parsing by pyTRS, twp and rge
        # will both be set as 'TRerr' by `.break_TRS()`. If there was a
        # section error, `sec` will be set as `secError`. Otherwise,
        # these three variables are set usefully.
        twp, rge, sec = pyTRS.break_trs(tractObj.trs)

        # We don't want to duplicate 'TRerr' when setting a key shortly,
        # so set twp and rge, such that only twp contains 'TRerr'.
        if 'TRerr' in twp+rge:
            twp = 'TRerr'
            rge = ''

        # If `sec` == 'secError', that will be passed through to
        # `.incorporate_tract()`, which handles that error.

        # Handling a twp, rge, and/or sec that are undefined.
        if twp == '':
            twp = 'undef'
            rge = ''
        if sec in ['', None]:
            sec = 0

        twprge = twp + rge

        # Get the TLD for this T&R from the lddb, if one exists. If not,
        # create and use a default TLD object. (We `force_tld_return` to
        # ensure that a TwpLotDefinitions object gets returned, instead
        # of None)
        tld = lddb.get_tld(
            twprge, allow_ld_defaults=allow_ld_defaults, force_tld_return=True)

        # If a TownshipGrid object does not yet exist for this T&R in
        # the dict, create one, and add it to the dict now.
        grid_dict.setdefault(twprge, TownshipGrid(twp=twp, rge=rge, tld=tld))

        # Now incorporate the Tract object into a SectionGrid object
        # within the dict. No /new/ SectionGrid objects are created at
        # this point (since a TownshipGrid object creates all 36 of them
        # at init), but SectionGrid objects are updated at this point to
        # incorporate our tracts.
        TwpGridObj = grid_dict[twprge]
        TwpGridObj.incorporate_tract(tractObj, sec)

    return grid_dict


def filter_tracts_by_twprge(tract_list, twprge_dict=None) -> dict:
    """Filter pyTRS.Tract objects into a dict, keyed by T&R (formatted
    '000x000y', or fewer digits)."""

    # If the user passes a PLSSDesc object, pull its TractList obj.
    if isinstance(tract_list, pyTRS.PLSSDesc):
        tract_list = tract_list.parsedTracts

    # construct a dict to link Tracts to their respective Twps
    if twprge_dict is None:
        twprge_dict = {}
    twprge_to_tract = {}

    # Copy the twp_dict to twp_to_tract
    for twp_key, twp_val in twprge_dict.items():
        twprge_to_tract[twp_key] = twp_val

    # Sort each Tract object in the tract_list into the new dict, alongside the
    # old data (if any).
    for tract in tract_list:
        twprge = tract.twp + tract.rge
        if 'TRerr' in twprge:
            twprge = 'TRerr'
        if twprge == '':
            twprge = 'undef'
        twprge_to_tract.setdefault(twprge, [])
        twprge_to_tract[twprge].append(tract)

    return twprge_to_tract


def confirm_file(fp, extension=None) -> bool:
    """Check if `fp` is a filepath to an existing file. Optionally also
    confirm whether that file has the specified extension (must include
    the leading period -- ex: '.csv')."""

    from pathlib import Path
    try:
        if not Path(fp).is_file():
            return False
    except:
        return False

    if extension is None:
        return True

    # If extension was specified, confirm the fp ends in such.
    return Path(fp).suffix.lower() == extension.lower()


def confirm_file_ext(fp, extension) -> bool:
    """Check if `fp` is a filepath ending in `extension` (must include
    the leading period for `extension` -- ex: '.csv')."""

    from pathlib import Path
    return Path(fp).suffix.lower() == extension.lower()


########################################################################
# Misc. tools for formatting / reformatting lots and QQs
########################################################################

def _smooth_QQs(aliquot_text) -> list:
    """Ensure the input aliquot text is in a list of properly formatted
    QQ's. (Expects already-parsed data that consists only of standard
    aliquot divisions -- e.g., 'NENE' or 'N2NE' or 'S½SE¼' or 'ALL',
    etc.).
        ex: 'N2NE' -> ['NENE', 'NWNE']
        ex: 'NENE' -> ['NENE']
        ex: 'S2NENE' -> ['NENE']
    NOTE: Does NOT convert lots to QQ."""

    qq_l = []
    for aliq in aliquot_text.replace(' ', '').split(','):
        scrubbed = pyTRS.scrub_aliquots(aliq, cleanQQ=True)
        scrubbed = pyTRS.unpack_aliquots(scrubbed)
        for qq in scrubbed:
            # Append only the last 4 chars (ie. the true QQ: 'S2NENE' -> 'NENE')
            qq_l.append(qq[-4:])
    return qq_l


def _lot_without_div(lot) -> str:
    """Cull lot divisions and return a clean lot name.
        ex: 'N2 of L1' -> 'L1'
        ex: 1 -> 'L1'"""
    # If only an int is fed in, return it as a formatted lot str
    # (i.e. 1 -> 'L1')
    if isinstance(lot, int):
        return f"L{lot}"
    return lot.split(' ')[-1].upper()


def _simplify_lot_number(lot) -> str:
    """Cull leading 'L' from lot name.  Also cull lot divisions, if any.
    Returns a numeric-only string.
        ex: 'N2 of L1' -> '1'
        ex: 'L1' -> '1'"""
    lot = _lot_without_div(lot)
    return lot.replace('L', '')


