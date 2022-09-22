
import sys
import unittest

sys.path.append(r'..\..')

import pytrs

from pytrsplat.plat_gen.grid import (
    SectionGrid,
    TownshipGrid,
    LotDefinitions,
    TwpLotDefinitions,
    LotDefDB,
)


class SectionGridTests(unittest.TestCase):

    def test_sec_grid_basic(self):
        """
        Creation of SectionGrid from standard init, ``.from_trs()``, and
        from ``pytrs.Tract`` object.
        """
        sg0 = SectionGrid()
        self.assertEqual('___z___z00', sg0.trs)

        sg1 = SectionGrid(14, '154n', '97w')
        self.assertEqual('154n97w14', sg1.trs)
        sg2 = SectionGrid.from_trs('154n97w14')
        self.assertEqual('154n97w14', sg2.trs)

        tract = pytrs.Tract('NE/4', '154n97w14')
        self.assertEqual('154n97w14', tract.trs)
        sg3 = SectionGrid.from_tract(tract)
        self.assertEqual('154n97w14', sg3.trs)

    # def test_apply_lddb():

    # def test_apply_tld():

    # def lots_by_qq_name():

    # def test_lots_by_grid():

    def test_incorporate_qq_list(self):
        qqs = ['NENE', 'SWNW']
        expected = """=====================
|    |    |    |XXXX|
|----+----+----+----|
|XXXX|    |    |    |
|----+----+----+----|
|    |    |    |    |
|----+----+----+----|
|    |    |    |    |
====================="""

        sg = SectionGrid()
        sg.incorporate_qq_list(qqs)
        self.assertEqual(expected, sg.output_text_plat())

    def test_incorporate_lot_list(self):
        lots = ['L3', 'L4']
        expected = """=====================
|XXXX|XXXX|    |    |
|----+----+----+----|
|    |    |    |    |
|----+----+----+----|
|    |    |    |    |
|----+----+----+----|
|    |    |    |    |
====================="""

        defs = {'L3': 'NENW', 'L4': 'NWNW'}
        ld = LotDefinitions()
        ld.absorb_ld(defs)

        sg = SectionGrid(ld=ld)
        sg.incorporate_lot_list(lots)
        self.assertEqual(expected, sg.output_text_plat())

    def test_incorporate_tract(self):
        tract = pytrs.Tract(
            'Lots 3, 4, NENE, SWNW', config='clean_qq', parse_qq=True)
        expected = """=====================
|XXXX|XXXX|    |XXXX|
|----+----+----+----|
|XXXX|    |    |    |
|----+----+----+----|
|    |    |    |    |
|----+----+----+----|
|    |    |    |    |
====================="""

        defs = {'L3': 'NENW', 'L4': 'NWNW'}
        ld = LotDefinitions()
        ld.absorb_ld(defs)

        sg = SectionGrid(ld=ld)
        sg.incorporate_tract(tract)
        self.assertEqual(expected, sg.output_text_plat())

    def test_filled_coords(self):
        qqs = ['NENE', 'SWNW']
        expected = [(3, 0), (0, 1)]
        sg = SectionGrid()
        sg.incorporate_qq_list(qqs)
        self.assertEqual(expected, sg.filled_coords())

    def test_has_any(self):
        qqs = ['NENE', 'SWNW']
        expected = [(3, 0), (0, 1)]
        sg = SectionGrid()
        # QQ's not yet incorporated.
        self.assertFalse(sg.has_any())
        sg.incorporate_qq_list(qqs)
        self.assertTrue(sg.has_any())
