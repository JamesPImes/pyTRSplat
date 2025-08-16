from __future__ import annotations
from warnings import warn

from PIL import Image, ImageDraw
import pytrs
from pytrs.parser.tract.aliquot_simplify import AliquotNode

from ..plat_settings2 import Settings
from ...utils2 import calc_midpt, get_box, get_box_outline
from .lot_definer import LotDefiner

__all__ = [
    'Plat',
    'PlatGroup',
    'MegaPlat',
]

DEFAULT_SETTINGS = Settings()


class SettingsOwner:
    """
    Interface for a class that has a ``Settings`` object in its
    ``.settings`` attribute.
    """
    settings: Settings


class ImageOwner:
    """
    Interface for a class that has the following attributes:

    ``.image``  (``Image``)
    ``.draw``  (``ImageDraw.Draw``)
    ``.overlay_image``  (``Image``)
    ``.overlay_draw``  (``ImageDraw.Draw``)
    ``.footer_image``  (``Image``)
    ``.footer_draw``  (``ImageDraw.Draw``)
    ``.image_layers``  (tuple of ``Image``)

    And an ``.output()`` method.
    """
    image: Image
    draw: ImageDraw.Draw
    overlay_image: Image
    overlay_draw: ImageDraw.Draw
    footer_image: Image
    footer_draw: ImageDraw.Draw
    image_layers: tuple[Image]

    def output(self):
        """Compile and return the merged image of the plat."""
        if not self.image_layers:
            return None
        merged = Image.alpha_composite(*self.image_layers[:2])
        for i in range(2, len(self.image_layers)):
            merged = Image.alpha_composite(merged, self.image_layers[i])
        return merged


class ILotDefinerOwner:
    """
    Interface for a class that has a ``LotDefiner`` object in its
    ``.lot_definer`` attribute.
    """
    lot_definer: LotDefiner
    # Cache of lot definitions (including defaults). Gets used while
    # executing queue, then cleared.
    all_lot_defs_cached: dict


class IPlatOwner(SettingsOwner, ImageOwner, ILotDefinerOwner):
    """
    Composite interface for a class that incorporates all necessary
    interfaces necessary for platting.
    """
    pass


class ISettingsLotDefinerOwner(SettingsOwner, ILotDefinerOwner):
    """
    Composite interface for a class that incorporates ``SettingsOwner``
    and ``ILotDefinerOwner``.
    """
    pass


class SettingsOwned:
    """
    Class with an ``owner`` (``SettingsOwner``) that has a
    ``.settings`` attribute to be passed down as a ``.settings``
    property.
    """
    owner: SettingsOwner

    @property
    def settings(self):
        if self.owner is not None:
            return self.owner.settings
        return DEFAULT_SETTINGS


class ImageOwned:
    """
    Class with an ``owner`` (``ImageOwner``) with the various image and
    draw properties needed for platting.
    """
    owner: ImageOwner

    @property
    def image(self):
        return self.owner.image

    @property
    def draw(self):
        return self.owner.draw

    @property
    def overlay_image(self):
        return self.owner.overlay_image

    @property
    def overlay_draw(self):
        return self.owner.overlay_draw

    @property
    def footer_image(self):
        return self.owner.footer_image

    @property
    def footer_draw(self):
        return self.owner.footer_draw


class QueueSingle:
    """
    Class that can take in a ``pytrs.Tract`` and add it to the
    ``.queue`` (a ``pytrs.TractList``).
    """

    queue: pytrs.TractList()

    def add_tract(self, tract: pytrs.Tract):
        """
        Add a tract to the queue.

        .. note::
          The tract must already be parsed for lots/QQs. (See ``pyTRS``
          documentation for details.)
        """
        self.queue.append(tract)


class QueueMany(QueueSingle):
    """
    Class that can take in multiple tracts or a raw PLSS description and
    add the results to the ``.queue`` (a ``pytrs.TractList``).
    """

    def add_tracts(
            self, tracts: list[pytrs.Tract] | pytrs.TractList | pytrs.PLSSDesc) -> None:
        """
        Add multiple tracts to the queue. If no plat yet exists for the
        Twp/Rge of any of these tracts, plats will be created as needed.

        .. note::
          The tracts must already be parsed for lots/QQs. (See ``pyTRS``
          documentation for details.)

        :param tracts: A collection of ``pytrs.Tract`` objects,
         such as a ``pytrs.PLSSDesc``, ``pytrs.TractList``, or any other
         iterable object that contains ``pytrs.Tract``.
        """
        for tract in tracts:
            self.add_tract(tract)
        return None

    def add_description(self, txt: str, pytrs_config: str = None) -> pytrs.TractList:
        """
        Parse the land description and add the resulting tracts to the
        plat group. If one or more Twp/Rge's are newly identified, plats
        will be created as needed.

        :param txt: The land description.
        :param pytrs_config: The config parameters for parsing. (See
         pyTRS documentation for details.)
        :return: A ``pytrs.TractList`` containing the tracts in which
         the parser could not identify any lots or aliquots.
        """
        plssdesc = pytrs.PLSSDesc(txt, parse_qq=True, config=pytrs_config)
        self.add_tracts(plssdesc)
        no_lots_qqs = pytrs.TractList()
        for tract in plssdesc:
            if not tract.lots_qqs:
                no_lots_qqs.append(tract)
        return no_lots_qqs


class PlatAliquotNode(AliquotNode, SettingsOwned, ImageOwned):
    """
    INTERNAL USE:

    Subclass to extend pytrs's ``AliquotNode`` for platting.
    """

    def __init__(self, parent=None, label=None, owner: IPlatOwner = None):
        """
        :param owner: The ``Plat`` object that is the ultimate owner of
         this node. (Controls the settings that dictate platting
         behavior and appearance, and contains the image objects that
         will be drawn on.)
        """
        super().__init__(parent=parent, label=label)
        # Coord of top-left of this square.
        self.xy: tuple[int, int] = None
        # `.owner` must have .settings, .image, .draw, .overlay_image, .overlay_draw
        self.owner: IPlatOwner = owner

    @property
    def sec_length_px(self):
        """Get the configured length of a section line, in pixels."""
        return self.settings.sec_length_px

    @property
    def square_dim(self):
        """
        Calculate the length of this aliquot division's line, in pixels,
        based on the configured length of a section line.
        """
        return self.sec_length_px // (2 ** self.depth)

    def configure(
            self,
            parent_xy: tuple[int, int] = None
    ):
        """
        Retrofit this node and all its children for platting, using the
        specified configurations.

        :param parent_xy: The top-left coord of the parent node (or for
         the root node, the section's top-left coord).
        """
        stn = self.settings
        if parent_xy is None:
            parent_xy = self.xy
        x, y = parent_xy
        if self.label is not None:
            # Offset this subdivided square from the top-left of parent square.
            # 'NW' (the top-left) remains at parent's (x, y).
            if self.label in ('NE', 'SE'):
                x += self.square_dim
            if self.label in ('SE', 'SW'):
                y += self.square_dim
        self.xy = (x, y)
        if stn.max_depth is not None and self.depth >= stn.max_depth:
            # Discard nodes beyond the specified ``max_depth``. (Destroys
            # all granularity in aliquots beyond that depth.)
            self.children = {}
            return None
        for label, child_node in self.children.items():
            child_node.owner = self.owner
            child_node.configure(parent_xy=self.xy)
        return None

    def fill(self, rgba: tuple[int, int, int, int] = None):
        """
        Fill in this aliquot on the plat.
        :param rgba: The RGBA value to use. If not passed, will use what
         is configured in the owner's settings.
        """
        if rgba is None:
            cf = self.settings
            rgba = cf.qq_fill_rgba
        if self.is_leaf():
            box = get_box(self.xy, dim=self.square_dim)
            self.overlay_draw.polygon(box, rgba)
        for child in self.children.values():
            child.fill(rgba)
        return None

    def write_lot_numbers(self, at_depth):
        """
        Write lot numbers to the plat.

        :param at_depth: Depth at which to write the lots. MUST match
         the depth at which the lot definitions have been parsed.
         Default is 2 (i.e., quarter-quarters), specified above in the
         stack.
        """
        if self.depth == at_depth:
            lot_txt = ', '.join(str(l) for l in sorted(self.sources))
            stn = self.settings
            draw = self.draw
            font = stn.lotfont
            fill = stn.lotfont_rgba
            offset = stn.lot_num_offset_px
            x, y = self.xy
            draw.text(xy=(x + offset, y + offset), text=lot_txt, font=font, fill=fill)
            return None
        for child in self.children.values():
            child.write_lot_numbers(at_depth)


class PlatSection(SettingsOwned, ImageOwned):
    """A section of land, as represented in the plat."""

    def __init__(
            self,
            trs: pytrs.TRS = None,
            grid_offset: tuple[int, int] = None,
            owner: IPlatOwner = None,
            is_lot_writer: bool = False,
    ):
        """
        :param trs: The Twp/Rge/Sec (a ``pytrs.TRS`` object) of this
         section.
        :param grid_offset: How many sections down and right from the
         top-left of the township. (The offset of Section 6 is (0, 0);
         whereas the offset of Section 36 is (6, 6).)
        :param owner: The ``Plat`` object that is the ultimate owner of
         this section. (Controls the settings that dictate platting
         behavior and appearance, and contains the image objects that
         will be drawn on.)
        :param is_lot_writer: If True, this is only intended for writing
         lot numbers to the plat.
        """
        if trs is not None:
            trs = pytrs.TRS(trs)
        self.trs: pytrs.TRS = trs
        self.aliquot_tree = PlatAliquotNode(owner=owner)
        self.queue = pytrs.TractList()
        self.square_dim: int = None
        # Coord of top-left of this square.
        self.xy: tuple[int, int] = None
        self.sec_length_px: int = None
        self.grid_offset: tuple[int, int] = grid_offset
        # `.owner` must have .settings, .image, .draw, .overlay_image, .overlay_draw
        self.owner: IPlatOwner = owner
        self.is_lot_writer = is_lot_writer

    def configure(self, grid_xy):
        """
        Configure this section and its subordinates.

        :param grid_xy: The top-left coord of the township to which this
         section belongs.
        """
        settings = self.settings
        sec_length_px = settings.sec_length_px
        x, y = grid_xy
        i, j = self.grid_offset
        x += j * sec_length_px
        y += i * sec_length_px
        self.sec_length_px = sec_length_px
        self.square_dim = sec_length_px
        self.xy = (x, y)
        if not self.is_lot_writer:
            self.draw_lines()
            self.clear_center()
        self.aliquot_tree.configure(parent_xy=self.xy)

    def draw_lines(self):
        """
        Draw section lines, and aliquot division lines (halves,
        quarters, quarter-quarters, etc.).

        The number of aliquot divisions that are drawn is controlled by
        ``.min_depth`` in the settings.
        """
        settings = self.settings
        min_depth: int = settings.min_depth
        # Top-left of this section.
        x, y = self.xy
        sec_len = settings.sec_length_px
        sec_lines = get_box_outline(xy=(x, y), dim=sec_len)
        # Calculate coords for desired lines.
        # ... Outer lines are section boundaries.
        depth_lines: dict[int, list[tuple[int, int]]] = {0: sec_lines}
        # ... Lines for halves (depth=1), quarters (depth=2), quarter-quarters, etc.
        for depth in range(1, min_depth + 1):
            depth_lines[depth] = []
            div_sec_len = sec_len // (2 ** depth)
            for i in range(1, (2 ** depth) + 1, 2):
                ns = ((x + div_sec_len * i, y), (x + div_sec_len * i, y + sec_len))
                depth_lines[depth].append(ns)
                ew = ((x, y + div_sec_len * i), (x + sec_len, y + div_sec_len * i))
                depth_lines[depth].append(ew)

        draw = self.draw
        for depth in reversed(depth_lines.keys()):
            lines = depth_lines[depth]
            width = settings.line_stroke.get(depth, settings.line_stroke[None])
            fill = settings.line_rgba.get(depth, settings.line_rgba[None])
            for line in lines:
                draw.line(line, fill=fill, width=width)
        return None

    def clear_center(self):
        """
        Clear the center of the section. If so configured, write the
        section number there.
        """
        settings = self.settings
        draw = self.draw
        # Draw middle white space.
        cb_dim = settings.centerbox_dim
        x_center, y_center = calc_midpt(xy=self.xy, square_dim=self.sec_length_px)
        topleft = x_center - cb_dim // 2, y_center - cb_dim // 2
        centerbox = get_box(xy=topleft, dim=cb_dim)
        draw.polygon(centerbox, Settings.RGBA_WHITE)
        if not settings.write_section_numbers:
            return None
        font = settings.secfont
        fill = settings.secfont_rgba
        txt = str(self.trs.sec_num)
        _, _, w, h = draw.textbbox(xy=(0, 0), text=txt, font=font)
        # Force a slight upward shift of the section text. Looks wrong otherwise.
        horizontal_tweak_pct = 1.2
        sec_topleft = (x_center - w // 2, y_center - int((h // 2) * horizontal_tweak_pct))
        draw.text(xy=sec_topleft, text=txt, font=font, fill=fill)
        return None

    def execute_queue(self) -> pytrs.TractList:
        """
        Execute the queue of tracts to fill in the plat.
        """
        unplattable_tracts = pytrs.TractList()
        if not self.queue:
            return unplattable_tracts
        for tract in self.queue:
            self.owner.lot_definer.process_tract(tract, commit=True)
            if not tract.qqs and not tract.lots_as_qqs and not tract.undefined_lots:
                message = (
                    "No lots or aliquots could be identified for tract: "
                    f"<{tract.quick_desc_short()}>"
                )
                warn(message, UserWarning)
                unplattable_tracts.append(tract)
            self.aliquot_tree.register_all_aliquots(tract.qqs)
            self.aliquot_tree.register_all_aliquots(tract.lots_as_qqs)
            if tract.undefined_lots:
                message = (
                    "Undefined lots that could not be shown on the plat: "
                    f"<{tract.trs}: {', '.join(tract.undefined_lots)}>"
                )
                warn(message, UserWarning)
        if len(self.queue) != len(unplattable_tracts):
            self.aliquot_tree.configure()
            self.aliquot_tree.fill()
        return unplattable_tracts

    def write_lot_numbers(self, at_depth=2):
        """
        Write the lot numbers in the section.

        :param at_depth: At which depth to write the numbers. Defaults
         to 2 (i.e., quarter-quarters).
        """
        ld = self.owner.all_lot_defs_cached
        lots_definitions = ld.get(self.trs.twprge, {}).get(self.trs.sec_num, {})
        for lot, definitions in lots_definitions.items():
            tract = pytrs.Tract(
                definitions, parse_qq=True, config=f"clean_qq,qq_depth.{at_depth}")
            ilot = int(lot.split('L')[-1])
            self.aliquot_tree.register_all_aliquots(tract.qqs, ilot)
        self.aliquot_tree.configure(parent_xy=self.xy)
        self.aliquot_tree.write_lot_numbers(at_depth)
        return None


class PlatBody(SettingsOwned, ImageOwned):
    """
    The part of a ``Plat`` that contains the township grid (36
    sections).
    """

    # PLSS sections "snake" from the NE corner of the township west
    # then down, then they cut back east, then down and west again,
    # etc., thus:
    #           6   5   4   3   2   1
    #           7   8   9   10  11  12
    #           18  17  16  15  14  13
    #           19  20  21  22  23  24
    #           30  29  28  27  26  25
    #           31  32  33  34  35  36
    SEC_NUMS = list(range(6, 0, -1))
    SEC_NUMS.extend(list(range(7, 13)))
    SEC_NUMS.extend(list(range(18, 12, -1)))
    SEC_NUMS.extend(list(range(19, 25)))
    SEC_NUMS.extend(list(range(30, 24, -1)))
    SEC_NUMS.extend(list(range(31, 37)))
    SEC_NUMS = tuple(SEC_NUMS)

    def __init__(
            self,
            twp: str = None,
            rge: str = None,
            owner: IPlatOwner = None,
            is_lot_writer=False
    ):
        """
        :param twp: The Twp of the Twp/Rge represented by this body.
        :param rge: The Rge of the Twp/Rge represented by this body.
        :param owner: The ``Plat`` object that is the ultimate owner of
         this body. (Controls the settings that dictate platting
         behavior and appearance, and contains the image objects that
         will be drawn on.)
        :param is_lot_writer: Tell this ``PlatBody`` that it will only
         be used to write lots onto the plat. (If ``True``, prevents
         redrawing section lines, quarter lines, etc.; and enables the
         writing of lot numbers in the respective QQs.)
        """
        self.owner: IPlatOwner = owner
        self.twp = twp
        self.rge = rge
        self.sections: dict[int, PlatSection] = {}
        sections_per_side = 6
        k = 0
        # Store each section's "offset" from the top-left of the grid.
        for i in range(sections_per_side):
            for j in range(sections_per_side):
                sec_num = self.SEC_NUMS[k]
                trs = pytrs.TRS.from_twprgesec(twp, rge, sec_num)
                plat_sec = PlatSection(
                    trs,
                    grid_offset=(i, j),
                    owner=self.owner,
                    is_lot_writer=is_lot_writer)
                self.sections[sec_num] = plat_sec
                k += 1
        # Coord of top-left of the grid.
        self.xy: tuple[int, int] = None
        self.is_lot_writer = is_lot_writer

    def nonempty_sections(self):
        """Get a list of any sections that have aliquots to be platted."""
        output = []
        for sec_num, plat_sec in self.sections.items():
            if not plat_sec.aliquot_tree.is_leaf():
                output.append(sec_num)
        return output

    def configure(self, xy: tuple[int, int] = None):
        """
        Enact the settings to configure this plat body.

        :param xy: The top-left coord of the area of the plat containing
         the grid.
        """
        if xy is None:
            xy = self.settings.grid_xy
        self.xy = xy
        for plat_sec in self.sections.values():
            plat_sec.configure(grid_xy=xy)
        return None

    def write_lot_numbers(self, at_depth=2):
        """
        Write the lot numbers into the respective squares.

        :param at_depth: At which depth to write the numbers. Defaults
         to 2 (i.e., quarter-quarters).
        """
        if not self.is_lot_writer:
            raise ValueError(
                'This `PlatBody` is not a lot writer. '
                'Pass `is_lot_writer=True` at init.'
            )
        for sec_plat in self.sections.values():
            sec_plat.write_lot_numbers(at_depth)
        return None

    def draw_outline(self):
        """
        Draw the boundary around the township.
        """
        stn = self.settings
        lines = get_box_outline(xy=self.xy, dim=stn.sec_length_px * 6)
        width = stn.line_stroke[-1]
        fill = stn.line_rgba[-1]
        for line in lines:
            self.draw.line(line, fill=fill, width=width)


class PlatHeader(SettingsOwned, ImageOwned):

    def __init__(self, owner: IPlatOwner):
        self.owner = owner

    def write_header(
            self,
            twp=None,
            rge=None,
            xy: tuple[int, int] = None,
            custom_header: str = None,
            align='default',
            **kw
    ) -> None:
        """
        Write the header to the plat.

         .. note::
            The default header is the Twp/Rge, styled as follows
            ``Township 154 North, Range 97 West``.
            if ``short_header=True`` in the settings, the resulting
            header will be styled as ``T154N-R97W``. The header can be
            styled differently if appropriate keyword arguments are
            passed as ``kw``. Further, the exact header text can be
            passed as ``custom_header``, which will override everything
            else.

        :param twp: The Twp of this plat (e.g., ``'154n'``)
        :param rge: The Rge of this plat (e.g., ``'97w'``)
        :param xy: The anchor point at which to write. (Defaults to
         above the plat, as configured by margins in settings.)
        :param custom_header: (Optional) Override the default header and
         use this text instead. If used, any other keyword arguments
         will be ignored.
        :param align: Either ``'default'`` (to aligned horizontally
         centered) or ``'center_center'`` (to center both horizontally
         and vertically).
        :param kw: (Optional) keyword arguments to pass to
         ``pytrs.TRS.pretty_twprge()`` to control how the Twp/Rge header
         should be spelled out.
        """
        if align not in ('default', 'center_center'):
            raise ValueError(
                f"`align` must be one of ('default', 'center_center'). "
                f"Passed: {align!r}"
            )
        header = custom_header
        if not kw and not self.settings.short_header:
            kw = {
                't': 'Township ',
                'n': ' North',
                's': ' South',
                'r': 'Range ',
                'e': ' East',
                'w': ' West',
                'delim': ', '
            }
        if header is None:
            trs = pytrs.TRS.from_twprgesec(twp, rge, 0)
            header = trs.pretty_twprge(**kw)
        font = self.settings.headerfont
        fill = self.settings.headerfont_rgba
        draw = self.draw
        _, _, w, h = draw.textbbox(xy=(0, 0), text=header, font=font)
        if xy is None and align == 'default':
            x = (self.image.width - w) // 2
            y = self.settings.body_marg_top_y - h - self.settings.header_px_above_body
        else:
            x, y = xy
        if align == 'center_center':
            x -= w // 2
            y -= h // 2
        draw.text(xy=(x, y), text=header, font=font, fill=fill)
        return None


class PlatFooter(SettingsOwned, ImageOwned):
    """
    The part of a ``Plat`` that will contain written text, such as the
    tract descriptions.
    """

    def __init__(self, owner: IPlatOwner = None):
        """
        :param owner: The ``Plat`` object (or other appropriate type)
         that is the ultimate owner of this footer. (Controls the
         settings that dictate platting behavior and appearance, and
         contains the image objects that will be drawn on.)
        """
        self.owner: IPlatOwner = owner
        self._x = None
        self._y = None
        self._text_line_height = None
        self._trs_indent = None

    def configure(self):
        """
        Enact the settings to configure this plat footer.
        """
        stn = self.settings
        x = stn.footer_marg_left_x
        y = (stn.body_marg_top_y + stn.sec_length_px * 6 + stn.footer_px_below_body)
        self._x, self._y = (x, y)
        sample_trs = 'XXXzXXXzXX:'
        font = stn.footerfont
        _, _, w, h = self.draw.textbbox(xy=(0, 0), text=sample_trs, font=font)
        self._text_line_height = h
        self._trs_indent = x + w

    def _write_line(
            self, x: int, text: str, fill: tuple[int, int, int, int] = None) -> None:
        """
        INTERNAL USE:

        Write an already-verified line of text, with no linebreaks.

        :param x: Left-most position at which to write text.
        :param text: The line to write.
        """
        stn = self.settings
        font = stn.footerfont
        if fill is None:
            fill = stn.footerfont_rgba
        draw = self.footer_draw
        draw.text(xy=(x, self._y), text=text, font=font, fill=fill)
        self._y += self._text_line_height + stn.footer_px_between_lines
        return None

    def check_text(
            self,
            text,
            xy_0: tuple[int, int],
            xy_limit: tuple[int, int] = None
    ) -> (list[str], str | None):
        """
        Check if the ``text`` can be written within the confines of this
        footer. Returns two parts: (1) the reformatted text (broken onto
        a list of writable lines) and (2) any text that can't fit (a
        string). If all text can be written, the second returned value
        will be ``None``.
        """
        x0, y0 = xy_0
        if xy_limit is None:
            stn = self.settings
            xy_limit = (
                stn.dim[0] - stn.footer_marg_right_x,
                stn.dim[1] - stn.footer_marg_bottom_y
            )
        x_lim, y_lim = xy_limit
        avail_w = x_lim - x0
        avail_h = y_lim - y0
        stn = self.settings
        unwritable = None
        words = text.split()
        writable_lines = []
        line = ""
        for i, word in enumerate(words):
            cand_line = f"{line} {word}"
            c_width = stn.footerfont.getlength(cand_line)
            if c_width <= avail_w:
                line = cand_line
            else:
                writable_lines.append(line)
                line = word
                avail_h -= (self._text_line_height + stn.footer_px_between_lines)
                if avail_h <= self._text_line_height:
                    unwritable = ' '.join(words[i:])
                    break
        if line:
            writable_lines.append(line)
        return writable_lines, unwritable

    def write_tracts(
            self,
            tracts: pytrs.TractList | pytrs.PLSSDesc,
            write_partial=True,
    ) -> list[pytrs.Tract]:
        """
        Write multiple tracts in the footer. Will return a list of
        tracts that could not be written (or an empty list if all were
        successfully written or at least partially written).

        :param write_partial: (Optional, on by default) If there is not
         space to write a tract's entire description, write whatever
         will fit. (A partially written tract will NOT be included in
         the returned unwritten tracts.)
        :return: A list of tracts that could not be written in the space
         available.
        """
        unwritten = []
        for tract in tracts:
            unwritten_tract = self.write_tract(tract, write_partial)
            if unwritten_tract is not None:
                unwritten.append(tract)
        return unwritten

    def write_tract(
            self,
            tract: pytrs.Tract,
            write_partial=True,
            font_rgba: tuple[int, int, int, int] = None,
    ) -> pytrs.Tract | None:
        """
        Write a single tract in the footer.

        :param write_partial: (Optional, on by default) If there is not
         space to write the tract's entire description, write whatever
         will fit. (A partially written tract will NOT be returned as
         unwritten.)
        :param font_rgba: (Optional) Specify the RGBA code to use for
         this tract. If not specified, will use the ``.footerfont_rgba``
         specified in the settings.
        :return: If the tract is successfully written (or partially
         written), this will return None. If it could not be written,
         the original tract will be returned.
        """
        stn = self.settings
        draw = self.footer_draw
        font = stn.footerfont
        fill = stn.footerfont_rgba
        if font_rgba is not None:
            fill = font_rgba
        trs = tract.trs
        desc = tract.desc
        writable_lines, unwritable_txt = self.check_text(desc, xy_0=(self._trs_indent, self._y))
        if unwritable_txt is not None:
            if not write_partial or len(writable_lines) == 0:
                return tract
            if len(writable_lines) > 0 and len(writable_lines[-1]) >= 3:
                # Ellide the text in the final writable line.
                writable_lines[-1] = writable_lines[-1][:-3] + '...'
        if not writable_lines:
            # If no description for this tract, we still want to move the cursor down.
            writable_lines.append('')
        # TRS is written separately.
        draw.text(xy=(self._x, self._y), text=f"{trs}:", font=font, fill=fill)
        # If any undefined lots, use the warning color for the desc of this tract.
        if hasattr(tract, 'undefined_lots') and len(tract.undefined_lots) > 0:
            fill = stn.warningfont_rgba
        for line in writable_lines:
            # This moves the y cursor down appropriately.
            self._write_line(x=self._trs_indent, text=line, fill=fill)
        return None

    def write_text(self, txt, write_partial=False) -> str | None:
        """
        Write a block of text in the footer.

        :param write_partial: (Optional, off by default) If there is not
         space to write the entire block of text, write whatever will
         fit.
        :return: If the entire block is successfully written, this will
         return None. If not, the portion of the text that could not be
         written will be returned (and if ``write_partial=False``, then
         the whole text block will be returned as unwritten).
        """
        writable_lines, unwritable_txt = self.check_text(txt, xy_0=(self._x, self._y))
        if unwritable_txt is not None:
            if not write_partial:
                return txt
        for line in writable_lines:
            self._write_line(x=self._x, text=line)
        return unwritable_txt


class Plat(IPlatOwner, QueueSingle):
    """A plat of a single Twp/Rge."""

    def __init__(
            self,
            twp: str = None,
            rge: str = None,
            settings: Settings = None,
            lot_definer: LotDefiner = None,
            owner: SettingsOwner | None = None):
        """
        :param twp: The Twp of the Twp/Rge represented by this Plat.
        :param rge: The Rge of the Twp/Rge represented by this Plut.
        :param settings: The ``Settings`` object to control the behavior
         and appearance of this plat. (Will be overridden by the
         settings in ``owner``, if that is passed.)
        :param owner: (Optional) The ``PlatGroup`` object (or other)
         that this ``Plat`` belongs to. (If used, the ``owner`` will
         control the settings of this ``Plat``.)
        """
        self.twp = twp
        self.rge = rge
        self.queue = pytrs.TractList()
        # Main image and draw object.
        self.image: Image = None
        self.draw: ImageDraw.Draw = None
        # Overlays the main image with QQs, etc.
        self.overlay_image: Image = None
        self.overlay_draw: ImageDraw.Draw = None
        # Footer image and draw object.
        self.footer_image: Image = None
        self.footer_draw: ImageDraw.Draw = None
        self.image_layers: tuple[Image] = None
        self.header = PlatHeader(owner=self)
        self.body = PlatBody(twp, rge, owner=self)
        self.footer = PlatFooter(owner=self)
        # If `.owner` is used, it must include .settings attribute.
        self.owner: ISettingsLotDefinerOwner | None = owner
        # ._settings will not be used if this Plat has an owner.
        self._settings: Settings = settings
        if settings is None and owner is None:
            self._settings = DEFAULT_SETTINGS
        self._lot_definer: LotDefiner | None = lot_definer
        if lot_definer is None and owner is None:
            self._lot_definer = LotDefiner()
        # ._all_lot_defs_cached will not be used if this Plat has an owner.
        # It's a cache of lot definitions (including defaults). Gets used while
        # executing queue, then cleared.
        self._all_lot_defs_cached = {}
        self.configure()

    @property
    def settings(self):
        if self.owner is not None:
            return self.owner.settings
        return self._settings

    @settings.setter
    def settings(self, new_settings):
        """
        Set and execute the new settings, and pass them to subordinates.
        """
        if self.owner is not None:
            raise AttributeError(
                'Attempting to change settings in an object that has an owner.'
                ' Change the settings in the owner object instead.'
            )
        self._settings = new_settings
        self.configure()

    @property
    def lot_definer(self):
        if self.owner is not None:
            return self.owner.lot_definer
        return self._lot_definer

    @lot_definer.setter
    def lot_definer(self, new_lot_definer):
        if self.owner is not None:
            raise AttributeError(
                'Attempting to change `lot_definer` in an object that has an owner.'
                ' Change the `lot_definer` in the owner object instead.'
            )
        self._new_lot_definer = new_lot_definer

    @property
    def all_lot_defs_cached(self):
        if self.owner is not None:
            return self.owner.all_lot_defs_cached
        return self._all_lot_defs_cached

    @all_lot_defs_cached.setter
    def all_lot_defs_cached(self, new_cached):
        if self.owner is None:
            self._all_lot_defs_cached = new_cached

    def configure(self):
        """Configure this plat and its subordinates."""
        self.image = Image.new('RGBA', self.settings.dim, Settings.RGBA_WHITE)
        self.draw = ImageDraw.Draw(self.image, 'RGBA')
        self.overlay_image = Image.new('RGBA', self.settings.dim, (255, 255, 255, 0))
        self.overlay_draw = ImageDraw.Draw(self.overlay_image, 'RGBA')
        self.footer_image = Image.new('RGBA', self.settings.dim, (255, 255, 255, 0))
        self.footer_draw = ImageDraw.Draw(self.footer_image, 'RGBA')
        # The images in the order that they should be stacked for output.
        self.image_layers = (self.image, self.overlay_image, self.footer_image)
        self.body.configure()
        self.footer.configure()
        return None

    def execute_queue(self) -> pytrs.TractList:
        """
        Execute the queue of tracts to fill in the plat.
        :return: A ``pytrs.TractList`` containing all tracts that could
         not be platted (no lots or aliquots identified).
        """
        twprge = f"{self.twp}{self.rge}"
        unplattable_tracts = pytrs.TractList()
        self.queue.custom_sort()
        if self.owner is None:
            cached = self.lot_definer.get_all_definitions(mandatory_twprges=[twprge])
            self.all_lot_defs_cached = cached
        for tract in self.queue:
            self.lot_definer.process_tract(tract, commit=True)
            sec = tract.sec_num
            plat_sec = self.body.sections[sec]
            plat_sec.queue.append(tract)
        for plat_sec in self.body.sections.values():
            unplattable = plat_sec.execute_queue()
            unplattable_tracts.extend(unplattable)
        if self.settings.write_tracts:
            for tract in self.queue:
                tractfont_rgba = self.settings.footerfont_rgba
                if tract in unplattable_tracts:
                    tractfont_rgba = self.settings.warningfont_rgba
                self.footer.write_tract(tract, font_rgba=tractfont_rgba)
        if self.settings.write_header:
            self.write_header(twp=self.twp, rge=self.rge)
        if self.settings.write_lot_numbers:
            self.write_lot_numbers(at_depth=2)
        if self.owner is None:
            self.all_lot_defs_cached = None
        return None

    def write_header(self, custom_header: str = None, **kw) -> None:
        """
        Write the header to the top of the plat.

         .. note::
            The default header is the Twp/Rge, styled as follows
            ``Township 154 North, Range 97 West``.
            if ``short_header=True`` in the settings, the resulting
            header will be styled as ``T154N-R97W``. The header can be
            styled differently if appropriate keyword arguments are
            passed as ``kw``. Further, the exact header text can be
            passed as ``custom_header``, which will override everything
            else.

        :param custom_header: (Optional) Override the default header and
         use this text instead. If used, any other keyword arguments
         will be ignored.
        :param kw: (Optional) keyword arguments to pass to
         ``pytrs.TRS.pretty_twprge()`` to control how the Twp/Rge header
         should be spelled out.
        """
        self.header.write_header(custom_header=custom_header, **kw)

    def write_lot_numbers(self, at_depth=2):
        lotwriter = PlatBody(twp=self.twp, rge=self.rge, owner=self, is_lot_writer=True)
        lotwriter.configure(xy=self.settings.grid_xy)
        lotwriter.write_lot_numbers(at_depth)
        return None

    def write_tracts(self, tracts: pytrs.TractList | pytrs.PLSSDesc = None):
        """
        Write all the tract descriptions in the footer.
        """
        if tracts is None:
            tracts = self.queue
        return self.footer.write_tracts(tracts)

    def write_footer_text(self, txt: str):
        """Write a block of text in the footer."""
        return self.footer.write_text(txt)


class PlatGroup(SettingsOwner, QueueMany):
    """
    A collection of Plats that can span multiple Twp/Rge. Access the
    plats in ``.plats`` (keyed by a ``twprge`` string in the ``pytrs``
    format, e.g., ``'154n97w'``).
    """

    def __init__(self, settings: Settings = None, lot_definer: LotDefiner = None):
        if settings is None:
            settings = Settings.preset('default')
        self._settings: Settings = settings
        if lot_definer is None:
            lot_definer = LotDefiner()
        self.lot_definer: LotDefiner = lot_definer
        self.plats: dict[str, Plat] = {}
        # Cache of lot definitions (including defaults). Gets used while
        # executing queue, then cleared.
        self.all_lot_defs_cached: dict = {}

    @property
    def settings(self):
        return self._settings

    @settings.setter
    def settings(self, new_settings):
        """
        Execute the new settings, and pass them to subordinates.
        """
        self._settings = new_settings
        for plat in self.plats.values():
            plat.configure()

    def register_plat(self, twp: str, rge: str) -> Plat:
        """
        Register a new plat for the specified ``twp`` and ``rge``. If
        a plat already exists for the Twp/Rge, this will raise a
        ``KeyError``.
        """
        plat = Plat(twp, rge, owner=self)
        trs = pytrs.TRS.from_twprgesec(twp, rge, sec=None)
        twprge = trs.twprge
        if twprge in self.plats:
            raise KeyError(f"Duplicate Twp/Rge {twprge!r} cannot registered.")
        self.plats[trs.twprge] = plat
        plat.configure()
        return plat

    def add_tract(self, tract: pytrs.Tract) -> None:
        """
        Add a tract to the queue. If no plat yet exists for the Twp/Rge
        of this tract, one will be created.

        .. note::
          The tract must already be parsed for lots/QQs. (See ``pyTRS``
          documentation for details.)
        """
        plat = self.plats.get(tract.twprge)
        if plat is None:
            plat = self.register_plat(tract.twp, tract.rge)
        plat.add_tract(tract)
        return None

    def execute_queue(self):
        """
        Execute the queue of tracts to fill in the plats.
        """
        self.all_lot_defs_cached = self.lot_definer.get_all_definitions(
            mandatory_twprges=list(self.plats.keys())
        )
        for plat in self.plats.values():
            plat.execute_queue()
        self.all_lot_defs_cached = {}
        return None


class MegaPlat(IPlatOwner, QueueMany):
    def __init__(self, settings: Settings = None, lot_definer: LotDefiner = None):
        self.queue = pytrs.TractList()
        if settings is None:
            settings = Settings()
        self.settings: Settings = settings
        if lot_definer is None:
            lot_definer = LotDefiner()
        self.lot_definer: LotDefiner = lot_definer
        self.subplats: dict[str, PlatBody] = {}
        # dim gets dynamically set when executing the queue.
        self.dim = (1, 1)
        self.image_layers: tuple[Image] = tuple()

    def _clean_queue(self, queue=None):
        """
        Scrub out any undefined or error townships in the ``queue`` of
        tracts.
        """
        out_queue = pytrs.TractList()
        if queue is None:
            queue = self.queue
        if not queue:
            return out_queue
        queue.custom_sort()
        for tract in queue:
            if not tract.trs_is_undef() and not tract.trs_is_error():
                out_queue.append(tract)
            else:
                # TODO: Warn?
                pass
        return out_queue

    def _get_twprge_spans(self, queue: pytrs.TractList):
        """
        Get a list of Twp numbers and a list of Rge numbers that
        encompass the entirety of the tracts in the ``queue``.
        If the townships are "North", they will be sorted largest to
        smallest (so that the highest number appears at the top of the
        eventual plat); and vice versa for "South".
        If the ranges are "West", they will be sorted largest to
        smallest (so that the highest number appears at the left of the
        eventual plat); and vice versa for "East".
        :return: Two lists: One of Twp numbers, and another for Rge
         numbers.
        """
        if not queue:
            return [], []
        # Find the boundaries.
        tract = queue[0]
        ns = tract.ns
        ew = tract.ew
        min_twp_tract = tract
        max_twp_tract = tract
        min_rge_tract = tract
        max_rge_tract = tract
        for tract in queue:
            if tract.ns != ns:
                raise ValueError('Township N/S must all be the same.')
            if tract.ew != ew:
                raise ValueError('Range E/W must all be the same.')
            if tract.twp_num < min_twp_tract.twp_num:
                min_twp_tract = tract
            if tract.twp_num > max_twp_tract.twp_num:
                max_twp_tract = tract
            if tract.rge_num < min_rge_tract.rge_num:
                min_rge_tract = tract
            if tract.rge_num > max_rge_tract.rge_num:
                max_rge_tract = tract
        needed_twp_nums = list(range(min_twp_tract.twp_num, max_twp_tract.twp_num + 1))
        needed_rge_nums = list(range(min_rge_tract.rge_num, max_rge_tract.rge_num + 1))
        if ns == 'n':
            needed_twp_nums.reverse()
        if ew == 'w':
            needed_rge_nums.reverse()
        return needed_twp_nums, needed_rge_nums

    def _gen_subplats(self, queue: pytrs.TractList):
        """
        Generate subplats for the tracts in the ``queue`` of tracts.
        Also establishes the ``.dim`` of the image, and the ``.image``
        and related attributes.
        """
        stn = self.settings
        subplats = {}
        all_marg = stn.body_marg_top_y
        topleft = (all_marg, all_marg)
        sec_len = stn.sec_length_px
        twp_len = sec_len * 6
        needed_twp_nums, needed_rge_nums = self._get_twprge_spans(queue)
        self.dim = (
            # x is set by number of rge_nums (plus margins).
            len(needed_rge_nums) * twp_len + all_marg * 2,
            # y is set by number of twp_nums (plus margins).
            len(needed_twp_nums) * twp_len + all_marg * 2
        )

        # Create the images here, because `self.dim` was just calculated.
        self.image = Image.new('RGBA', self.dim, Settings.RGBA_WHITE)
        self.draw = ImageDraw.Draw(self.image, 'RGBA')
        self.overlay_image = Image.new('RGBA', self.dim, (255, 255, 255, 0))
        self.overlay_draw = ImageDraw.Draw(self.overlay_image, 'RGBA')
        # No footer to a MegaPlat.
        self.footer_image = None
        self.footer_draw = None
        self.image_layers = (self.image, self.overlay_image)
        self.draw = ImageDraw.Draw(self.image)

        sample_tract = queue[0]
        ns = sample_tract.ns
        ew = sample_tract.ew
        subplat_lotwriter_info = []
        for i, twp_num in enumerate(needed_twp_nums):
            for j, rge_num in enumerate(needed_rge_nums):
                twp = f"{twp_num}{ns}"
                rge = f"{rge_num}{ew}"
                twprge = f"{twp}{rge}"
                subplat_topleft = (topleft[0] + twp_len * j, topleft[1] + twp_len * i)
                # Write the header before configuring the subplat itself, so that the
                # text appears behind the section lines, etc.
                subplat_header = PlatHeader(owner=self)
                # Anchor the 'header' to the center of the subplat.
                header_xy = (subplat_topleft[0] + twp_len // 2, subplat_topleft[1] + twp_len // 2)
                subplat_header.write_header(twp, rge, xy=header_xy, align='center_center')
                # Create and configure the grid itself.
                subplat = PlatBody(twp, rge, owner=self)
                subplat.configure(xy=subplat_topleft)
                subplat.draw_outline()
                subplats[twprge] = subplat
                # Store Twp/Rge/topleft_xy for lotwriters.
                subplat_lotwriter_info.append((twp, rge, subplat_topleft))

        if self.settings.write_lot_numbers:
            mandated = list(subplats.keys())
            all_defs = self.lot_definer.get_all_definitions(mandatory_twprges=mandated)
            self.all_lot_defs_cached = all_defs
            for twp, rge, subplat_xy in subplat_lotwriter_info:
                lotwriter = PlatBody(twp=twp, rge=rge, owner=self, is_lot_writer=True)
                lotwriter.configure(xy=subplat_xy)
                lotwriter.write_lot_numbers(at_depth=2)
            self.all_lot_defs_cached = {}
        return subplats

    def configure(self):
        queue = self._clean_queue()
        self._gen_subplats(queue)

    def execute_queue(self, subset_twprges: list[str] = None) -> pytrs.TractList:
        """
        Execute the queue of tracts, and generate the plat.
        :return: A ``pytrs.TractList`` containing all tracts that could
         not be written.
        """
        queue = self.queue
        if subset_twprges is not None:
            queue = queue.filter(key=lambda tract: tract.twprge in subset_twprges)
        # Confirm all tracts are valid.
        queue = self._clean_queue(queue)
        if not queue:
            return None

        # Generate subplats. Also determines the `.dim` of our output.
        subplats = self._gen_subplats(queue)

        unplattable_tracts = pytrs.TractList()
        for tract in queue:
            self.lot_definer.process_tract(tract, commit=True)
            subplat = subplats[tract.twprge]
            sec = tract.sec_num
            plat_sec = subplat.sections[sec]
            plat_sec.queue.append(tract)
        for subplat in subplats.values():
            for plat_sec in subplat.sections.values():
                unplattable = plat_sec.execute_queue()
                unplattable_tracts.extend(unplattable)
        return unplattable_tracts
