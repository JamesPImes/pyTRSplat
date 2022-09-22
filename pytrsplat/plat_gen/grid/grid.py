# Copyright (C) 2020, James P. Imes, all rights reserved.

"""
Grid-based representations of PLSS Sections (i.e. 4x4 grid of QQs) and
Townships (i.e. 6x6 grid of Sections), as well as objects for how
specific lots should be interpreted in terms of QQ(s). Also includes
interpreters for converting parsed pytrs.PLSSDesc and pytrs.Tract data
into SectionGrid and TownshipGrid objects.
"""

import pytrs
from pytrsplat.utils import _smooth_QQs, _lot_without_div

_ERR_SEC = pytrs.MasterConfig._ERR_SEC
_UNDEF_SEC = pytrs.MasterConfig._UNDEF_SEC,


class SectionGrid:
    """
    A grid of a single Section, divided into standard PLSS aliquot
    quarter-quarters (QQs) -- i.e. 4x4 for a standard section.
    Takes optional ``ld=`` argument for specifying a ``LotDefinitions``
    object (defaults to a 'standard' township layout if not specified --
    i.e. Sections 1 - 7, 18, 19, 30, and 31 have ~40-acre lots, because
    they are along the northern and/or western boundaries of the
    township). A ``TwpLotDefinitions`` object may also be passed, so
    long as ``sec``, ``twp``, and ``rge`` are also correctly specified.

    If ``sec=<int or str>``, ``twp=<str>``, and ``rge=<str>`` are not
    specified at init, the object may not have full functionality in
    conjunction with other modules.

        example::

            sg_obj = SectionGrid(sec=14, twp='154n', rge='97w')

        equivalently::

            sg_obj = SectionGrid.from_trs('154n97w14')

    (Passing ``ld=...`` in either example is optional, but advisable.)

    If a lot was not defined for this SectionGrid but the lot is
    incorporated into the ``SectionGrid`` anyway, it will not set any
    hits, but the lot will be added to the list in the
    ``.unhandled_lots`` attribute.

    QQ's have been assigned these coordinates, with ``(0,0)`` being the
    NWNW and ``(3,3)`` being the SESE -- i.e. moving from top-to-bottom
    and left-to-right::

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
        """
        :param sec: Section number (passed as an int, or as a 2-digit
        string).

        :param twp: Township number (up to 3 digits) and N/S direction
         (as a single lowercase character). Such as: ``'154n'``,
         ``'1s'``, etc.

        :param rge: Range number (up to 3 digits) and E/W direction
         (as a single lowercase character). Such as: ``'97w'``,
         ``'7e'``, etc.

        :param ld: A ``LotDefinitions`` object, defining how lots
         should be interpreted in this section, in terms of QQs.

        :param allow_ld_defaults: Whether 'default' lot definitions are
         allowed as a fall-back option, when lots have not been
         explicitly defined for a given section. (Default lots are the
         'usual' lots in Sections 1 - 7, 18, 19, 30, and 31 of a
         'standard' township -- i.e. along the northern and western
         boundaries of a township. Potentially useful as a 'better-than-
         nothing' option, but not as reliable as user-specified lot
         definitions.)
        """

        try:
            sec_num = int(sec)
            sec = str(sec_num)
        except ValueError:
            sec = '00'
            sec_num = 0

        # Note: twp and rge should have their direction specified
        #   ('n' or 's' for twp; and 'e' or 'w' for rge). Without doing
        #   so, various functionality may break.
        trs = pytrs.TRS.from_twprgesec(twp, rge, sec)
        self.twp = trs.twp
        self.rge = trs.rge
        self.sec = trs.sec
        self.twprge = trs.twprge
        self.trs = trs.trs
        self.unhandled_lots = []

        self.ld = {}
        if ld is None and allow_ld_defaults:
            # If ld was not specified, but the user wants to allow
            # defaults (i.e. for Sections 1 - 7, 18, 19, 30, and 31)
            self.ld = LotDefinitions(default=sec_num)
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
        self.qq_grid = {
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
        # by `.incorporate_lot_list()` -- even if no values were
        # actually set, or if values were later reset to 0).
        self._was_pinged = False

    @staticmethod
    def from_trs(trs='', ld=None, allow_ld_defaults=False):
        """
        Create and return a ``SectionGrid`` object by passing in a
        Twp/Rge/Sec (e.g., ``'154n97w14'``), rather than the separate
        Sec, Twp, Rge components. Also takes optional ``ld`` argument
        for specifying ``LotDefinitions`` object.

        All available parameters have the same effect as for vanilla
        __init__(), except:

        :param trs: The Twp/Rge/Sec specified as a single string, in the
         format ``'000x000x00'`` (up to 3 digits for twp and rge,
         exactly 2 digits for section, as used in pyTRS).

            ex: ``'154n97w01'``, ``'1s7e36'``, etc.

        :return: A new ``SectionGrid`` object.
        """
        trs_ = pytrs.TRS(trs)
        return SectionGrid(
            trs_.sec, trs_.twp, trs_.rge, ld=ld,
            allow_ld_defaults=allow_ld_defaults)

    @staticmethod
    def from_tract(tract: pytrs.Tract, ld=None, allow_ld_defaults=False):
        """
        Return a new SectionGrid object created from a parsed
        pytrs.Tract object and incorporate the `.lots` and qqs from
        that Tract.

        All available parameters have the same effect as for vanilla
        __init__(), except:
        :param tract: A pytrs.Tract object (already parsed into lots and
        QQs).
        :return: A SectionGrid object.
        """
        twp, rge, sec = tract.twp, tract.rge, tract.sec
        sec_grid = SectionGrid(
            sec=sec, twp=twp, rge=rge, ld=ld,
            allow_ld_defaults=allow_ld_defaults)
        sec_grid.incorporate_tract(tract)

        return sec_grid

    def apply_lddb(self, lddb):
        """
        Apply the appropriate ``LotDefinitions`` object from the
        ``LotDefDB`` object passed as ``lddb``, if such a LD object
        exists in that LDDB. Will not write/overwrite anything if no LD
        object exists for this section in the LDDB.

        :param lddb: A ``LotDefDB`` object, ideally containing a
         ``TwpLotDefinitions`` object for this section's twprge, which
         in turn contains a ``LotDefinitions`` object for this section.
        """
        ld = lddb.trs(self.trs)
        if ld is not None:
            self.ld = ld
        return None

    def apply_tld(self, tld):
        """
        Apply the appropriate ``LotDefinitions`` object from the
        ``TwpLotDefinitions`` object, if such a LD object exists in that
        TLD. Will not write/overwrite anything if no LD object exists
        for this section in the TLD.

        :param tld: A ``TwpLotDefinitions`` object, ideally containing
         a ``LotDefinitions`` object for this section.
        """
        ld = tld.get(int(self.sec), None)
        if ld is not None:
            self.ld = ld
        return None

    def lots_by_qq_name(self) -> dict:
        """
        Generate a dict, with QQs as keys, and whose values are each a
        list of the lot(s) that correspond with those QQs. Note that it
        is possible for more than 1 lot per QQ, so the values are all
        lists.
        """
        # This functionality is handled by LotDefinitions object.
        return self.ld.lots_by_qq_name()

    def lots_by_grid(self) -> list:
        """
        Convert this ``SectionGrid`` into a grid (nested list),
        depicting which lots fall within which coordinate. For example,
        ``'L1'`` through ``'L4'`` in a standard Section 1 correspond to
        the N2N2 QQ's, respectively -- so this method would output a
        grid whose (0,0), (1,0), (2,0), and (3,0) are filled with
        ``['L4']``, ``['L3']``, ``['L2']``, and ``['L1']``,
        respectively.  (Note that they are inside lists, because
        multiple lots can correspond to a single QQ.)
        """
        lots_by_qq_name_dict = self.lots_by_qq_name()
        ar = self.output_array()
        for qq_name, dv in self.qq_grid.items():
            x = dv['coord'][0]
            y = dv['coord'][1]
            lots = lots_by_qq_name_dict.get(qq_name)
            if lots is not None:
                ar[y][x] = lots
            else:
                ar[y][x] = []

        return ar

    def incorporate_tract(self, tract: pytrs.Tract):
        """
        Check the `.lots` and qqs of a parsed pytrs.Tract object,
        and incorporate any hits into the grid.
        NOTE: Relies on the LotDefinitions object in `.ld` at the time
        this method is called. Later changes to `.ld` will not
        modify what has already been done here.
        """

        # Track that this SectionGrid was 'pinged' by a setter,
        # regardless what the value of its QQ's may be (now or later on)
        self._was_pinged = True

        self.incorporate_qq_list(tract.qqs)
        self.incorporate_lot_list(tract.lots)

    def incorporate_lot_list(self, lots: list):
        """
        Incorporate all lots in the passed ``.lots`` into the grid.
            ex: Passing ['L1', 'L3', 'L4', 'L5'] might set 'NENE',
                'NENW', 'NWNW', and 'SWNW' as hits for a hypothetical
                SectionGrid, depending on how lots 1, 3, 4, and 5 are
                defined in LotDefinitions object in the `.ld` attribute
                of the SectionGrid.
        NOTE: Relies on the LotDefinitions object in `.ld` at the time
        this method is called. Later changes to `.ld` will not
        modify what has already been done here.
        """

        # Track that this SectionGrid was 'pinged' by a setter,
        # regardless what the value of its QQ's may be (now or later on)
        self._was_pinged = True

        # QQ equivalents to Lots
        equiv_qq = []

        # Convert each lot to its equivalent QQ, per the ld, and
        # add them to the equiv_qq list.
        for lot in lots:
            # First remove any divisions in the lot (e.g., 'N2 of L1' -> 'L1')
            lot = _lot_without_div(lot)

            eq_qqs_from_lot = self._unpack_ld(lot)
            if eq_qqs_from_lot is None:
                self.unhandled_lots.append(lot)
                continue
            equiv_qq.extend(eq_qqs_from_lot)

        self.incorporate_qq_list(equiv_qq)

    def incorporate_qq_list(self, qqs: list):
        """
        Incorporate all QQs in the passed list of QQs (`qqs`) into the
        grid.
            ex: Passing 'NENE', 'NENW', 'NWNW', and 'SWNW' sets all of
                those QQ's as hits in a SectionGrid.
        """

        # Track that this SectionGrid was 'pinged' by a setter,
        # regardless what the value of its QQ's may be (now or later on)
        self._was_pinged = True

        # `qq` can be fed in as 'NENE' or 'NENE,NWNE'. So we need to break it
        # into components before incorporating.
        for qq in qqs:
            for qq_ in qq.replace(' ', '').split(','):
                # Also, ensure we're only getting 4-characters max -- i.e.
                # 'N2NENE' -> 'NENE' by passing through `_smooth_QQs()`.
                # That returns a list (should be of 1 element), so get
                # the first (only) element in the returned list.
                qq_ = _smooth_QQs(qq_)[0]
                self.turn_on_qq(qq_)

    def _unpack_ld(self, lot):
        """
        INTERNAL USE:
        Pass a lot number (string 'L1' or int 1), and get a list of the
        corresponding / properly formatted QQ(s) from the `.ld` of this
        SectionGrid object. Returns None if the lot is undefined, or if
        it was defined with invalid QQ's.
        """

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
        """
        Output a simple plat (as a string) of the Section grid values.
        """

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
                plat_txt = (
                        plat_txt + ('-' * box_width + '+') * (total_columns - 1)
                )
                plat_txt = plat_txt + '-' * box_width + '|'

        plat_txt = plat_txt + '\n' + '=' * total_width

        return (header + '\n') * include_header + plat_txt

    def output_array(self) -> list:
        """
        Convert the grid to an array (oriented from NWNW to SESE),
        with resulting coords formatted (y, x).
        ex:
            ar = sg_obj.output_array()
            ar[y][x]  # Accesses the value at (x, y) in `sg_obj.qq_grid`
        """

        max_x = 0
        max_y = 0
        for qq in self.qq_grid.values():
            if qq['coord'][0] > max_x:
                max_x = qq['coord'][0]
            if qq['coord'][1] > max_y:
                max_y = qq['coord'][1]

        # Create an array of all zero-values, with equal dimensions as
        # in the SectionGrid.qq_grid (which is 4x4 in a standard section).
        ar = [[0 for _a in range(max_x + 1)] for _b in range(max_y + 1)]

        for qq in self.qq_grid.values():
            x = qq['coord'][0]
            y = qq['coord'][1]
            if qq['val'] != 0:
                ar[y][x] = qq['val']

        return ar

    def turn_off_qq(self, qq: str):
        """
        Set the value of the specified QQ (e.g. 'NENE') to 0.
        :param qq: The name of a QQ (one of the 16 standard QQs only
        -- e.g. 'NENE', 'SWSE', etc.)
        """
        qq = qq.upper()
        if qq in self.qq_grid.keys():
            self.qq_grid[qq]['val'] = 0

    def turn_on_qq(self, qq: str, custom_val=1):
        """
        Set the value of the specified QQ (e.g. 'NENE') to 1.

        :param qq: The name of a QQ (one of the 16 standard QQs only
        -- e.g. 'NENE', 'SWSE', etc.)
        :param custom_val: Instead of 1, use a different 'on' value
        for this QQ.
        WARNING: Using a `custom_val` as anything other than 1 will
        break most functionality in this module, so it should only be
        used if you have a deep understanding of its implications.
        """

        # Track that this SectionGrid was 'pinged' by a setter,
        # regardless what the value of its QQ's may be (now or later on)
        self._was_pinged = True

        # Note: Passing anything other than `1` to `custom_val` will
        # probably cause other current functionality to break. But it
        # might be useful for some purposes (e.g., tracking which
        # PLSS descriptions include that QQ).
        qq = qq.upper()
        if qq in self.qq_grid.keys():
            self.qq_grid[qq]['val'] = custom_val

    def filled_coords(self) -> list:
        """
        Return a list of coordinates in the SectionGrid that contain a
        a hit (i.e. anything other than `0` val).
        """
        ar = self.output_array()
        filled = []
        for y in range(len(ar)):
            for x in range(len(ar[y])):
                if ar[y][x] != 0:
                    filled.append((x, y))
        return filled

    def filled_qqs(self) -> list:
        """
        Return a list of QQs in the SectionGrid that contain a hit.
        """
        hits = []
        for qq, v in self.qq_grid.items():
            if v['val'] != 0:
                hits.append(qq)
        return hits

    def has_any(self):
        """
        Return a bool, whether at least one QQ contains a hit anywhere
        in this SectionGrid.
        """
        ar = self.output_array()
        for i in ar:
            for j in i:
                if j != 0:
                    return True
        return False


class TownshipGrid:
    """
    A grid of a single Township/Range, containing in its `.sections`
    attribute a dict (keyed by integers 1 - 36, inclusive) of a separate
    SectionGrid object for each of its 36 sections. Also contains a dict
    key `0` (i.e. a nonsense 'Section 0'), as a 'junk drawer' for error-
    ridden sections.
    """

    # Sections 1-6, 13-18, and 25-30 (inclusive) are east-to-west (i.e.
    # right-to-left) -- all other sections are left-to-right.
    RIGHT_TO_LEFT_SECTIONS = list(
        range(1, 7)) + list(range(13, 19)) + list(range(25, 31))

    def __init__(self, twp='', rge='', tld=None, allow_ld_defaults=False):
        """
        A grid of a single Township/Range, containing in its `.sections`
        attribute a dict (keyed by integers 1 - 36, inclusive) of a
        separate SectionGrid object for each of its 36 sections. Also
        contains a dict key `0` (i.e. a nonsense 'Section 0'), as a
        'junk drawer' for error- ridden sections.

        :param twp: Township number (up to 3 digits) and N/S direction
        (as a single lowercase character).
            ex: '154n', '1s', etc.
        :param rge: Range number (up to 3 digits) and E/W direction
        (as a single lowercase character).
            ex: '97w', '7e', etc.
        :param tld: A pytrsplat.TwpLotDefinitions object, defining how
        lots should be interpreted in each respective section, in terms
        of QQs.
        :param allow_ld_defaults: Whether 'default' lot definitions are
        allowed as a fall-back option, when lots have not been
        explicitly defined for a given section. (Default lots are the
        'usual' lots in Sections 1 - 7, 18, 19, 30, and 31 of a
        'standard' township -- i.e. along the northern and western
        boundaries of a township. Potentially useful as a 'better-than-
        nothing' option, but not as reliable as user-specified lot
        definitions.)
        """
        # NOTE: `tld` stands for `TwpLotDefinitions`

        total_sections = 36

        self.twp = twp
        self.rge = rge
        self.twprge = f"{twp}{rge}"

        # dict of SectionGrid objects for each section, keyed by ints 1 - 36
        self.sections = {}

        # dict of (x,y) coords for each section in the Twp, keyed by ints 1 - 36
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
        for sec_num in range(1, total_sections + 1):
            x = (sec_num - 1) // 6
            if sec_num in TownshipGrid.RIGHT_TO_LEFT_SECTIONS:
                y = -sec_num % 6
            else:
                y = sec_num % 6
            # Pull the LotDefinitions from our TLD, if it's been set for
            # this section. If not set, check with `allow_ld_defaults`
            # whether to pull a default LD, or to pull an empty LD.
            ld = self.tld.get_ld(
                sec_num, allow_ld_defaults=allow_ld_defaults,
                force_ld_return=True)
            self.sections[sec_num] = SectionGrid(
                sec=sec_num, twp=twp, rge=rge, ld=ld)
            self.section_coords[sec_num] = (x, y)

        # Also add a nonsense 'Section 0' (which never actually exists
        # for any real-life township). This way, we can handle section
        # errors (e.g., from a flawed parse by pytrs, which can generate
        # a section number of '__' or 'XX') by changing them to Sec 0,
        # without crashing the program, but while also being able to
        # check if there were flaws (e.g., if there are any changes made
        # to this SectionGrid object).
        self.sections[0] = SectionGrid(sec=0, twp=twp, rge=rge)
        self.section_coords[0] = (-1, -1)

    def apply_tld(self, tld):
        """
        Apply the appropriate pytrsplat.LotDefinitions objects from the
        pytrsplat.TwpLotDefinitions object to the respective SectionGrid
        objects in this TownshipGrid (if such LD objects exists in that
        TLD for such sections). Will not write/overwrite anything if no
        LD object exists for a given section in the TLD.

        :param tld: A pytrsplat.TwpLotDefinitions object, ideally
        containing a LotDefinitions object for each section.
        """
        if not isinstance(tld, TwpLotDefinitions):
            raise TypeError('`tld` must be `TwpLotDefinitions` object.')
        for key, val in tld.items():
            self.apply_ld(key, val)

    def apply_ld(self, sec_num: int, ld):
        """
        Apply a LotDefinitions object (`ld`) to the SectionGrid object
        that is designated by the section number (`sec_num`).
        """
        if not isinstance(ld, LotDefinitions):
            raise TypeError('`ld` must be type `LotDefinitions`')
        self.sections[int(sec_num)].ld = ld

    def filled_section_grids(self, include_pinged=False) -> list:
        """
        Return a list of pytrsplat.SectionGrid objects that have at
        least one QQ filled.

        :param include_pinged: Optionally, also include all SectionGrid
        objects that were 'pinged' by any setter method, even if no
        values were set (e.g., an empty list was passed to the
        `.incorporate_lotlist()` method, resulting in no actually-set
        values. This is potentially useful if a pytrs.Tract object was
        parsed but did not have any identifiable lots or QQ's and we
        still want to include the corresponding SectionGrid object here.
        Defaults to False.
        :return: A list of SectionGrid objects.
        """
        x_sec = []
        for sec_num, val in self.sections.items():
            if val.has_any() or (val._was_pinged and include_pinged):
                x_sec.append(val)
        return x_sec

    def incorporate_tract(self, tract: pytrs.Tract, sec_num=None):
        """
        Check the `.lots` and `.qqs` attributes of a parsed
        pytrs.Tract object, and incorporate any hits into the
        appropriate SectionGrid.
        NOTE: Relies on the TwpLotDefinitions object in `.tld` at the
        time this method is called. Later changes to `.tld` will not
        modify what has already been done here.
        :param tract: The pytrs.Tract object whose lots and qqs
        should be incorporated into the TownshipGrid.
        :param sec_num: The section number for the Tract being
        incorporated. If not specified, it will pull the `.sec`
        attribute from the Tract object.
        """
        if sec_num is None:
            sec_num = tract.sec_num
        # '__' or 'XX' can be returned by pytrs in the event of a flawed
        # parse, so we handle this by setting sec_num to 0 (a section number
        # that can't exist in reality), before trying to
        # convert `sec` to an int causes a ValueError.
        if sec_num in [None, _UNDEF_SEC, _ERR_SEC]:
            sec_num = 0
        sec_grid_obj = self.sections[sec_num]
        sec_grid_obj.incorporate_tract(tract)
        return None

    def turn_off_qq(self, sec_num: int, qq: str):
        """
        For the specified section, set the value of the specified QQ
        (e.g. 'NENE') to 0, in the appropriate SectionGrid in the
        `.sections` attribute of this TownshipGrid object.

        :param sec_num: An integer (1 - 36) for section number. (Use 0
        to throw away into the junk drawer without raising an error.)
        :param qq: The name of a QQ (one of the 16 standard QQs only
        -- e.g. 'NENE', 'SWSE', etc.)
        """
        if sec_num in self.sections.keys():
            self.sections[int(sec_num)].turn_on_qq(qq=qq)

    def turn_on_qq(self, sec_num: int, qq: str, custom_val=1):
        """
        For the specified section, set the value of the specified QQ
        (e.g. 'NENE') to `1`, in the appropriate SectionGrid in the
        `.sections` attribute of this TownshipGrid object.
        :param sec_num: An integer (1 - 36) for section number. (Use 0
        to throw away into the junk drawer without raising an error.)
        :param qq: The name of a QQ (one of the 16 standard QQs only
        -- e.g. 'NENE', 'SWSE', etc.)
        :param custom_val: Instead of 1, use a different 'on' value
        for this QQ.
        WARNING: Using a `custom_val` as anything other than 1 will
        break most functionality in this module, so it should only be
        used if you have a deep understanding of its implications.
        """

        # Note: Passing anything other than `1` to `custom_val` will
        # probably cause other current functionality to break. But it
        # might be useful for some purposes (e.g., tracking which
        # PLSS descriptions include that QQ).

        if sec_num in self.sections.keys():
            self.sections[int(sec_num)].turn_on_qq(qq=qq, custom_val=custom_val)


class LotDefinitions(dict):
    """
    A dict object (which often get abbreviated 'ld' or 'LD' in code
    comments and documentation) for defining which lots correspond to
    which QQ in a given section. At init, pass in an int 1 - 36
    (inclusive) to set to the /default/ for that section in a STANDARD
    township (i.e. perhaps 'better-than-nothing').

    These objects can also be contained within a TwpLotDefinitions
    object for a 36-section collection of such lot-to-QQ definitions.
    In turn, TwpLotDefinitions can be contained within a LotDefDB
    object for definitions of lots in the sections of any number of
    townships.

    See `LotDefDB.from_csv()` or `TwpLotDefinitions.from_csv()` for
    loading larger databases from .csv files, rather than creating
    LotDefinitions objects individually.

    Additional documentation on LotDefinitions is maintained under
    pytrsplat.LotDefDB objects, to avoid undue repetition.
    """

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
        is acceptable), by passing definitions through pytrs parsing."""

        # If no leading 'L' was fed in, add it now (e.g. 1 -> 'L1')
        if str(lot).upper()[0] != 'L':
            lot = 'L' + str(lot).upper()

        # Ensure the definitions are broken down into QQ's by passing them
        # through pytrs.Tract parsing, and pulling the resulting qqs.
        qq_list = pytrs.Tract(
            desc=definition, parse_qq=True,
            config='clean_qq,qq_depth.2').qqs
        self[lot] = ','.join(qq_list)

    def absorb_ld(self, dct):
        """Absorb another LotDefinitions object. Will overwrite existing
        keys, if any. Using this method ensures that the resulting
        format will be as expected elsewhere in the program (assuming
        input format is acceptable), by passing definitions through
        pytrs parsing."""
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
    """
    A dict object (which often get abbreviated 'tld' or 'TLD' in code
    comments and documentation) of LotDefinition objects (i.e.
    essentially a nested dict) for an entire township. Each key is a
    section number (an int), whose value is a LotDefinition object for
    that section. If a section number (int) or list of section numbers
    (all ints) is passed at init, will create default LotDefinitions
    objects for those sections.

    A pytrsplat.TwpLotDefinitions object is a nested dict with this
    structure:
    - TwpLotDefinitions - dict, keyed by sec number (int), value-type:
    -- LotDefinitions - dict, keyed by lot name (ex: 'L2'), value-type:
    --- a string, being QQ name(s), separated by comma if more than one
            (i.e. how each lot should be interpreted in terms of QQ's
                ex: 'L2' -> 'NWNE')
    Thus, rudimentary access might be:
        tld_obj[1]['L2'] -> 'NWNE'
            (i.e. Lot 2, of Sec 1 of this township corresponds with the
            NW/4NE/4 of said section)
    However, see custom getter method `TwpLotDefinitions.get_ld()`,
    which has more robust handling of default / unspecified values.

    IMPORTANT: TwpLotDefinitions objects contain ONLY one element by
    default: Key `0`, whose value is a meaningless LotDefinitions obj,
    used as a 'junk drawer' for error-ridden sections. Additional
    LotDefinitions objects can be added with the `.set_section()` method
    or by loading appropriately formatted data from a .csv file with
    `.load_csv()`.

    NOTE: The `.get_ld()` method is recommended over Python's built-in
    dict getters (i.e. `dct['key']` or `dct.get('key')`), because it
    adds more specific functionality for handling defaults.

    These objects can be contained within a pytrsplat.LotDefDB object
    (keyed by T&R, formatted '000x000x' or fewer digits -- e.g.,
    '154n97w' for T154N-R97W) for definitions of lots in the sections of
    any number of townships.

    See `LotDefDB.from_csv()` or `TwpLotDefinitions.from_csv()` for
    loading larger databases from .csv files, rather than creating
    TwpLotDefinitions objects individually.

    Additional documentation on TwpLotDefinitions is maintained under
    pytrsplat.LotDefDB objects, to avoid undue repetition.
    """

    def __init__(self, default_sections=None):
        """
        A dict object (which often get abbreviated 'tld' or 'TLD' in
        code comments and documentation) of LotDefinition objects (i.e.
        essentially a nested dict) for an entire township. Each key is a
        section number (an int), whose value is a LotDefinition object
        for that section. If a section number (int) or list of section
        numbers (all ints) is passed at init, will create default
        LotDefinitions objects for those sections.

        :param default_sections: A single integer, or list of integers,
        for the section(s) for which default LotDefinitions should be
        created at init. Defaults to None.
        """
        super().__init__()

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
        """
        Set the LotDefinitions object for a specified section.
        """
        # This need not be a defined method, but it's more intuitively
        # named, so... why not.
        self[sec_num] = lot_defs

    def get_ld(self, sec_num: int, allow_ld_defaults=False,
               force_ld_return=False):
        """
        A custom getter for pulling LotDefinitions object for the
        requested section, out of this TwpLotDefinitions object. There
        are two parameters to dictate the behavior of this getter, in
        the event that the key (`sec_num`) does not exist in this dict,
        and they apply in order:
        -- `allow_ld_defaults` (defaults to False): If an explicit
        LotDefinitions object does not already exist for the requested
        key (`sec_num`), then create and return a default LotDefinitions
        object, whose lots are defined as defaults according to the
        `sec_num`. In other words, if `sec_num` is an integer of 1 - 7,
        18, 19, 30, or 31, the returned LotDefinitions object will have
        some lots defined (per a 'standard' township); but any other
        section number would be an empty LotDefinitions object.
            NOTE: This getter does NOT add the returned default
                LotDefinitions object to the TwpLotDefinitions object!
        -- `force_ld_return` (defaults to False): If an explicit
        LotDefinitions object does not already exist, and the user did
        not want a default LotDefinitions object as a backup, then this
        parameter dictates whether to return None (i.e. `=False`), or to
        return an empty LotDefinitions object (i.e. `=True`).
            NOTE: This getter does NOT add the returned empty
                LotDefinitions object to the TwpLotDefinitions object!

        :param sec_num: The section number, whose LotDefinitions object
        is requested (i.e. the dict key).
        :param allow_ld_defaults: As discussed above.
        :param force_ld_return:  As discussed above.
        :return: If [a] a LotDefinitions object exists for the requested
        section, [b] the user passed `allow_ld_defaults=True`, AND/OR
        [c] the user passed `force_ld_return=True` -- then will return a
        LotDefinitions object. Otherwise, will return None.
        """

        sec_num = int(sec_num)
        ld = self.get(sec_num, None)
        if ld is not None:
            return ld
        elif allow_ld_defaults:
            # If there was no LD set for this section, but the user wants
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
        """
        Generate a TwpLotDefinitions object from a properly formatted**
        .csv file at filepath `fp`. Specify `twp=<str>` and `rge=<str>`
        for which rows should match.
            ex: tld_obj = TwpLotDefinitions.from_csv(
                    r'assets/examples/SAMPLE_LDDB.csv',
                    twp='154n', rge='97w')

        **See the docstring for LotDefDB for proper .csv formatting.

        :param fp: Filepath to the .csv file to load.
        :param twp: Township number (up to 3 digits) and N/S direction
        (as a single lowercase character).
            ex: '154n', '1s', etc.
        :param rge: Range number (up to 3 digits) and E/W direction
        (as a single lowercase character).
            ex: '97w', '7e', etc.
        :return: A new TwpLotDefinitions object that has loaded all
        relevant data from the .csv file.
        """

        if None in [twp, rge]:
            raise ValueError('`twp` and `rge` must be specified.')

        twp = twp.lower()
        rge = rge.lower()

        # Load a full LotDefDB object from .csv file, and then pull our
        # twp+rge from it. If our twp+rge does not exist as a key,
        # return an empty TLD object.
        temp_lddb = LotDefDB(from_csv=fp)
        return temp_lddb.get_tld(
            twp+rge, allow_ld_defaults=False, force_tld_return=True)


class LotDefDB(dict):
    """
    A dict object (which often get abbreviated 'lddb' or 'LDDB' in code
    comments and documentation) for defining which lots correspond to
    which QQs, for any number of sections in any number of Twp/Rge's.
    Keyed by Twp/Rge (as a single string, i.e. '154n97w' for T154N-R97W
    or '1s7e' for T1S-R7E), whose values are a TwpLotDefinition object
    for that Twp/Rge.

    A pytrsplat.LotDefDB object is a nested dict with this structure:
    - LotDefDB - dict, keyed by Twp/Rge (str), value-type:
    -- TwpLotDefinitions - dict, keyed by sec number (int), value-type:
    --- LotDefinitions - dict, keyed by lot name (ex: 'L2'), value-type:
    ---- a string, being QQ name(s), separated by comma if more than one
            (i.e. how each lot should be interpreted in terms of QQ's
                ex: 'L2' -> 'NWNE')
    Thus, rudimentary access might be:
        lddb_obj['154n97w'][1]['L2'] -> 'NWNE'
            (i.e. Lot 2, of Sec 1, T154N-R97W corresponds with the
            NW/4NE/4 of said section)
    However, see custom getter methods `LotDefDB.get_tld()` and
    `LotDefDB.trs()`, which have more robust handling of default /
    unspecified values. (See also `TwpLotDefinitions.get_ld()` method
    for similar reasons.)

    The `.get_tld()` method (for getting TwpLotDefinitions by `twprge`
    key) is recommended over Python's built-in dict getters (i.e.
    `dct['key']` or `dct.get('key')`), because it adds more specific
    functionality for handling defaults / key errors.
    There also exists the `.trs()` method, which is a deeper-level
    getter, i.e. it pulls out the (section-level) LotDefinitions object
    from another level down in this dict structure; rather than the
    (Twp/Rge-level) TwpLotDefinitions object, which is stored as a value
    of this dict.

    NOTE: If a string filepath to a properly formatted** .csv file is
    passed as init parameter `from_csv=`, the object will load the data
    represented in the .csv file. (See below for proper formatting.)

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
                        (These get passed through pytrs parsing, so
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
        """
        A nested dict of definitions of how specific lots should be
        interpreted, in terms of their QQ counterparts.
        :param from_csv: (Optional) The filepath to a .csv file that
        contains properly formatted data, which can be loaded into this
        LotDefDB object. (See LotDefDB documentation for guidelines on
        how a .csv file must be formatted.)
        """
        super().__init__()
        if from_csv is not None:
            self._import_csv(from_csv)

    def _import_csv(self, fp):
        """
        Read in a properly formatted** .csv file at filepath `fp`, and
        convert each unique T&R represented in the .csv file into a
        separate TwpLotDefinitions object, keyed by T&R (keys formatted
        '000x000y' or fewer digits -- ex: '154n97w' for T154N-R97W, or
        '1s6e' for T1S-R6E).

        **See the docstring for LotDefDB for proper .csv formatting.
        """

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
        """
        Set the TwpLotDefinitions object for a specified `twprge`
        (formatted '000x000z' or fewer digits, if not needed).
        """
        # This need not be a defined method, but it's more intuitively
        # named, so... why not.
        self[twprge] = tld_obj

    def get_tld(self, twprge, allow_ld_defaults=False,
                force_tld_return=False):
        """
        A custom getter for pulling TwpLotDefinitions object for the
        requested `twprge`, out of this LotDefDB object. There are two
        parameters to dictate the behavior of this getter, in the event
        that the key (`twprge`) does not exist in this dict, and they
        apply in order:
        -- `allow_ld_defaults` (defaults to False): If an explicit
        LotDefinitions object does not already exist for the requested
        key (`sec_num`), then create and return a TwpLotDefinitions
        object with default definitions for every section (i.e. sections
        1 - 7, 18, 19, 30, and 31 will have LotDefinitions objects with
        some lots defined (per a 'standard' township); but all other
        sections have empty LotDefinitions objects).
            NOTE: This getter does NOT add the returned default
                TwpLotDefinitions object to the LotDefDB object!
        -- `force_tld_return` (defaults to False): If an explicit
        TwpLotDefinitions object does not already exist, and the user
        did not want a default TwpLotDefinitions object as a backup,
        then this parameter dictates whether to return None (i.e.
        `=False`), or to return an empty TwpLotDefinitions object (i.e.
        `=True`).
            NOTE: This getter does NOT add the returned empty
                TwpLotDefinitions object to the LotDefDB object!

        :param twprge: The Twp/Rge combo (e.g. '154n97w', '1s8e', etc.),
        whose TwpLotDefinitions object is requested (i.e. the dict key).
        :param allow_ld_defaults: As discussed above.
        :param force_tld_return:  As discussed above.
        :return: If [a] a TwpLotDefinitions object exists for the
        requested twprge, [b] the user passed `allow_ld_defaults=True`,
        AND/OR [c] the user passed `force_tld_return=True` -- then will
        return a TwpLotDefinitions object. Otherwise, will return None.
        """

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
        return None

    def trs(self, trs, allow_ld_defaults=None, force_ld_return=False):
        """
        A custom getter for pulling the (section-level) LotDefinitions
        object for the specified `trs` (i.e. Twp/Rge/Sec), if one
        exists in this LotDefDB.

        Like the`TwpLotDefinitions.get_ld()`, this has two backup
        parameters that take over if no such LotDefinitions object
        exists, both with equivalent functionality as in that method:
        -- `allow_ld_defaults` (defaults to False)
        -- `force_ld_return` (defaults to False)
        NOTE: This getter will not set the returned default/empty
            LotDefinitions object (if any) to this LotDefDB object!

        :param trs: The Twp/Rge/Sec of the desired section, in the
        format '000x000x00' (up to 3 digits for twp and rge, exactly 2
        digits for section).
            ex: '154n97w01', '1s7e36', etc.
        :param allow_ld_defaults: As discussed above.
        :param force_ld_return:  As discussed above.
        :return: If [a] a LotDefinitions object exists for the requested
        section, [b] the user passed `allow_ld_defaults=True`, AND/OR
        [c] the user passed `force_ld_return=True` -- then will return a
        LotDefinitions object. Otherwise, will return None.
        """

        trs_obj = pytrs.TRS(trs)
        tld = self.get_tld(
            trs_obj.twprge, allow_ld_defaults=allow_ld_defaults,
            force_tld_return=force_ld_return)
        if tld is not None:
            return tld.get_ld(
                sec_num=trs_obj.sec_num, allow_ld_defaults=allow_ld_defaults,
                force_ld_return=force_ld_return)
        return None


def plssdesc_to_twp_grids(
        plssdesc: pytrs.PLSSDesc, lddb=None,
        allow_ld_defaults=False) -> dict:
    """
    Generate a dict of TownshipGrid objects (keyed by T&R, i.e. up to
    3 digits for township and range number, and a single lowercase
    letter for N/S and E/W -- i.e. '154n97w' for T154N-R97W or '1s7e'
    for T1S-R7E) from a parsed pytrs.PLSSDesc object.

    :param plssdesc: An already-parsed pytrs.PLSSDesc object whose
    subordinate pytrs.Tract objects (which have also been parsed into
    lots and QQs) should be applied to the resulting TownshipGrid
    objects (i.e. incorporating the Tract objects' `.lots` and
    `.qqs` attributes into the subordinate SectionGrid objects under
    the TownshipGrids).
    :param lddb: Either a pytrsplat.LotDefDB object, or a filepath (str)
    to a .csv file** that can be loaded into a LotDefDB -- for how every
    lot should be interpreted in terms of its QQ counterpart(s).
    (**See LotDefDB documentation for how to properly format.)
    :param allow_ld_defaults: Whether 'default' lot definitions are
    allowed as a fall-back option, when lots have not been explicitly
    defined for a given section. (Default lots are the 'usual' lots in
    Sections 1 - 7, 18, 19, 30, and 31 of a 'standard' township -- i.e.
    along the northern and western boundaries of a township. Potentially
    useful as a 'better-than-nothing' option, but not as reliable as
    user-specified lot definitions.)
    :return: A dict (keyed by T&R) of TownshipGrid objects, whose values
    are set according to the .
    """
    tl = plssdesc.tracts
    return tracts_into_twp_grids(
        tl, lddb=lddb, allow_ld_defaults=allow_ld_defaults)


def tracts_into_twp_grids(
        tract_list, grid_dict=None, lddb=None, allow_ld_defaults=False) -> dict:
    """
    Incorporate a list of parsed pytrs.Tract objects into respective
    TownshipGrid objects, and return a dict of those TownshipGrid objs
    (keyed by T&R). If an existing `grid_dict` is passed, it will be
    updated and returned. If not, a new one will be created and
    returned.
    Optionally specify `lddb=<LotDefDB>` to define lots and get better
    results.

    :param tract_list: A list of already-parsed pytrs.Tract objects
    whose `.lots` and `.qqs` attributes should incorporated into
    the TownshipGrid objects.
    :param grid_dict: An existing dict (keyed by T&R) of TownshipGrid
    objects (one TownshipGrid per unique Twp/Rge), which will be updated
    and returned. (If no existing dict is passed here, a new one will be
    created and returned.)
    :param lddb: Either a pytrsplat.LotDefDB object, or a filepath (str)
    to a .csv file** that can be loaded into a LotDefDB -- for how every
    lot should be interpreted in terms of its QQ counterpart(s).
    (**See LotDefDB documentation for how to properly format.)
    :param allow_ld_defaults: Whether 'default' lot definitions are
    allowed as a fall-back option, when lots have not been explicitly
    defined for a given section. (Default lots are the 'usual' lots in
    Sections 1 - 7, 18, 19, 30, and 31 of a 'standard' township -- i.e.
    along the northern and western boundaries of a township. Potentially
    useful as a 'better-than-nothing' option, but not as reliable as
    user-specified lot definitions.)
    """
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
    for tract in tract_list:

        # Get the TLD for this T&R from the lddb, if one exists. If not,
        # create and use a default TLD object. (We `force_tld_return` to
        # ensure that a TwpLotDefinitions object gets returned, instead
        # of None)
        tld = lddb.get_tld(
            tract.twprge, allow_ld_defaults=allow_ld_defaults, force_tld_return=True)

        # If a TownshipGrid object does not yet exist for this T&R in
        # the dict, create one, and add it to the dict now.
        grid_dict.setdefault(
            tract.twprge, TownshipGrid(twp=tract.twp, rge=tract.rge, tld=tld))

        # Now incorporate the Tract object into a SectionGrid object
        # within the dict. No /new/ SectionGrid objects are created at
        # this point (since a TownshipGrid object creates all 36 of them
        # at init), but SectionGrid objects are updated at this point to
        # incorporate our tracts.
        twp_grid = grid_dict[tract.twprge]
        twp_grid.incorporate_tract(tract, tract.sec_num)

    return grid_dict
