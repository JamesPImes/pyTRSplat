import unittest
from pathlib import Path

try:
    from pytrsplat import LotDefiner
except ImportError:
    import sys

    sys.path.append('../')
    from pytrsplat import LotDefiner

RESOURCE_DIR = Path(r"_resources")


class LotDefinerTests(unittest.TestCase):

    def test_init(self):
        ld = LotDefiner(allow_defaults=True)
        self.assertEqual(ld.allow_defaults, True)

    def test_from_csv(self):
        fp = RESOURCE_DIR / 'test_lot_definitions.csv'
        ld = LotDefiner.from_csv(fp)
        self.assertEqual(len(ld.definitions.keys()), 2)
        self.assertTrue(ld.definitions.get('154n97w08', None) is not None)
        self.assertTrue(ld.definitions.get('12s58e14', None) is not None)

if __name__ == '__main__':
    unittest.main()
