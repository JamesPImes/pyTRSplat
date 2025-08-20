from __future__ import annotations
import csv
from pathlib import Path
from copy import deepcopy

import pytrs

__all__ = [
    'LotDefiner',
]


class LotDefiner:
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
         north and west township boundaries. Can be changed later in the
         ``.allow_defaults`` attribute.
        :param standard_lot_size: How big we assume a 'standard' lot is
         in the township(s) being considered. Must be either ``40`` or
         ``80``. (This determines the default lot definitions.) Can be
         changed later in the ``.standard_lot_size`` property.
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
        compatible with ``pyTRS`` formatting. E.g:
         * ``twp``: ``'154n'``
         * ``rge``: ``'97w'``
         * ``sec``: ``'01'`` (with or without leading ``'0'`` for single digits)
         * ``lot``: ``'L1'``
         * ``qq``: ``'NENE'``

        :param fp: Path to the .csv file to load.
        :param twp: Header for the Twp.
        :param rge: Header for the Rge.
        :param sec: Header for the Sec.
        :param lot: Header for the Lot.
        :param qq: Header for the lot definition (aliquots).
        :param allow_defaults: Whether to assume that all sections are
         'standard', with typical lots (if any) in sections along the
         north and west township boundaries. Can be changed later in the
         ``.allow_defaults`` attribute.
        :param standard_lot_size: How big we assume a 'standard' lot is
         in the township(s) being considered. Must be either ``40`` or
         ``80``. (This determines the default lot definitions.) Can be
         changed later in the ``.standard_lot_size`` property.
        """
        out = cls(allow_defaults=allow_defaults, standard_lot_size=standard_lot_size)
        out.load_from_csv(fp, twp, rge, sec, lot, qq)
        return out

    def load_from_csv(
            self, fp: Path | str, twp='twp', rge='rge', sec='sec', lot='lot', qq='qq'):
        """
        Load lot definitions from csv file. The data should be
        compatible with ``pyTRS`` formatting. E.g:
         * ``twp``: ``'154n'``
         * ``rge``: ``'97w'``
         * ``sec``: ``'01'`` (with or without leading ``'0'`` for single digits)
         * ``lot``: ``'L1'``
         * ``qq``: ``'NENE'``

        :param fp: Path to the .csv file to load.
        :param twp: Header for the Twp.
        :param rge: Header for the Rge.
        :param sec: Header for the Sec.
        :param lot: Header for the Lot.
        :param qq: Header for the lot definition (aliquots).
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

    def get_all_definitions(
            self,
            include_defaults: bool = None,
            mandatory_twprges: list[str] = None
    ) -> dict[str, dict[str, dict[str, str]]]:
        """
        Get all definitions, including any defaults (if so configured or
        requested).
        :param include_defaults: Whether to include defaults in the
         returned definitions. If not specified here, will use whatever
         has been configured in ``.allow_defaults``.
        :param mandatory_twprges: (Optional) A list of Twp/Rge's (in the
         ``pyTRS`` format, ``'154n97w'``) that must be included in the
         return definitions. Will add any such Twp/Rge that is not
         already found in this ``LotDefiner``.
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
         north and west township boundaries. If not specified here, will
         use whatever is configured in the ``.allow_defaults``
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
    ) -> dict[str, dict[str, list[str]]]:
        """
        Find all tracts that have one or more lots that have not been
        defined.

        :param tracts: A collection of ``pytrs.Tract`` objects that have
         been parsed to lots and QQs.
        :param allow_defaults: Whether to assume that all sections are
         'standard', with typical lots (if any) in sections along the
         north and west township boundaries. If not specified here, will
         use whatever is configured in the ``.allow_defaults``
         attribute.
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
