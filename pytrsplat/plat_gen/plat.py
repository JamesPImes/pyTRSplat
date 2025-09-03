from __future__ import annotations
from typing import Union
from warnings import warn
from pathlib import Path

from PIL import Image, ImageDraw
import pytrs
from pytrs.parser.tract.aliquot_simplify import AliquotNode

from .lot_definer import LotDefiner
from .plat_warnings import UnplattableWarning, UndefinedLotWarning
from .plat_settings import Settings
from .utils import calc_midpt, get_box, get_box_outline, save_output_images

__all__ = [
    'Plat',
    'PlatGroup',
    'MegaPlat',
]

try:
    DEFAULT_SETTINGS = Settings.preset('default')
    DEFAULT_MEGAPLAT_SETTINGS = Settings.preset('megaplat_default')
except (FileNotFoundError, KeyError):
    Settings.restore_presets()
    DEFAULT_SETTINGS = Settings.preset('default')
    DEFAULT_MEGAPLAT_SETTINGS = Settings.preset('megaplat_default')


class QueueSingle:
    """
    Class that can take in one or more ``pytrs.Tract`` objects or a raw
    PLSS description and add the results to the ``.queue`` (a
    ``pytrs.TractList``).

    This class mandates that all tracts lie within the same Twp/Rge, and
    a ``ValueError`` will be raised when encountering a mismatched
    Twp/Rge.
    """

    queue: pytrs.TractList()

    def add_tract(self, tract: pytrs.Tract):
        """
        Add a tract to the queue. If there are already tracts in the
        queue, this tract must match the existing Twp/Rge, or it will
        raise a ``ValueError``.

        .. note::

            The tract must already be parsed for lots/QQs. (See
            ``pyTRS`` documentation for details.)

        :param tract: A ``pytrs.Tract`` that has been parsed into Lots
            and QQ's. (Its Twp/Rge must match what is already in the
            queue.)
        :raise ValueError: If a Twp/Rge is added that does not share the
            same Twp/Rge of every other tract in the queue.
        """

        twp = None
        rge = None
        twprge_defined = False
        if hasattr(self, 'twp') and hasattr(self, 'rge'):
            twp = self.twp
            rge = self.rge
            if twp is not None and rge is not None:
                twprge_defined = True
        elif self.queue:
            sample_tract: pytrs.Tract = self.queue[0]
            twp = sample_tract.twp
            rge = sample_tract.rge
            twprge_defined = True
        existing_twprge = pytrs.TRS.from_twprgesec(twp, rge).twprge

        if not twprge_defined or (tract.twprge == existing_twprge):
            self.queue.append(tract)
            if hasattr(self, 'twp') and hasattr(self, 'rge'):
                self.twp = tract.twp
                self.rge = tract.rge
            return None

        msg = (
            f"Mismatched Twp/Rge: {tract.twprge!r} does not match existing "
            f"{existing_twprge!r}.\n"
            "Consider using platting class that will accept multiple Twp/Rges "
            " (e.g., `PlatGroup` or `MegaPlat`)."
        )
        raise ValueError(msg)

    def add_tracts(
            self, tracts: Union[list[pytrs.Tract], pytrs.TractList, pytrs.PLSSDesc]
    ) -> None:
        """
        Add multiple tracts to the queue. All tracts must share the same
        Twp/Rge as any tracts already existing in the queue.

        .. note::

            The tracts must already be parsed for lots/QQs. (See
            ``pyTRS`` documentation for details.)

        .. note::

            All tracts in the queue must share the same Twp/Rge, or a
            ``ValueError`` will be raised. If there is any doubt about
            whether the tracts being added include other Twp/Rges,
            consider using a platting object (e.g., ``PlatGroup`` or
            ``MegaPlat``) that can process multiple Twp/Rges.

        :param tracts: A collection of ``pytrs.Tract`` objects,
            such as a ``pytrs.PLSSDesc``, ``pytrs.TractList``, or any
            other iterable object that contains exclusively
            ``pytrs.Tract``.
        :raise ValueError: If a Twp/Rge is added that does not share the
            same Twp/Rge of every other tract in the queue.
        """
        for tract in tracts:
            self.add_tract(tract)
        return None

    def add_description(self, txt: str, config: str = None) -> pytrs.TractList:
        """
        Parse the land description and add the resulting tracts to the
        queue.

        .. note::

            All tracts in the queue must share the same Twp/Rge, or a
            ``ValueError`` will be raised. If there is any doubt about
            whether the land description being added includes other
            Twp/Rges, consider using a platting object (e.g.,
            ``PlatGroup`` or ``MegaPlat``) that can process multiple
            Twp/Rges.

        :param txt: The land description.
        :param config: The config parameters for parsing, to be passed
            through to the ``pytrs`` library. (See pyTRS documentation
            for details.)
        :return: A ``pytrs.TractList`` containing the tracts in which
            the parser could NOT identify any lots or aliquots.
        :raise ValueError: If a Twp/Rge is added that does not share the
            same Twp/Rge of every other tract in the queue.
        """
        plssdesc = pytrs.PLSSDesc(txt, parse_qq=True, config=config)
        self.add_tracts(plssdesc)
        no_lots_qqs = pytrs.TractList()
        for tract in plssdesc:
            if not tract.lots_qqs:
                no_lots_qqs.append(tract)
        return no_lots_qqs


class QueueMany(QueueSingle):
    """
    Class that can take in one or more ``pytrs.Tract`` objects or a raw
    PLSS description and add the results to the ``.queue`` (a
    ``pytrs.TractList``).

    This class allows any number of unique Twp/Rges.
    """

    def add_tract(self, tract: pytrs.Tract):
        """
        Add a tract to the queue.

        .. note::

            The tract must already be parsed for lots/QQs. (See
            ``pyTRS`` documentation for details.)
        """
        self.queue.append(tract)
        return None

    def add_tracts(
            self, tracts: Union[list[pytrs.Tract], pytrs.TractList, pytrs.PLSSDesc]
    ) -> None:
        """
        Add multiple tracts to the queue.

        .. note::

            The tracts must already be parsed for lots/QQs. (See
            ``pyTRS`` documentation for details.)

        :param tracts: A collection of ``pytrs.Tract`` objects,
            such as a ``pytrs.PLSSDesc``, ``pytrs.TractList``, or any
            other iterable object that contains exclusively
            ``pytrs.Tract``.
        """
        for tract in tracts:
            self.add_tract(tract)
        return None

    def add_description(self, txt: str, config: str = None) -> pytrs.TractList:
        """
        Parse the land description and add the resulting tracts to the
        plat group. If one or more Twp/Rge's are newly identified, plats
        will be created as needed.

        :param txt: The land description.
        :param config: The config parameters for parsing, to be passed
            through to the ``pytrs`` library. (See pyTRS documentation
            for details.)
        :return: A ``pytrs.TractList`` containing the tracts in which
            the parser could not identify any lots or aliquots.
        """
        plssdesc = pytrs.PLSSDesc(txt, parse_qq=True, config=config)
        self.add_tracts(plssdesc)
        no_lots_qqs = pytrs.TractList()
        for tract in plssdesc:
            if not tract.lots_qqs:
                no_lots_qqs.append(tract)
        return no_lots_qqs


class LotDefinerOwner(QueueSingle):
    """
    Class that has a ``LotDefiner`` object in its ``.lot_definer``
    attribute, and appropriate methods for passing through methods that
    affect its queue.
    """
    lot_definer: LotDefiner
    # Cache of lot definitions (including defaults). Gets used while
    # executing queue, then cleared.
    all_lot_defs_cached: dict

    def find_undefined_lots(
            self,
            allow_defaults: bool = None,
            fp: Union[str, Path] = None,
            **headers,
    ) -> dict[str, list[str]]:
        """
        Find all tracts in the queue that have one or more lots that
        have not been defined. Optionally write them to a .csv file at
        path ``fp``, to facilitate defining them externally.

        .. warning::

            If passing ``fp``, any file at that path will be overwritten
            without warning.

        :param allow_defaults: Whether to assume that all sections are
            'standard', with typical lots (if any) in sections along the
            north and west township boundaries. If not specified here,
            will use whatever is configured in the
            ``lot_definer.allow_defaults`` attribute.
        :param fp: (Optional) A filepath at which to create a .csv file
            containing the undefined lots.
        :param headers: (Optional) If saving the undefined lots to a
            .csv file, pass keyword arguments to specify the desired
            headers. (Reference the docs for
            ``LotDefiner.save_to_csv()`` for the appropriate
            parameters.)
        :return: A dict, keyed by Twp/Rge/Sec (``'154n97w01'``), whose
            values are a sorted list of lots for that Twp/Rge/Sec.
        """
        return self.lot_definer.find_undefined_lots(
            tracts=self.queue, allow_defaults=allow_defaults, fp=fp, **headers)

    def prompt_define(self, allow_defaults: bool = None):
        """
        Prompt the user in console to define all lots that have not yet
        been defined for tracts in the ``.queue``. Any new lot
        definitions will be added to the ``.lot_definer``.

        (You may wish to save the results with
        ``.lot_definer.save_to_csv()`` so that they can be loaded and
        reused later.)

        :param allow_defaults: Whether to assume that this section is
            'standard', with typical lots (if any) in sections along the
            north and west township boundaries. If not specified here,
            will use whatever is configured in the
            ``.lot_definer.allow_defaults`` attribute.
        """
        return self.lot_definer.prompt_define(self.queue, allow_defaults)

    def find_unplattable_tracts(self, allow_defaults: bool = None) -> pytrs.TractList:
        """
        Get a ``pytrs.TractList`` containing all tracts that cannot be
        platted with the currently provided lot definitions (optionally
        accounting for default lots, if so configured).

        .. note::
            If a tract has any aliquots and/or any lots that have been
            defined, it will be considered plattable, even if some of
            its lots have NOT been defined. To check for undefined lots,
            use the ``.find_undefined_lots()`` method.

        :param allow_defaults: Whether to assume that all sections are
            'standard', with typical lots (if any) in sections along the
            north and west township boundaries. If not specified here,
            will use whatever is configured in the
            ``lot_definer.allow_defaults`` attribute.
        """
        unplattable_tracts = pytrs.TractList()
        if not self.queue:
            return unplattable_tracts
        for tract in self.queue:
            converted_aliquots, undefined_lots = self.lot_definer.process_tract(
                tract,
                allow_defaults=allow_defaults,
                commit=False
            )
            if not tract.qqs and not converted_aliquots:
                unplattable_tracts.append(tract)
        return unplattable_tracts


class SettingsOwner:
    """
    Interface for a class that has a ``Settings`` object in its
    ``.settings`` attribute.
    """
    settings: Settings


class ImageOwner:
    """
    Interface for a class that has the following attributes:

    ``.DEFAULT_LAYER_NAMES`` (class attribute) - A list of standard
        layer names, in the standard output order (bottom-up).

    ``._layers`` - A dict of images (``Image.Image``), keyed by layer
        name.

    ``._draws`` - A dict of draws (``ImageDraw.Draw``), keyed by layer
        name.

    ``.output_layer_names`` - A list of layer names to be written to
        the merged output image, in bottom-up order.

    ``._active_layer`` - The name of the currently active layer.

    And methods:
    ``._get_layer_image()`` - Get the ``Image.Image`` of the layer.

    ``._get_layer_draw()`` - Get the ``ImageDraw.Draw`` of the layer.

    And ``._create_layer()``, ``._create_default_layers()`` and
    ``.output()`` methods.
    """
    DEFAULT_LAYER_NAMES = (
        'background',
        'header',
        'footer',
        'inner_lines',
        'sec_nums',
        'aliquot_fill',
        'lot_nums',
        'sec_border',
        'twp_border',
    )
    _images: dict[str, Image.Image]
    _draws: dict[str, ImageDraw.Draw]
    output_layer_names: list[str]
    dim: Union[tuple[int, int], None]

    def __init__(self):
        self._images = {}
        self._draws = {}
        self.output_layer_names = list(self.DEFAULT_LAYER_NAMES)

    def _get_layer_draw(
            self, layer_name: str, create=False, dim: tuple[int, int] = None):
        """
        Get the ``ImageDraw.Draw`` for a given layer.

        :param layer_name: Name of the layer.
        :param create: (Optional) If the layer doesn't exist, create it.
        :param dim: (Optional) If creating the layer, use these
            dimensions. If not specified here, will fall back to
            ``.dim`` attribute.
        """
        draw = self._draws.get(layer_name)
        if draw is None and create:
            self._create_layer(layer_name, dim)
            draw = self._draws.get(layer_name)
        return draw

    def _get_layer_image(
            self, layer_name: str, create=False, dim: tuple[int, int] = None):
        """
        Get the ``Image.Image`` for a given layer.

        :param layer_name: Name of the layer.
        :param create: (Optional) If the layer doesn't exist, create it.
        :param dim: (Optional) If creating the layer, use these
            dimensions. If not specified here, will fall back to
            ``.dim`` attribute.

        """
        image = self._images.get(layer_name)
        if image is None and create:
            self._create_layer(layer_name, dim)
            image = self._images.get(layer_name)
        return image

    def _create_layer(self, layer_name: str, dim: tuple[int, int] = None, rgba=None):
        """Register a layer of size ``dim``, with name ``layer_name``."""
        if dim is None:
            dim = self.dim
        if rgba is None:
            rgba = (0, 0, 0, 0)
            if layer_name == 'background':
                rgba = Settings.RGBA_WHITE
        im = Image.new('RGBA', dim, rgba)
        draw = ImageDraw.Draw(im, 'RGBA')
        self._images[layer_name] = im
        self._draws[layer_name] = draw
        return None

    def _create_default_layers(self, dim: tuple[int, int] = None):
        """Register all default layers, with size ``dim``."""
        if dim is None:
            dim = self.dim
        for layer_name in self.DEFAULT_LAYER_NAMES:
            self._create_layer(layer_name, dim)

    def _reset_layers(self, dim: tuple[int, int] = None):
        """Discard all existing layers and create a new ``'background'``."""
        layer_names = list(self._images.keys())
        for layer_name in layer_names:
            self._images.pop(layer_name)
            self._draws.pop(layer_name)
        self._create_layer('background', dim)
        return None

    def output(
            self,
            fp: Union[str, Path] = None,
            image_format: str = None,
            layers: list[str] = None,
            **_kw
    ) -> Union[Image.Image, None]:
        """
        Compile and return the merged image of the plat. Optionally
        save the results to disk, either as an image or as a .zip file
        containing the image.

        :param fp: (Optional) If provided, save the output to the
            specified filepath.
        :param image_format: (Optional) Override the image format of the
            file specified in ``fp``. If not provided, will defer to the
            file extension in ``fp``. (Only relevant if saving to file.)
        :param layers: (Optional) Choose which image layers (in
            bottom-up order) to include in the output. (See
            ``Plat.DEFAULT_LAYER_NAMES`` for the standard layer names.)
            Nonexistent or empty layers will be ignored.
        :param _kw: No effect. (Included to mirror ``.output()`` of
            other classes.)
        :return: The generated image. If no layers have been configured
            and/or ``layers`` contains only layers that are nonexistent
            or empty, will return ``None`` instead.
        """
        selected_layers = self.output_layer_names
        if selected_layers is None:
            selected_layers = self.DEFAULT_LAYER_NAMES
        if layers is not None:
            # Param `layers` overrides attributes.
            selected_layers = layers
        selected_layer_ims = []
        for layer_name in selected_layers:
            im = self._get_layer_image(layer_name)
            if im is None:
                continue
            selected_layer_ims.append(im)
        if not selected_layer_ims:
            return None
        elif len(selected_layer_ims) == 1:
            return selected_layer_ims[0]
        merged = Image.alpha_composite(*selected_layer_ims[:2])
        for i in range(2, len(selected_layer_ims)):
            merged = Image.alpha_composite(merged, selected_layer_ims[i])
        merged = merged.convert('RGB')
        if fp is not None:
            save_output_images([merged], fp, image_format)
        return merged


class IPlatOwner(SettingsOwner, ImageOwner, LotDefinerOwner):
    """
    Composite interface for a class that incorporates all necessary
    interfaces necessary for platting.
    """
    pass


class ISettingsLotDefinerOwner(SettingsOwner, LotDefinerOwner):
    """
    Composite interface for a class that incorporates ``SettingsOwner``
    and ``LotDefinerOwner``.
    """
    pass


class LotDefinerOwned:
    """
    Class with an ``owner`` (``LotDefinerOwner``) that has a
    ``.lot_definer`` attribute.
    """
    owner: LotDefinerOwner

    @property
    def lot_definer(self):
        return self.owner.lot_definer


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

    def _get_layer_draw(
            self, layer_name: str, create=False, dim: tuple[int, int] = None):
        """
        Reference docs for ``ImageOwner._get_layer_draw()``. (Passed
        through to ``._get_layer_draw()`` for ``.owner``.)
        """
        return self.owner._get_layer_draw(layer_name, create, dim)

    def _get_layer_image(
            self, layer_name: str, create=False, dim: tuple[int, int] = None):
        """
        Reference docs for ``ImageOwner._get_layer_image()``. (Passed
        through to ``._get_layer_image()`` for ``.owner``.)
        """
        return self.owner._get_layer_image(layer_name, create, dim)


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
        # `.owner` must have .settings, .image, .draw, .header_image, .header_draw,
        #   .overlay_image, .overlay_draw
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

    def _configure(
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
            child_node._configure(parent_xy=self.xy)
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
            draw = self._get_layer_draw('aliquot_fill', create=True)
            draw.polygon(box, rgba)
        for child in self.children.values():
            child.fill(rgba)
        return None

    def write_lot_numbers(self, at_depth):
        """
        Write lot numbers to the plat.

        :param at_depth: Depth at which to write the lots. MUST match
            the depth at which the lot definitions have been parsed.
            Default is 2 (i.e., quarter-quarters), specified above in
            the stack.
        """
        if self.depth == at_depth:
            lot_txt = ', '.join(str(l) for l in sorted(self.sources))
            stn = self.settings
            draw = self._get_layer_draw('lot_nums', create=True)
            font = stn.lotfont
            fill = stn.lotfont_rgba
            offset = stn.lot_num_offset_px
            x, y = self.xy
            draw.text(xy=(x + offset, y + offset), text=lot_txt, font=font, fill=fill)
            return None
        for child in self.children.values():
            child.write_lot_numbers(at_depth)


class PlatSection(SettingsOwned, ImageOwned, LotDefinerOwned):
    """A section of land, as represented in the plat."""

    def __init__(
            self,
            trs: pytrs.TRS = None,
            grid_offset: tuple[int, int] = None,
            owner: IPlatOwner = None,
    ):
        """
        :param trs: The Twp/Rge/Sec (a ``pytrs.TRS`` object) of this
            section.
        :param grid_offset: How many sections down and right from the
            top-left of the township. (The offset of Section 6 is
            (0, 0); whereas the offset of Section 36 is (6, 6).)
        :param owner: The ``Plat`` object that is the ultimate owner of
            this section. (Controls the settings that dictate platting
            behavior and appearance, and contains the image objects that
            will be drawn on.)
        """
        if trs is not None:
            trs = pytrs.TRS(trs)
        self.trs: pytrs.TRS = trs
        self.aliquot_tree = PlatAliquotNode(owner=owner)
        # Lot definitions will be written separately to the `.lot_writer` aliquot tree.
        self.lot_writer = PlatAliquotNode(owner=owner)
        self.queue = pytrs.TractList()
        self.square_dim: int = None
        # Coord of top-left of this square.
        self.xy: tuple[int, int] = None
        self.sec_length_px: int = None
        self.grid_offset: tuple[int, int] = grid_offset
        # `.owner` must have .settings, .image, .draw, .overlay_image, .overlay_draw
        self.owner: IPlatOwner = owner

    @property
    def _is_dummy(self):
        return self.grid_offset is None

    def _configure(self, grid_xy):
        """
        Configure this section and its subordinates.

        :param grid_xy: The top-left coord of the township to which this
            section belongs.
        """
        if self._is_dummy:
            return None
        settings = self.settings
        sec_length_px = settings.sec_length_px
        x, y = grid_xy
        i, j = self.grid_offset
        x += j * sec_length_px
        y += i * sec_length_px
        self.sec_length_px = sec_length_px
        self.square_dim = sec_length_px
        self.xy = (x, y)
        self.draw_lines()
        self.clear_center()
        self.aliquot_tree._configure(parent_xy=self.xy)

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

        for depth in reversed(depth_lines.keys()):
            draw = self._get_layer_draw('inner_lines', create=True)
            if depth == 0:
                draw = self._get_layer_draw('sec_border', create=True)
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
        draw = self._get_layer_draw('inner_lines', create=True)
        # Draw middle white space.
        cb_dim = settings.centerbox_dim
        x_center, y_center = calc_midpt(xy=self.xy, square_dim=self.sec_length_px)
        topleft = x_center - cb_dim // 2, y_center - cb_dim // 2
        centerbox = get_box(xy=topleft, dim=cb_dim)
        draw.polygon(centerbox, (0, 0, 0, 0))
        if not settings.write_section_numbers:
            return None
        font = settings.secfont
        fill = settings.secfont_rgba
        txt = str(self.trs.sec_num)
        draw = self._get_layer_draw('sec_nums', create=True)
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
        elif self._is_dummy:
            for tract in self.queue:
                warning = UnplattableWarning.unclear_trs(tract)
                warn(warning)
                unplattable_tracts.append(tract)
            return unplattable_tracts
        platted_aliquots = set()
        for tract in self.queue:
            self.lot_definer.process_tract(tract, commit=True)
            if not tract.qqs and not tract.lots_as_qqs:
                if len(tract.undefined_lots) > 0:
                    warning = UnplattableWarning.only_undefined_lots(tract)
                else:
                    warning = UnplattableWarning.no_lots_qqs(tract)
                warn(warning)
                unplattable_tracts.append(tract)
            self.aliquot_tree.register_all_aliquots(tract.qqs)
            platted_aliquots.update(tract.qqs)
            self.aliquot_tree.register_all_aliquots(tract.lots_as_qqs)
            platted_aliquots.update(tract.lots_as_qqs)
            if tract.undefined_lots:
                warning = UndefinedLotWarning.from_tract(tract)
                warn(warning)
        if len(platted_aliquots) > 0:
            self.aliquot_tree._configure()
            self.aliquot_tree.fill()
        return unplattable_tracts

    def write_lot_numbers(self, at_depth=2):
        """
        Write the lot numbers in the section.

        :param at_depth: At which depth to write the numbers. Defaults
            to 2 (i.e., quarter-quarters).
        """
        ld = self.owner.all_lot_defs_cached
        lots_definitions = ld.get(self.trs.trs, {})
        for lot, definitions in lots_definitions.items():
            tract = pytrs.Tract(
                definitions, parse_qq=True, config=f"clean_qq,qq_depth.{at_depth}")
            ilot = int(lot.split('L')[-1])
            self.lot_writer.register_all_aliquots(tract.qqs, ilot)
        self.lot_writer._configure(parent_xy=self.xy)
        self.lot_writer.write_lot_numbers(at_depth)
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
            owner: IPlatOwner = None
    ):
        """
        :param twp: The Twp of the Twp/Rge represented by this body.
        :param rge: The Rge of the Twp/Rge represented by this body.
        :param owner: The ``Plat`` object that is the ultimate owner of
            this body. (Controls the settings that dictate platting
            behavior and appearance, and contains the image objects that
            will be drawn on.)
        """
        self.owner: IPlatOwner = owner
        self.twp = twp
        self.rge = rge
        self.plat_secs: dict[Union[int, None], PlatSection] = {}
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
                    owner=self.owner
                )
                self.plat_secs[sec_num] = plat_sec
                k += 1
        # A dummy section, for tracts with undefined/error section number.
        self.plat_secs[None] = PlatSection(None, grid_offset=None, owner=self.owner)
        # Coord of top-left of the grid.
        self.xy: tuple[int, int] = None

    def nonempty_sections(self):
        """Get a list of any sections that have aliquots to be platted."""
        output = []
        for sec_num, plat_sec in self.plat_secs.items():
            if not plat_sec.aliquot_tree.is_leaf():
                output.append(sec_num)
        return output

    def _configure(self, xy: tuple[int, int] = None, twp: str = None, rge: str = None):
        """
        Enact the settings to configure this plat body.

        :param xy: The top-left coord of the area of the plat containing
            the grid.
        :param twp: The Twp of the Twp/Rge of the parent plat or
            subplat. (If not specified, will remain unchanged.)
        :param rge: The Rge of the Twp/Rge of the parent plat or
            subplat. (If not specified, will remain unchanged.)
        """
        if xy is None:
            xy = self.settings.grid_xy
        self.xy = xy
        if twp is None:
            twp = self.twp
        if rge is None:
            rge = self.rge
        for sec_num, plat_sec in self.plat_secs.items():
            plat_sec.trs = pytrs.TRS.from_twprgesec(twp, rge, sec_num)
            plat_sec._configure(grid_xy=xy)
        return None

    def add_tract(self, tract: pytrs.Tract):
        """
        Add a tract to the queue of the appropriate subordinate
        ``PlatSec``.

        .. note::

            This assumes that the Twp/Rge of the ``tract`` already
            matches the Twp/Rge of this ``PlatBody``, or that Twp/Rge is
            irrelevant.

        :param tract: A ``pytrs.Tract`` that has been parsed into Lots
            and QQ's.
        """
        # tracts with sec_num that is `None` or otherwise not found in the `.plat_secs`
        # dict (e.g., nonsense "Section 0" or "Section 37" or higher) will get
        # added to the queue for the dummy plat_sec -- i.e., `.plat_secs[None]`.
        plat_sec = self.plat_secs.get(tract.sec_num, self.plat_secs[None])
        plat_sec.queue.append(tract)
        return None

    def execute_subordinate_queues(self) -> pytrs.TractList:
        """
        Execute the queue in each subordinate ``PlatSec``.

        :return: A ``pytrs.TractList`` containing all tracts that could
            not be platted (no lots or aliquots identified).
        """
        unplattable_tracts = pytrs.TractList()
        for plat_sec in self.plat_secs.values():
            unplattable = plat_sec.execute_queue()
            unplattable_tracts.extend(unplattable)
        return unplattable_tracts

    def write_lot_numbers(self, at_depth=2, subset_sec_nums: list[int] = None):
        """
        Write the lot numbers into the respective squares.

        :param at_depth: At which depth to write the numbers. Defaults
            to 2 (i.e., quarter-quarters).
        :param subset_sec_nums: (Optional) If passed, lots will be
            written only for the sections in this list.
        """
        if subset_sec_nums is None:
            subset_sec_nums = [
                sec_num for sec_num in self.plat_secs.keys()
                if sec_num is not None
            ]
        for sec_num in subset_sec_nums:
            sec_plat = self.plat_secs[sec_num]
            sec_plat.write_lot_numbers(at_depth)
        return None

    def draw_outline(self):
        """
        Draw the boundary around the township.
        """
        stn = self.settings
        width = stn.line_stroke[-1]
        fill = stn.line_rgba[-1]
        lines = get_box_outline(
            xy=self.xy, dim=stn.sec_length_px * 6, extend_px=width // 2 - 1)
        draw = self._get_layer_draw('twp_border', create=True)
        for line in lines:
            draw.line(line, fill=fill, width=width)


class PlatHeader(SettingsOwned, ImageOwned):
    """The header of a plat."""

    def __init__(self, owner: IPlatOwner):
        """
        :param owner: The ``Plat`` object (or other appropriate type)
            that is the ultimate owner of this header. (Controls the
            settings that dictate platting behavior and appearance, and
            contains the image objects that will be drawn on.)
        """
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
            centered) or ``'center_center'`` (to center both
            horizontally and vertically).
        :param kw: (Optional) keyword arguments to pass to
            ``pytrs.TRS.pretty_twprge()`` to control how the Twp/Rge
            header should be spelled out.
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
        draw = self._get_layer_draw('header', create=True)
        im_width = draw.im.size[0]
        _, _, w, h = draw.textbbox(xy=(0, 0), text=header, font=font)
        if xy is None and align == 'default':
            x = (im_width - w) // 2
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

    def _configure(self):
        """
        Enact the settings to configure this plat footer.
        """
        stn = self.settings
        x = stn.footer_marg_left_x
        y = (stn.body_marg_top_y + stn.sec_length_px * 6 + stn.footer_px_below_body)
        self._x, self._y = (x, y)
        sample_trs = 'XXXzXXXzXX:'
        font = stn.footerfont
        draw = self._get_layer_draw('footer', create=True)
        _, _, w, h = draw.textbbox(xy=(0, 0), text=sample_trs, font=font)
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
        draw = self._get_layer_draw('footer', create=True)
        draw.text(xy=(x, self._y), text=text, font=font, fill=fill)
        self._y += self._text_line_height + stn.footer_px_between_lines
        return None

    def check_text(
            self,
            text,
            xy_0: tuple[int, int],
            xy_limit: tuple[int, int] = None
    ) -> (list[str], Union[str, None]):
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
            if line:
                cand_line = f"{line} {word}"
            else:
                cand_line = word
            bbox = stn.footerfont.getbbox(cand_line)
            c_width = bbox[2] - bbox[0]
            c_height = bbox[3] - bbox[1]
            if c_width <= avail_w and c_height <= avail_h:
                line = cand_line
            elif c_height > avail_h:
                if line:
                    unwritable = f"{line} {' '.join(words[i:])}"
                else:
                    unwritable = ' '.join(words[i:])
                return writable_lines, unwritable
            elif c_width > avail_w:
                writable_lines.append(line)
                line = word
                avail_h -= (self._text_line_height + stn.footer_px_between_lines)
                if avail_h <= self._text_line_height:
                    unwritable = ' '.join(words[i:])
                    return writable_lines, unwritable
        if line:
            writable_lines.append(line)
        return writable_lines, unwritable

    def write_tracts(
            self,
            tracts: Union[list[pytrs.Tract], pytrs.TractList, pytrs.PLSSDesc],
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
    ) -> Union[pytrs.Tract, None]:
        """
        Write a single tract in the footer.

        :param write_partial: (Optional, on by default) If there is not
            space to write the tract's entire description, write
            whatever will fit. (A partially written tract will NOT be
            returned as unwritten.)
        :param font_rgba: (Optional) Specify the RGBA code to use for
            this tract. If not specified, will use the ``.footerfont_rgba``
            specified in the settings.
        :return: If the tract is successfully written (or partially
            written), this will return None. If it could not be written,
            the original tract will be returned.
        """
        stn = self.settings
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
        draw = self._get_layer_draw('footer', create=True)
        draw.text(xy=(self._x, self._y), text=f"{trs}:", font=font, fill=fill)
        # If any undefined lots, use the warning color for the desc of this tract.
        if hasattr(tract, 'undefined_lots') and len(tract.undefined_lots) > 0:
            fill = stn.warningfont_rgba
        for line in writable_lines:
            # This moves the y cursor down appropriately.
            self._write_line(x=self._trs_indent, text=line, fill=fill)
        return None

    def write_text(self, txt, write_partial=False) -> Union[str, None]:
        """
        Write a block of text in the footer.

        :param write_partial: (Optional, off by default) If there is not
            space to write the entire block of text, write whatever will
            fit.
        :return: If the entire block is successfully written, this will
            return None. If not, the portion of the text that could not
            be written will be returned (and if ``write_partial=False``,
            then the whole text block will be returned as unwritten).
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
    ):
        """
        :param twp: The Twp of the Twp/Rge represented by this Plat.
        :param rge: The Rge of the Twp/Rge represented by this Plat.
        :param settings: The ``Settings`` object to control the behavior
            and appearance of this plat. (Will be overridden by the
            settings in ``owner``, if that is passed.)
        """
        super().__init__()
        self.twp = twp
        self.rge = rge
        self.queue = pytrs.TractList()
        self.header = PlatHeader(owner=self)
        self.body = PlatBody(twp, rge, owner=self)
        self.footer = PlatFooter(owner=self)
        # If `.owner` is used, it must include .settings attribute.
        self.owner: Union[ISettingsLotDefinerOwner, None] = None
        # ._settings will not be used if this Plat has an owner.
        self._settings: Settings = settings
        if settings is None:
            self._settings = DEFAULT_SETTINGS
        self._lot_definer: Union[LotDefiner, None] = lot_definer
        if lot_definer is None:
            self._lot_definer = LotDefiner()
        # ._all_lot_defs_cached will not be used if this Plat has an owner.
        # It's a cache of lot definitions (including defaults). Gets used while
        # executing queue, then cleared.
        self._all_lot_defs_cached = {}

    @property
    def dim(self):
        return self.settings.dim

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
        self._configure()

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

    def _set_owner(self, owner: ISettingsLotDefinerOwner):
        """
        INTERNAL USE:

        Set this plat's owner, whose ``.settings`` and ``.lot_definer``
        will control.
        """
        self._settings = None
        self._lot_definer = None
        self.owner = owner

    @property
    def all_lot_defs_cached(self):
        if self.owner is not None:
            return self.owner.all_lot_defs_cached
        return self._all_lot_defs_cached

    @all_lot_defs_cached.setter
    def all_lot_defs_cached(self, new_cached):
        if self.owner is None:
            self._all_lot_defs_cached = new_cached

    def _configure(self):
        """Configure this plat and its subordinates."""
        self._reset_layers(dim=self.dim)
        self.body._configure(twp=self.twp, rge=self.rge)
        self.footer._configure()
        return None

    def execute_queue(self, prompt_define=False) -> pytrs.TractList:
        """
        Execute the queue of tracts to fill in the plat.

        :param prompt_define: (Optional) If ``True``, first check for
            undefined lots, and prompt the user in console to define
            them.
        :return: A ``pytrs.TractList`` containing all tracts that could
            not be platted (no lots or aliquots identified).
        """
        if prompt_define:
            self.prompt_define()
        self._configure()
        twprge = f"{self.twp}{self.rge}"
        self.queue.custom_sort()
        if self.owner is None:
            cached = self.lot_definer.get_all_definitions(mandatory_twprges=[twprge])
            self.all_lot_defs_cached = cached
        for tract in self.queue:
            if self.twp is None:
                self.twp = tract.twp
            if self.rge is None:
                self.rge = tract.rge
            self.body.add_tract(tract)
        unplattable_tracts = self.body.execute_subordinate_queues()
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
        return unplattable_tracts

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
            ``pytrs.TRS.pretty_twprge()`` to control how the Twp/Rge
            header should be spelled out.
        """
        self.header.write_header(custom_header=custom_header, **kw)

    def write_lot_numbers(self, at_depth=2, only_for_queue: bool = None):
        """
        Write the lot numbers to the plat.

        :param at_depth: Depth at which to write the lots. Default is 2
            (i.e., quarter-quarters).
        :param only_for_queue: (Optional) If ``True``, only write
            section numbers for those sections that appear in the
            ``.queue``.
        """
        subset_sec_nums = None
        clear_cache_after = False
        if only_for_queue is None:
            only_for_queue = self.settings.lots_only_for_queue
        if only_for_queue:
            subset_sec_nums = sorted(set([tract.sec_num for tract in self.queue]))
        if not self.all_lot_defs_cached and self.owner is None:
            twprge = f"{self.twp}{self.rge}"
            cached = self.lot_definer.get_all_definitions(mandatory_twprges=[twprge])
            self.all_lot_defs_cached = cached
            clear_cache_after = True
        self.body.write_lot_numbers(at_depth=at_depth, subset_sec_nums=subset_sec_nums)
        if clear_cache_after:
            self.all_lot_defs_cached = None
        return None

    def write_tracts(
            self,
            tracts: Union[list[pytrs.Tract], pytrs.TractList, pytrs.PLSSDesc] = None
    ):
        """
        Write all the tract descriptions in the footer.
        """
        if tracts is None:
            tracts = self.queue
        return self.footer.write_tracts(tracts)

    def write_footer_text(self, txt: str, write_partial=False):
        """
        Write a block of text in the footer.

        :param txt: The block of text to write.
        :param write_partial: (Optional, off by default) If there is not
            space to write the entire block of text, write whatever will
            fit.
        """
        return self.footer.write_text(txt, write_partial)


class PlatGroup(ISettingsLotDefinerOwner, QueueMany):
    """
    A collection of Plats that can span multiple Twp/Rge. Access the
    plats in ``.plats`` (keyed by a ``twprge`` string in the ``pytrs``
    format, e.g., ``'154n97w'``).
    """

    def __init__(self, settings: Settings = None, lot_definer: LotDefiner = None):
        """
        :param settings: The ``Settings`` object to control the behavior
            and appearance of the subordinate plats.
        :param lot_definer: A ``LotDefiner`` object to use for defining
            lots in tracts that are added to the queue. (Can also be
            modified or replaced in the ``.lot_definer`` attribute
            later.)
        """
        if settings is None:
            settings = DEFAULT_SETTINGS
        self._settings: Settings = settings
        if lot_definer is None:
            lot_definer = LotDefiner()
        self.lot_definer: LotDefiner = lot_definer
        self.queue = pytrs.TractList()
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
            plat._configure()

    def register_plat(self, twp: str, rge: str) -> Plat:
        """
        Register a new plat for the specified ``twp`` and ``rge``. If
        a plat already exists for the Twp/Rge, this will raise a
        ``KeyError``.
        """
        plat = Plat(twp, rge)
        # Register self as owner, in order to use this PlatGroup's
        # .settings and .lot_definer.
        plat._set_owner(owner=self)
        trs = pytrs.TRS.from_twprgesec(twp, rge, sec=None)
        twprge = trs.twprge
        if twprge in self.plats:
            raise KeyError(f"Duplicate Twp/Rge {twprge!r} cannot registered.")
        self.plats[trs.twprge] = plat
        plat._configure()
        return plat

    def add_tract(self, tract: pytrs.Tract) -> None:
        """
        Add a tract to the queue. If no plat yet exists for the Twp/Rge
        of this tract, one will be created.

        .. note::

            The tract must already be parsed for lots/QQs. (See
            ``pyTRS`` documentation for details.)
        """
        # Add tract to own queue.
        self.queue.append(tract)
        # Create plat if necessary.
        plat = self.plats.get(tract.twprge)
        if plat is None:
            plat = self.register_plat(tract.twp, tract.rge)
        # Add tract to that plat's queue.
        plat.add_tract(tract)
        return None

    def execute_queue(
            self,
            subset_twprges: list[str] = None,
            prompt_define=False
    ) -> pytrs.TractList:
        """
        Execute the queue of tracts to fill in the plats.

        :param subset_twprges: (Optional) Limit the generated image to
            this list of Twp/Rges (in the pyTRS format -- e.g.,
            ``['154n97w', '155n97w']``).
        :param prompt_define: (Optional) If ``True``, first check for
            undefined lots, and prompt the user in console to define
            them.
        :return: A ``pytrs.TractList`` containing all tracts that could
            not be platted (no lots or aliquots identified).
        """
        self.all_lot_defs_cached = self.lot_definer.get_all_definitions(
            mandatory_twprges=list(self.plats.keys())
        )
        all_unplattable = pytrs.TractList()
        selected_tracts = self.queue
        if subset_twprges is None:
            subset_twprges = sorted(self.plats.keys())
        else:
            selected_tracts = self.queue.filter(lambda t: t.twprge in subset_twprges)
        if prompt_define:
            self.lot_definer.prompt_define(tracts=selected_tracts)
        for twprge in subset_twprges:
            plat = self.plats[twprge]
            unplattable = plat.execute_queue()
            all_unplattable.extend(unplattable)
        self.all_lot_defs_cached = {}
        return all_unplattable

    def write_lot_numbers(self, at_depth=2, only_for_queue: bool = None):
        """
        Write the lot numbers to the plats.

        :param at_depth: Depth at which to write the lots. Default is 2
            (i.e., quarter-quarters).
        :param only_for_queue: (Optional) If ``True``, only write
            section numbers for those sections that appear in the
            ``.queue``.
        """
        for plat in self.plats.values():
            plat.write_lot_numbers(at_depth=at_depth, only_for_queue=only_for_queue)
        return None

    def output(
            self,
            fp: Union[str, Path] = None,
            image_format: str = None,
            stack=None,
            subset_twprges: list[str] = None,
            layers: list[str] = None
    ) -> list[Image.Image]:
        """
        Compile and return the merged image of the plats. Optionally
        save the results to disk, either as one or more images, or as a
        .zip file containing the image(s).

        .. note::

            Most image file formats are acceptable. If saving to a
            ``.pdf`` or ``.tiff`` file extension, this will assume the
            user wants a single file -- but separate files can be forced
            with ``stack=False``.

            If multiple files must be created (e.g., if the image format
            is ``'png'``), then the respective Twp/Rge will be added to
            each filename, before the file extension. For example, with
            ``fp='some_file.png'``, it might create
            ``some_file 154n97w.png``, ``some_file 155n97w.png``, etc.

        :param fp: (Optional) If provided, save the output to the
            specified filepath. If the path has a ``.zip`` extension,
            the results will be put into a .zip file at that path. In
            that case, you may want to specify the ``image_format``.
        :param image_format: (Optional) Override the file format of the
            file specified in ``fp``. If not provided, will defer to the
            file extension in ``fp``. (Only relevant if saving to file.)
        :param stack: (Optional) Whether to save the images to a single
            file (assuming an appropriate image format is used). If the
            file extension or specified ``image_format`` are ``'tiff'``
            or ``'pdf'``, then the resulting image will be stacked by
            default (but can be overridden with ``stack=False``). Any
            other format will result in separate images.
        :param subset_twprges: (Optional) Output the plats only for the
            selected Twp/Rges (formatted as ``['154n97w', '12s58e']``).
        :param layers: (Optional) Choose which image layers (in
            bottom-up order) to include in the output. (See
            ``Plat.DEFAULT_LAYER_NAMES`` for the standard layer names.)
            Nonexistent or empty layers will be ignored.
        :return: The resulting plat image(s) as a list of images.
        """
        results = []
        written_twprges = []
        twprges = sorted(self.plats.keys())
        if subset_twprges is not None:
            twprges = subset_twprges
        for twprge in twprges:
            plat = self.plats[twprge]
            results.append(plat.output(layers=layers))
            written_twprges.append(twprge)
        if fp is not None:
            save_output_images(results, fp, image_format, stack, written_twprges)
        return results


class MegaPlat(IPlatOwner, QueueMany):
    """
    A dynamic plat showing multiple townships on the same page.

    Does not allow for footers, and 'headers' are instead written at the
    center of each township. Consider using a ``.headerfont_rgba`` in
    the settings that is faint, to avoid obfuscating section lines, etc.

    .. warning::

        The dimensions of a ``MegaPlat`` output are determined by the
        number and spread of the townships in the tracts added to the
        queue. The resulting images can probably be extremely large. As
        a safeguard, specify ``max_dim=(int, int)`` as a limit to the
        dimensions you are willing to generate. If either of those
        dimensions is violated, it will raise a ``RuntimeError``.

    .. note::

        The size of each component plat (one for each township) is
        controlled by ``.sec_length_px``. And ``.body_marg_top_y``
        serves as the margins on all four sides of the resulting group
        of plats.

    .. note::

        This will not allow Townships in the queue to be both North and
        South (i.e., ``'154n'`` and ``'27s'`` cannot coexist in the
        queue). Similarly, Ranges may not be both East and West
        (``'97w'`` and ``'58e'`` cannot coexist). If either condition is
        violated, a ``ValueError`` will be raised.
    """

    def __init__(
            self,
            settings: Settings = None,
            lot_definer: LotDefiner = None,
            max_dim: tuple[int, int] = None,
    ):
        """
        :param settings: The ``Settings`` object to control the behavior
            and appearance of this plat.
        :param lot_definer: A ``LotDefiner`` object to use for defining
            lots in tracts that are added to the queue. (Can also be
            modified or replaced in the ``.lot_definer`` attribute
            later.)
        :param max_dim: (Optional) Specify the largest dimensions that
            may be generated. If exceeded, a ``RuntimeError`` will be
            raised prior to plat generation.
        """
        super().__init__()
        self.queue = pytrs.TractList()
        if settings is None:
            settings = DEFAULT_MEGAPLAT_SETTINGS
        self.settings: Settings = settings
        if lot_definer is None:
            lot_definer = LotDefiner()
        self.lot_definer: LotDefiner = lot_definer
        self.subplats: dict[str, PlatBody] = {}
        # dim gets dynamically set when executing the queue.
        self.dim = (1, 1)
        if max_dim is None:
            max_dim = (float('inf'), float('inf'))
        self.max_dim = max_dim
        self.image_layers: list[Image.Image] = []
        self.latest_subplats: dict[str, PlatBody] = {}
        self._configure()

    def _configure(self):
        """
        Configure this ``MegaPlat`` and subordinates.
        """
        self._reset_layers(dim=self.dim)
        return None

    def _clean_queue(self, queue=None) -> (pytrs.TractList, pytrs.TractList):
        """
        Scrub out any undefined or error townships in the ``queue`` of
        tracts.
        :return: A ``TractList`` of clean tracts, and a ``TractList`` of
            unplattable tracts.
        """
        out_queue = pytrs.TractList()
        unplattable_tracts = pytrs.TractList()
        if queue is None:
            queue = self.queue
        if not queue:
            return out_queue
        queue.custom_sort()
        for tract in queue:
            if not tract.trs_is_undef(sec=False) and not tract.trs_is_error(sec=False):
                out_queue.append(tract)
            else:
                unplattable_tracts.append(tract)
                warning = UnplattableWarning.unclear_trs(tract)
                warn(warning)
        return out_queue, unplattable_tracts

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
        self.latest_subplats = {}
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
        if self.dim[0] > self.max_dim[0] or self.dim[1] > self.max_dim[1]:
            raise RuntimeError(
                f"Configured max dimensions {self.max_dim} exceeded: {self.dim}")

        # Create the images here, because `self.dim` was just calculated.
        self._configure()

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
                subplat._configure(xy=subplat_topleft)
                subplat.draw_outline()
                self.latest_subplats[twprge] = subplat
                # Store Twp/Rge/topleft_xy for lotwriters.
                subplat_lotwriter_info.append((twp, rge, subplat_topleft))

        if self.settings.write_lot_numbers:
            self.write_lot_numbers(only_for_queue=self.settings.lots_only_for_queue)
        return self.latest_subplats

    def write_lot_numbers(self, at_depth=2, only_for_queue: bool = None):
        """
        Write the lot numbers to the MegaPlat.

        .. note::

            Lot numbers will only be written for the Twp/Rge's that were
            last processed with ``.execute_queue()``.

        :param at_depth: Depth at which to write the lots. Default is 2
            (i.e., quarter-quarters).
        :param only_for_queue: (Optional) If ``True``, only write
            section numbers for those sections that appear in the
            ``.queue``.
        """
        mandated = list(self.latest_subplats.keys())
        all_defs = self.lot_definer.get_all_definitions(mandatory_twprges=mandated)
        self.all_lot_defs_cached = all_defs
        if only_for_queue is None:
            only_for_queue = self.settings.lots_only_for_queue
        for twprge, subplat in self.latest_subplats.items():
            subset_sec_nums = None
            if only_for_queue:
                relevant_tracts = self.queue.filter(key=lambda tr: tr.twprge == twprge)
                subset_sec_nums = sorted(set([tr.sec_num for tr in relevant_tracts]))
            subplat.write_lot_numbers(
                at_depth=at_depth, subset_sec_nums=subset_sec_nums)
        self.all_lot_defs_cached = {}

    def execute_queue(
            self,
            subset_twprges: list[str] = None,
            prompt_define=False
    ) -> pytrs.TractList:
        """
        Execute the queue of tracts, and generate the plat.

        :param subset_twprges: (Optional) Limit the generated images to
            this list of Twp/Rges (in the pyTRS format -- e.g.,
            ``['154n97w', '155n97w']``).
        :param prompt_define: (Optional) If ``True``, first check for
            undefined lots, and prompt the user in console to define
            them.
        :return: A ``pytrs.TractList`` containing all tracts that could
            not be platted.
        """
        queue = self.queue
        if subset_twprges is not None:
            queue = queue.filter(key=lambda tract: tract.twprge in subset_twprges)
        if prompt_define:
            self.prompt_define()
        # Confirm all tracts are valid.
        queue, unplattable_tracts = self._clean_queue(queue)
        if not queue:
            return unplattable_tracts

        # Generate subplats. Also determines the `.dim` of our output.
        subplats = self._gen_subplats(queue)

        for tract in queue:
            self.lot_definer.process_tract(tract, commit=True)
            subplat = subplats[tract.twprge]
            subplat.add_tract(tract)
        for subplat in subplats.values():
            unplattable = subplat.execute_subordinate_queues()
            unplattable_tracts.extend(unplattable)
        return unplattable_tracts
