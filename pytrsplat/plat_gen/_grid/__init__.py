# Copyright (c) 2020-2022, James P. Imes, all rights reserved.

"""
Grid-based representations of PLSS Sections (i.e. 4x4 _grid of QQs) and
Townships (i.e. 6x6 _grid of Sections), as well as objects for how
specific lots should be interpreted in terms of QQ. Also includes
interpreters for converting parsed ``pytrs.PLSSDesc`` and
``pytrs.Tract`` data into ``SectionGrid`` and ``TownshipGrid`` objects.
"""

from .grid import (
    SectionGrid,
    TownshipGrid,
    LotDefinitions,
    TwpLotDefinitions,
    LotDefDB,
)

from .grid import plssdesc_to_twp_grids, tracts_into_twp_grids