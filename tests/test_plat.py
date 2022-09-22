
import sys
import unittest
import os

sys.path.append(r'..\..')

import pytrs

from pytrsplat.plat_gen.plat import (
    Plat,
    MultiPlat,
)


OUTPUT_DIR = './results'
os.makedirs(OUTPUT_DIR, exist_ok=True)


class PlatTest(unittest.TestCase):

    def test_plat_tract(self):
        tract = pytrs.Tract(
            'N2SE, NENE, SWNW', '154n97w14', config='clean_qq', parse_qq=True)
        plat = Plat('154n', '97w', settings='square_m')
        plat.plat_tract(tract)
        plat.output(f"{OUTPUT_DIR}/test_plat.png")

    def test_plat_error(self):
        tract = pytrs.Tract('NE/4', 'asldkfjas', parse_qq=True)
        plat = Plat(settings='square_m')
        plat.plat_tract(tract)
        plat.output(f"{OUTPUT_DIR}/test_plat_error_tract.png")


class MultiPlatTest(unittest.TestCase):

    def test_multiplat_plssdesc(self):
        desc = pytrs.PLSSDesc(
            'T154N-R97W Sec 14: NE/4, Sec 15: W/2, T155N-R97W Sec 1: S/2S/2',
            parse_qq=True)
        multiplat = MultiPlat(settings='square_m')
        multiplat.plat_plssdesc(desc)
        multiplat.output_to_png(f"{OUTPUT_DIR}/test_multiplat.png")
