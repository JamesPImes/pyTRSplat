# Copyright (c) 2020, James P. Imes. All rights reserved.

"""
A basic GUI for pyTRSplat.
"""

# TODO: This first version was hacked together pretty quickly. I want to write
#   it properly as I have time. Once I get a decent working version, I want to
#   switch over to using a nicer-looking but non-Python-native GUI module.

# TODO: Allow user to save selected page(s), rather than all.

# TODO: Implement option to view / delete added PLSSDesc objs in mpq.

# TODO: Implement / allow use of 'default' TwpLotDefinitions.

# TODO: Implement custom settings options.

import Plat
import _constants

from pyTRS.interface_tools.config_popup import prompt_config
from pyTRS import pyTRS
from pyTRS import version as pyTRSversion

import tkinter as tk
from tkinter.ttk import Combobox
from tkinter import messagebox, filedialog
from tkinter import Label

from PIL import ImageTk

from pathlib import Path

main_window = tk.Tk()
main_window.title('pyTRSplat - Text-to-Plat Generator')

# Default config parameters for parsing.
main_window.setvar(name='config_text', value='')

# Store an empty LotDefDB object as `.lddb`
main_window.lddb = Plat.LotDefDB()

# Store a (currently empty) queue of all objects to be added to the plat.
main_window.mpq = Plat.MultiPlatQueue()

# A list of Image objects of previews of the plats
main_window.previews = []
# A list of twp/rge (strings) to use as headers for previews of the plats
main_window.previews_twprge = []

# Current index of the preview
main_window.preview_index = 0

# a Settings object for the mini-preview, with no margins. (Hard-coded
# here, rather than creating it as a preset, so that it will never be
# changed to unexpected settings.)
prev_settings = Plat.Settings(preset=None)
prev_settings.qq_side = 8
prev_settings.centerbox_wh = 12
prev_settings.sec_line_stroke = 1
prev_settings.qql_stroke = 1
prev_settings.ql_stroke = 1
prev_settings.sec_line_RGBA = (0, 0, 0, 255)
prev_settings.ql_RGBA = (128, 128, 128, 255)
prev_settings.qql_RGBA = (230, 230, 230, 255)
prev_settings.dim = (
    prev_settings.qq_side * 4 * 6 + prev_settings.sec_line_stroke,
    prev_settings.qq_side * 4 * 6 + prev_settings.sec_line_stroke)
prev_settings.y_top_marg = 0
prev_settings.set_font('sec', size=11)
prev_settings.write_header = False
prev_settings.write_tracts = False
prev_settings.write_lot_numbers = False

########################################################################
# PLSS Descriptions / pyTRS parsing / Load LotDefDB
########################################################################

# For getting the PLSS descriptions from user.
desc_frame = tk.Frame(main_window)
desc_frame.grid(row=0, column=1, sticky='n', padx=5, pady=5)

# For getting .csv file for LotDefDB from user
lddb_save_frame = tk.Frame(desc_frame)
lddb_save_frame.grid(row=5, column=1, sticky='sw')

def cf_btn_clicked():
    config_popup_tk = tk.Toplevel()
    config_popup_tk.title('Set pyTRS Config Parameters')
    prompt_config(
        parameters=[
            'cleanQQ', 'requireColon', 'ocrScrub', 'segment', 'layout'
        ],
        show_save=False, show_cancel=False, config_window=config_popup_tk,
        main_window=main_window)


def parse_btn_clicked():
    """Pull the entered text, and use the chosen config parameters (if
    any) to generate a PLSSDesc object, and add it to the queue to plat."""
    config_text = main_window.getvar(name='config_text')
    descrip_text = desc_box_entry.get("1.0", "end-1c")
    # Create a PLSSDesc object from the supplied text and parse it using the
    # specified config parameters (if any).
    desc = pyTRS.PLSSDesc(descrip_text, config=config_text, initParseQQ=True)

    # Add desc to the MPQ.
    main_window.mpq.queue(desc)

    # Clear the text from the desc_box_entry
    desc_box_entry.delete("1.0", 'end-1c')

    # And update the preview plat.
    gen_preview()


def clear_btn_clicked():
    """Clear all plats and descriptions (reset to start)"""
    prompt = messagebox.askyesno(
        'Confirm?',
        'Delete all added descriptions and reset plats to blank?',
        icon='warning')

    if prompt is True:
        # Set the `.mpq` to an empty MPQ obj
        main_window.mpq = Plat.MultiPlatQueue()

        # Generate a new preview (which will be an empty plat)
        gen_preview()


def lddb_btn_clicked():
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
                main_window.lddb = Plat.LotDefDB(from_csv=lddb_fp)

                # Update the preview window
                gen_preview()

                # Set the label
                max_chars = 20
                name = Path(lddb_fp).name
                if len(name) > max_chars:
                    name = name[:max_chars-3] + '...'
                lddp_fp_text.set(
                    f"Current lot definitions: {name}")

            except:
                messagebox.showerror(
                    'Could Not Load File',
                    f"Chosen file '{lddb_fp}' could not be loaded.")
        else:
            messagebox.showerror(
                '.csv Files Only', 'May only load \'.csv\' files containing '
                                   'lot definitions.')


# Button to configure pyTRS parameters
cf_button = tk.Button(
    desc_frame, text='Configure Parse', height=2,
    command=cf_btn_clicked)
cf_button.grid(row=3, column=1, pady=8, sticky='w')

# Button to commence pyTRS parsing (and add resulting PLSSDesc to MPQ)
parse_button = tk.Button(
    desc_frame, text='Parse Description / Add to Plat', height=2,
    command=parse_btn_clicked)
parse_button.grid(row=3, column=1, pady=8, sticky='e')

desc_box_header = tk.Label(desc_frame, text='Enter land description:')
desc_box_header.grid(row=1, column=1, sticky='w')

desc_box_entry = tk.Text(desc_frame, width=36, height=9)
desc_box_entry.grid(row=2, column=1)

# Button to clear all PLSSDesc's from the MPQ
clear_button = tk.Button(
    desc_frame, text='Clear All Descriptions', height=2,
    command=clear_btn_clicked)
clear_button.grid(row=4, column=1, pady=10, sticky='e')

# Button to load LotDefDB from .csv file
lddb_button = tk.Button(
    desc_frame, text='Get lot definitions from .csv', height=2,
    command=lddb_btn_clicked)
lddb_button.grid(row=4, column=1, pady=10, sticky='w')

lddp_fp_text = tk.StringVar('')
lddb_label = tk.Label(desc_frame, textvariable=lddp_fp_text)
lddb_label.grid(row=5, column=1, sticky='w')

########################################################################
# Platting / pyTRSplat
########################################################################

# For handling everything with the plat, other than getting the PLSS descrips.
plat_frame = tk.Frame(main_window)
plat_frame.grid(row=0, column=2, sticky='n')

# For showing a preview of the plat, and controls for left/right
plat_preview_frame = tk.Frame(plat_frame)
plat_preview_frame.grid(row=1, column=1, sticky='n')
# For showing the preview
plat_preview_display_frame = tk.Frame(plat_preview_frame)
plat_preview_display_frame.grid(row=1, column=1, sticky='n')
# For controlling the preview (scroll left/right)
plat_preview_control_frame = tk.Frame(plat_preview_frame)
plat_preview_control_frame.grid(row=2, column=1, sticky='n')
plat_preview_showfull_frame = tk.Frame(plat_preview_frame)
plat_preview_showfull_frame.grid(row=4, column=1, sticky='n')

# For getting the plat settings from user.
settings_frame = tk.Frame(plat_preview_frame)
settings_frame.grid(row=3, column=1, sticky='n')



####################################
# Generating the Plat(s)
####################################

def gen_plat():
    """Generate and return the Plat(s)."""
    # Get the name of the preset `Settings` object we'll create.
    preset = settings_combo.get()
    return Plat.MultiPlat.from_queue(
        mpq=main_window.mpq, settings=preset, lddb=main_window.lddb)


####################################
# Preview / Save
####################################

preview_disp_header = Label(plat_preview_display_frame, text='Quick Preview')
preview_disp_header.grid(row=1, column=1, pady=2, sticky='n')

# A label below the preview image to display T&R
preview_footer = tk.StringVar('')
preview_disp_footer = Label(
    plat_preview_display_frame, textvariable=preview_footer)
preview_disp_footer.grid(row=3, column=1, sticky='n')

def gen_preview():
    """Generate a new list of preview plats (Image objects) and set it
    to main_window's `.previews`."""
    mpq = main_window.mpq
    lddb = main_window.lddb
    # Create a new MP
    new_preview_mp = Plat.MultiPlat.from_queue(
        mpq, settings=prev_settings, lddb=lddb)

    # Tracking if we're displaying a dummy (empty plat)
    dummy_set = False

    # If there's nothing yet in the MPQ, manually create a 'dummy'
    # plat and append it, so that there's something to show (an empty plat)
    if len(mpq.keys()) == 0:
        dummy = Plat.Plat(settings=prev_settings)
        new_preview_mp.plats.append(dummy)
        dummy_set = True

    # Output the plat images to a list, and set to `.previews`
    main_window.previews = new_preview_mp.output()

    # And create a list of 'twprge' values for each of the images, and
    # set to `.previews_twprge`.
    main_window.previews_twprge = []
    for plObj in new_preview_mp.plats:
        main_window.previews_twprge.append(plObj.twprge)

    # Update the preview display
    update_preview_mp_display()

    # If we did set a dummy, clear the footer.
    if dummy_set:
        preview_footer.set('')

def update_preview_mp_display(index=None):
    """Update the preview image and header in the tk window."""

    if index is None:
        index = main_window.preview_index

    # Pull the image from the `.previews` list, and convert it to
    # `ImageTk.PhotoImage` obj
    if index > len(main_window.previews) -1:
        index = 0
        main_window.preview_index = 0
    img = main_window.previews[index]
    preview = ImageTk.PhotoImage(img)

    # Display the preview in this label.
    preview_disp_label = Label(plat_preview_display_frame, image=preview)
    preview_disp_label.image = preview
    preview_disp_label.grid(row=2, column=1, sticky='n')

    # Also update the footer.
    foot_txt = main_window.previews_twprge[index]
    foot_txt = f"{foot_txt}  [{index + 1} / {len(main_window.previews)}]"
    preview_footer.set(foot_txt)



def scroll_preview_left():
    """Scroll the preview left."""
    scroll_preview(-1)


def scroll_preview(direction=1):
    """Scroll the preview left or right. (right -> +1; left -> -1).
    Defaults to scrolling right."""
    main_window.preview_index += direction
    if main_window.preview_index >= len(main_window.previews):
        # If we've gone over the length of the `.plats` list, reset to 0
        main_window.preview_index = 0
    if main_window.preview_index < 0:
        # If we've gone under 0, set to the index of the final element
        # in the `.previews` list
        main_window.preview_index = len(main_window.previews) - 1
    update_preview_mp_display()


def preview_btn_clicked():
    """Generate the MultiPlat and display one of the plats from it. If
    the desired `index` is greater than the number of plats generated,
    will show the final one."""
    mp = gen_plat()
    if len(mp.plats) == 0:
        messagebox.showinfo(
            'No plats',
            'No plats to preview. Add land descriptions and try again.')
        return

    index = main_window.preview_index
    if index >= len(mp.plats):
        index = len(mp.plats) - 1

    mp.show(index)


def save_btn_clicked():
    """Generate plats and save them to .png or .pdf at user-selected
    filepath."""

    mp = gen_plat()
    if len(mp.plats) == 0:
        messagebox.showinfo(
            'No plats',
            'No plats to save. Add land descriptions and try again.')
        return

    write_it = False
    multi_png = False
    start_dir = '/'
    ext = ''

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
            print(start_dir)  # TESTING

        if save_fp.lower().endswith('.pdf'):
            write_it = True
            ext = '.pdf'
            break

        elif save_fp.lower().endswith('.png') and len(main_window.previews) > 1:

            # Generate the warning message, that `.png` will save to multiple.
            msg_txt = (
                'Multiple plats have been generated. When saving to '
                '.png specifically, each file will be saved separately, '
                'as follows:\n'
            )
            for i in range(len(main_window.previews)):
                msg_txt = f"{msg_txt}\n{stem}_{str(i).rjust(3, '0')}.png"
                if i == 3 and len(main_window.previews) > i:
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
        'Success!',  'Plat saved. Open file now?')

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


# Update the `.previews` list
gen_preview()


# Button to scroll preview right
preview_right_button = tk.Button(
    plat_preview_control_frame, text='>', height=1, width=8,
    command=scroll_preview)
preview_right_button.grid(row=1, column=2, padx=8, pady=5, sticky='n')

# Button to scroll preview left
preview_left_button = tk.Button(
    plat_preview_control_frame, text='<', height=1, width=8,
    command=scroll_preview_left)
preview_left_button.grid(row=1, column=1, padx=8, pady=5, sticky='n')

# Button to show a full-sized version of the preview, using current settings
preview_full_button = tk.Button(
    plat_preview_showfull_frame, text='Page Preview', height=2, width=12,
    command=preview_btn_clicked)
preview_full_button.grid(row=2, column=1, padx=4, pady=5, sticky='w')

# Button to save plats
save_button = tk.Button(
    plat_preview_showfull_frame, text='Save Plats', height=2, width=12,
    command=save_btn_clicked)
save_button.grid(row=2, column=2, padx=4, pady=5, sticky='e')

####################################
# Choosing Plat Settings
####################################

settings_label = Label(settings_frame, text='Output settings:')
settings_label.grid(row=2, column=1, pady=3, sticky='e')

settings_combo = Combobox(settings_frame, width=9)
avail_presets = Plat.Settings.list_presets()
settings_combo['values'] = avail_presets
settings_combo.grid(row=2, column=2, sticky='w')
# Set the combo to 'default' preset. (If that doesn't exist, set to
# whatever's first in the list.)
try:
    settings_index = avail_presets.index('default')
except ValueError:
    settings_index = 0
settings_combo.current(settings_index)


########################################################################
# About
########################################################################

def about_btn_clicked():
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


# Button to display 'about' info
about_button = tk.Button(
    desc_frame, text='About', height=1, width=6,
    command=about_btn_clicked)
about_button.grid(row=6, column=1, padx=4, pady=2, sticky='sw')


main_window.mainloop()