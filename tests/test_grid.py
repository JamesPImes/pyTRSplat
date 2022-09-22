
import sys
import unittest

sys.path.append(r'..\..')

import pytrs

from ..pytrsplat.plat_gen.grid import (
    SectionGrid,
    TownshipGrid,
    LotDefinitions,
    TwpLotDefinitions,
    LotDefDB,
)


class GridTests(unittest.TestCase):

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
