# Copyright (c) 2020, James P. Imes. All rights reserved.

"""
A basic GUI for pyTRSplat.
"""

# TODO: Allow user to save selected page(s), rather than all.

# TODO: Implement option to view / delete added PLSSDesc objs in mpq.

# TODO: Implement / allow use of 'default' TwpLotDefinitions.

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

        # Store a (currently empty) queue of all objects to be added to
        # the plat(s)
        self.mpq = Plat.MultiPlatQueue()

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


########################################################################
# PLSSDesc Frame
########################################################################

class DescFrame(tk.Frame):
    """A frame for getting / clearing text of description to parse and
    add to the plat, getting LotDefDB from .csv."""
    def __init__(self, master=None):
        tk.Frame.__init__(self, master)
        self.master = master

        # a tk var containing Default config parameters for pyTRS parsing.
        self.setvar(name='config_text', value='')

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

        desc_box_header = tk.Label(desc_frame, text='Enter land description:')
        desc_box_header.grid(row=1, column=1, sticky='w')

        self.desc_box_entry = tk.Text(desc_frame, width=36, height=9)
        self.desc_box_entry.grid(row=2, column=1)

        # Button to clear all PLSSDesc's from the MPQ
        clear_button = tk.Button(
            desc_frame, text='Clear All Descriptions', height=2,
            command=self.clear_btn_clicked)
        clear_button.grid(row=4, column=1, pady=5, sticky='e')

        # Button to load LotDefDB from .csv file
        lddb_button = tk.Button(
            desc_frame, text='Get lot definitions from .csv', height=2,
            command=self.lddb_btn_clicked)
        lddb_button.grid(row=4, column=1, pady=5, sticky='w')

        self.lddp_fp_text = tk.StringVar('')
        self.lddp_fp_text.set(f"Current lot definitions: [None loaded]")
        lddb_label = tk.Label(desc_frame, textvariable=self.lddp_fp_text)
        lddb_label.grid(row=5, column=1, sticky='w')

    def cf_btn_clicked(self):
        """Config button was clicked; launch popup window to get Config
        parameters from user (results are stored in 'config_text' var of
        `master`, per design of `pyTRS.prompt_config()` function -- use
        `self.getvar(name='config_text')` to retrieve after it's set)."""
        config_popup_tk = tk.Toplevel()
        config_popup_tk.title('Set pyTRS Config Parameters')
        prompt_config(
            parameters=[
                'cleanQQ', 'requireColon', 'ocrScrub', 'segment', 'layout'
            ],
            show_save=False, show_cancel=False, config_window=config_popup_tk,
            main_window=self)

    def parse_btn_clicked(self):
        """Pull the entered text, and use the chosen config parameters (if
        any) to generate a PLSSDesc object, and add it to the queue to plat."""
        config_text = self.getvar(name='config_text')
        descrip_text = self.desc_box_entry.get("1.0", "end-1c")
        # Create a PLSSDesc object from the supplied text and parse it using the
        # specified config parameters (if any).
        desc = pyTRS.PLSSDesc(descrip_text, config=config_text, initParseQQ=True)

        # Add desc to the MPQ.
        self.master.mpq.queue(desc)

        # Clear the text from the desc_box_entry
        self.desc_box_entry.delete("1.0", 'end-1c')

        # And update the preview plat.
        self.master.preview_frame.gen_preview()

    def clear_btn_clicked(self):
        """Clear all plats and descriptions (reset to start)"""
        prompt = messagebox.askyesno(
            'Confirm?',
            'Delete all added descriptions and reset plats to blank?',
            icon='warning')

        if prompt is True:
            # Set the `.mpq` to an empty MPQ obj
            self.master.mpq = Plat.MultiPlatQueue()

            # Generate a new preview (which will be an empty plat)
            self.master.preview_frame.gen_preview()

    def lddb_btn_clicked(self):
        """Prompt user for .csv file containing LotDefDB data. If selected,
         loads from that file into main_window's `.lddb` attribute, and
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


########################################################################
# About
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


########################################################################
# Generating, Displaying, and Controlling Plat Preview
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
            command=self.scroll_preview_left)
        preview_left_button.grid(
            row=1, column=1, padx=8, pady=5, sticky='n')

    def gen_preview(self):
        """Generate a new list of preview plats (Image objects) and set
        it to main_window's `.previews`."""
        mpq = self.master.mpq
        lddb = self.master.lddb
        # Create a new MP
        new_preview_mp = Plat.MultiPlat.from_queue(
            mpq, settings=self.settings, lddb=lddb)

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
        """Update the preview image and header in the tk window."""

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

    def scroll_preview_left(self):
        """Scroll the preview left."""
        self.scroll_preview(-1)

    def scroll_preview(self, direction=1):
        """Scroll the preview left or right. (right -> +1; left -> -1).
        Defaults to scrolling right."""
        self.preview_index += direction
        if self.preview_index >= len(self.previews):
            # If we've gone over the length of the `.plats` list, reset to 0
            self.preview_index = 0
        if self.preview_index < 0:
            # If we've gone under 0, set to the index of the final element
            # in the `.previews` list
            self.preview_index = len(self.previews) - 1
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
        # Get the name of the preset `Settings` object we'll create.
        preset = self.settings_combo.get()
        return Plat.MultiPlat.from_queue(
            mpq=self.master.mpq, settings=preset, lddb=self.master.lddb)

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

        # TODO: This will probably break.
        index = self.master.preview_frame.preview_index
        if index >= len(mp.plats):
            index = len(mp.plats) - 1

        mp.show(index)

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


if __name__ == '__main__':
    app = MainWindow()
    app.mainloop()