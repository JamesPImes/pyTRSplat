# Copyright (c) 2020-2021, James P. Imes. All rights reserved.

"""
pyTRSplat -- A module to generate customizable land plat images from
PLSS land descriptions ('legal descriptions'), using the pyTRS parsing
module; and/or from manually-selected lands. Import as a module (as
``pytrsplat``), or use the GUI application by running
``pytrsplat/pyTRSplat_app_windowed.pyw``.

Quick Guide to Module Structure / Packages:
``pytrsplat.launch_app()`` -- Launch the GUI application
        (or run 'pytrsplat/pyTRSplat_app_windowed.pyw' directly)

These functions and classes from the various packages are all imported
as top-level classes and functions. But additional documentation can
be found in their respective source packages:

``pytrsplat.plat`` -- Generate plat images
    classes:    Plat, MultiPlat
    functions:  text_to_plats()

``pytrsplat.grid`` -- Interpret pytrs.PLSSDesc and pytrs.Tract objects,
        define how specific lots should be interpreted, manually.
    classes:    ``SectionGrid``, ``TownshipGrid``, ``LotDefinitions``,
        ``TwpLotDefinitions``, ``LotDefDB``
    functions:  ``tracts_into_twp_grids()``, ``plssdesc_to_twp_grids()``

``pytrsplat.platqueue`` -- Streamlined queuing of objects to add to plats
    classes:    ``PlatQueue``, ``MultiPlatQueue``

``pytrsplat.platsettings`` -- Configure plats (size, colors, fonts, etc.)
    classes:    ``Settings``

``pytrsplat.settingseditor`` -- A GUI editor for `platsettings.Settings`
    classes:    ``SettingsEditor`` (NOTE: use the
        ``launch_settings_editor()`` function to use this class, unless
        it is being incorporated into an application.)
    functions:  ``launch_settings_editor()``

``pytrsplat.utils`` -- Misc. utils
    functions:  ``filter_tracts_by_twprge()``
"""


import pytrsplat._constants as _constants

__version__ = _constants.__version__
__versionDate__ = _constants.__versionDate__
__author__ = _constants.__author__
__email__ = _constants.__email__
__license__ = _constants.__license__


def version():
    """Return the current version and version date as a string."""
    return f'v{__version__} - {__versionDate__}'


from pytrsplat.plat import (
    Plat,
    MultiPlat,
    text_to_plats,
)

from pytrsplat.grid import (
    TownshipGrid,
    SectionGrid,
    LotDefinitions,
    TwpLotDefinitions,
    LotDefDB,
    tracts_into_twp_grids,
    plssdesc_to_twp_grids,
)

from pytrsplat.platsettings import Settings
from pytrsplat.settingseditor import SettingsEditor, launch_settings_editor
from pytrsplat.platqueue import PlatQueue, MultiPlatQueue


def launch_app():
    """
    Launch the GUI application.
    """
    from .pytrsplat_app import launch_app
    launch_app()
