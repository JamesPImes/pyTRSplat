# Copyright (c) 2020, James P. Imes. All rights reserved.

"""
A basic GUI for pyTRSplat.
"""

# TODO: Allow user to save selected page(s), rather than all.

# TODO: Implement option to view / delete added PLSSDesc objs in mpq.

# TODO: Implement custom settings options.

# TODO: Warn/confirm when error parse detected.

# TODO: Warn/confirm of unhandled lots (i.e. lots for which no definition exists) before
#  saving / preview.

import Plat
import _constants

from pyTRS.interface_tools.config_popup import prompt_config
from pyTRS import pyTRS
from pyTRS import version as pyTRSversion
import pyTRS._constants as pyTRS_constants

import tkinter as tk
from tkinter.ttk import Combobox
from tkinter import messagebox, filedialog
from tkinter import Label

from PIL import ImageTk

from pathlib import Path


class MainWindow(tk.Tk):
    def __init__(self):
        tk.Tk.__init__(self)
        self.title('pyTRSplat - Text-to-Plat Generator')

        # Store an empty LotDefDB object as `.lddb`
        self.lddb = Plat.LotDefDB()

        # Store a (currently empty) queue of ad-hoc objects to be added
        # to the plat(s) -- e.g. SectionGrid, TownshipGrid, etc.
        # TODO: Currently has no functionality. Will eventually add the
        #   option to manually add QQ's with an editor.
        self.ad_hoc_mpq = Plat.MultiPlatQueue()

        # Store a plain list (currently empty) of PLSSDesc objects that
        # will be platted
        self.plssdesc_list = []

        # A widget for entering land descriptions, configuring parse,
        # loading LotDefDB, etc.
        self.desc_frame = DescFrame(master=self)
        self.desc_frame.grid(row=1, column=1)

        # A widget for displaying a mini preview of the plat so far
        self.preview_frame = PlatPreview(master=self)
        self.preview_frame.grid(row=1, column=2, sticky='n')

        # A widget for output settings / buttons. (Contains the plat
        # generator at `.output_frame.gen_plat()`
        self.output_frame = OutputFrame(master=self)
        self.output_frame.grid(row=2, column=2, sticky='n')

        # Widget containing 'About' and 'disclaimer' buttons.
        self.about = About(master=self)
        self.about.grid(row=2, column=1, padx=4, pady=4, sticky='sw')

    @property
    def mpq(self):
        """Return a MultiPlatQueue object from the `self.plssdesc_list`
        and `self.ad_hoc_mpq`."""
        mpq = Plat.MultiPlatQueue()
        for obj in self.plssdesc_list:
            mpq.queue(obj)
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
    add to the plat, getting LotDefDB from .csv."""
    def __init__(self, master=None, grandmaster=None):
        tk.Frame.__init__(self, master)
        self.master = master
        if grandmaster is None:
            grandmaster = master
        self.grandmaster = grandmaster

        # a tk var containing Default config parameters for pyTRS parsing.
        self.setvar(name='config_text', value='')
        self.config_popup_tk = None

        # For getting the PLSS descriptions from user.
        desc_frame = tk.Frame(self)
        desc_frame.grid(row=0, column=1, sticky='n', padx=5, pady=5)

        # For getting .csv file for LotDefDB from user
        lddb_save_frame = tk.Frame(self)
        lddb_save_frame.grid(row=5, column=1, sticky='sw')

        # Button to configure pyTRS parameters
        cf_button = tk.Button(
            desc_frame, text='Configure Parse', height=2,
            command=self.cf_btn_clicked)
        cf_button.grid(row=3, column=1, pady=8, sticky='w')

        # Button to commence pyTRS parsing (and add resulting PLSSDesc to MPQ)
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
            desc_frame, text='View / Edit Descriptions', height=2,
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

        self.lddp_fp_text = tk.StringVar('')
        self.lddp_fp_text.set(f"Current lot definitions: [None loaded]")
        lddb_label = tk.Label(desc_frame, textvariable=self.lddp_fp_text)
        lddb_label.grid(row=6, column=1, sticky='w')

        default_lots_frame = tk.Frame(desc_frame)
        default_lots_frame.grid(row=7, column=1, sticky='w')

        self.trust_default_lots = tk.BooleanVar(
            desc_frame, value=True, name='trust_default_lots')
        lots_chkbtn = tk.Checkbutton(
            default_lots_frame, text='Trust Default Lots', onvalue=True,
            offvalue=False, variable=self.trust_default_lots,
            command=self.trigger_update_preview)
        lots_chkbtn.grid(row=1, column=2, sticky='w')

        lots_help_btn = tk.Button(
            default_lots_frame, text='?', padx=4,
            command=self.lots_help_btn_clicked)
        lots_help_btn.grid(
            row=1, column=1, sticky='w')

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
        """Config button was clicked; launch popup window to get Config
        parameters from user (results are stored in 'config_text' var of
        `master`, per design of `pyTRS.prompt_config()` function -- use
        `self.getvar(name='config_text')` to retrieve after it's set)."""
        if isinstance(self.config_popup_tk, tk.Toplevel):
            # Kill the previously opened config popup, if any.
            self.config_popup_tk.destroy()

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
                'the plat will NOT be affected by changes to these config '
                'parameters.')
        prompt_config(
            parameters=[
                'cleanQQ', 'requireColon', 'ocrScrub', 'segment', 'layout'
            ],
            show_save=False, show_cancel=False,
            config_window=self.config_popup_tk, main_window=self,
            prompt_after_ok=after_prompt)

    def parse_btn_clicked(self):
        """Pull the entered text, and use the chosen config parameters (if
        any) to generate a PLSSDesc object, and add it to the queue to plat."""
        config_text = self.getvar(name='config_text')
        descrip_text = self.desc_box_entry.get("1.0", "end-1c")

        if len(descrip_text) < 2:
            return

        # Create a PLSSDesc object from the supplied text and parse it using the
        # specified config parameters (if any).
        desc = pyTRS.PLSSDesc(descrip_text, config=config_text, initParseQQ=True)

        # Add desc to the plssdesc_list
        self.master.plssdesc_list.append(desc)

        # Clear the text from the desc_box_entry
        self.desc_box_entry.delete("1.0", 'end-1c')

        # And update the preview plat.
        self.trigger_update_preview()

    def trigger_update_preview(self):
        self.master.preview_frame.gen_preview()

    def clear_btn_clicked(self):
        """Clear all plats and descriptions (reset to start)"""
        prompt = messagebox.askyesno(
            'Confirm?',
            'Delete all added descriptions and reset plats to blank?',
            icon='warning')

        if prompt is True:
            # Set the `.plssdesc_list` to an empty list
            self.master.plssdesc_list = []
            # Set the `.ad_hoc_mpq` to an empty MPQ obj
            self.master.ad_hoc_mpq = Plat.MultiPlatQueue()

            # Generate a new preview (which will be an empty plat)
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
                    self.master.lddb = Plat.LotDefDB(from_csv=lddb_fp)

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
            "lots in a 'standard' township, unless the user has defined lots "
            "differently in a .csv file that has been loaded. (See the "
            "included example, plus the documentation, for how to format such "
            "a .csv file.)"
            "\n\n"
            "NOTE: Default lots will ONLY be used where no lots have been "
            "defined for a given section in a loaded .csv file. (If a .csv "
            "file has been loaded, but it does not define any lots in Section "
            "4, T154N-R97W, then default lots would be used for that Section "
            "4 -- as long as this box is checked.)"
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
            "defining specific lots in a .csv spreadsheet and loading from "
            "that will render a more accurate plat."
        )
        messagebox.showinfo('Default Lots', msg)



########################################################################
# Generating, Displaying, and Controlling Plat Mini-Preview
########################################################################

class PlatPreview(tk.Frame):
    """A frame displaying a preview of the plat, plus its controls."""

    def __init__(self, master=None):
        tk.Frame.__init__(self, master)
        self.master = master

        # A list of Image objects of previews of the plats
        self.previews = []
        # A list of twp/rge (strings) to use as headers for previews of the plats
        self.previews_twprge = []
        # Current index of the preview
        self.preview_index = 0
        # Tracking if we're displaying a dummy (empty plat) in the preview
        self.dummy_set = False

        # Subframe for handling everything with the plat, other than getting
        # the PLSS descrips.
        plat_frame = tk.Frame(self)
        plat_frame.grid(row=0, column=2, sticky='n')

        # # Subframe for showing a preview of the plat, and controls for
        # # left/right
        # plat_preview_frame = tk.Frame(plat_frame)
        # plat_preview_frame.grid(row=1, column=1, sticky='n')

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


        ###################
        # Plat.Settings object
        ###################
        # Generate a Settings object for the mini-preview, with no
        # margins. (Hard-coded here, rather than creating it as a preset,
        # so that it will never be changed to unexpected settings.)
        setObj = Plat.Settings(preset=None)
        setObj.qq_side = 8
        setObj.centerbox_wh = 12
        setObj.sec_line_stroke = 1
        setObj.qql_stroke = 1
        setObj.ql_stroke = 1
        setObj.sec_line_RGBA = (0, 0, 0, 255)
        setObj.ql_RGBA = (128, 128, 128, 255)
        setObj.qql_RGBA = (230, 230, 230, 255)
        setObj.dim = (
            setObj.qq_side * 4 * 6 + setObj.sec_line_stroke,
            setObj.qq_side * 4 * 6 + setObj.sec_line_stroke)
        setObj.y_top_marg = 0
        setObj.set_font('sec', size=11)
        setObj.write_header = False
        setObj.write_tracts = False
        setObj.write_lot_numbers = False
        self.settings = setObj

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
        mpq = self.master.mpq
        lddb = self.master.lddb

        # Get the bool var that decides whether we're supposed to trust
        # default lots (i.e. pass through to `allow_ld_defaults=`)
        trust_default_lots = self.master.desc_frame.getvar(
            name='trust_default_lots')
        trust_default_lots = bool(trust_default_lots)

        # Create a new MP
        new_preview_mp = Plat.MultiPlat.from_queue(
            mpq, settings=self.settings, lddb=lddb,
            allow_ld_defaults=trust_default_lots)

        self.dummy_set = False

        # If there's nothing yet in the MPQ, manually create a 'dummy' plat
        # and append it, so that there's something to show (an empty plat)
        if len(mpq.keys()) == 0:
            dummy = Plat.Plat(settings=self.settings)
            new_preview_mp.plats.append(dummy)
            self.dummy_set = True

        # Output the plat images to a list, and set to `.previews`
        self.previews = new_preview_mp.output()

        # And create a list of 'twprge' values for each of the images, and
        # set to `.previews_twprge`.
        self.previews_twprge = []
        for plObj in new_preview_mp.plats:
            self.previews_twprge.append(plObj.twprge)

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
        preview = ImageTk.PhotoImage(img)

        # Display the preview in this label.
        self.preview_disp_label = Label(
            self.plat_preview_display_frame, image=preview)
        self.preview_disp_label.image = preview
        self.preview_disp_label.grid(row=2, column=1, sticky='n')

        # Also update the footer.
        foot_txt = self.previews_twprge[index]
        foot_txt = f"{foot_txt}  [{index + 1} / {len(self.previews)}]"
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
    button, and corresponding functionality. Also contains the plat
    generator. (Interacts with the `preview_frame` and `.mpq` of
    `master`."""
    def __init__(self, master=None):
        tk.Frame.__init__(self, master)
        self.master = master

        ####################################
        # Choosing Plat Settings
        ####################################

        # Subframe for getting the plat settings from user.
        self.settings_frame = tk.Frame(self)
        self.settings_frame.grid(row=1, column=1, sticky='n')

        self.settings_label = Label(
            self.settings_frame, text='Output settings:')
        self.settings_label.grid(row=2, column=1, pady=3, sticky='e')

        self.settings_combo = Combobox(self.settings_frame, width=9)
        avail_presets = Plat.Settings.list_presets()
        self.settings_combo['values'] = avail_presets
        self.settings_combo.grid(row=2, column=2, sticky='w')
        # Set the combo to 'default' preset. (If that doesn't exist, set to
        # whatever's first in the list.)
        try:
            settings_index = avail_presets.index('default')
        except ValueError:
            settings_index = 0
        self.settings_combo.current(settings_index)

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

    ####################################
    # Generating the Plat(s)
    ####################################

    def gen_plat(self):
        """Generate and return the Plat(s)."""

        # Get the name of the preset `Settings` object we'll use.
        preset = self.settings_combo.get()

        # Get the bool var that decides whether we're supposed to trust
        # default lots (i.e. pass through to `allow_ld_defaults=`)
        trust_default_lots = self.master.desc_frame.getvar(
            name='trust_default_lots')
        trust_default_lots = bool(trust_default_lots)

        return Plat.MultiPlat.from_queue(
            mpq=self.master.mpq, settings=preset, lddb=self.master.lddb,
            allow_ld_defaults=trust_default_lots)

    def preview_btn_clicked(self):
        """Generate the MultiPlat and display one of the plats from it. If
        the desired `index` is greater than the number of plats generated,
        will show the final one."""
        mp = self.gen_plat()
        if len(mp.plats) == 0:
            messagebox.showinfo(
                'No plats',
                'No plats to preview. Add land descriptions and try again.')
            return

        index = self.master.preview_frame.preview_index
        if index >= len(mp.plats):
            index = len(mp.plats) - 1

        #mp.show(index)
        # output() returns a list (in this case, only one page), so grab
        # the first (only) element from it.
        preview_img = mp.output(pages=index)[0]
        preview_window = FullPreviewWindow(
            master=self, img=preview_img,
            settings_name=self.settings_combo.get())

    def save_btn_clicked(self):
        """Generate plats and save them to .png or .pdf at user-selected
        filepath."""

        mp = self.gen_plat()
        if len(mp.plats) == 0:
            messagebox.showinfo(
                'No plats',
                'No plats to save. Add land descriptions and try again.')
            return

        write_it = False
        multi_png = False
        start_dir = '/'
        ext = ''

        # Look at how many images are in the `previews` list to see how
        # many plats there will be.
        num_plats = len(self.master.preview_frame.previews)

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
        #about_frame = tk.Frame(master=self)

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

    def about_btn_clicked(self):
        splash_info = (
            f"pyTRSplat {Plat.version()}\n"
            "Copyright (c) 2020, James P. Imes, all rights reserved.\n"
            "A program for generating plats from PLSS land descriptions (often "
            "called 'legal descriptions').\n\n"

            f"Built on pyTRS {pyTRSversion()}.\n"
            "Copyright (c) 2020, James P. Imes, all rights reserved.\n"
            "A program for parsing PLSS land descriptions into their component "
            "parts.\n\n"

            f"Contact: <{_constants.__email__}>"

        )
        messagebox.showinfo('pyTRSplat - About', splash_info)

    def disclaimer_btn_clicked(self):
        """Display the disclaimer text from the pyTRS module."""
        messagebox.showinfo('pyTRS disclaimer', pyTRS_constants.__disclaimer__)


class FullPreviewWindow(tk.Toplevel):
    """A popup window containing a full-size preview of the requested
    plat page."""

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


        #
        # preview_display = tk.Label(display_frame, image=big_preview)
        # preview_display.image = big_preview
        # preview_display.grid(row=1, column=1, sticky='n')


class ScrollResizeDisplay(tk.Frame):
    """A frame that displays an image, which can be scaled and scrolled
    with built-in controls and scrollers."""

    def __init__(self, master=None, img=None, **kw):
        tk.Frame.__init__(self, master=master, **kw)
        self.master = master

        #########################################
        # Control Frame / Buttons
        #########################################

        control_frame = tk.Frame(master=self)
        control_frame.grid(row=1, column=1)

        # Smaller button
        img_smaller_btn = tk.Button(
            control_frame, text='-', padx=4,
            command=lambda: self.adjust_display_scale(-10))
        img_smaller_btn.grid(row=1, column=1, padx=4, pady=4, sticky='n')

        # Bigger button
        img_bigger_btn = tk.Button(
            control_frame, text='+', padx=4,
            command=lambda: self.adjust_display_scale(10))
        img_bigger_btn.grid(row=1, column=2, padx=4, pady=4, sticky='n')

        ###################
        # Simple subframe for Scale display / zoom button pair
        ###################
        # Create the scale_frame and put it in the control_frame
        self.scale_frame = tk.Frame(control_frame)
        self.scale_frame.grid(row=1, column=3, padx=6, sticky='e')
        # Box to display the current scale / get the zoomed scale
        self.scale_box = tk.Entry(self.scale_frame, width=6)
        self.scale_box.grid(row=1, column=2, ipady=2, padx=2, sticky='w')
        scale_zoom_btn = tk.Button(
            self.scale_frame, text='Zoom to:', padx=2,
            command=self.zoom_btn_clicked)
        scale_zoom_btn.grid(row=1, column=1, sticky='e')
        ###################

        # Reset to full-size button
        reset_scale_btn = tk.Button(
            control_frame, text='Full Size', padx=4,
            command=lambda: self.set_display_scale(100))
        reset_scale_btn.grid(row=1, column=4, padx=4, pady=4, sticky='w')

        # Fit to width button
        fit_page_w_btn = tk.Button(
            control_frame, text='Fit Page Width', padx=4,
            command=self.set_window_page_width)
        fit_page_w_btn.grid(row=1, column=5, padx=4, pady=4, sticky='n')

        # Fit to height button
        fit_page_h_btn = tk.Button(
            control_frame, text='Fit Page Height', padx=4,
            command=self.set_window_page_height)
        fit_page_h_btn.grid(row=1, column=6, padx=4, pady=4, sticky='n')

        #########################################
        # Image / Canvas
        #########################################

        # Current scale of the original preview image (where `100` means 100%).
        self.scale = 100
        # Min/Max scale settings
        self.min_scale = 10
        self.max_scale = 300

        self.canvas_w = 800
        self.canvas_h = 600

        self.img = img
        self.shown_img = ImageTk.PhotoImage(img)

        ###################
        # A subframe for holding the canvas and its scrollbars
        ###################
        cvs_frame = tk.Frame(self)
        cvs_frame.grid(row=2, column=1, sticky='n')

        self.cvs = tk.Canvas(
            cvs_frame, height=self.canvas_h, width=self.canvas_w)
        self.cvs.create_image(
            0, 0, tags='displayed_preview', anchor='nw', image=self.shown_img)
        self.cvs.grid(row=0, column=0, sticky='n')

        # TODO: Better scrolling controls. Currently, if the image scales past
        #   the width of the canvas, can't scroll any farther than that.

        self.v_scroller = tk.Scrollbar(cvs_frame, orient='vertical', width=24)
        self.v_scroller.grid(row=0, column=1, sticky='ns')
        self.h_scroller = tk.Scrollbar(cvs_frame, orient='horizontal', width=24)
        self.h_scroller.grid(row=1, column=0, sticky='ew')

        self.cvs.config(
            xscrollcommand=self.h_scroller.set,
            yscrollcommand=self.v_scroller.set)

        self.v_scroller.config(command=self.cvs.yview)
        self.h_scroller.config(command=self.cvs.xview)
        self.cvs.config(scrollregion=self.cvs.bbox('all'))
        # TODO: Mouse-drag controls.
        ###################

        # If our image is wider than the canvas, show the page-width
        # view by default
        if self.img.width > self.canvas_w:
            self.set_window_page_width()

    def resize_displayed_image(self, scale=None):
        """Resize the original `.img` to the scale in `self.scale` (a
        percentage represented as an int -- i.e. `scale=100` meaning
        100%; `scale=50` meaning 50%)."""

        if scale is None:
            scale = self.scale

        img = self.img.copy()
        w0, h0 = img.size
        w1 = int(w0 * (scale / 100))
        h1 = int(h0 * (scale / 100))
        resized_img = img.resize((w1, h1))
        self.update_display_image(resized_img)

    def update_display_image(self, new_img):
        self.shown_img = ImageTk.PhotoImage(new_img)
        self.cvs.itemconfig('displayed_preview', image=self.shown_img)

    def adjust_display_scale(self, increment=10):
        """Make the displayed image bigger or smaller by the specified
        `increment`; and updates the displaed image. (Defaults to 10%
        larger.)"""

        # Set the new scale.
        self.set_display_scale(self.scale + increment)

    def set_display_scale(self, scale=100):
        """Set the size of the displayed image to the specified `scale`;
        and updates the displayed image. Defaults to `100` (i.e. 100%)."""

        # Set the new scale.
        self.scale = scale

        # Force it within the min/max, as necessary.
        if self.scale < self.min_scale:
            self.scale = self.min_scale
        if self.scale > self.max_scale:
            self.scale = self.max_scale

        # Enact the new scale.
        self.resize_displayed_image()

        # Update the text in the scale box.
        self.update_scale_box()

    def set_window_page_width(self):
        """Fit the size of the displayed image to the width of the canvas."""
        self.set_display_scale(scale=int(self.canvas_w / self.img.width * 100))

    def set_window_page_height(self):
        """Fit the size of the displayed image to the height of the canvas."""
        self.set_display_scale(scale=int(self.canvas_h / self.img.height * 100))

    def zoom_btn_clicked(self):
        """Set the scale to the value specified by the user in the
        scale_box."""
        input_scale = self.scale_box.get()
        while True:
            input_scale_chk = input_scale
            input_scale_chk = input_scale_chk.strip('%')
            input_scale_chk = input_scale_chk.strip()
            if input_scale_chk == input_scale:
                break
            input_scale = input_scale_chk
        try:
            input_scale = int(input_scale)
        except ValueError:
            messagebox.showerror('Numbers Only', 'Input only numbers!')
            self.update_scale_box()
            self.focus()
            return

        self.set_display_scale(input_scale)

    def update_scale_box(self):
        """Update the text displayed inside the scale_box."""
        self.scale_box.delete(0, 'end')
        self.scale_box.insert(tk.END, str(self.scale) + '%')


class DescriptionEditor(tk.Toplevel):
    """A widget for viewing, editing, reconfiguring, and reparsing PLSSDesc
    objects that are currently in the MultiPlatQueue.

    NOTE: At init, specify `plssdesc_list_owner=<object>` (e.g., a root
    Tk() object), if that's where the list of updated/saved PLSSDesc
    objects should be stored to (defaults to same as `master`, but may
    need to be a higher-level master)."""

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
            # If we've already displayed an sde, remove it from the grid now
            self.displayed_sde.grid_remove()

        # Set the new displayed_sde, and place it on the grid.
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
            new_plssdesc_list.append(sde.plssdesc_obj)
        return new_plssdesc_list

    def export_to_master(self):
        """Collect the updated PLSSDesc objects in a new list, and set it
        to the plssdesc_list_owner's `.plssdesc_list`. Update the plat
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

        # Remove this SDE from the grid
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
            'yet been applied to the plat?')
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
    single pyTRS.PLSSDesc object."""

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
            plssdesc_obj = pyTRS.PLSSDesc()
        self.plssdesc_obj = plssdesc_obj

        # Tracking the PLSSDesc object from which we're currently viewing
        # tracts and flags, and whether the displayed data has been 'saved'
        self.current_display_tract_source = plssdesc_obj
        self.current_display_flag_source = plssdesc_obj
        self.current_display_tract_status = 'saved'
        self.current_display_flag_status = 'saved'

        self.replacement_plssdesc_obj = None

        # Tracking whether this Editor object has created a new PLSSDesc
        # object
        self.created_new_plssdesc = False

        # Tracking whether we've reparsed since last saving.
        self.reparse_since_last_save = False

        # The first 'original description' (`.origDesc`) that had been
        # stored in the PLSSDesc object as of init. (`.origDesc` may
        # change after this point, but this will not.)
        self._first_orig_desc = plssdesc_obj.origDesc
        # The new description that we'll use, if we end up replacing
        # our original PLSSDesc object.
        self.new_desc_text = self._first_orig_desc
        self.current_display_desc_status = 'saved'

        # The first Config text (decompiled from `.config`) that had
        # been used to parse the PLSSDesc object as of init. (`.config`
        # may change after this point, but this will not.)
        #
        # NOTE: Dictated layout gets stripped out. (This is due to a
        # limitation in .decompile_to_text() from the pyTRS module that
        # causes bugs here if left in.)
        first_config = plssdesc_obj.config.decompile_to_text()
        first_config = SingleDescriptionEditor.strip_layout(first_config)
        self._first_config = first_config

        # The new config parameters that we'll use, if we end up
        # replacing our original PLSSDesc object. (Can be changed by
        # clicking 'Reconfigure' button.)
        self.setvar(name='config_text', value=self._first_config)

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

        save_changes_btn = tk.Button(
            control_frame, text='Save Changes', height=2, padx=2,
            command=self.save_clicked)
        save_changes_btn.grid(row=0, column=3, padx=btn_padx, sticky='n')

        # TODO: Reset button / functionality.

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
        # should be placed in the grid.
        self.tract_table_row_col = (1, 1)
        self.tract_table_padx_pady = (5, 5)
        self.flag_table_row_col = (3, 1)
        self.flag_table_padx_pady = (5, 10)

        # The parsed tracts are displayed in `.tract_table` (set to None
        # here, but initialized as a TractTable obj in `.display_new_tracts`)
        self.tract_table = None
        self.display_new_tracts(
            source_plssdesc=self.plssdesc_obj, status='saved')

        # Warning and Error Flags are displayed in `.flag_table` (set to
        # None here, but initialized as a FlagTable obj in `.display_new_flags`)
        self.flag_table = None
        self.display_new_flags(
            source_plssdesc=self.plssdesc_obj, status='saved')

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
            self.pytrs_display_frame, wflag_list=source_plssdesc.wFlagList,
            eflag_list=source_plssdesc.eFlagList, more_info=self.more_info,
            text_color=text_color)
        if self.more_info:
            # Only if `.more_info==True` do we place this on the grid.
            self.flag_table.grid(
                row=self.flag_table_row_col[0],
                column=self.flag_table_row_col[1],
                padx=self.flag_table_padx_pady[0],
                pady=self.flag_table_padx_pady[1], sticky='nws')

    def display_new_tracts(self, source_plssdesc=None, status=None):
        """Display the data for the parsed pyTRS.Tract in the specified
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
        # using as the tract_list the `.parsedTracts` from the chosen
        # source PLSSDesc object.
        if self.tract_table is not None:
            self.tract_table.destroy()
        self.tract_table = TractTable(
            self.pytrs_display_frame,
            tract_list=source_plssdesc.parsedTracts,
            text_color=text_color, more_info=self.more_info)
        self.tract_table.grid(
            row=self.tract_table_row_col[0],
            column=self.tract_table_row_col[1],
            padx=self.tract_table_padx_pady[0],
            pady=self.tract_table_padx_pady[1], sticky='nw')

    def reparse(self):
        """Reparse the pyTRS.PLSSDesc object at the specified index in
        `self.plssdesc_list`, using the optionally re-specified `config`
        parameters. (If `config` has not been specified, will use
        whatever was already in the PLSSDesc object.)

        Note: This will create a new PLSSDesc object and set it to
        `self.replacement_plssdesc_obj`. Beware lists that contain the
        original PLSSDesc object, as those will NOT be automatically
        updated with this new object."""

        config = self.getvar(name='config_text')
        if config == 'CANCEL':
            # If the user hit the cancel button in the config popup, use
            # the original config
            config = self._first_config
        desc = self.new_desc_text
        d_obj = pyTRS.PLSSDesc(desc, config=config, initParseQQ=True)
        self.replacement_plssdesc_obj = d_obj
        self.created_new_plssdesc = True
        self.display_new_descrip(status='not_saved')
        self.display_new_tracts(source_plssdesc=d_obj, status='not_saved')
        self.display_new_flags(source_plssdesc=d_obj, status='not_saved')
        self.created_new_plssdesc = True
        self.reparse_since_last_save = True

    def reconfig_btn_clicked(self):
        """Re-Config button was clicked; launch popup window to get Config
        parameters from user (results are stored in 'reconfig_text' var
        of `self`, per design of `pyTRS.prompt_config()` function -- use
        `self.getvar(name='config_text')` to retrieve after it's set)."""
        if isinstance(self.config_popup_tk, tk.Toplevel):
            # Kill the previously opened config popup, if any.
            self.config_popup_tk.destroy()

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
        prompt_config(
            parameters=[
                'cleanQQ', 'requireColon', 'ocrScrub', 'segment', 'layout'
            ],
            show_save=False, show_cancel=True,
            config_window=self.config_popup_tk, main_window=self,
            prompt_after_ok=after_prompt)

    def save_clicked(self):
        """Close open sub-editor popup windows, and save the reparsed
        changes, if any."""

        # Close any subordinate popups.
        try:
            self.config_popup_tk.destroy()
        except:
            pass
        try:
            self.new_desc_pop_up_tk.destroy()
        except:
            pass

        if not self.reparse_since_last_save:
            confirm = tk.messagebox.askyesno(
                'Reparse first?',
                'You have not yet reparsed this description, so saving '
                'would have no effect.\n\n'
                'Reparse and save now?')
            self.focus()
            self.grab_set()

            if confirm:
                self.reparse()
            else:
                return

        if self.current_display_desc_status == 'not_activated':
            confirm = tk.messagebox.askyesnocancel(
                'Reparse first?',
                'You have unparsed edits to this description that would'
                'not be included in saving.\n\n'
                'Do you want to reparse before saving?')
            self.focus()
            self.grab_set()

            if confirm:
                self.reparse()
            elif confirm is None:
                return

        self._save_changes()

    def _save_changes(self):
        """Save the reparsed changes, if any (i.e. store the reparsed
        PLSSDesc object to `self.plssdesc_obj`)."""

        if self.replacement_plssdesc_obj is not None:
            # Set the main PLSSDesc obj to the new replacement.
            self.plssdesc_obj = self.replacement_plssdesc_obj

        self.current_display_tract_status = 'saved'
        self.current_display_flag_status = 'saved'
        if self.current_display_desc_status == 'not_saved':
            # If the edited description was not reparsed, then it should
            # remain red, because it has not been incorporated into the
            # newly saved PLSSDesc object.
            self.current_display_desc_status = 'saved'
            self.display_new_descrip(status='saved')
        self.display_new_tracts(
            source_plssdesc=self.plssdesc_obj, status='saved')
        self.display_new_flags(
            source_plssdesc=self.plssdesc_obj, status='saved')

        self.reparse_since_last_save = False

    @staticmethod
    def strip_layout(config_text) -> str:
        """Strip out a dictated layout from pyTRS config text."""
        for layout in pyTRS.__implementedLayouts__:
            config_text = config_text.replace(f",layout.{layout}", '')

        return config_text


class DescTextEditWindow(tk.Toplevel):
    """A pop-up window in which the user may make edits to the text of a
    pyTRS.PLSSDesc object."""

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
    """A frame containing a table of parsed data from a list of
    pyTRS.Tract objects."""

    trs_col_width = 10
    trs_wraplength = 240

    desc_col_width = 30
    desc_wraplength = 200

    lotqq_col_width = 30
    lotqq_wraplength = 200

    def __init__(
            self, master=None, tract_list=None, text_color='black',
            more_info=False, **kw):
        tk.Frame.__init__(self, master, **kw)
        self.master = master

        if tract_list is None:
            tract_list = []
        self.tract_list = tract_list

        # Use a copy of this list (because we'll be inserting, and we
        # want the original list to remain intact).
        tract_list = tract_list.copy()

        # Insert None at the start of the list, because we'll write
        # headers on our first pass
        tract_list.insert(0, None)
        i = 0
        for tract_obj in tract_list:
            # Generate a row for each tract (and also for header)

            # ...for TRS
            trs_frm = tk.Frame(
                master=self, highlightbackground='black', highlightthickness=1)
            trs_frm.grid(row=i, column=1, sticky='ns')
            if tract_obj is None:
                trs_txt = 'TRS'
                anchor = 'n'
            else:
                trs_txt = tract_obj.trs
                anchor = 'nw'
            trs_lbl = tk.Label(
                master=trs_frm, text=trs_txt, fg=text_color,
                width=TractTable.trs_col_width,
                wraplength=TractTable.trs_wraplength, justify='left')
            trs_lbl.grid(sticky='nws')

            # ...for tract descrip.
            desc_frm = tk.Frame(
                master=self, highlightbackground='black', highlightthickness=1)
            desc_frm.grid(row=i, column=2, sticky='ns')
            if tract_obj is None:
                desc_txt = 'Description'
            else:
                desc_txt = tract_obj.desc
            desc_lbl = tk.Label(
                master=desc_frm, text=desc_txt, fg=text_color, anchor=anchor,
                width=TractTable.desc_col_width,
                wraplength=TractTable.desc_wraplength, justify='left')
            desc_lbl.grid(sticky='nws')

            # ...for more info
            if more_info:
                # If more info requested, also display Parsed Lots / QQ's
                frm = tk.Frame(
                    master=self, highlightbackground='black',
                    highlightthickness=1)
                frm.grid(row=i, column=3, sticky='nws')
                if tract_obj is None:
                    lotqq_txt = 'Identified Lots / QQs'
                else:
                    lotqq_txt = f"{', '.join(tract_obj.lotQQList)}"
                lotqq_lbl = tk.Label(
                    master=frm, text=lotqq_txt, fg=text_color, anchor=anchor,
                    width=TractTable.lotqq_col_width,
                    wraplength=TractTable.lotqq_wraplength, justify='left')
                lotqq_lbl.grid(row=i, column=2, sticky='ns')

            i += 1


class FlagTable(tk.Frame):
    """A frame containing a table of warning/error flags from a parsed
    pyTRS.PLSSDesc object."""

    flag_col_width = 35
    flag_wraplength = 240

    def __init__(
            self, master=None, wflag_list=None, eflag_list=None,
            text_color='black', more_info=False, **kw):
        tk.Frame.__init__(self, master, **kw)
        self.master = master

        if wflag_list is None:
            wflag_list = []
        self.wflag_list = wflag_list

        if eflag_list is None:
            eflag_list = []
        self.eflag_list = eflag_list

        if len(wflag_list) == 0:
            wflag_list.append('None')

        if len(eflag_list) == 0:
            eflag_list.append('None')

        i = 0
        while i < 2 and more_info:
            # Generate a row for each tract (and also for header)

            # ...for Warning Flags
            wflag_frm = tk.Frame(
                master=self, highlightbackground='black', highlightthickness=1)
            wflag_frm.grid(row=i, column=1, sticky='ns')
            if i == 0:
                # Write a header for the first row
                wflag_txt = 'Warning Flags'
                anchor = 'n'
            else:
                wflag_txt = ', '.join(wflag_list)
                anchor = 'nw'
            wflag_lbl = tk.Label(
                master=wflag_frm, text=wflag_txt, fg=text_color, anchor=anchor,
                width=FlagTable.flag_col_width, justify='left',
                wraplength=FlagTable.flag_wraplength)
            wflag_lbl.grid(sticky='nw')

            # ...For Error Flags
            eflag_frm = tk.Frame(
                master=self, highlightbackground='black', highlightthickness=1)
            eflag_frm.grid(row=i, column=2, sticky='ns')
            if i == 0:
                # Write a header for the first row
                eflag_txt = 'Error Flags'
            else:
                eflag_txt = ', '.join(eflag_list)
            eflag_lbl = tk.Label(
                master=eflag_frm, text=eflag_txt, fg=text_color, anchor=anchor,
                width=FlagTable.flag_col_width, justify='left',
                wraplength=FlagTable.flag_wraplength)
            eflag_lbl.grid(sticky='nw')

            i += 1


def main():
    app = MainWindow()
    app.mainloop()

# desc = '''T154N-R97W
# Sec 14: NE/4 asdjfakjsdfh akjsdfh laksdjf lkasjdf lkasjdf laksdjf lakjsdf lkasjlk jlofgisjasldkfj asiodfj laksjdf asdjf ;alksdjf ;alksdjf alksjdf
# Sec 15: W/2
# Sec 22: N/2
# '''
#
# desc2 = '''T158N-R98W
# Sec 1: Lots 1 - 3, S/2N/2
# '''
#
# d = pyTRS.PLSSDesc(desc, initParseQQ=True)
# d2 = pyTRS.PLSSDesc(desc2, initParseQQ=True)
#
# root = tk.Tk()
# t = DescriptionEditor(master=root, plssdesc_list=[d, d2])
# #t.grid(row=1, column=1)
# root.mainloop()

if __name__ == '__main__':
    main()