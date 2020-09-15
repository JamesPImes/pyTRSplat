# Copyright (c) 2020, James P. Imes. All rights reserved.

"""
pyTRSplat -- A module to generate land plat images of full townships
(6x6 grid) or single sections from PLSS land descriptions ('legal
descriptions'), using the pyTRS parsing module.
"""

# TODO: Decide on license.

from Plat import Plat, MultiPlat
from Plat import text_to_plats

from pyTRS.pyTRS import PLSSDesc, Tract
from pyTRS import version as pyTRSversion

from Grid import TownshipGrid, SectionGrid, LotDefinitions, TwpLotDefinitions, LotDefDB
from Grid import tracts_into_twp_grids
from PlatSettings import Settings
from PlatQueue import PlatQueue, MultiPlatQueue

import _constants

__version__ = _constants.__version__
__versionDate__ = _constants.__versionDate__
__author__ = _constants.__author__
__email__ = _constants.__email__


def version():
    """Return the current version and version date as a string."""
    return f'v{__version__} - {__versionDate__}'