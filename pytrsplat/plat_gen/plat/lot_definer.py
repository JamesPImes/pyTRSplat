from __future__ import annotations
import csv
from pathlib import Path
from copy import deepcopy

import pytrs

__all__ = [
    'LotDefiner',
]


class LotDefiner:
    """
    A class for specifying which lots correspond to which aliquots, and
    for converting those lots into aliquots.

    Can be passed as ``lot_definer=`` when initializing one of the
    various plat types, or accessed / modified in its ``.lot_definer``
    attribute later.
    """

    # Defaults in townships with ~40-acre lots.
    DEF_01_THRU_05_40AC = {
        'L1': 'NENE',
        'L2': 'NWNE',
        'L3': 'NENW',
        'L4': 'NWNW'
    }
    DEF_06_40AC = {
        'L1': 'NENE',
        'L2': 'NWNE',
        'L3': 'NENW',
        'L4': 'NWNW',
        'L5': 'SWNW',
        'L6': 'NWSW',
        'L7': 'SWSW',
    }
    DEF_07_18_19_30_31_40AC = {
        'L1': 'NWNW',
        'L2': 'SWNW',
        'L3': 'NWSW',
        'L4': 'SWSW'
    }

    # Defaults in townships with (mostly) ~80-acre lots.
    DEF_01_THRU_05_80AC = {
        'L1': 'N2NE',
        'L2': 'N2NW',
    }
    DEF_06_80AC = {
        'L1': 'N2NE',
        'L2': 'NENW',  # This is the exception.
        'L3': 'W2NW',
        'L4': 'W2SW',
    }
    DEF_07_18_19_30_31_80AC = {
        'L1': 'W2NW',
        'L2': 'W2SW',
    }

    # All other sections in a /standard/ Twp have no lots.
    DEF_00 = {}

    def __init__(self, allow_defaults=False, standard_lot_size: int = 40):
        """
        :param allow_defaults: Whether to assume that all sections are
            'standard', with typical lots (if any) in sections along the
            north and west township boundaries. Can be changed later in
            the ``.allow_defaults`` attribute.
        :param standard_lot_size: How big we assume a 'standard' lot is
            in the township(s) being considered. Must be either ``40``
            or ``80``. (This determines the default lot definitions.)
            Can be changed later in the ``.standard_lot_size`` property.
        """
        # {twprge:      {sec:   {lot:   definition} } }
        # {'154n97w':   {1:     {'L1':  'NENE', 'L2': 'NWNE', ...} } }
        self.definitions = {}
        self.allow_defaults = allow_defaults
        self._standard_lot_size: int = standard_lot_size
        # This is generated when .standard_lot_size is set.
        self.default_definitions: dict = {}
        self.standard_lot_size = standard_lot_size

    @property
    def standard_lot_size(self):
        return self._standard_lot_size

    @standard_lot_size.setter
    def standard_lot_size(self, new_standard: int):
        if not isinstance(new_standard, int):
            raise TypeError(
                f"`standard_lot_size` must be an int (either 40 or 80). "
                f"Passed type: {type(new_standard)}"
            )
        if new_standard not in (40, 80):
            raise ValueError(
                f"`standard_lot_size` must be either 40 or 80. Passed: {new_standard}")
        self._standard_lot_size = new_standard
        self.default_definitions = self.defaults()

    def __repr__(self):
        return str(self.definitions)

    def defaults(self):
        """Get default lot definitions."""
        output = {}
        if self.standard_lot_size == 40:
            for sec_num in range(1, 6):
                output[sec_num] = self.DEF_01_THRU_05_40AC.copy()
            output[6] = self.DEF_06_40AC.copy()
            for sec_num in (7, 18, 19, 30, 31):
                output[sec_num] = self.DEF_07_18_19_30_31_40AC.copy()
        elif self.standard_lot_size == 80:
            for sec_num in range(1, 6):
                output[sec_num] = self.DEF_01_THRU_05_80AC.copy()
            output[6] = self.DEF_06_80AC.copy()
            for sec_num in (7, 18, 19, 30, 31):
                output[sec_num] = self.DEF_07_18_19_30_31_80AC.copy()
        return output

    def define_lot(self, trs: str | pytrs.TRS, lot: int | str, definition: str):
        """
        :param trs: The Twp/Rge/Sec in the pyTRS format (e.g.,
            ``'154n97w01'``).
        :param lot: The lot number, either as ``'L1'`` or as int.
        :param definition: The aliquots that make up this lot, separated
            by comma if necessary. (Be sure to use ``'clean_qq'``
            compatible definitions, such as ``'NENE'`` or
            ``'N2NW,SENW'``. (Reference the pyTRS documentation for more
            info.)
        """
        trs = pytrs.TRS(trs)
        self.definitions.setdefault(trs.twprge, {})
        self.definitions[trs.twprge].setdefault(trs.sec_num, {})
        if isinstance(lot, int):
            lot = f"L{lot}"
        self.definitions[trs.twprge][trs.sec_num][lot] = definition

    @classmethod
    def from_csv(
            cls,
            fp: Path | str,
            twp='twp',
            rge='rge',
            sec='sec',
            lot='lot',
            qq='qq',
            allow_defaults=False,
            standard_lot_size: int = 40,
    ) -> LotDefiner:
        """
        Create a ``LotDefiner`` from csv file. The data should be
        compatible with ``pyTRS`` formatting.

        Example .csv formatting:

        +------+-----+-----+-----+-----------+
        | twp  | rge | sec | lot | qq        |
        +======+=====+=====+=====+===========+
        | 154n | 97w | 1   | L1  | NENE      |
        +------+-----+-----+-----+-----------+
        | 12s  | 58e | 04  | 1   | N2NE,SENE |
        +------+-----+-----+-----+-----------+

        ``sec`` may optionally have a leading ``0`` (e.g., ``4`` or
        ``'04'``).

        ``lot`` may optionally have a leading ``L`` (e.g., ``1`` or
        ``'L1'``).

        ``qq`` can be one or more aliquots. Be sure to use 'clean' QQ
        definitions, such as the above.

        :param fp: Path to the .csv file to load.
        :param twp: Header for the Twp column.
        :param rge: Header for the Rge column.
        :param sec: Header for the Sec column.
        :param lot: Header for the Lot column.
        :param qq: Header for the lot definition (aliquots) column.
        :param allow_defaults: Whether to assume that all sections are
            'standard', with typical lots (if any) in sections along the
            north and west township boundaries. Can be changed later in
            the ``.allow_defaults`` attribute.
        :param standard_lot_size: How big we assume a 'standard' lot is
            in the township(s) being considered. Must be either ``40``
            or ``80``. (This determines the default lot definitions.)
            Can be changed later in the ``.standard_lot_size`` property.
        """
        out = cls(allow_defaults=allow_defaults, standard_lot_size=standard_lot_size)
        out.read_csv(fp, twp, rge, sec, lot, qq)
        return out

    def read_csv(
            self, fp: Path | str, twp='twp', rge='rge', sec='sec', lot='lot', qq='qq'):
        """
        Load lot definitions from csv file into this existing
        ``LotDefiner``. The data should be compatible with ``pyTRS``
        formatting.

        Example .csv formatting:

        +------+-----+-----+-----+-----------+
        | twp  | rge | sec | lot | qq        |
        +======+=====+=====+=====+===========+
        | 154n | 97w | 1   | L1  | NENE      |
        +------+-----+-----+-----+-----------+
        | 12s  | 58e | 04  | 1   | N2NE,SENE |
        +------+-----+-----+-----+-----------+

        ``sec`` may optionally have a leading ``0`` (e.g., ``4`` or
        ``'04'``).

        ``lot`` may optionally have a leading ``L`` (e.g., ``1`` or
        ``'L1'``).

        ``qq`` can be one or more aliquots. Be sure to use 'clean' QQ
        definitions, such as the above.

        :param fp: Path to the .csv file to load.
        :param twp: Header for the Twp column.
        :param rge: Header for the Rge column.
        :param sec: Header for the Sec column.
        :param lot: Header for the Lot column.
        :param qq: Header for the lot definition (aliquots) column.
        """
        with open(fp, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                twp_ = row[twp]
                rge_ = row[rge]
                sec_ = int(row[sec])
                lot_ = row[lot]
                try:
                    lot_ = f"L{int(lot_)}"
                except ValueError:
                    pass
                lot_def = row[qq]
                twprge = f"{twp_}{rge_}"
                self.definitions.setdefault(twprge, {})
                self.definitions[twprge].setdefault(sec_, {})
                self.definitions[twprge][sec_][lot_] = lot_def
        return self.definitions

    def _save_definitions_to_csv(
            self,
            # {twprge:      {sec:   {lot:   definition} } }
            definitions: dict[str, dict[int | str, dict[int | str, str]]],
            fp: Path | str,
            twp='twp',
            rge='rge',
            sec='sec',
            lot='lot',
            qq='qq'
    ):
        """
        Convert the ``definitions`` and write it to a .csv file at
        ``fp`` that can be reloaded later with ``.from_csv()`` or
        ``.read_csv()``.

        ``definitions`` can be either the dict in the ``.definitions``
        attribute, or a dict of undefined lots as output by
        ``.find_undefined_lots()``. For the latter, it will add a column
        for a user to add aliquots for each lot, but the column will be
        empty.

        .. warning::

            Will overwrite any file that exists as ``fp`` without
            warning.

        :param fp: Path to the .csv file to save to.
        :param twp: Header for the Twp column.
        :param rge: Header for the Rge column.
        :param sec: Header for the Sec column.
        :param lot: Header for the Lot column.
        :param qq: Header for the lot definition (aliquots) column.
        """
        headers = [twp, rge, sec, lot, qq]
        with open(fp, mode='w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(headers)
            for twprge, sec_dict in definitions.items():
                trs = pytrs.TRS(twprge)
                twp_ = trs.twp
                rge_ = trs.rge
                for sec_num, lot_definitions in sec_dict.items():
                    for lot_ in lot_definitions:
                        try:
                            # We are writing a defined lots.
                            definition = lot_definitions.get(lot_)
                        except AttributeError:
                            # We are actually writing an UNDEFINED lot.
                            definition = None
                        row = [twp_, rge_, sec_num, lot_, definition]
                        writer.writerow(row)
        return None

    def save_to_csv(
            self, fp: Path | str, twp='twp', rge='rge', sec='sec', lot='lot', qq='qq'):
        """
        Save the definitions (excluding defaults) to a .csv file that
        can be reloaded later with ``.from_csv()`` or ``.read_csv()``.

        .. warning::

            Will overwrite any file that exists as ``fp`` without
            warning.

        :param fp: Path to the .csv file to save to.
        :param twp: Header for the Twp column.
        :param rge: Header for the Rge column.
        :param sec: Header for the Sec column.
        :param lot: Header for the Lot column.
        :param qq: Header for the lot definition (aliquots) column.
        """
        self._save_definitions_to_csv(self.definitions, fp, twp, rge, sec, lot, qq)
        return None

    def prompt_define(self, tracts: pytrs.TractList, allow_defaults: bool = None):
        """
        Prompt the user in console to define all lots that have not yet
        been defined. Any new lot definitions will be added to the
        ``LotDefiner``.

        (You may wish to save the results with ``.save_to_csv()`` so
        that they can be loaded and reused later.)

        :param allow_defaults: Whether to assume that this section is
            'standard', with typical lots (if any) in sections along the
            north and west township boundaries. If not specified here,
            will use whatever is configured in the ``.allow_defaults``
            attribute.
        """
        undefined = self.find_undefined_lots(tracts, allow_defaults)
        if not undefined:
            return None
        print(
            "Prompting user to define lots."
            "\n - Leave blank to skip. "
            "\n - Enter 'quit' to quit."
        )
        for twprge in undefined:
            for sec_num, lots in undefined[twprge].items():
                trs = pytrs.TRS(f"{twprge}{str(sec_num).rjust(2, '0')}")
                for lot in lots:
                    while True:
                        defin = input(f"{trs}: {lot} = ")
                        if not defin:
                            break
                        if defin.lower() == 'quit':
                            return None
                        tract = pytrs.Tract(defin, parse_qq=True, config='clean_qq')
                        if not tract.qqs:
                            msg = (
                                "No aliquots could be identified in that response. "
                                "Try again?\n"
                                "(Leave blank to skip; 'quit' to quit.)"
                            )
                            print(msg)
                        else:
                            self.define_lot(trs, lot, defin)
                            break
        return None


    def get_all_definitions(
            self,
            include_defaults: bool = None,
            mandatory_twprges: list[str] = None
    ) -> dict[str, dict[str, dict[str, str]]]:
        """
        Get all definitions, including any defaults (if so configured or
        requested).

        :param include_defaults: Whether to include defaults in the
            returned definitions. If not specified here, will use
            whatever has been configured in ``.allow_defaults``.

        :param mandatory_twprges: (Optional) A list of Twp/Rge's (in the
            ``pyTRS`` format, ``'154n97w'``) that must be included in
            the return definitions. Will add any such Twp/Rge that is
            not already found in this ``LotDefiner``.

        :return: A nested dict of definitions.
            ``twprge > sec > lot: definition``
        """
        if include_defaults is None:
            include_defaults = self.allow_defaults
        if not include_defaults:
            output = deepcopy(self.definitions)
            for twprge in mandatory_twprges:
                output.setdefault(twprge, {})
            return output
        output = {}
        # Merge actual definitions into defaults, overwriting any defaults.
        for twprge, sec_def in self.definitions.items():
            output.setdefault(twprge, {})
            output[twprge] = deepcopy(self.default_definitions)
            existing_twprge_def = output[twprge]
            for sec_num, definitions in sec_def.items():
                existing_twprge_def[sec_num] = definitions
        for twprge in mandatory_twprges:
            if twprge not in output:
                output[twprge] = deepcopy(self.default_definitions)
        return output

    def convert_lots(
            self,
            lots: list[str],
            twprge: str,
            sec_num: int,
            allow_defaults: bool = None,
    ) -> (list[str], list[str]):
        """
        Convert a list of lots (from the ``.lots`` of a ``pytrs.Tract``
        object) into corresponding aliquots.
        """
        def_twprge = self.definitions.get(twprge, {})
        def_sec = def_twprge.get(sec_num, {})
        default_def_sec = None
        if allow_defaults is None:
            allow_defaults = self.allow_defaults
        if allow_defaults:
            default_def_sec = self.default_definitions.get(sec_num, {})
        return self._lots_to_aliquots(lots, def_sec, default_def_sec)

    def process_tract(
            self,
            tract: pytrs.Tract,
            allow_defaults: bool = None,
            commit=True
    ) -> (list[str], list[str]):
        """
        Convert ``.lots`` in the ``tract`` into QQs, identify any
        undefined lots. If ``commit=True``, set them to ad-hoc
        attributes ``.lots_as_qqs`` and ``undefined_lots``,
        respectively.

        :param tract: A ``pytrs.Tract`` object that has already been
            parsed into lots and QQs.
        :param allow_defaults: Whether to assume that this section is
            'standard', with typical lots (if any) in sections along the
            north and west township boundaries. If not specified here,
            will use whatever is configured in the ``.allow_defaults``
            attribute.
        :param commit: (Optional, on by default). Whether to store the
            results to ``.lots_as_qqs`` and ``undefined_lots``.
        :return: Two lists: The first being the converted aliquots, and
            the second being a list of lots that have not been defined.
        """
        twprge = tract.twprge
        sec_num = tract.sec_num
        qqs, undefined_lots = self.convert_lots(
            tract.lots, twprge, sec_num, allow_defaults)
        if commit:
            tract.lots_as_qqs = qqs
            tract.undefined_lots = undefined_lots
        return qqs, undefined_lots

    def process_tracts(
            self, tracts: pytrs.TractList | pytrs.PLSSDesc) -> None:
        """
        Convert ``.lots`` in the ``tracts`` into QQs, and add them to
        ad-hoc attribute ``.lots_as_qqs`` for each tract. Also add an
        ad-hoc ``.undefined_lots`` attribute to each tract for any lots
        that have not been defined.

        :param tracts: A container of ``pytrs.Tract`` objects that have
            already been parsed into lots and QQs.
        """
        for tract in tracts:
            self.process_tract(tract, commit=True)
        return None

    def find_undefined_lots(
            self,
            tracts: pytrs.TractList | pytrs.PLSSDesc,
            allow_defaults: bool = None,
            fp: str | Path = None,
            **headers,
    ) -> dict[str, dict[str, list[str]]]:
        """
        Find all tracts that have one or more lots that have not been
        defined. Optionally write them to a .csv file at path ``fp``, to
        facilitate defining them externally.

        .. warning::

            If passing ``fp``, any file at that path will be overwritten
            without warning.

        :param tracts: A collection of ``pytrs.Tract`` objects that have
            been parsed to lots and QQs.
        :param allow_defaults: Whether to assume that all sections are
            'standard', with typical lots (if any) in sections along the
            north and west township boundaries. If not specified here,
            will use whatever is configured in the ``.allow_defaults``
            attribute.
        :param fp: (Optional) A filepath at which to create a .csv file
            containing the undefined lots.
        :param headers: (Optional) If saving the undefined lots to a
            .csv file, pass keyword arguments to specify the desired
            headers. (Reference the docs for
            ``LotDefiner.save_to_csv()`` for the appropriate
            parameters.)
        :return: A nested dict, keyed by Twp/Rge (``'154n97w'``), then
            keyed by section number (``1``), and the deep values being a
            sorted list of lots for that Twp/Rge/Sec.
        """
        output = {}
        for tract in tracts:
            _, undefined_lots = self.process_tract(tract, allow_defaults, commit=False)
            if undefined_lots:
                output.setdefault(tract.twprge, {})
                output[tract.twprge].setdefault(tract.sec_num, set())
                # Convert lots ['L1', 'L2'] to integers [1, 2] for later sorting.
                ilots = [int(lt.split('L')[-1]) for lt in undefined_lots]
                output[tract.twprge][tract.sec_num].update(ilots)
        for twprge, sec_dict in output.items():
            for k, lot_set in sec_dict.items():
                # Convert back to ['L1', 'L2', ...].
                sec_dict[k] = [f"L{lt}" for lt in sorted(lot_set)]
        if fp is not None:
            self._save_definitions_to_csv(output, fp, **headers)
        return output

    @staticmethod
    def _lots_to_aliquots(
            lots: list[str],
            lot_defs: dict[str, str],
            default_defs: dict[str, str] = None
    ) -> (list[str], list[str]):
        """
        Convert a list of lots (from the ``.lots`` of a ``pytrs.Tract``
        object) into corresponding aliquots.
        """

        def process_aliquot(aliq: str, into: list[str]):
            """
            Helper function to parse aliquot string and put into the list of
            resulting QQs.
            """
            tract = pytrs.Tract(aliq, parse_qq=True, config='clean_qq')
            into.extend(tract.qqs)
            return None

        if default_defs is None:
            default_defs = {}
        qqs = []
        undefined_lots = []
        for lot in lots:
            div = ''
            if ' of ' in lot:
                div, lot = lot.split(' of ')
            defined_aliquot = lot_defs.get(lot)
            if defined_aliquot is None:
                defined_aliquot = default_defs.get(lot)
            if defined_aliquot is None:
                undefined_lots.append(lot)
                continue
            # Ensure division is appropriate for the defined aliquot.
            defined_aliquot = defined_aliquot.replace(';', ',')
            tract = pytrs.Tract(defined_aliquot, parse_qq=True, config='clean_qq')
            if len(tract.aliquots) > 1:
                # Throw away division if lot division is for irregular shape.
                div = ''
            for aliq in tract.aliquots:
                aliq = f"{div}{aliq}"
                process_aliquot(aliq, into=qqs)
        return qqs, undefined_lots
