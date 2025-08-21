import unittest

try:
    from pytrsplat import Plat
except ImportError:
    import sys

    sys.path.append('../')
    from pytrsplat import Plat

class PlatTests(unittest.TestCase):
    def test_init(self):
        plat = Plat('154n', '97w')
        self.assertEqual(plat.twp, '154n')
        self.assertEqual(plat.rge, '97w')

if __name__ == '__main__':
    unittest.main()
