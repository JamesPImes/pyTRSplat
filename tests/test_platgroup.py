import unittest

try:
    from pytrsplat import PlatGroup
except ImportError:
    import sys

    sys.path.append('../')
    from pytrsplat import PlatGroup

class PlatTests(unittest.TestCase):
    def test_init(self):
        plat_group = PlatGroup()
        self.assertTrue(len(plat_group.queue) == 0)


if __name__ == '__main__':
    unittest.main()
