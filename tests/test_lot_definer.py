import unittest

try:
    from pytrsplat import LotDefiner
except ImportError:
    import sys

    sys.path.append('../')
    from pytrsplat import LotDefiner


class LotDefinerTests(unittest.TestCase):
    def test_init(self):
        ld = LotDefiner(allow_defaults=True)
        self.assertEqual(ld.allow_defaults, True)  # add assertion here


if __name__ == '__main__':
    unittest.main()
