# Copyright (c) 2020, James P. Imes. All rights reserved.

"""
pyTRSplat -- A module to generate customizable land plat images from
PLSS land descriptions ('legal descriptions'), using the pytrs parsing
module; and/or from manually-selected lands. Import as a module, or use
the GUI application ('pyTRSplat/pyTRSplat_app_windowed.pyw').

Quick Guide to Module Structure / Packages:
`pyTRSplat.launch_app()` -- Launch the GUI application
        (or run 'pyTRSplat/pyTRSplat_app_windowed.pyw' directly)

These functions and classes from the various packages are all imported
as main-level objects and functions. But additional documentation can
be found in their respective source packages:
`pyTRSplat.plat` -- Generate plat images
    classes:    Plat, MultiPlat
    functions:  text_to_plats()
`pyTRSplat.grid` -- Interpret pytrs.PLSSDesc and pytrs.Tract objects,
        define how specific lots should be interpreted, manually.
    classes:    SectionGrid, TownshipGrid, LotDefinitions,
        TwpLotDefinitions, LotDefDB
    functions:  tracts_into_twp_grids(), plssdesc_to_twp_grids()
`pyTRSplat.platqueue` -- Streamlined queuing of objects to add to plats
    classes:    PlatQueue, MultiPlatQueue
`pyTRSplat.platsettings` -- Configure plats (size, colors, fonts, etc.)
    classes:    Settings
`pyTRSplat.settingseditor` -- A GUI editor for `platsettings.Settings`
    classes:    SettingsEditor (NOTE: use the `launch_settings_editor()`
        function to use this class, unless it is being incorporated into
        an application.)
    functions:  launch_settings_editor()
`pyTRSplat.utils` -- Misc. utils
    functions:  filter_tracts_by_twprge()
"""


import pyTRSplat._constants as _constants

__version__ = _constants.__version__
__versionDate__ = _constants.__versionDate__
__author__ = _constants.__author__
__email__ = _constants.__email__
__license__ = _constants.__license__


def version():
    """Return the current version and version date as a string."""
    return f'v{__version__} - {__versionDate__}'

from pyTRSplat.plat import Plat, MultiPlat
from pyTRSplat.plat import text_to_plats
from pyTRSplat.grid import TownshipGrid, SectionGrid
from pyTRSplat.grid import LotDefinitions, TwpLotDefinitions, LotDefDB
from pyTRSplat.grid import tracts_into_twp_grids, plssdesc_to_twp_grids
from pyTRSplat.platsettings import Settings
from pyTRSplat.settingseditor import SettingsEditor
from pyTRSplat.settingseditor import launch_settings_editor
from pyTRSplat.platqueue import PlatQueue, MultiPlatQueue
from pyTRSplat.utils import filter_tracts_by_twprge


def launch_app():
    """
    Launch the GUI application.
    """
    from .pyTRSplat_app import launch_app
    launch_app()
