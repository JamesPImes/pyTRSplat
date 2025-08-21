import unittest

try:
    from pytrsplat import MegaPlat
except ImportError:
    import sys

    sys.path.append('../')
    from pytrsplat import MegaPlat

class MegaPlatTests(unittest.TestCase):
    def test_init(self):
        megaplat = MegaPlat()
        self.assertTrue(len(megaplat.queue) == 0)


if __name__ == '__main__':
    unittest.main()
