# Copyright (c) 2020, James P. Imes. All rights reserved.

"""
A GUI application for converting text of PLSS land descriptions ('legal
descriptions') to plats using the pytrsplat module.
"""

import sys
sys.path.append('../../')

import pytrsplat._constants as _constants
from pytrsplat import version
from pytrsplat.plat_gen._plat import Plat, MultiPlat
from pytrsplat.plat_gen._grid import SectionGrid, LotDefDB
from pytrsplat.plat_gen._platsettings import Settings
from pytrsplat.plat_gen._platqueue import MultiPlatQueue
from pytrsplat._utils import _simplify_lot_number, break_trs

from pytrsplat.gui.settingseditor import SettingsEditor
from pytrsplat.gui.imgdisplay import ScrollResizeDisplay

import pytrs
import pytrs.interface_tools
import pytrs._constants as pytrs_constants
from pytrs import version as pytrs_version

import tkinter as tk
from tkinter.ttk import Combobox, Checkbutton
from tkinter import messagebox, filedialog
from tkinter import Label

from pathlib import Path

from PIL import ImageTk


########################################################################
# Main Application Window
########################################################################

class MainWindow(tk.Tk):

    def __init__(self):
        tk.Tk.__init__(self)
        self.title('pyTRSplat - Text-to-Plat Generator')

        # Store an empty LotDefDB object as `.lddb`
        self.lddb = LotDefDB()

        # Store (initially empty) queue of ad-hoc objects to be added to
        # the _plat(s) -- e.g. SectionGrid, TownshipGrid, etc.
        self.ad_hoc_mpq = MultiPlatQueue()

        # Store a plain list (currently empty) of PLSSDesc objects that
        # will be platted
        self.plssdesc_list = []

        # A tab-notebook for switching between adding descriptions and
        # manually adding QQ's
        self.adder_tabs = tk.ttk.Notebook(self)
        self.adder_tabs.grid(row=1, column=1)

        # A widget for entering land descriptions, configuring parse,
        # loading LotDefDB, etc.
        self.desc_frame = DescFrame(master=self)
        self.adder_tabs.add(
            self.desc_frame, text='Add lands by description text')

        # A widget for adding QQ's manually (into `.ad_hoc_mpq`)
        self.manual_platter = ManualPlatter(
            master=self, mpq_owner=self)
        self.adder_tabs.add(self.manual_platter, text="Add QQ's manually")

        right_side_frame = tk.Frame(self)
        right_side_frame.grid(row=1, column=2, sticky='ns')

        # A widget for displaying a mini preview of the _plat so far
        self.preview_frame = PlatPreview(right_side_frame, preview_owner=self)
        self.preview_frame.grid(row=1, column=2, sticky='n')

        # A widget for output settings / buttons. (Contains the _plat
        # generator at `.output_frame.gen_plat()`
        self.output_frame = OutputFrame(right_side_frame, output_owner=self)
        self.output_frame.grid(row=2, column=2, pady=24, sticky='s')

        # Widget containing 'About' and 'disclaimer' buttons.
        self.about = About(master=self)
        self.about.grid(row=2, column=1, padx=4, pady=4, sticky='sw')

        #################################
        # Configurables:
        #################################

        # Whether to display a pop-up message every time a flawed parse
        # is noticed in the `.desc_frame`
        self.warn_flawed_parse = True

        # When clicking preview/save buttons, warn about any lots that
        # were not defined. If True and any are found, will prompt user
        # to define them now.
        self.warn_unhandled_lots = True

    @property
    def mpq(self):
        """Return a MultiPlatQueue object from the `self.plssdesc_list`
        and `self.ad_hoc_mpq`."""
        mpq = MultiPlatQueue()
        for obj in self.plssdesc_list:
            mpq.queue_add(obj)
        mpq.absorb(self.ad_hoc_mpq)
        return mpq

    def trigger_update_preview(self):
        """Update the preview in `.preview_frame`."""
        self.preview_frame.gen_preview()


########################################################################
# Getting / Parsing / Managing Land Descriptions and loading LotDefDB
########################################################################

class DescFrame(tk.Frame):
    """A frame for getting / clearing text of description to parse and
    add to the _plat, getting LotDefDB from .csv."""
    def __init__(self, master=None):
        tk.Frame.__init__(self, master)
        self.master = master
        if not hasattr(master, 'warn_flawed_parse'):
            master.warn_flawed_parse = True
        # a tk var containing Default config parameters for pytrs parsing.
        self.config_text = tk.StringVar()
        self.config_text.set('')
        self.config_popup_tk = None

        # For getting the PLSS descriptions from user.
        desc_frame = tk.Frame(self)
        desc_frame.grid(row=0, column=1, sticky='n', padx=5, pady=5)

        # For getting .csv file for LotDefDB from user
        lddb_save_frame = tk.Frame(self)
        lddb_save_frame.grid(row=5, column=1, sticky='sw')

        # Button to configure pytrs parameters
        cf_button = tk.Button(
            desc_frame, text='Configure Parse', height=2,
            command=self.cf_btn_clicked)
        cf_button.grid(row=3, column=1, pady=8, sticky='w')

        # Button to commence pytrs parsing (and add resulting PLSSDesc to MPQ)
        parse_button = tk.Button(
            desc_frame, text='Parse Description / Add to Plat', height=2,
            command=self.parse_btn_clicked)
        parse_button.grid(row=3, column=1, pady=8, sticky='e')

        desc_box_header = tk.Label(
            desc_frame, text='Enter one or more land descriptions:')
        desc_box_header.grid(row=1, column=1, sticky='w')

        self.desc_box_entry = tk.Text(desc_frame, width=36, height=9)
        self.desc_box_entry.grid(row=2, column=1)

        # Button to launch description editor
        editor_button = tk.Button(
            desc_frame, text='Description Editor', height=2,
            command=self.editor_btn_clicked)
        editor_button.grid(row=4, column=1, pady=5, sticky='w')

        # Button to clear all PLSSDesc's from the MPQ
        clear_button = tk.Button(
            desc_frame, text='Clear All Descriptions', height=2,
            command=self.clear_btn_clicked)
        clear_button.grid(row=4, column=1, pady=5, sticky='e')

        # Button to load LotDefDB from .csv file
        lddb_button = tk.Button(
            desc_frame, text='Get lot definitions from .csv', height=2,
            command=self.lddb_btn_clicked)
        lddb_button.grid(row=5, column=1, pady=5, sticky='w')

        # Button to view / manually define lots
        ld_editor_btn = tk.Button(
            desc_frame, text='View / define Lots', height=2,
            command=self.manual_lddb_clicked)
        ld_editor_btn.grid(row=5, column=1, pady=5, sticky='e')

        # Our current LotDefEditor toplevel (if any)
        self.lde = None

        self.lddp_fp_text = tk.StringVar(master=master, value='')
        self.lddp_fp_text.set(f"Current lot definitions: [None loaded]")
        lddb_label = tk.Label(desc_frame, textvariable=self.lddp_fp_text)
        lddb_label.grid(row=7, column=1, sticky='w')

        default_lots_frame = tk.Frame(desc_frame)
        default_lots_frame.grid(row=8, column=1, sticky='w')

        self.trust_default_lots = tk.BooleanVar(
            desc_frame, value=True, name='trust_default_lots')
        lots_chkbtn = Checkbutton(
            default_lots_frame, text='Trust Default Lots', onvalue=True,
            offvalue=False, variable=self.trust_default_lots,
            command=self.trigger_update_preview)
        lots_chkbtn.grid(row=1, column=2, sticky='w')

        lots_help_btn = tk.Button(
            default_lots_frame, text='?', padx=4,
            command=self.lots_help_btn_clicked)
        lots_help_btn.grid(
            row=1, column=1, sticky='w')

    def manual_lddb_clicked(self):
        """
        Check if any lots currently exist in the parsed descriptions.
        If so, launch the lot viewer / editor window.
        """
        try:
            self.lde.destroy()
        except:
            pass

        def unpack_tract(tract, lots):
            for lot in tract.lots:
                lots.setdefault(tract.trs, [])
                if lot not in lots[tract.trs]:
                    lots[tract.trs].append(lot)

        # Use tiny settings for speed. Only want the unhandled lots.
        mp = self.master.output_frame.gen_plat(use_tiny=True)

        # Get a unhandled_lots dict, and set it to `lots` variable.
        # (Here we don't care about the first-returned value, a bool.)
        _, lots = self.master.output_frame._check_for_unhandled_lots(
            mp, warn=False, do_not_launch=True)

        for desc_obj in self.master.plssdesc_list:
            for tract in desc_obj:
                unpack_tract(tract, lots)

        if len(lots) == 0:
            messagebox.showinfo(
                'No Lots',
                'There are currently no lots in parsed descriptions. Try '
                'adding one or more land descriptions above.'
            )
            return

        self.lde = LotDefEditor(
            self, top_owner=self.master, target_lddb=self.master.lddb,
            lots=lots)
        self.lde.focus()

    def editor_btn_clicked(self):
        """Launch (or refocus-on) a DescriptionEditor popup window, for
        editing already-added descriptions."""
        if len(self.master.plssdesc_list) == 0:
            messagebox.showinfo(
                'No descriptions',
                'No descriptions to view / edit. Add land descriptions above.')
            return

        # Try grabbing the existing editor window, if it exists. If not,
        # launch a new editor window.
        try:
            self.editor_window.focus()
            self.editor_window.grab_set()
            return
        except:
            pass

        self.editor_window = DescriptionEditor(
            self, plssdesc_list=self.master.plssdesc_list,
            plssdesc_list_owner=self.master)
        self.editor_window.title('pyTRSplat - View / Edit Descriptions')
        self.editor_window.focus()
        self.editor_window.grab_set()

    def cf_btn_clicked(self):
        """
        Config button was clicked; launch popup window to get Config
        parameters from user (results are stored in StringVar
        `self.config_text`).
        """
        try:
            # Kill the previously opened config popup, if any.
            self.config_popup_tk.destroy()
        except:
            pass

        # Open a config popup, and store it to attrib.
        self.config_popup_tk = tk.Toplevel()
        self.config_popup_tk.focus()
        self.config_popup_tk.grab_set()
        self.config_popup_tk.title('Set pyTRS Config Parameters')
        after_prompt = None
        if len(self.master.plssdesc_list) > 0:
            # If the user has already parsed one or more descriptions,
            # we'll give this notice after config parameters are set.
            after_prompt = (
                'NOTE: '
                'The config parameters that have just been set will ONLY '
                'affect descriptions that are parsed AFTER this point. Any '
                'descriptions that have already been parsed and added to '
                'the _plat will NOT be affected by changes to these config '
                'parameters. (To reconfigure already-parsed descriptions, '
                'use the Description Editor.)')
        pc = pytrs.interface_tools.PromptConfig(
            master=self.config_popup_tk, target_var=self.config_text,
            parameters=[
                'default_ns',
                'default_ew',
                'clean_qq',
                'sec_colon_required',
                'sec_colon_cautious',
                'ocr_scrub',
                'segment',
                'sec_within',
                'layout'
            ],
            show_cancel=False, prompt_after_ok=after_prompt, exit_after_ok=True)
        pc.pack(padx=20, pady=10)

    def parse_btn_clicked(self):
        """
        Pull the entered text, and use the chosen config parameters (if
        any) to generate a PLSSDesc object, and add it to the queue to
        _plat.
        """
        config_text = self.config_text.get()
        descrip_text = self.desc_box_entry.get("1.0", "end-1c")

        if len(descrip_text) < 2:
            return

        # Create a PLSSDesc object from the supplied text and parse it using the
        # specified config parameters (if any).
        desc = pytrs.PLSSDesc(
            descrip_text, config=config_text, parse_qq=True)

        if len(desc.e_flags) > 0 and self.master.warn_flawed_parse:
            eFlags = ', '.join(desc.e_flags)
            confirm = tk.messagebox.askokcancel(
                'Flawed Description Identified',
                'One or more apparent flaws was identified when parsing this '
                'description, potentially due to non-standard abbreviations, '
                'typos, etc., or due to limitations in the parsing library:\n\n'
                f"<flag codes:  {eFlags}>"
                '\n\n'
                'The description can still be platted, although results may '
                'not be as intended.\n\n'
                '(The Description Editor can also be used at any time to view '
                '/ edit descriptions, and see additional parsing information.)'
            )

            if not confirm:
                return

        # Add desc to the plssdesc_list
        self.master.plssdesc_list.append(desc)

        # Clear the text from the desc_box_entry
        self.desc_box_entry.delete("1.0", 'end-1c')

        # And update the preview _plat.
        self.trigger_update_preview()

    def trigger_update_preview(self):
        self.master.preview_frame.gen_preview()

    def clear_btn_clicked(self):
        """
        Clear all plats and descriptions (reset to start).
        NOTE: Does NOT clear manually added QQ's.
        """
        prompt = messagebox.askyesno(
            'Confirm?',
            'Delete all added descriptions? (Does not delete manually added '
            "QQ's.)",
            icon='warning')

        if prompt is True:
            # Set the `.plssdesc_list` to an empty list
            self.master.plssdesc_list = []

            # Generate a new preview (which will be an empty _plat)
            self.master.preview_frame.gen_preview()

    def lddb_btn_clicked(self):
        """Prompt user for .csv file containing LotDefDB data. If
        selected, loads from that file into `master.lddb` attribute, and
        replaces the existing LotDefDB in that attribute."""
        lddb_fp = filedialog.askopenfilename(
            initialdir='/',
            filetypes=[("CSV Files", "*.csv")],
            title='CSV containing Lot Definition data...'
        )
        if lddb_fp:
            if lddb_fp.lower().endswith('.csv'):
                try:
                    # Load the LDDB
                    self.master.lddb._import_csv(lddb_fp)

                    # Update the preview window
                    self.master.preview_frame.gen_preview()

                    # Set the label
                    max_chars = 20
                    name = Path(lddb_fp).name
                    if len(name) > max_chars:
                        name = name[:max_chars - 3] + '...'
                    self.lddp_fp_text.set(
                        f"Current lot definitions: {name}")

                except:
                    messagebox.showerror(
                        'Could Not Load File',
                        f"Chosen file '{lddb_fp}' could not be loaded.")
            else:
                messagebox.showerror(
                    '.csv Files Only', 'May only load \'.csv\' files containing '
                                       'lot definitions.')

    def lots_help_btn_clicked(self):
        """Display info about LotDefDB and default lots."""

        msg = (
            "By checking 'Trust Default Lots', this program will interpret "
            "lots in Sections 1 - 7, 18, 19, 30, and 31 as though they are "
            "lots in a 'standard' township, unless the user has otherwise "
            "defined lots for a given section manually (with the 'Define "
            "Lots' function) and/or by loading a .csv file containing lot "
            "definitions (to see how to format such a .csv file, see the "
            "included `SAMPLE_LDDB.csv` and/or the documentation)."
            "\n\n"
            "NOTE: Default lots will ONLY be used where no lots have been "
            "defined for a given section individually or in a loaded .csv "
            "file. (If a .csv file has been loaded, and/or if some lots have "
            "been defined individually, but not any lots for Section 4, "
            "T154N-R97W, then default lots would be used for that Section 4 "
            "-- as long as this box is checked.)"
            "\n\n\n"
            "MORE INFO:\n"
            "A so-called 'standard' township would have been surveyed in such "
            "a way that there are lots along the northern and western "
            "boundaries -- i.e. along the boundaries of Sections 1 - 7, 18, "
            "19, 30, and 31. These lot numbers are predictable (e.g. Lots 1, "
            "2, 3, and 4 in a 'standard' Section 1 correspond with the NE¼NE¼, "
            "NW¼NE¼, NE¼NW¼, and NW¼NW¼, respectively). Every other square in "
            "a 'standard' township is an essentially perfect 40-acre square "
            "called a 'quarter-quarter' (or 'QQ')."
            "\n\n"
            "However, in practice, townships are rarely 'standard'. Natural "
            "features like rivers, lakes, mountains, the curvature of the "
            "earth, etc. -- or faulty surveys -- may result in differently "
            "numbered lots in Sections 1 - 7, 18, 19, 30, and 31; as well as "
            "lots in any other sections."
            "\n\n"
            "'Trust Default Lots' may be useful as a backup option, but "
            "a more accurate _plat can be achieved by defining specific lots "
            "individually with the 'Define Lots' feature, and/or by defining "
            "them in a .csv spreadsheet and loading from that."
        )
        messagebox.showinfo('Default Lots', msg)


########################################################################
# Generating, Displaying, and Controlling Plat Mini-Preview
########################################################################

class PlatPreview(tk.Frame):
    """A frame displaying a preview of the _plat, plus its controls."""

    ###################
    # pytrsplat.settings.Settings object
    ###################
    # Generate a Settings object for the mini-preview, with no
    # margins. (Hard-coded here, rather than creating it as a preset,
    # so that it will never be changed to unexpected settings.)
    PREVIEW_SETTINGS = Settings(preset=None)
    PREVIEW_SETTINGS_NONE = Settings(preset=None)
    for set_obj in [PREVIEW_SETTINGS, PREVIEW_SETTINGS_NONE]:
        set_obj.qq_side = 8
        set_obj.centerbox_wh = 12
        set_obj.sec_line_stroke = 1
        set_obj.qql_stroke = 1
        set_obj.ql_stroke = 1
        set_obj.sec_line_RGBA = (0, 0, 0, 255)
        set_obj.ql_RGBA = (128, 128, 128, 255)
        set_obj.qql_RGBA = (230, 230, 230, 255)
        set_obj.dim = (
            set_obj.qq_side * 4 * 6 + set_obj.sec_line_stroke,
            set_obj.qq_side * 4 * 6 + set_obj.sec_line_stroke)
        set_obj.y_top_marg = 0
        set_obj.set_font('sec', size=11)
        set_obj.write_header = False
        set_obj.write_tracts = False
        set_obj.write_lot_numbers = False

    # When there is nothing to preview, will show a grayed-out dummy _plat.
    PREVIEW_SETTINGS_NONE.sec_line_RGBA = (148, 148, 148, 255)
    PREVIEW_SETTINGS_NONE.secfont_RGBA = (168, 168, 168, 255)
    PREVIEW_SETTINGS_NONE.ql_RGBA = (196, 196, 196, 255)
    PREVIEW_SETTINGS_NONE.centerbox_wh = 14

    def __init__(self, master=None, preview_owner=None):
        tk.Frame.__init__(self, master)
        self.master = master

        if preview_owner is None:
            preview_owner = master
        self.preview_owner = preview_owner

        # A list of Image objects of previews of the plats
        self.previews = []
        # A list of twp/rge (strings) to use as headers for previews of the plats
        self.previews_twprge = []
        # Current index of the preview
        self.preview_index = 0
        # Tracking if we're displaying a dummy (empty _plat) in the preview
        self.dummy_set = False

        # Subframe for handling everything with the _plat, other than getting
        # the PLSS descrips.
        plat_frame = tk.Frame(self)
        plat_frame.grid(row=0, column=2, sticky='n')

        # # Subframe for showing a preview of the _plat, and controls for
        # # left/right
        # plat_preview_frame = tk.Frame(plat_frame)
        # plat_preview_frame._grid(row=1, column=1, sticky='n')

        # Subframe for showing the preview (this one does get stored to
        # self, because it gets updated with a new image periodically.
        self.plat_preview_display_frame = tk.Frame(master=self)
        self.plat_preview_display_frame.grid(row=1, column=1, sticky='n')

        # Subframe for controlling the preview (scroll left/right)
        plat_preview_control_frame = tk.Frame(master=self)
        plat_preview_control_frame.grid(row=2, column=1, sticky='n')

        preview_disp_header = Label(
            self.plat_preview_display_frame, text='Quick Preview')
        preview_disp_header.grid(row=1, column=1, pady=2, sticky='n')

        # A label below the preview image to display T&R
        self.preview_footer_text = tk.StringVar()
        preview_disp_footer = Label(
            self.plat_preview_display_frame,
            textvariable=self.preview_footer_text)
        preview_disp_footer.grid(row=3, column=1, sticky='n')

        self.preview_disp_label = None

        # Update the `self.previews` list (starts as an empty list).
        self.gen_preview()

        # Button to scroll preview right
        preview_right_button = tk.Button(
            plat_preview_control_frame, text='>', height=1, width=8,
            command=self.scroll_preview)
        preview_right_button.grid(
            row=1, column=2, padx=8, pady=5, sticky='n')

        # Button to scroll preview left
        preview_left_button = tk.Button(
            plat_preview_control_frame, text='<', height=1, width=8,
            command=lambda: self.scroll_preview(-1))
        preview_left_button.grid(
            row=1, column=1, padx=8, pady=5, sticky='n')

    def gen_preview(self):
        """Generate a new list of preview plats (Image objects) and set
        it to `self.previews`. (Discards the old previews.) Updates
        `self.dummy_set` as appropriate."""
        mpq = self.preview_owner.mpq
        lddb = self.preview_owner.lddb

        # Get the bool var that decides whether we're supposed to trust
        # default lots (i.e. pass through to `allow_ld_defaults=`)
        trust_default_lots = self.preview_owner.desc_frame.getvar(
            name='trust_default_lots')
        trust_default_lots = bool(trust_default_lots)

        # Create a new MP
        new_preview_mp = MultiPlat.from_queue(
            mpq, settings=self.PREVIEW_SETTINGS, lddb=lddb,
            allow_ld_defaults=trust_default_lots)

        self.dummy_set = False

        # If there's nothing yet in the MPQ, manually create a 'dummy' _plat
        # and append it, so that there's something to show (an empty _plat)
        if len(mpq.keys()) == 0:
            dummy = Plat(settings=self.PREVIEW_SETTINGS_NONE)
            new_preview_mp.plats.append(dummy)
            self.dummy_set = True

        # Output the _plat images to a list, and set to `.previews`
        self.previews = new_preview_mp.output()

        # And create a list of 'twprge' values for each of the images, and
        # set to `.previews_twprge`.
        self.previews_twprge = []
        for plObj in new_preview_mp.plats:
            # Extract the TwpRge in the format '154n97w'.
            tr = plObj.twprge
            # pytrs.TRS object will have error section, but we only need
            # the township and range, to convert it with .pretty_twprge()
            # to 'T154N-R97W'.
            trs_obj = pytrs.TRS(tr)
            self.previews_twprge.append(trs_obj.pretty_twprge())

        # Update the preview display
        self.update_preview_display()

    def update_preview_display(self, index=None):
        """Update the preview image and header in this widget."""

        if index is None:
            index = self.preview_index

        # Pull the image from the `.previews` list, and convert it to
        # `ImageTk.PhotoImage` obj
        if index > len(self.previews) - 1:
            index = 0
            self.preview_index = 0
        img = self.previews[index]
        preview = ImageTk.PhotoImage(img, master=self)

        # Display the preview in this label.
        self.preview_disp_label = Label(
            self.plat_preview_display_frame, image=preview)
        self.preview_disp_label.image = preview
        self.preview_disp_label.grid(row=2, column=1, sticky='n')

        # Also update the footer.
        foot_txt = self.previews_twprge[index]
        foot_txt = f"{foot_txt}   [{index + 1} / {len(self.previews)}]"
        self.preview_footer_text.set(foot_txt)

        # But if we've most recently set a dummy, clear the footer.
        if self.dummy_set:
            self.preview_footer_text.set('[No plats to display.]')

    def scroll_preview(self, direction=1):
        """Scroll the preview left or right. (1 -> right;  -1 -> left).
        Defaults to scrolling right."""
        self.preview_index += direction

        # Wrap the index around, if it goes above or below the length
        # of our previews list.
        self.preview_index %= len(self.previews)
        self.update_preview_display()


########################################################################
# Generating the Plats, Previewing a Final Page, Saving to File
########################################################################

class OutputFrame(tk.Frame):
    """A frame containing output settings, preview button, and save
    button, and corresponding functionality. Also contains the _plat
    generator. (Interacts with the `preview_frame` and `.mpq` of
    `master`."""
    def __init__(self, master=None, output_owner=None):
        tk.Frame.__init__(self, master)
        self.master = master

        if output_owner is None:
            output_owner = master
        self.output_owner = output_owner

        # Most recent custom Settings object, as configured in SettingsEditor
        self.current_custom_settings = None

        ####################################
        # Choosing Plat Settings
        ####################################

        # Subframe for getting the _plat settings from user.
        self.settings_frame = tk.Frame(self)
        self.settings_frame.grid(row=1, column=1, sticky='n')

        self.settings_label = Label(
            self.settings_frame, text='Output settings:')
        self.settings_label.grid(row=2, column=1, pady=3, sticky='e')

        self.avail_settings = Settings.list_presets()
        self.settings_combo = Combobox(self.settings_frame, width=9)
        self.settings_combo['values'] = self.avail_settings
        self.settings_combo.grid(row=2, column=2, sticky='w')
        # Set the combo to 'default' preset. (If that doesn't exist, set to
        # whatever's first in the list.)
        try:
            settings_index = self.avail_settings.index('default')
        except ValueError:
            settings_index = 0
        self.settings_combo.current(settings_index)

        self.current_editor = None
        launch_editor_btn = tk.Button(
            self.settings_frame, text='Customize Settings', padx=3,
            command=self.editor_btn_clicked)
        launch_editor_btn.grid(row=3, column=1, sticky='w')

        ####################################
        # Full Page Preview / Save buttons
        ####################################

        # Subframe for 'save' button and 'show full preview' button
        self.save_full_preview_frame = tk.Frame(self)
        self.save_full_preview_frame.grid(row=2, column=1, sticky='n')

        # Button to show a full-sized version of the preview, using
        # current settings of the master window
        self.preview_full_button = tk.Button(
            self.save_full_preview_frame, text='Page Preview', height=2,
            width=12, command=self.preview_btn_clicked)
        self.preview_full_button.grid(
            row=2, column=1, padx=4, pady=5, sticky='w')

        # Button to save plats
        self.save_button = tk.Button(
            self.save_full_preview_frame, text='Save Plats', height=2,
            width=12, command=self.save_btn_clicked)
        self.save_button.grid(row=2, column=2, padx=4, pady=5, sticky='e')

    def editor_btn_clicked(self):
        """
        Launch a CustomSettingsEditor window.
        :return:
        """
        try:
            self.current_editor.destroy()
        except:
            pass
        self.current_editor = tk.Toplevel(self)
        self.current_editor.title('pyTRSplat - Customize Plat Settings')

        set_obj = self._get_settings(force_settings_return=True)

        editor = CustomSettingsEditor(
            master=self.current_editor, output_frame=self,
            first_settings_obj=set_obj)
        # Pre-fill the 'Load Preset' combo with what was set in the OutputFrame
        editor.load_preset_name.delete(0, tk.END)
        editor.load_preset_name.insert(tk.END, self.settings_combo.get())

        editor.pack()
        self.current_editor.focus()
        self.current_editor.grab_set()

    ####################################
    # Generating the Plat(s)
    ####################################

    def _get_settings(self, force_settings_return=False):
        """
        Get the appropriate Settings object, according to prior user
        input.
        """
        cur_set_name = self.settings_combo.get()
        if cur_set_name == '<customized>':
            set_obj = self.current_custom_settings
        elif cur_set_name in self.avail_settings:
            set_obj = Settings(preset=cur_set_name)
        elif force_settings_return:
            set_obj = Settings(preset=None)
        else:
            tk.messagebox.showerror(
                'Unrecognized Settings Name',
                "Choose one of the available settings. Or use 'Customize "
                "Settings' to configure the plats.")
            self.focus()
            self.grab_set()
            return False

        return set_obj

    def gen_plat(self, use_tiny=False):
        """
        Generate and return the Plat(s).
        :param use_tiny: Whether to use 'tiny' settings, when we don't
        actually care about the output, and just want to process as
        quickly as possible to see what issues would pop up for when we
        eventually create the _plat for real (e.g., unhandled lots).
        """

        if use_tiny:
            set_obj = PlatPreview.PREVIEW_SETTINGS
        else:
            # Get the name of the preset `Settings` object we'll use.
            set_obj = self._get_settings()
        if set_obj is False:
            return

        # Get the bool var that decides whether we're supposed to trust
        # default lots (i.e. pass through to `allow_ld_defaults=`)
        trust_default_lots = self.output_owner.desc_frame.getvar(
            name='trust_default_lots')
        trust_default_lots = bool(trust_default_lots)

        return MultiPlat.from_queue(
            mpq=self.output_owner.mpq, settings=set_obj,
            lddb=self.output_owner.lddb, allow_ld_defaults=trust_default_lots)

    def _check_for_unhandled_lots(self, mp, warn=None, do_not_launch=False):
        """
        Check for any unhandled lots in any of the plats. Raise a
        warning if any are found. (Warning may be disabled in main
        window settings.)
        :param mp: A MultiPlat object.
        :param warn: Whether to warn of discovered unhandled lots and
        ask the user whether to define them now. (If not specified,
        defaults to what is configured in `.warn_unhandled_lots` in main
        app Tk window.) If set to `False`, will automatically launch the
        definer if any undefined lots were identified.
        :param do_not_launch: A bool, whether to simply return what is
        found, without prompting the user to launch the editor or
        warning the user first. (Defaults to False.)
        :return: If user declines to define lots now (or if
        `do_not_launch` is passed as True), returns a 2-tuple:
            First element: bool (whether or not unhandled lots are found
                -- i.e. `True` means there is at least 1 unhandled lot;
            Second element: A dict containing all the unhandled lots,
                keyed by TRS (a string -- i.e. `154n97w01` for Sec 1,
                T154N-R97W), whose values are a list of lots that had
                no definition.
        If the user DOES decide to define lots now, this returns None
        and starts up a series of lot definers.
        """
        confirm = True
        if warn is None:
            warn = self.output_owner.warn_unhandled_lots
            confirm = False

        if do_not_launch:
            warn = False
            confirm = False

        uhl = mp.all_unhandled_lots
        ret_uhl = {}  # the unhandled lots that will be returned (keyed by TRS)
        for twprge, plat_level_uhl in uhl.items():
            for sec_num, sec_uhl in plat_level_uhl.items():
                if len(sec_uhl) > 0:
                    trs = twprge + str(sec_num).rjust(2, '0')
                    ret_uhl[trs] = sec_uhl
                    # TODO: check if it's a 'default' lot
                    #   (i.e. Sections 1-7 etc.)

        uhl_found = len(ret_uhl) > 0
        if uhl_found and warn:
            txt = ''
            for trs, lots in ret_uhl.items():
                txt = f"{txt}\n{trs}: {', '.join(lots)}"
            txt.strip()
            confirm = tk.messagebox.askyesno(
                'Undefined Lots',
                'One or more lots were identified in the parsed '
                'description(s) for which no definitions have been given:\n'
                f"{txt}\n\n"
                'These cannot be depicted on the _plat until defined. '
                'Do so now?'
            )

        if confirm and uhl_found:
            self.lot_definers = SeriesLotDefiner(
                self, top_owner=self.output_owner,
                target_lddb=self.output_owner.lddb, lots_to_define=ret_uhl)
            return None

        return (uhl_found, ret_uhl)

    def preview_btn_clicked(self):
        """Generate the MultiPlat and display one of the plats from it. If
        the desired `index` is greater than the number of plats generated,
        will show the final one."""
        mp = self.gen_plat()
        if mp is None:
            return

        if self.output_owner.warn_unhandled_lots:
            confirm = self._check_for_unhandled_lots(mp)
            if confirm is None:
                return

        if len(mp.plats) == 0:
            messagebox.showinfo(
                'No plats',
                "No plats to preview. Add land descriptions or manually add "
                "QQ's and try again.")
            return

        index = self.output_owner.preview_frame.preview_index
        if index >= len(mp.plats):
            index = len(mp.plats) - 1

        # output() returns a list (in this case, only one page), so grab
        # the first (only) element from it.
        preview_img = mp.output(pages=index)[0]
        preview_window = FullPreviewWindow(
            self, img=preview_img, settings_name=self.settings_combo.get())

    def save_btn_clicked(self):
        """Generate plats and save them to .png or .pdf at user-selected
        filepath."""

        mp = self.gen_plat()
        if mp is None:
            return

        if self.output_owner.warn_unhandled_lots:
            confirm = self._check_for_unhandled_lots(mp)
            if confirm is None:
                return

        if len(mp.plats) == 0:
            messagebox.showinfo(
                'No plats',
                "No plats to save. Add land descriptions or manually add "
                "QQ's and try again.")
            return

        write_it = False
        multi_png = False
        start_dir = '/'
        ext = ''

        # Look at how many images are in the `previews` list to see how
        # many plats there will be.
        num_plats = len(self.output_owner.preview_frame.previews)

        while True:
            save_fp = filedialog.asksaveasfilename(
                initialdir=start_dir,
                filetypes=[("PNG Files", "*.png"), ("PDF Files", "*.pdf")],
                title='Save to PDF or PNG...'
            )

            if save_fp == '':
                break
            else:
                # If we need to re-prompt for filepath, we'll go back to the
                # same directory at least.
                start_dir = str(Path(save_fp).parent)
                stem = str(Path(save_fp).stem)

            if save_fp.lower().endswith('.pdf'):
                write_it = True
                ext = '.pdf'
                break

            elif save_fp.lower().endswith('.png') and num_plats > 1:

                # Generate the warning message, that `.png` will save multiple.
                msg_txt = (
                    'Multiple plats have been generated. When saving to '
                    '.png specifically, each file will be saved separately, '
                    'as follows:\n'
                )
                for i in range(num_plats):
                    msg_txt = f"{msg_txt}\n{stem}_{str(i).rjust(3, '0')}.png"
                    if i == 3 and num_plats > i:
                        msg_txt = msg_txt + '\netc.'
                        break
                msg_txt = msg_txt + '\n\nIt will NOT prompt before overwriting files.'
                msg_txt = msg_txt + '\n\nContinue with saving?'

                confirm = messagebox.askyesno(
                    'Confirm saving to multiple files?', msg_txt)
                if confirm:
                    write_it = True
                    multi_png = True
                    ext = '.png'
                    break
                else:
                    continue

            elif save_fp.lower().endswith('.png'):
                write_it = True
                ext = '.png'
                break

            else:
                messagebox.showerror(
                    '.png and .pdf Files Only',
                    'May only save to \'.pdf\' or \'.png\' files.')

        if not write_it:
            # If the user hasn't confirmed a good filepath,
            return

        if ext == '.png':
            mp.output_to_png(save_fp)
        else:
            mp.output_to_pdf(save_fp)

        open_confirm = tk.messagebox.askyesno(
            'Success!', 'Plat saved. Open file now?')

        if not open_confirm:
            return

        import os
        if not multi_png:
            os.startfile(save_fp)
            return

        # If we saved more than one .png, cut the ext off the fp, add the
        # numeral for the first file, and re-add the ext
        first_png = save_fp[:-4] + '_000.png'
        os.startfile(first_png)


########################################################################
# About and Disclaimer Buttons
########################################################################

class About(tk.Frame):
    """A frame containing the 'About' button, and corresponding
    functionality."""

    def __init__(self, master=None):
        tk.Frame.__init__(self, master)
        self.master = master

        # Button to display 'about' info
        about_button = tk.Button(
            self, text='About', height=1, width=6,
            command=self.about_btn_clicked)
        about_button.grid(row=1, column=1, padx=4, sticky='w')

        # Button to display pyTRS disclaimer
        disclaimer_button = tk.Button(
            self, text='pyTRS disclaimer', height=1,
            command=self.disclaimer_btn_clicked)
        disclaimer_button.grid(row=1, column=2, ipadx=2, padx=4, sticky='e')

    @staticmethod
    def about_btn_clicked():
        splash_info = (
            f"pyTRSplat {version()}\n"
            "Copyright © 2020-2021, James P. Imes, all rights reserved.\n"
            "A program for generating plats from PLSS land descriptions (often "
            "called 'legal descriptions').\n\n"

            f"Built on pyTRS {pytrs_version()}.\n"
            "Copyright © 2020-2021, James P. Imes, all rights reserved.\n"
            "A program for parsing PLSS land descriptions into their component "
            "parts.\n\n"

            f"Contact: <{_constants.__email__}>"

        )
        messagebox.showinfo('pyTRSplat - About', splash_info)

    @staticmethod
    def disclaimer_btn_clicked():
        """Display the disclaimer text from the pytrs module."""
        messagebox.showinfo('pyTRS disclaimer', pytrs_constants.__disclaimer__)


########################################################################
# Preview Full Image Display Window
########################################################################

class FullPreviewWindow(tk.Toplevel):
    """A popup window containing a full-size preview of the requested
    _plat page."""

    def __init__(self, master=None, img=None, settings_name=None):
        tk.Toplevel.__init__(self, master=master)
        self.master = master
        if settings_name is None:
            settings_name = ''
        else:
            settings_name = f'   [settings: {settings_name}]'
        self.title(f"pyTRSplat - Page Preview{settings_name}")

        if img is None:
            self.destroy()
        else:
            display_window = ScrollResizeDisplay(self, img=img)
            display_window.grid(row=1, column=1, sticky='n')


########################################################################
# Generic table rows (used for a couple different subclasses)
########################################################################

class TableRow(tk.Frame):
    """
    A generic row in a table.
    """

    def __init__(
            self, master=None, column_data=None, col_widths=None,
            col_wraps=None, is_header=False, first_tk_col=0):
        """
        :param column_data: A list of strings to write in the columns.
        The number of elements in the list will dictate how many
        columns are created.
        :param col_widths: A list of integers, each representing the
        width for that column. (List must have the same number of
        elements as `column_data`.)
        :param col_wraps: A list of integers, each representing the
        textwrap for that column, in Tkinter 'text units'.
        (List must have the same number of elements as `column_data`.)
        :param is_header: Whether this row contains headers. (Defaults
        to False.)
        :param first_tk_col: The first tkinter _grid column in which to
        place the table (probably only used for TableRow subclasses).
        """
        tk.Frame.__init__(self, master)
        self.master = master
        if column_data is None:
            column_data = []
        if col_widths is None:
            col_widths = [None for _ in column_data]
        if col_wraps is None:
            col_wraps = [None for _ in column_data]

        anchor = 'nw'
        if is_header:
            anchor = 'n'

        for i in range(len(column_data)):
            txt = column_data[i]
            width = col_widths[i]
            wrap = col_wraps[i]
            frm = tk.Frame(
                master=self, highlightbackground='black', highlightthickness=1)
            frm.grid(row=0, column=first_tk_col + i, sticky='ns')
            lbl = tk.Label(
                master=frm, text=txt, anchor=anchor, width=width,
                wraplength=wrap, justify='left')
            lbl.grid(sticky='nw')


########################################################################
# Description Editor Window / Subframes
########################################################################

class DescriptionEditor(tk.Toplevel):
    """
    A widget for viewing, editing, reconfiguring, and reparsing PLSSDesc
    objects that are currently in the MultiPlatQueue.

    NOTE: At init, specify `plssdesc_list_owner=<object>` (e.g., a root
    Tk() object), if that's where the list of updated/saved PLSSDesc
    objects should be stored to (defaults to same as `master`, but may
    need to be a higher-level master).
    """

    SDE_ROW = 1
    SDE_COL = 1

    def __init__(self, master=None, plssdesc_list=None,
                 plssdesc_list_owner=None, **kw):
        tk.Toplevel.__init__(self, master, **kw)
        self.master = master
        if plssdesc_list_owner is None:
            plssdesc_list_owner = master
        self.plssdesc_list_owner = plssdesc_list_owner
        if not hasattr(self.plssdesc_list_owner, 'plssdesc_list'):
            self.plssdesc_list_owner.plssdesc_list = []
        if plssdesc_list is None:
            plssdesc_list = []

        self.plssdesc_list = plssdesc_list

        self.more_info = False

        # The index of the currently displayed SDE
        self.displayed_sde_index = None

        # A list of SingleDescriptionEditor objects (a tk.Frame subclass),
        # one for each PLSSDesc object in `self.plssdesc_list`
        self.editors = self.populate_editors()

        ##############################
        # Control Frame / Buttons
        ##############################
        control_frame = tk.Frame(self)
        control_frame.grid(row=0, column=1, sticky='nesw')

        self.header_lbl = tk.Label(control_frame, text='')
        self.header_lbl.grid(row=0, column=1)

        # Subframe for left/right scrol
        scroll_frame = tk.Frame(control_frame)
        scroll_frame.grid(row=1, column=1)

        # Button to scroll preview right
        scroll_right_button = tk.Button(
            scroll_frame, text='>', height=1, width=8,
            command=self.scroll_sde)
        scroll_right_button.grid(
            row=1, column=2, padx=8, pady=2, sticky='n')

        # Button to scroll preview left
        scroll_left_button = tk.Button(
            scroll_frame, text='<', height=1, width=8,
            command=lambda: self.scroll_sde(-1))
        scroll_left_button.grid(
            row=1, column=1, padx=8, pady=2, sticky='n')

        # Button for toggling more/less info to be displayed
        if self.more_info:
            more_info_btn_txt = 'Show less info'
        else:
            more_info_btn_txt = 'Show more info'
        self.more_info_btn = tk.Button(
            control_frame, text=more_info_btn_txt, width=14,
            command=self.toggle_more_info)
        self.more_info_btn.grid(row=2, column=1, padx=8, pady=5, sticky='n')

        ##############
        # Subframe for the 'big' choices -- Restore / Apply / Delete
        ##############
        bc_padx = 16
        bc_ipadx = 4

        big_choices_frame = tk.Frame(control_frame)
        big_choices_frame.grid(row=1, column=2, padx=15, sticky='n')

        # Button to restore all descriptions (and SDE's) to their original
        # state, as of when this window was opened.
        restore_button = tk.Button(
            big_choices_frame, text='Restore All', height=2, padx=bc_ipadx,
            command=self.restore_clicked)
        restore_button.grid(row=1, column=3, padx=bc_padx, sticky='n')

        # Button to export saved results back to `master.plssdesc_list`
        # and optionally close this popup window
        export_button = tk.Button(
            big_choices_frame, text='Apply Changes to Plat',
            height=2, padx=bc_ipadx, command=self.export_to_master)
        export_button.grid(row=1, column=4, padx=bc_padx, sticky='n')

        # Button to delete current description
        delete_button = tk.Button(
            big_choices_frame, text='Delete This Description', height=2,
            padx=bc_ipadx, command=self.delete_desc_clicked)
        delete_button.grid(row=1, column=5, padx=bc_padx, sticky='n')

        ##############################
        # Currently Displayed SingleDescriptionEditor frame
        ##############################

        self.displayed_sde = None
        if len(self.editors) > 0:
            self.displayed_sde_index = 0
            self.update_displayed_editor(0)
        self.update_header()

    def populate_editors(self):
        """Populate a separate SingleDescriptionEditor object for each
        PLSSDesc object in `self.plssdesc_list`. Return the resulting
        list of SDE objects."""
        editors = []
        for obj in self.plssdesc_list:
            sde = SingleDescriptionEditor(
                self, plssdesc_obj=obj, more_info=self.more_info)
            editors.append(sde)
        return editors

    def update_displayed_editor(self, index=None):
        """Display the SingleDescriptionEditor stored at the specified
        `index`."""
        if index is None:
            index = self.displayed_sde_index

        if index is None:
            # If still None, don't do anything else.
            return

        if self.displayed_sde is not None:
            # If we've already displayed an sde, remove it from the _grid now
            self.displayed_sde.grid_remove()

        # Set the new displayed_sde, and place it on the _grid.
        self.displayed_sde = self.editors[index]
        self.displayed_sde.grid(
            row=DescriptionEditor.SDE_ROW,
            column=DescriptionEditor.SDE_COL,
            sticky='nwse')

    def scroll_sde(self, direction=1):
        """Scroll the SDE left or right. (1 -> right;  -1 -> left).
        Defaults to scrolling right."""
        if self.displayed_sde_index is not None:
            self.displayed_sde_index += direction

        # Wrap the index around, if it goes above or below the length
        # of our previews list.
        if len(self.editors) not in [None, 0]:
            self.displayed_sde_index %= len(self.editors)
        self.update_displayed_editor()
        self.update_header()

    def update_header(self):
        """Update the label showing which index we're currently on."""
        if self.displayed_sde_index is not None:
            header_txt = f"{self.displayed_sde_index + 1} / {len(self.editors)}"
        else:
            header_txt = "[No descriptions to display.]"
        self.header_lbl.config(text=header_txt)

    def toggle_more_info(self):
        """Toggle whether `more_info` should be displayed, and enact the
        change for each SDE."""
        self.more_info = not self.more_info

        for sde in self.editors:
            sde.set_more_info(self.more_info)
            sde.display_new_flags()
            sde.display_new_tracts()

        if self.more_info:
            text = 'Show less info'
        else:
            text = 'Show more info'
        self.more_info_btn.config(text=text)

    def collect_plssdesc_objects(self):
        """Return a new list of the re-saved PLSSDesc objects."""
        new_plssdesc_list = []
        for sde in self.editors:
            new_plssdesc_list.append(sde.cur_plssdesc_obj)
        return new_plssdesc_list

    def export_to_master(self):
        """Collect the updated PLSSDesc objects in a new list, and set it
        to the plssdesc_list_owner's `.plssdesc_list`. Update the _plat
        previews. And close this window."""
        self.plssdesc_list_owner.plssdesc_list = self.collect_plssdesc_objects()
        try:
            self.plssdesc_list_owner.trigger_update_preview()
        except:
            pass

        self.destroy()

    def delete_desc_clicked(self):
        """'Delete' the currently displayed SDE object. (In actuality,
        the SDE object will simply be removed from the `self.editors`
        list. As a result, the PLSSDesc object contained in said SDE
        will not be included when exporting back to owner -- but if this
        window is closed without exporting, this deletion will not have
        had any effect.)"""
        # Current index
        ind = self.displayed_sde_index

        if ind is None:
            return

        confirm = tk.messagebox.askyesno(
            'Confirm Delete', 'Delete this description?')
        self.focus()
        self.grab_set()

        if not confirm:
            return

        # Remove this SDE from the _grid
        self.editors[ind].grid_remove()

        # Remove the SDE from the list of `editors`
        self.editors.pop(ind)

        # Set the index appropriately; and update the display, if there
        # are any left.
        if len(self.editors) == 0:
            self.displayed_sde_index = None
        else:
            self.displayed_sde_index %= len(self.editors)
            self.update_displayed_editor()

        # And update the header.
        self.update_header()

    def restore_clicked(self):
        """Restore all PLSSDesc objects to how they were when this
        window was initialized (including un-deleting any)."""

        if len(self.plssdesc_list) == 0:
            return

        confirm = tk.messagebox.askyesno(
            'Confirm Restore',
            'Discard all changes (including deletions) that have not '
            'yet been applied to the _plat?')
        self.focus()
        self.grab_set()

        if not confirm:
            return

        for sde in self.editors:
            sde.destroy()

        self.editors = self.populate_editors()
        self.displayed_sde = None
        self.displayed_sde_index = None
        if len(self.editors) > 0:
            self.displayed_sde_index = 0
        self.update_displayed_editor()

        self.update_header()


class SingleDescriptionEditor(tk.Frame):
    """A subframe for viewing, editing, reconfiguring, and reparsing a
    single pytrs.PLSSDesc object."""

    # Display colors of text, depending on whether it's original data,
    # edited data that has not yet been activated, or edited data that
    # has been activated but not yet saved
    SAVED_COLOR = 'black'
    EDIT_UNACTIVATED_COLOR = 'red'
    EDIT_UNSAVED_COLOR = 'blue'

    def __init__(
            self, master=None, plssdesc_obj=None, more_info=False,
            display_more_info_btn=False, **kw):
        tk.Frame.__init__(self, master, **kw)
        if plssdesc_obj is None:
            plssdesc_obj = pytrs.PLSSDesc('')
        self.cur_plssdesc_obj = plssdesc_obj
        self._orig_plssdesc_obj = plssdesc_obj

        # Tracking the PLSSDesc object from which we're currently viewing
        # tracts and flags, and whether the displayed data has been 'saved'
        self.current_display_tract_source = plssdesc_obj
        self.current_display_flag_source = plssdesc_obj
        self.current_display_tract_status = 'parsed'
        self.current_display_flag_status = 'parsed'

        # Tracking whether this Editor object has created a new PLSSDesc
        # object (may also be reset to False by the 'Restore' button)
        self.created_new_plssdesc = False

        # The first 'original description' (`.orig_desc`) that had been
        # stored in the PLSSDesc object as of init. (`.orig_desc` may
        # change after this point, but this will not.)
        self._first_orig_desc = plssdesc_obj.orig_desc
        # The new description that we'll use, if we end up replacing
        # our original PLSSDesc object.
        self.new_desc_text = self._first_orig_desc
        self.current_display_desc_status = 'parsed'

        # The pytrs Config text (decompiled from our PLSSDesc obj's
        # `.config` attrib) that was last used to parse the text. Hold
        # onto it to use in case the user hits the 'CANCEL' button in
        # the config_popup.
        cf = plssdesc_obj.config  # currently a pytrs.Config obj
        if not plssdesc_obj.layout_specified:
            # If the layout was NOT specified in `config` param when the
            # PLSSDesc obj was parsed (i.e. layout was deduced), we want
            # to deduce the layout for our replacement PLSSDesc object
            # too, rather than use the layout that this PLSSDesc ended
            # up with
            cf.layout = None
        first_config = cf.decompile_to_text()
        self._last_used_config = first_config

        # The new config parameters that we'll use, if we end up
        # replacing our original PLSSDesc object. (Can be changed by
        # clicking 'Reconfigure' button.)
        self.config_text = tk.StringVar()
        self.config_text.set(self._last_used_config)

        # Frame holding controls and orig description
        control_orig_desc_frame = tk.Frame(self)
        control_orig_desc_frame.grid(row=0, column=0, pady=5, sticky='nws')

        #####################################
        # Edit / Reconfig / Reparse Controls
        #####################################

        # Whether the user wants to see more info on parsed data
        # (e.g., lots/QQ's, warning/error flags)
        self.more_info = more_info

        control_frame = tk.Frame(control_orig_desc_frame)
        control_frame.grid(row=0, column=0, sticky='nw')

        # Keeping track of the config_popup and/or new_desc_pop_up we've
        # lauched from this editor, if any
        self.config_popup_tk = None
        self.new_desc_pop_up_tk = None

        btn_padx = 4

        reconfig_btn = tk.Button(
            control_frame, text='Reconfigure', height=2, padx=2,
            command=self.reconfig_btn_clicked)
        reconfig_btn.grid(row=0, column=0, padx=btn_padx, sticky='n')

        edit_desc_btn = tk.Button(
            control_frame, text='Edit Text', height=2, padx=2,
            command=self.edit_desc_btn_clicked)
        edit_desc_btn.grid(row=0, column=1, padx=btn_padx, sticky='n')

        reparse_btn = tk.Button(
            control_frame, text='Reparse', height=2, padx=2,
            command=self.reparse)
        reparse_btn.grid(row=0, column=2, padx=btn_padx, sticky='n')

        restore_btn = tk.Button(
            control_frame, text='Restore', height=2, padx=2,
            command=self.restore)
        restore_btn.grid(row=0, column=3, padx=btn_padx, sticky='n')

        # We display more info (i.e. lots/QQs, warning/error flags) in
        # the tables, depending on `.more_info`. However, we only show
        # a `Show More/Less Info` button if `display_more_info_btn=True`
        # was specified at init. (Allows control from higher-level
        # widget, but also the option to create a SDE with this
        # functionality.)
        if self.more_info:
            more_info_btn_txt = 'Show less info'
        else:
            more_info_btn_txt = 'Show more info'
        self.more_info_btn = tk.Button(
            control_frame, text=more_info_btn_txt, height=2, width=14,
            command=self.toggle_more_info)
        self.display_more_info_btn = display_more_info_btn
        if display_more_info_btn:
            self.more_info_btn.grid(row=0, column=4, padx=btn_padx, sticky='n')

        #####################################
        # Display
        #####################################

        # Displaying the original description.
        self.orig_desc_frame = tk.Frame(control_orig_desc_frame)
        self.orig_desc_frame.grid(row=2, column=0, padx=btn_padx, sticky='nswe')

        self.orig_desc_lbl_width = 40
        self.orig_desc_lbl_wraplength = 240

        # Orig Descrip
        self.orig_desc_lbl = tk.Label(self.orig_desc_frame, anchor='nw')
        self.orig_desc_lbl.config(
            fg=SingleDescriptionEditor.SAVED_COLOR,
            text=self._first_orig_desc,
            width=self.orig_desc_lbl_width,
            wraplength=self.orig_desc_lbl_wraplength,
            justify='left')
        self.orig_desc_lbl.grid(row=0, column=0, sticky='nw')

        self.pytrs_display_frame = tk.Frame(self)
        self.pytrs_display_frame.grid(row=0, column=3, sticky='n')

        # Variables to configure how/where the TractTable and FlagTable
        # should be placed in the _grid.
        self.tract_table_row_col = (1, 1)
        self.tract_table_padx_pady = (5, 5)
        self.flag_table_row_col = (3, 1)
        self.flag_table_padx_pady = (5, 10)

        # The parsed tracts are displayed in `.tract_table` (set to None
        # here, but initialized as a TractTable obj in `.display_new_tracts`)
        self.tract_table = None
        self.display_new_tracts(
            source_plssdesc=self.cur_plssdesc_obj, status='saved')

        # Warning and Error Flags are displayed in `.flag_table` (set to
        # None here, but initialized as a FlagTable obj in `.display_new_flags`)
        self.flag_table = None
        self.display_new_flags(
            source_plssdesc=self.cur_plssdesc_obj, status='saved')

    def toggle_more_info(self):
        """Toggle whether 'more info' should be displayed, and enact."""
        self.more_info = not self.more_info
        self.set_more_info()

    def set_more_info(self, set_to=None):
        """Set whether 'more info' should be displayed, and enact."""
        if set_to is None:
            set_to = self.more_info
        self.more_info = set_to
        self.display_new_flags()
        self.display_new_tracts()
        if self.more_info:
            text='Show less info'
        else:
            text='Show more info'
        self.more_info_btn.config(text=text)

    def edit_desc_btn_clicked(self):
        """Prompt the user to make edits to the original description."""
        if self.new_desc_pop_up_tk is not None:
            self.new_desc_pop_up_tk.destroy()
        self.new_desc_pop_up_tk = DescTextEditWindow(
            master=self, orig_text=self.new_desc_text)
        self.new_desc_pop_up_tk.focus()
        self.new_desc_pop_up_tk.grab_set()

    def display_new_descrip(self, status='not_activated'):
        """Update the displayed description for the PLSSDesc object
        (pulled from `self.new_desc_text`). If the text has been edited
        but not enacted, set the color to red. If it has been enacted,
        but not yet saved, set to blue. If saved, set to black."""
        if status == 'not_activated':
            text_color = SingleDescriptionEditor.EDIT_UNACTIVATED_COLOR
        elif status == 'not_saved':
            text_color = SingleDescriptionEditor.EDIT_UNSAVED_COLOR
        else:
            text_color = SingleDescriptionEditor.SAVED_COLOR

        self.orig_desc_lbl.config(fg=text_color, text=self.new_desc_text)
        self.current_display_desc_status = status

    def display_new_flags(self, source_plssdesc=None, status=None):

        # If status not specified, get it from `self`. Also update `self`
        # on the status.
        if status is None:
            status = self.current_display_flag_status
        self.current_display_flag_status = status

        if status == 'not_saved':
            text_color = SingleDescriptionEditor.EDIT_UNSAVED_COLOR
        else:
            text_color = SingleDescriptionEditor.SAVED_COLOR

        if source_plssdesc is None:
            source_plssdesc = self.current_display_flag_source

        # Update the tracker, as to which PLSSDesc obj we're displaying
        # tracts from
        self.current_display_flag_source = source_plssdesc

        # Destroy the old flag_table, and replace it with a new one
        if self.flag_table is not None:
            self.flag_table.destroy()
        self.flag_table = FlagTable(
            self.pytrs_display_frame, wflag_list=source_plssdesc.w_flags,
            eflag_list=source_plssdesc.e_flags, more_info=self.more_info)
        if self.more_info:
            # Only if `.more_info==True` do we place this on the _grid.
            self.flag_table.grid(
                row=self.flag_table_row_col[0],
                column=self.flag_table_row_col[1],
                padx=self.flag_table_padx_pady[0],
                pady=self.flag_table_padx_pady[1], sticky='nws')

    def display_new_tracts(self, source_plssdesc=None, status=None):
        """Display the data for the parsed pytrs.Tract in the specified
        `source_plssdesc`."""
        # If status not specified, get it from `self`. Also update `self`
        # on the status.
        if status is None:
            status = self.current_display_tract_status
        self.current_display_tract_status = status

        if status == 'not_saved':
            text_color = SingleDescriptionEditor.EDIT_UNSAVED_COLOR
        else:
            text_color = SingleDescriptionEditor.SAVED_COLOR

        if source_plssdesc is None:
            # Default to pulling the replacement.
            source_plssdesc = self.current_display_tract_source

        # Update the tracker, as to which PLSSDesc obj we're displaying
        # tracts from
        self.current_display_tract_source = source_plssdesc

        # Destroy the old tract_table, and replace it with a new one,
        # using as the tract_list the `.parsed_tracts` from the chosen
        # source PLSSDesc object.
        if self.tract_table is not None:
            self.tract_table.destroy()
        self.tract_table = TractTable(
            self.pytrs_display_frame,
            tract_list=source_plssdesc.tracts, more_info=self.more_info)
        self.tract_table.grid(
            row=self.tract_table_row_col[0],
            column=self.tract_table_row_col[1],
            padx=self.tract_table_padx_pady[0],
            pady=self.tract_table_padx_pady[1], sticky='nw')

    def reparse(self):
        """
        Reparse the pytrs.PLSSDesc object at the specified index in
        `self.plssdesc_list`, using the optionally re-specified `config`
        parameters. (If `config` has not been specified, will use
        whatever was already in the PLSSDesc object.)

        Note: This will create a new PLSSDesc object and set it to
        `self.cur_plssdesc_obj`. Beware lists that contain the original
        PLSSDesc object, as those will NOT be automatically updated with
        this new object.
        """

        # Close any subordinate popups.
        try:
            self.config_popup_tk.destroy()
        except AttributeError:
            pass
        try:
            self.new_desc_pop_up_tk.destroy()
        except AttributeError:
            pass

        config = self.config_text.get()
        if config == 'CANCEL':
            # If the user hit the cancel button in the config popup, use
            # the original config
            config = self._last_used_config
        desc = self.new_desc_text
        d_obj = pytrs.PLSSDesc(desc, config=config, parse_qq=True)
        # Set the main PLSSDesc obj to the new replacement.
        self.cur_plssdesc_obj = d_obj
        # Update our last-used config text (again stripping out layout,
        # if it was deduced, rather than dictated by user)
        cf = d_obj.config  # currently a pytrs.Config obj
        if not d_obj.layout_specified:
            cf.layout = None
        self._last_used_config = cf.decompile_to_text()

        # Update our displays.
        self.display_new_descrip(status='parsed')
        self.display_new_tracts(source_plssdesc=d_obj, status='parsed')
        self.display_new_flags(source_plssdesc=d_obj, status='parsed')
        # And keep track of the fact that we've created a new PLSSDesc obj.
        self.created_new_plssdesc = True

    def restore(self):
        """
        Restore the original pytrs.PLSSDesc object, as it existed at the
        creation of this editor instance.
        """

        confirm = tk.messagebox.askyesno(
            'Confirm Restore',
            'Discard all changes made to this description since opening '
            'this editor window?')
        if not confirm:
            return

        # TODO: Prompt "Are You Sure"

        # Close any subordinate popups.
        try:
            self.config_popup_tk.destroy()
            self.config_popup_tk = None
        except:
            pass
        try:
            self.new_desc_pop_up_tk.destroy()
            self.new_desc_pop_up_tk = None
        except:
            pass

        d_obj = self._orig_plssdesc_obj
        self.cur_plssdesc_obj = d_obj
        self.display_new_tracts(source_plssdesc=d_obj, status='parsed')
        self.display_new_flags(source_plssdesc=d_obj, status='parsed')
        self.created_new_plssdesc = False
        self.new_desc_text = self.cur_plssdesc_obj.orig_desc
        self.display_new_descrip(status='parsed')

    def reconfig_btn_clicked(self):
        """
        Re-Config button was clicked; launch popup window to get Config
        parameters from user (results are stored in StringVar
        `self.config_text`).
        """
        try:
            # Kill the previously opened config popup, if any.
            self.config_popup_tk.destroy()
        except:
            pass

        # Open a config popup, and store it to attrib.
        self.config_popup_tk = tk.Toplevel()
        self.config_popup_tk.focus()
        self.config_popup_tk.grab_set()
        self.config_popup_tk.title('Change pyTRS Config Parameters')
        after_prompt = (
            'NOTE: '
            'The config parameters that have just been set will ONLY '
            'affect THIS description. You MUST hit \'Reparse\' '
            'for these config parameters to have any effect.')
        pc = pytrs.interface_tools.PromptConfig(
            master=self.config_popup_tk, target_var=self.config_text,
            parameters=[
                'default_ns',
                'default_ew',
                'clean_qq',
                'require_colon',
                'ocr_scrub',
                'segment',
                'layout'
            ],
            show_cancel=False, prompt_after_ok=after_prompt, exit_after_ok=True)
        pc.pack(padx=20, pady=10)


class DescTextEditWindow(tk.Toplevel):
    """A pop-up window in which the user may make edits to the text of a
    pytrs.PLSSDesc object."""

    def __init__(self, master=None, orig_text=None, **kw):
        tk.Toplevel.__init__(self, master, **kw)
        self.master = master

        self.orig_text = orig_text

        desc_box_header = tk.Label(
            self, text='Replace existing land description with:')
        desc_box_header.grid(row=1, column=1, sticky='w')

        self.desc_box_entry = tk.Text(self, width=64, height=16)
        self.desc_box_entry.grid(row=2, column=1, padx=4, pady=4)

        # Fill with the text box with the existing text.
        if orig_text is not None:
            self.desc_box_entry.insert(tk.END, orig_text)

        control_frame = tk.Frame(self)
        control_frame.grid(row=3, column=1)
        ok_button = tk.Button(
            control_frame, text='Confirm', width=12,
            command=self.ok_btn_clicked)
        ok_button.grid(row=1, column=2, padx=16, pady=10, sticky='n')

        cancel_button = tk.Button(
            control_frame, text='Cancel', width=12,
            command=self.cancel_btn_clicked)
        cancel_button.grid(row=1, column=1, padx=16, pady=10, sticky='n')

    def ok_btn_clicked(self):
        # Set the new description.
        self.master.new_desc_text = self.desc_box_entry.get("1.0", "end-1c")
        # Display it.
        self.master.display_new_descrip(status='not_activated')
        # Destroy this text pop_up.
        self.master.new_desc_pop_up_tk = None
        self.destroy()

    def cancel_btn_clicked(self):
        if self.orig_text != self.desc_box_entry.get("1.0", "end-1c"):
            # If there were changes made to the text, confirm with user
            # that they should be discarded before destroying the window
            confirm = messagebox.askyesno(
                'Discard changes?',
                "Discard any changes you've made to this text?")
            self.focus()
            self.grab_set()

            if confirm:
                self.destroy()
        else:
            self.destroy()


class TractTable(tk.Frame):
    """
    A frame containing a table of parsed data from a list of
    pytrs.Tract objects.
    """

    trs_col_width = 10
    trs_wraplength = 240

    desc_col_width = 30
    desc_wraplength = 200

    lotqq_col_width = 30
    lotqq_wraplength = 200

    def __init__(
            self, master=None, tract_list=None, more_info=False, **kw):
        """
        :param tract_list: A list of pytrs.Tract objects to display.
        :param more_info: Whether the user wants to display 'more info'.
        In this case, the `.lots_qqs` attribute of each pytrs.Tract
        object is considered 'more info'.
        """
        tk.Frame.__init__(self, master, **kw)
        self.master = master
        if tract_list is None:
            tract_list = []
        self.tract_list = tract_list

        self.col_widths = [self.trs_col_width, self.desc_col_width]
        self.col_wraps = [self.trs_wraplength, self.desc_wraplength]

        if more_info:
            self.col_widths.append(self.lotqq_col_width)
            self.col_wraps.append(self.lotqq_wraplength)

        i = 0

        headers = ['TRS', 'Description']
        if more_info:
            headers = ['TRS', 'Description', 'Identified Lots / QQs']
        tr = TableRow(
            self, column_data=headers, col_widths=self.col_widths,
            col_wraps=self.col_wraps, is_header=True)
        tr.grid(row=i, column=0, sticky='ew')
        i += 1

        rows = []

        for tract_obj in tract_list:
            new_row = [tract_obj.trs, tract_obj.desc]
            if more_info:
                new_row.append(', '.join(tract_obj.lots_qqs))
            rows.append(new_row)

        for row in rows:
            tr = TableRow(
                self, column_data=row, col_widths=self.col_widths,
                col_wraps=self.col_wraps)
            tr.grid(row=i, column=0, sticky='ew')
            i += 1


class FlagTable(tk.Frame):
    """A frame containing a table of warning/error flags from a parsed
    pytrs.PLSSDesc object."""

    flag_col_width = 35
    flag_wraplength = 240

    col_widths = [flag_col_width, flag_col_width]
    col_wraps = [flag_wraplength, flag_wraplength]

    def __init__(
            self, master=None, wflag_list=None, eflag_list=None,
            more_info=False, **kw):
        """
        :param more_info: Whether the user wants to display 'more info'.
        In this case, all flag data is considered 'more info'.
        :param wflag_list: The `.w_flags` attribute from a
        pytrs.PLSSDesc object to display.
        :param eflag_list: The `.e_flags` attribute from a
        pytrs.PLSSDesc object to display.
        """
        tk.Frame.__init__(self, master, **kw)
        self.master = master

        if not more_info:
            return

        if wflag_list is None:
            wflag_list = ['None']
        elif len(wflag_list) == 0:
            wflag_list = ['None']

        if eflag_list is None:
            eflag_list = ['None']
        elif len(eflag_list) == 0:
            eflag_list = ['None']

        headers = ['Warning Flags', 'Error Flags']
        row_data = [', '.join(wflag_list), ', '.join(eflag_list)]

        i = 0
        tr = TableRow(
            self, column_data=headers, col_widths=self.col_widths,
            col_wraps=self.col_wraps, is_header=True)
        tr.grid(row=i, column=0, sticky='ew')
        i += 1
        tr = TableRow(
            self, column_data=row_data, col_widths=self.col_widths,
            col_wraps=self.col_wraps, is_header=True)
        tr.grid(row=i, column=0, sticky='ew')


########################################################################
# Plat Settings Editor
########################################################################

class CustomSettingsEditor(SettingsEditor):
    """
    An editor for configuring _plat settings, somewhat customized for
    this application.
    """
    def __init__(self, master=None, output_frame=None, first_settings_obj=None,
            show_save_preset=True, show_load_preset=True,
            show_save_custom=False, show_load_custom=False):
        SettingsEditor.__init__(
            self, master, first_settings_obj=first_settings_obj, show_ok=True,
            show_save_preset=show_save_preset, show_load_preset=show_load_preset,
            show_save_custom=show_save_custom, show_load_custom=show_load_custom)
        self.master = master

        # Output frame is where the resulting data should be stored.
        self.output_frame = output_frame
        self.ok_button.config(text='Update Plat With These Settings')

    def ok_btn_clicked(self):
        """
        Compile the Settings object and pass it to the main window.
        """
        set_obj = self.editor.compile_settings()
        if set_obj is False:
            return
        output_frame = self.output_frame
        output_frame.current_custom_settings = set_obj

        # Update the displayed presets in the output frame
        output_frame.avail_settings = Settings.list_presets()
        output_frame.avail_settings.append('<customized>')
        output_frame.settings_combo['values'] = output_frame.avail_settings
        output_frame.settings_combo.current(len(output_frame.avail_settings) - 1)

        # Destroy the toplevel containing this frame.
        self.master.destroy()


########################################################################
# On-The-Fly Lot Definitions
########################################################################

class SectionFiller(tk.Frame):
    """
    A frame with 4x4 button _grid for manually turning on/off QQ's.
    """
    def __init__(
            self, master=None, sec=0, twp='', rge='', trs='', ld=None,
            allow_ld_defaults=False, button_on_text='X'):
        """
        Specify EITHER `trs` OR `sec`, `twp`, and `rge`. If both sets
        are specified, will use `trs` only.

        :param ld: Same purpose as for ``pytrsplat._grid.SectionGrid``.
        :param allow_ld_defaults: Same purpose as for ``SectionGrid``.
        :param button_on_text: Character that should be displayed inside
        a QQ button when it's clicked.
        """
        tk.Frame.__init__(self, master)
        self.master = master

        self.go_btn = tk.Button(self, text='Go', command=self.go_btn_clicked)
        self.go_btn.grid(row=0, column=1)

        if trs != '':
            self.sec_grid = SectionGrid.from_trs(
                trs, ld=ld, allow_ld_defaults=allow_ld_defaults)
        else:
            self.sec_grid = SectionGrid(
                sec, twp, rge, ld=ld, allow_ld_defaults=allow_ld_defaults)

        self.twprge = self.sec_grid.twprge
        self.sec = self.sec_grid.sec
        self.trs = self.sec_grid.trs

        grid_frame = tk.Frame(self)
        grid_frame.grid(row=3, column=1, sticky='n')
        self.buttons = []
        for k, v in self.sec_grid.qq_grid.items():
            btn = self._QQButton(
                grid_frame, qq=k, qq_dict=v, on_text=button_on_text)
            self.buttons.append(btn)

    def go_btn_clicked(self):
        """
        Customizable method. Redefine this method depending on
        application. Gets called any time a QQ button gets clicked.
        """
        pass

    def qq_btn_clicked(self, qq_name):
        """
        Customizable method. Redefine this method depending on
        application. Gets called any time a QQ button gets clicked.

        :param qq_name: The name of the QQ button that was clicked
            (e.g., 'NENE')
        """
        pass

    class _QQButton(tk.Button):
        """
        A button for toggling a QQ.
        """
        W = 2
        H = 1
        def __init__(self, master=None, qq='', qq_dict=None, on_text='X', **kw):
            tk.Button.__init__(self, master, **kw)
            self.master = master
            self.qq = qq
            self.on_text = on_text
            self.qq_dict = qq_dict
            self.grid(row=qq_dict['coord'][1], column=qq_dict['coord'][0])
            self.config(command=self.toggle, width=self.W, height=self.H)
            self.config(text=self.on_text * self.qq_dict['val'])

        def toggle(self):
            self.qq_dict['val'] = (self.qq_dict['val'] + 1) % 2
            self.config(text=self.on_text * self.qq_dict['val'])
            self.master.master.qq_btn_clicked(self.qq)


class SeriesLotDefiner(tk.Toplevel):
    def __init__(
            self, master=None, top_owner=None, target_lddb=None,
            lots_to_define=None):
        """
        :param top_owner: The main application, which contains a
        .trigger_update_preview() method.
        :param target_lddb: A LotDefDB object that should be modified.
        :param lots_to_define: A dict, specifying which lots need to be
        defined, in this format:   <trs key> -> <list of lots>
            ex: {'154n97w01': ['L1, 'L2'], '154n97w02': ['L1', 'L3']}
        """
        tk.Toplevel.__init__(self, master)
        # The LotDefDB object that will be updated:
        self.target_lddb = target_lddb

        if top_owner is None:
            top_owner = master
        self.top_owner = top_owner

        # All of the lots we need to define -- i.e. an `unhandled_lots`
        # dict (`ret_uhl`) from `OutputFrame._check_for_unhandled_lots()`
        self.lots_to_define = lots_to_define
        self.cur_definer = None
        self.trs_keys = list(lots_to_define.keys())
        self.cur_trs = None
        self.cur_lots = []

        self.next_one()

    def next_one(self):
        try:
            self.cur_definer.destroy()
        except:
            pass

        if len(self.cur_lots) == 0:
            if len(self.trs_keys) == 0:
                self.done()
                return None
            self.cur_trs = self.trs_keys.pop(0)
            self.cur_lots = self.lots_to_define[self.cur_trs]

        lot = self.cur_lots.pop(0)
        self.cur_definer = SingleLotDefiner(
            self, target_lddb=self.target_lddb, trs=self.cur_trs, lot_num=lot)
        self.cur_definer.cancel_btn.grid(row=7, column=1)
        self.cur_definer.grid(row=0, column=0, padx=14, pady=14, sticky='nesw')
        self.cur_definer.focus()
        self.cur_definer.grab_set()

    def done(self):
        # TODO: Maybe a success message?
        self.top_owner.trigger_update_preview()
        self.destroy()

    def canceled(self):
        # TODO: Maybe a confirm / abandon message?
        self.top_owner.trigger_update_preview()
        self.destroy()


class LotRedefiner(SeriesLotDefiner):
    """
    A class for RE-defining lots already in a LotDefDB object.
    """

    def __init__(
            self, master=None, top_owner=None, target_lddb=None,
            trs=None, lot=0, uid=None):
        lots_to_define = {trs: [lot]}
        SeriesLotDefiner.__init__(
            self, master=master, top_owner=top_owner, target_lddb=target_lddb,
            lots_to_define=lots_to_define)

        # A bit hack-ish, but remove the "Leave Undefined" button.
        self.cur_definer.leaveit_btn.grid_forget()

        self.uid = uid

    def done(self):
        if hasattr(self.master, 'update_table'):
            self.master.update_table(self.uid)
        self.destroy()

    def canceled(self):
        self.destroy()


class SingleLotDefiner(SectionFiller):
    """
    A simple frame for defining lots on the fly.
    """
    def __init__(
            self, master=None, target_lddb=None, sec=0, twp='', rge='', trs='',
            lot_num=0):
        """
        Specify EITHER `trs` OR `sec`, `twp`, and `rge`. If both sets
        are specified, will use `trs` only.

        :param target_lddb: The LotDefDB object to be updated.
        :param button_on_text: Character that should be displayed inside
        a QQ button when it's clicked.
        """
        lot_num = _simplify_lot_number(lot_num)

        SectionFiller.__init__(
            self, master, sec=sec, twp=twp, rge=rge, trs=trs,
            button_on_text=lot_num)
        self.lot_num = lot_num

        if not isinstance(target_lddb, LotDefDB):
            raise ValueError(
                'Existing LotDefDB object must be provided as `lddb`')
        self.target_lddb = target_lddb

        self.go_btn.config(text='Confirm Lot Definition')
        lbl = Label(self, text=f"{self.trs}: Lot {lot_num}")
        lbl.grid(row=1, column=1)

        self.leaveit_btn = tk.Button(
            self, text='Leave Undefined', command=self.leaveit_btn_clicked)
        self.leaveit_btn.grid(row=5, column=1)

        self.cancel_btn = tk.Button(
            self, text='Cancel', command=self.cancel_btn_clicked)

    def go_btn_clicked(self):
        """
        Set or update the definition of this lot in the target_lddb.
        """

        filled = self.sec_grid.filled_qqs()
        if len(filled) == 0:
            confirm = tk.messagebox.askokcancel(
                'Are you sure?', "Leave this lot undefined?")

            if not confirm:
                return None

        definition = ','.join(filled)

        tld = self.target_lddb.get_tld(self.twprge, force_tld_return=True)

        try:
            sec_num = int(self.sec)
        except:
            sec_num = 0
        ld = tld.get_ld(sec_num, force_ld_return=True)
        ld.set_lot(self.lot_num, definition)
        tld.set_section(sec_num, ld)
        self.target_lddb.set_twp(self.twprge, tld)

        if hasattr(self.master, 'next_one'):
            self.master.next_one()

    def leaveit_btn_clicked(self):
        if hasattr(self.master, 'next_one'):
            self.master.next_one()

    def cancel_btn_clicked(self):
        if hasattr(self.master, 'canceled'):
            self.master.canceled()


class LotDefEditor(tk.Toplevel):
    """
    A frame for viewing, editing, and deleting LotDefinitions.
    """
    def __init__(
            self, master=None, top_owner=None, target_lddb=None, lots=None):
        """
        :param top_owner: The main application, which contains a
        .trigger_update_preview() method.
        :param target_lddb: A LotDefDB object that should be modified.
        :param lots: A dict, keyed by TRS (e.g., '154n9701'), and whose
        values are a list of lots that should be viewed. See example:
            sample_lots = {
                '154n97w25': ['L5', 'L8'],
                '154n97w01': ['L1', 'L3'],
                '155n97w04': ['L1', 'L2', 'L3', 'L4']
            }
        """
        tk.Toplevel.__init__(self, master)
        self.master = master
        self.target_lddb = target_lddb
        self.lots = lots.copy()
        self.orig_lots = lots
        self.top_owner = top_owner

        # The current LotDefEditor (if any).
        self.lde = None

        control_frm = tk.Frame(self)
        control_frm.grid(row=0, column=0, sticky='ns')

        define_all_btn = tk.Button(
            control_frm, text='Define All Remaining Lots',
            command=self.define_all_lots)
        define_all_btn.grid(row=0, column=1, padx=4, pady=4, sticky='ns')

        display_entire_lddb_btn = tk.Button(
            control_frm, text='Display All (SLOW)',
            command=self.toggle_all_lddb)
        display_entire_lddb_btn.grid(
            row=0, column=2, padx=4, pady=4, sticky='ns')

        del_btn = tk.Button(
            control_frm, text='Delete All Lot Definitions',
            command=self.del_btn_clicked)
        del_btn.grid(row=0, column=3, padx=4, pady=4, sticky='ns')

        close_btn = tk.Button(
            control_frm, text='Close Editor', command=self.close_btn_clicked)
        close_btn.grid(row=0, column=4, padx=4, pady=4, sticky='ns')

        # Our LotDefTable object, which will be populated shortly.
        self.table = None

        # Where to place the table in the _grid
        self.table_row = 1
        self.table_column = 0

        # Populate the table.
        self.gen_new_table()

    def toggle_all_lddb(self):
        """
        Include the entirety of the LotDefDB in the table.
        """
        confirm = tk.messagebox.askokcancel(
            'WARNING',
            "Viewing ALL lot definitions can be very slow if there are "
            "too many defined lots. It may be more efficient to view and edit "
            "numerous lot definitions externally in a .csv file, and then load "
            "that file here.\n\n"
            "Display all lots now?")

        self.focus()

        if not confirm:
            return None

        for twprge, tld in self.target_lddb.items():
            for sec, ld in tld.items():
                trs = f"{twprge}{str(sec).rjust(2, '0')}"
                self.lots.setdefault(trs, [])
                lots = list(ld.keys())
                for lot in lots:
                    if lot not in self.lots[trs]:
                        self.lots[trs].append(lot)
        self.gen_new_table()

    def del_btn_clicked(self):
        """
        Remove all items from the LotDefDB. (Does not actually destroy
        the dict values; just pops their keys from the dict.)
        """
        confirm = tk.messagebox.askokcancel(
            'Are you sure?', "Delete ALL current lot definitions?")

        self.focus()

        if not confirm:
            return None

        for i in range(len(self.target_lddb.keys())):
            self.target_lddb.pop(list(self.target_lddb.keys())[0], None)

        self.lots = self.orig_lots.copy()

        self.gen_new_table()

        self.top_owner.trigger_update_preview()

    def close_btn_clicked(self):
        self.destroy()

    def gen_new_table(self):
        """
        Generate a new LotDefTable for the lots.
        """
        try:
            self.table.destroy()
        except:
            pass

        self.table = LotDefTable(
            self, top_owner=self.top_owner, lots=self.lots,
            target_lddb=self.target_lddb)
        self.table.grid(
            row=self.table_row, column=self.table_column, sticky='nesw',
            padx=5, pady=5)

    def define_all_lots(self):
        """
        Define any lots that have not already been defined, one-by-one.
        """

        def no_lots():
            messagebox.showinfo(
                'No lots to define',
                "All lots have been defined. Click the respective edit buttons "
                "to re-define lots."
            )

        try:
            self.lde.destroy()
        except:
            pass

        if self.table is None:
            no_lots()
            return

        ld_dict = self.table.ld_dict
        if ld_dict is None:
            no_lots()
            return

        # Extract unhandled lots from the ld_dict (generated in the
        # LotDefTable object)
        uhl = {}
        for k, v in ld_dict.items():
            if v['definition'] != 'Undefined':
                continue
            trs = v['trs']
            lot = v['lot']
            uhl.setdefault(trs, [])
            uhl[trs].append(lot)

        if len(uhl) == 0:
            no_lots()
            return

        self.lde = LotDefEditor.TableSeriesDefiner(
            self, top_owner=self.top_owner, target_lddb=self.target_lddb,
            lots_to_define=uhl)

    class TableSeriesDefiner(SeriesLotDefiner):
        """
        A SeriesLotDefiner with slightly modified behavior for cancel
        and after completion.
        """

        def __init__(
                self, master=None, top_owner=None, target_lddb=None,
                lots_to_define=None):
            SeriesLotDefiner.__init__(
                self, master=master, top_owner=top_owner,
                target_lddb=target_lddb, lots_to_define=lots_to_define)

            # A bit hack-ish, but remove the "Leave Undefined" button.
            self.cur_definer.leaveit_btn.grid_forget()

            # These methods have the same functionality for this object.
            self.canceled = self.done

        def done(self):
            self.master.gen_new_table()
            try:
                self.top_owner.trigger_update_preview()
            except:
                pass
            self.destroy()


class LDTableRow(TableRow):
    """
    A TableRow object with added "Edit" and "Delete" buttons, specific
    to the lot definition editor.
    """

    def __init__(
            self, master=None, control_owner=None, column_data=None,
            col_widths=None, col_wraps=None, is_header=False, uid=None):
        """
        All parameters are the same as for TableRow, except:
        :param uid: The unique identifier for a lot (ex: '154n97w01_L1')
        :param control_owner: The tkinter object that controls this obj,
        and which has `.edit_btn_clicked()` and `.del_btn_clicked()`
        methods.
        """
        TableRow.__init__(
            self, master, column_data, col_widths, col_wraps, is_header,
            first_tk_col=2)
        self.uid = uid
        self.control_owner = control_owner

        if not is_header:
            ed_btn = tk.Button(
                self, text='Edit', width=5, command=self.edit_btn_clicked)
            del_btn = tk.Button(
                self, text='Delete', width=5, command=self.del_btn_clicked)
            ed_btn.grid(row=0, column=0, padx=4, sticky='ns')
            del_btn.grid(row=0, column=5, padx=4, sticky='ns')

    def edit_btn_clicked(self):
        self.control_owner.edit_btn_clicked(self.uid)

    def del_btn_clicked(self):
        self.control_owner.del_btn_clicked(self.uid)


class LotDefTable(tk.Frame):
    """
    A frame containing a table of LotDefinitions and edit/delete
    buttons.
    """

    trs_col_width = 12
    lot_name_col_width = 6
    ld_col_width = 35
    ld_wraplength = 240
    col_width = [trs_col_width, lot_name_col_width, ld_col_width]
    col_wrap = [None, None, ld_wraplength]
    max_rows_per_page = 15

    # The tk _grid column in the LotDefTable frame holding TableRow objs
    tbrow_col = 2

    def __init__(
            self, master=None, top_owner=None, lots=None, target_lddb=None,
            **kw):
        """
        :param lots: A dict, keyed by TRS (e.g., '154n9701'), and whose
        values are a list of lots that should be viewed. See example:
            sample_lots = {
                '154n97w25': ['L5', 'L8'],
                '154n97w01': ['L1', 'L3'],
                '155n97w04': ['L1', 'L2', 'L3', 'L4']
            }

        Note: This is the same structure as an 'unhandled lots' dict
        generated by the `MultiPlat.all_unhandled_lots` property.
        :param target_lddb: The LotDefDB object whose definitions should
        be displayed.
        """
        tk.Frame.__init__(self, master, **kw)
        self.master = master
        self.btn = tk.Button(text='Edit')

        if top_owner is None:
            top_owner = master
        self.top_owner = top_owner

        ###################3
        # Scroll frame

        control_frame = tk.Frame(self)
        control_frame.grid(row=0, column=1)

        # Subframe for left/right scrol
        scroll_frame = tk.Frame(control_frame)
        scroll_frame.grid(row=1, column=1)

        self.header_lbl = tk.Label(control_frame, text='')
        self.header_lbl.grid(row=0, column=1)

        # Button to scroll preview right
        scroll_right_button = tk.Button(
            scroll_frame, text='>', height=1, width=8,
            command=self.scroll_page)
        scroll_right_button.grid(
            row=1, column=2, padx=8, pady=2, sticky='n')

        # Button to scroll preview left
        scroll_left_button = tk.Button(
            scroll_frame, text='<', height=1, width=8,
            command=lambda: self.scroll_page(-1))
        scroll_left_button.grid(
            row=1, column=1, padx=8, pady=2, sticky='n')

        ##################
        # Gen pages
        ##################

        # A dict of pages (i.e. Frames), one of which is displayed at a time;
        # keyed by incremented ints, starting at 0
        self.pages = {}
        # The index of the currently displayed page.
        self.page_index = None
        # The current page (Frame) itself.
        self.current_page = None

        self.display_frame = tk.Frame(self)
        self.display_frame.grid(row=2, column=1, sticky='nesw')

        # A dict for keeping track of each TableRow, which lot definitions
        # it corresponds to, where to find it in the tk _grid, etc. Keyed
        # by unique ID in the format of TRS_lotnumber (ex: '154n97w01_L1')
        self.ld_dict = {}

        # The current LotRefiner object (if any)
        self.current_redefiner = None

        # Width and wrap configs for the table display

        if lots is None:
            lots = {}

        if target_lddb is None:
            target_lddb = LotDefDB()

        self.target_lddb = target_lddb

        uid_list = []

        def gen_header(page_num: int):
            """
            Generate a header for a new page.
            """

            uid = f"headers_{page_num}"
            header_data = ['Twp/Rge/Sec', 'Lot', 'Definition']
            self.ld_dict[uid] = {}
            self.ld_dict[uid]['row_data'] = header_data
            self.ld_dict[uid]['row_num'] = 0
            self.ld_dict[uid]['definition'] = 'na_headers'
            self.ld_dict[uid]['page'] = page_num
            uid_list.append(uid)

        i = 0
        for trs, lot_list in lots.items():
            ld = self.target_lddb.trs(trs)
            for lot in lot_list:
                definition = 'Undefined'
                if ld is not None:
                    definition = ld.get(lot, 'Undefined')
                # 'unique ID' to serve as dict key -- i.e. '154n97w01_L1'
                uid = f"{trs}_{lot}"
                uid_list.append(uid)

                # TODO: Refactor to use pytrs.TRS class
                twp, rge, sec = break_trs(trs)
                try:
                    sec = int(sec)
                except ValueError:
                    sec = 0

                self.ld_dict[uid] = {}
                self.ld_dict[uid]['ld'] = ld
                self.ld_dict[uid]['row_data'] = [trs, lot, definition]
                self.ld_dict[uid]['row_num'] = i % LotDefTable.max_rows_per_page + 1
                self.ld_dict[uid]['page'] = i // LotDefTable.max_rows_per_page
                self.ld_dict[uid]['twprge'] = twp + rge
                self.ld_dict[uid]['sec'] = sec
                self.ld_dict[uid]['trs'] = trs
                self.ld_dict[uid]['lot'] = lot
                self.ld_dict[uid]['definition'] = definition
                i += 1

        # Subtract the last one for an accurate total.
        i -= 1

        for page_num in range(i//LotDefTable.max_rows_per_page + 1):
            gen_header(page_num)
            new_frame = tk.Frame(self.display_frame)
            self.pages[page_num] = new_frame

        start_row = 2
        for uid in uid_list:
            # Generate a LDTableRow for each
            table_row_num = self.ld_dict[uid]['row_num']
            self.ld_dict[uid]['grid_row'] = table_row_num + start_row
            self.ld_dict[uid]['grid_col'] = self.tbrow_col
            self.gen_tablerow(uid)

        if len(self.pages) > 0:
            self.page_index = 0
            self.update_displayed_page()

    def scroll_page(self, direction=1):
        """Scroll the SDE left or right. (1 -> right;  -1 -> left).
        Defaults to scrolling right."""
        if self.page_index is not None:
            self.page_index += direction

        # Wrap the index around, if it goes above or below the length
        # of our previews list.
        if len(self.pages) not in [None, 0]:
            self.page_index %= len(self.pages)
        self.update_displayed_page()

    def update_displayed_page(self, page_index=None):
        """Display the SingleDescriptionEditor stored at the specified
        `index`."""
        if page_index is None:
            page_index = self.page_index

        if page_index is None:
            # If still None, don't do anything else.
            return

        if self.current_page is not None:
            # If we've already displayed an sde, remove it from the _grid now
            self.current_page.grid_remove()

        # Set the new page, and place it on the _grid.
        self.current_page = self.pages[page_index]
        self.current_page.grid( row=0, column=0, sticky='nwse')
        self.update_header()

    def update_header(self):
        """Update the label showing which index we're currently on."""
        if self.page_index is not None:
            header_txt = f"{self.page_index + 1} / {len(self.pages)}"
        else:
            header_txt = "[No lots to display.]"
        self.header_lbl.config(text=header_txt)

    def gen_tablerow(self, uid, page=None, row_data=None):
        """
        Generate a row in the table for the lot definition represented
        by the unique ID `uid`.
        :param uid: The unique ID of a lot, i.e. a key in `self.ld_dict`
        :param row_data: A list of strings to write for this row. (Leave
        unspecified, unless updating this row. If not specified, will
        use the data previously generated, e.g., at init.)
        """
        if row_data is None:
            row_data = self.ld_dict[uid]['row_data']
        if page is None:
            page = self.ld_dict[uid]['page']
        is_header = self.ld_dict[uid]['row_num'] == 0
        row = self.ld_dict[uid]['row_num']
        col = self.ld_dict[uid]['grid_col']
        self.ld_dict[uid]['tablerow'] = LDTableRow(
            master=self.pages[page], control_owner=self, column_data=row_data,
            col_widths=self.col_width,
            col_wraps=self.col_wrap, is_header=is_header, uid=uid)
        self.ld_dict[uid]['tablerow'].grid(row=row, column=col, sticky='ns')

    def edit_btn_clicked(self, uid):
        """
        Launch an editor for a target lot.

        :param uid: A key from `self.ld_dict`.
        """
        # Close the current redefiner, if any.
        try:
            self.current_redefiner.destroy()
        except:
            pass

        # Launch a new redefiner for this lot.
        self.current_redefiner = LotRedefiner(
            self, target_lddb=self.target_lddb, trs=self.ld_dict[uid]['trs'],
            lot=self.ld_dict[uid]['lot'], top_owner=self.top_owner, uid=uid)

    def del_btn_clicked(self, uid):
        """
        Delete the lot definition for this lot from the LDDB.
        """

        trs = self.ld_dict[uid]['trs']
        lot = self.ld_dict[uid]['lot']
        cur_definition = self.ld_dict[uid]['definition']
        ld = self.target_lddb.trs(trs)
        if ld is None or cur_definition == 'Undefined':
            return None

        confirm = tk.messagebox.askokcancel(
            'Are you sure?',
            f"Delete lot definition for {trs}: {lot}?"
        )

        self.focus()

        if not confirm:
            return None

        # Remove this key from the ld
        ld.pop(lot, None)

        # If there are no more lots for this section in the LotDefinitions,
        # let's remove the LotDefinitions from the LDDB (which would optionally
        # allow default lot definitions to take over).
        if len(ld.keys()) == 0:
            twprge = self.ld_dict[uid]['twprge']
            sec = self.ld_dict[uid]['sec']
            tld = self.target_lddb.get_tld(twprge)
            # tld should never be None here, but just in case...
            if tld is not None:
                # Remove this section as key.
                tld.pop(sec, None)

        self.ld_dict[uid]['row_data'] = [trs, lot, 'Undefined']
        self.update_table(uid)
        self.top_owner.trigger_update_preview()

    def update_table(self, uid):
        """
        Update the displayed table with the new definitions for the lot
        represented by the unique ID `uid`.
        """
        self.ld_dict[uid]['tablerow'].destroy()
        d = self.ld_dict[uid]
        trs = d['trs']
        lot = d['lot']
        sec_num = d['sec']
        definition = 'Undefined'

        tld = self.target_lddb.get_tld(d['twprge'], force_tld_return=False)
        if tld is not None:
            ld = tld.get_ld(sec_num, force_ld_return=True)
            definition = ld.get(lot, 'Undefined')

        new_row_data = [trs, lot, definition]
        self.ld_dict[uid]['row_data'] = new_row_data
        self.ld_dict[uid]['definition'] = definition
        self.gen_tablerow(uid, row_data=new_row_data)


########################################################################
# Manually Adding QQ's to Plat
########################################################################

class ManualPlatter(tk.Frame):
    """
    A frame for manually adding QQ's to the plats.
    """

    PLATTER_ROW = 3
    PLATTER_COL = 1
    TWPRGE_WID = 5
    NSEW_WID = 2

    def __init__(self, master=None, mpq_owner=None):
        tk.Frame.__init__(self, master)
        self.master = master
        if mpq_owner is None:
            mpq_owner = master
        self.mpq_owner = mpq_owner
        self.target_mpq = mpq_owner.ad_hoc_mpq

        # Space at the top.
        lbl = Label(self, text='')
        lbl.grid(row=0, column=1)

        # Frame for defining Twp, Rge, Sec
        trs_frame = tk.Frame(self)
        trs_frame.grid(row=1, column=1, padx=20)

        trs_col = 0

        lbl = tk.Label(trs_frame, text='Twp:')
        lbl.grid(row=0, column=trs_col)
        trs_col += 1

        self.twp_num = tk.Entry(trs_frame, width=self.TWPRGE_WID)
        self.twp_num.grid(row=0, column=trs_col)
        trs_col += 1

        self.twp_ns = Combobox(trs_frame, width=self.NSEW_WID)
        self.twp_ns['values'] = ['N', 'S']
        self.twp_ns.current(0)
        self.twp_ns.grid(row=0, column=trs_col)
        trs_col += 1

        lbl = tk.Label(trs_frame, text='  Rge:')
        lbl.grid(row=0, column=trs_col)
        trs_col += 1

        self.rge_num = tk.Entry(trs_frame, width=self.TWPRGE_WID)
        self.rge_num.grid(row=0, column=trs_col)
        trs_col += 1

        self.rge_ew = Combobox(trs_frame, width=self.NSEW_WID)
        self.rge_ew['values'] = ['W', 'E']
        self.rge_ew.current(0)
        self.rge_ew.grid(row=0, column=trs_col)
        trs_col += 1

        lbl = tk.Label(trs_frame, text='  Sec:')
        lbl.grid(row=0, column=trs_col)
        trs_col += 1

        self.sec_num = Combobox(trs_frame, width=self.NSEW_WID)
        self.sec_num['values'] = [i for i in range(1,37)]
        self.sec_num.current(0)
        self.sec_num.grid(row=0, column=trs_col)
        trs_col += 1

        clear_all_btn = tk.Button(
            self, text="Clear All Manually Added QQ's", height=2,
            command=self.clear_btn_clicked)
        clear_all_btn.grid(row=10, column=1, padx=10, pady=30)

        # The current ManualSectionPlatter object -- initialized as
        # None, then set in `.new_platter().
        self.cur_platter = None
        self.new_platter()

    def child_go_btn_clicked(self):
        """Add the QQ's to the target MultiPlatQueue."""

        # Compile TRS
        twprge, sec = self._compile_trs()
        # If invalid characters were identified, `.compile_trs()` returns
        # `False`, so check for that now.
        if twprge is False:
            return

        # Assign sec number to the SectionGrid object in the current platter
        sg = self.cur_platter.sec_grid
        sg.sec = sec

        # Add the SectionGrid object to the target MPQ, for the specified twprge
        self.target_mpq.queue_add(sg, twprge)

        # Get a new platter
        self.new_platter()

        # Update mini-preview
        try:
            self.mpq_owner.trigger_update_preview()
        except:
            pass

    def _compile_trs(self):
        """
        Compile the twprge ('000x000x') from the current entry/combo
        boxes.
        :return:
        """
        # Compile TRS
        twp_num = self.twp_num.get()
        NS = self.twp_ns.get().lower()
        rge_num = self.rge_num.get()
        EW = self.rge_ew.get().lower()
        sec = self.sec_num.get()

        for chk in [twp_num, rge_num]:
            if len(chk) > 3 or not chk.isnumeric():
                tk.messagebox.showerror(
                    'Invalid Twp / Rge',
                    'Enter Township and Range as 1 to 3 digits.'
                )
                return False, False

        if len(sec) > 2 or not sec.isnumeric():
            tk.messagebox.showerror(
                'Invalid Sec',
                'Enter Section as 1 or 2 digits.'
            )
            return False, False

        if NS.lower() not in ['n', 's']:
            tk.messagebox.showerror(
                'Invalid N/S',
                'Township must be designated as either N or S.'
            )
            return False, False

        if EW.lower() not in ['e', 'w']:
            tk.messagebox.showerror(
                'Invalid E/W',
                'Range must be designated as either E or W.'
            )
            return False, False

        return (twp_num + NS.lower() + rge_num + EW.lower(), sec)

    def clear_btn_clicked(self):
        """
        Clear all manually added QQ's from the plats.
        NOTE: Does NOT clear parsed descriptions.
        """
        prompt = messagebox.askyesno(
            'Confirm?',
            "Delete all manually added QQ's from plats? (Does not delete "
            "parsed text descriptions.)",
            icon='warning')

        if prompt is True:
            # Set the mpq owner's `.ad_hoc_mpq` to an empty MPQ
            self.master.ad_hoc_mpq = MultiPlatQueue()

            # Re-define our target_mpq to point to this new MPQ
            self.target_mpq = self.master.ad_hoc_mpq

            # Generate a new preview (which will be an empty _plat)
            self.master.preview_frame.gen_preview()

    def new_platter(self):
        try:
            self.cur_platter.destroy()
        except:
            pass
        self.cur_platter = ManualSectionPlatter(self)
        self.cur_platter.grid(
            row=self.PLATTER_ROW, column=self.PLATTER_COL, pady=10)


class ManualSectionPlatter(SectionFiller):
    """
    For manually platting QQ's in a section.
    """

    def __init__(self, master=None):
        SectionFiller.__init__(self, master)
        self.master = master
        self.go_btn.config(text="Add Selected QQ's to Plat", height=2)
        self.go_btn.grid(row=0, column=1, pady=20)

    def go_btn_clicked(self):
        self.master.child_go_btn_clicked()


########################################################################
# Main
########################################################################

def launch_app():
    app = MainWindow()
    app.mainloop()


if __name__ == '__main__':
    launch_app()