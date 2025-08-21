import unittest

try:
    from pytrsplat import Settings
except ImportError:
    import sys

    sys.path.append('../')
    from pytrsplat import Settings

class SettingsTests(unittest.TestCase):
    def test_init(self):
        settings = Settings()
        # Default fill, transparent blue.
        self.assertEqual(settings.qq_fill_rgba, (0, 0, 255, 100))


if __name__ == '__main__':
    unittest.main()
