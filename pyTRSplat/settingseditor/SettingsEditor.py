# Copyright (c) 2020, James P. Imes. All rights reserved.

"""
A GUI tkinter Frame for configuring Settings objects in the pyTRSplat
module.
"""

import tkinter as tk
from tkinter.ttk import Combobox, Checkbutton
from tkinter import messagebox, filedialog

from pyTRSplat.plat import MultiPlat
from pyTRSplat.platsettings import Settings
from pyTRSplat.imgdisplay import ScrollResizeDisplay

class SettingsEditor(tk.Frame):
    """
    The controller for an _EditorFrame object, including high-level
    functions (Load, Save, etc.).
    """
    EFRAME_ROW = 2
    EFRAME_COLUMN = 0

    AVAIL_PRESETS = Settings.list_presets()

    def __init__(
            self, master=None, first_settings_obj=None,
            show_ok=False, show_cancel=False, show_save_preset=True,
            show_load_preset=True, show_save_custom=False,
            show_load_custom=False):
        """
        The controller for an _EditorFrame object, including high-level
        functions (Load, Save, etc.). Note that OK and Cancel buttons
        can be placed or hidden with parameters `show_ok=True` and
        `show_cancel=True`, but they have no effect in this class. To
        give them any effect, create a subclass and customize
        `ok_btn_clicked()` and `cancel_btn_clicked()`, as needed for a
        given application.

        :param master:
        :param first_settings_obj: The Settings object whose data will
        populate the fields when the frame is first loaded.
        :param show_ok:
        :param show_cancel:
        :param show_save_preset:
        :param show_load_preset:
        :param show_save_custom:
        :param show_load_custom:
        """
        tk.Frame.__init__(self, master=master)
        self.master = master

        #########################################
        # CONTROL FRAME
        #########################################
        control_frame = tk.Frame(self)
        control_frame.grid(row=0, column=0, sticky='nesw')

        ctrl_next_col = 0
        self.preview_btn = tk.Button(
            control_frame, text='View Example Plat', command=self.preview_btn_clicked)
        self.preview_btn.grid(row=0, column=ctrl_next_col, padx=4, pady=4, sticky='w')
        ctrl_next_col += 1
        tk.Label(control_frame, width=2).grid(row=0, column=ctrl_next_col)
        ctrl_next_col += 1

        # SAVE PRESET -----------------------------
        self.ok_button = tk.Button(
            control_frame, text='OK', command=self.ok_btn_clicked, padx=4)

        if show_ok:
            self.ok_button.grid(row=0, column=ctrl_next_col)
            ctrl_next_col += 1
            tk.Label(control_frame, width=2).grid(row=0, column=ctrl_next_col)
            ctrl_next_col += 1

        # TODO: Cancel button

        # SAVE PRESET -----------------------------
        self.save_preset_btn = tk.Button(
            control_frame, text='Save as preset named:',
            command=self.save_preset_btn_clicked)
        self.new_preset_name = tk.Entry(control_frame, width=14)

        if show_save_preset:
            self.save_preset_btn.grid(row=0, column=ctrl_next_col)
            ctrl_next_col += 1
            self.new_preset_name.grid(row=0, column=ctrl_next_col)
            ctrl_next_col += 1
            tk.Label(control_frame, width=2).grid(row=0, column=ctrl_next_col)
            ctrl_next_col += 1

        # LOAD PRESET -----------------------------
        self.load_preset_btn = tk.Button(
            control_frame, text='Load preset:',
            command=self.load_preset_btn_clicked)
        self.load_preset_name = Combobox(
            control_frame, width=10)
        self.load_preset_name['values'] = self.AVAIL_PRESETS
        # Set the combo to 'default' preset. (If that doesn't exist, set to
        # whatever's first in the list.)
        try:
            settings_index = self.AVAIL_PRESETS.index('default')
        except ValueError:
            settings_index = 0
        self.load_preset_name.current(settings_index)

        if show_load_preset:
            self.load_preset_btn.grid(row=0, column=ctrl_next_col)
            ctrl_next_col += 1
            self.load_preset_name.grid(row=0, column=ctrl_next_col)
            ctrl_next_col += 1
            tk.Label(control_frame, width=2).grid(row=0, column=ctrl_next_col)
            ctrl_next_col += 1

        # TODO: Save custom to .txt file

        # TODO: Load custom from .txt file

        #########################################
        # EDITOR FRAME
        #########################################
        self.editor = _EditorFrame(self, load_settings=first_settings_obj)
        self.editor.grid(
            row=self.EFRAME_ROW, column=self.EFRAME_COLUMN, sticky='nesw')

    def ok_btn_clicked(self):
        """
        No effect. Customize this method if using the OK button for an
        application.
        """
        pass

    def preview_btn_clicked(self):
        """
        Show an example plat using the current settings.
        """

        # Compile a Settings object
        set_obj = self.editor.compile_settings()
        if set_obj is False:
            return False

        from pyTRS import PLSSDesc

        # Create a dummy PLSSDesc object, and generate a MultiPlat
        t = (
            'T154N-R97W\n'
            'Sec 1: Lots 1 - 3, S/2N/2\n'
            'Sec 5: Lot 4, The South Half of the Northwest Quarter, and '
            'The Southwest Quarter\n'
            'Sec 6: Lots 1 - 7, S/2NE/4, SE/4NW/4, E/2SW/4, SE/4\n'
            'Sec 12: Example tract with no identifiable Lots or QQs\n'
            'Sec 13: That portion of the E/2 lying north of the river and '
            'west of the private road right-of-way as more particularly '
            'described in Book 1234 / Page 567, recorded on January 1, '
            '1964 in the records of Example County, as amended in that '
            'Right-of-Way Amendment Agreement dated December 10, 1987, '
            'recorded on December 11, 1987 as Document No. 1987-1234567 '
            'of the records of Example County.\n'
            'Sec 14: NE/4\n'
        )
        d = PLSSDesc(t, initParseQQ=True)
        mp = MultiPlat.from_plssdesc(
            d, settings=set_obj, allow_ld_defaults=True)
        im = mp.output()[0]

        # Launch a preview window with this plat
        try:
            self.preview_window.destroy()
        except:
            pass
        self.preview_window = tk.Toplevel(self)
        self.preview_window.title('pyTRSplat - Settings Editor [Example Plat]')
        disp = ScrollResizeDisplay(self.preview_window, img=im)
        disp.pack()

    def save_preset_btn_clicked(self):
        # TODO: Check / confirm overwrite.
        name = self.new_preset_name.get().strip().lower()
        legal_check = name.split('_')
        for chk in legal_check:
            if not chk.isalnum():
                tk.messagebox.showerror(
                    'Invalid Preset Name',
                    'Preset names may contain only letters, numbers, and '
                    'underscores.')
                self.focus()
                return
        set_obj = self.editor.compile_settings()
        set_obj.save_preset(name)
        if name not in self.AVAIL_PRESETS:
            # Update the load_preset_name combobox.
            self.AVAIL_PRESETS.append(name)
            self.load_preset_name['values'] = self.AVAIL_PRESETS
            # Set the combo to 'default' preset. (If that doesn't exist, set to
            # whatever's first in the list.)
            try:
                settings_index = self.AVAIL_PRESETS.index(name)
                self.load_preset_name.current(settings_index)
            except ValueError:
                pass
        tk.messagebox.showinfo('Success', f"Preset has been saved as '{name}'.")
        self.focus()

    def load_preset_btn_clicked(self):
        # TODO: CONFIRM DISCARD CURRENT
        name = self.load_preset_name.get()
        if name not in self.AVAIL_PRESETS:
            tk.messagebox.showerror(
                'Preset Name Not Found',
                f"Could not find preset '{name}'. Check the name and try "
                "again.")
            self.focus()
            return
        set_obj = Settings(preset=name)
        self.new_load(set_obj)

    def new_load(self, settings: Settings):
        self.editor.destroy()
        self.editor = _EditorFrame(self, load_settings=settings)
        self.editor.grid(
            row=self.EFRAME_ROW, column=self.EFRAME_COLUMN, sticky='nesw')


class _EditorFrame(tk.Frame):
    """
    A widget for creating, editing, and saving Settings objects for the
    pyTRSplat module. (Not for direct use. SettingsEditor object embeds
    / controls this object.)
    """

    MW_PADX = 4
    MW_PADY = 1

    FIRST_WRITE_CHKBTN_ROW = 5

    SM_ENTRYBOX_WIDTH = 3
    MID_ENTRYBOX_WIDTH = 6
    ENTRYBOX_PADX = 4
    INNER_LBL_PADX = 4

    DIM_ROW = 1
    GRID_MARG_FIRST_ROW = 2
    LINE_CONFIG_FIRST_ROW = 30

    # For pulling typeface keys by value
    TYPEFACES_BY_FP = {}
    for k, v in Settings.TYPEFACES.items():
        TYPEFACES_BY_FP[v] = k
    DEFAULT_FONT_KEY = 'Sans-Serif'

    def __init__(self, master=None, load_settings=None):
        tk.Frame.__init__(self, master=master)
        self.master = master

        if load_settings is None:
            load_settings = Settings(preset=None)
        ls = load_settings

        # TODO: Toggle displaying px or inches
        # TODO: Configure ppi (when displaying inches)

        #################################
        # DIMENSIONS / MARGINS
        #################################
        dim_frame = tk.Frame(self)
        dim_frame.grid(row=self.DIM_ROW, column=1, sticky='w')
        self.page_width = self.IntVarSetter(
            dim_frame, var_name='RAW_width', display_name='Page Width',
            start_val=ls.dim[0])
        self.page_width.grid(
            row=0, column=1, padx=self.MW_PADX, pady=self.MW_PADY, sticky='w')
        self.page_height = self.IntVarSetter(
            dim_frame, var_name='RAW_width', display_name='Page Height',
            start_val=ls.dim[1])
        self.page_height.grid(
            row=0, column=2, padx=self.MW_PADX, pady=self.MW_PADY, sticky='w')

        # Main margins
        next_avail_row = self.GRID_MARG_FIRST_ROW
        self.y_top_marg = self.IntVarSetter(
            self, var_name='y_top_marg',
            display_name='Upper Margin (Grid)', start_val=ls.y_top_marg)
        self.y_top_marg.grid(
            row=next_avail_row, column=1,
            padx=self.MW_PADX, pady=self.MW_PADY, sticky='w')
        next_avail_row += 1

        self.y_bottom_marg = self.IntVarSetter(
            self, var_name='y_bottom_marg', start_val=ls.y_bottom_marg,
            display_name='Bottom Margin (Entire Page)')
        self.y_bottom_marg.grid(
            row=next_avail_row, column=1,
            padx=self.MW_PADX, pady=self.MW_PADY, sticky='w')
        next_avail_row += 1

        self.qq_side = self.QQSideSetter(
            self, var_name='qq_side',
            display_name='Side length of each QQ square', start_val=ls.qq_side)
        self.qq_side.grid(
            row=next_avail_row, column=1,
            padx=self.MW_PADX, pady=self.MW_PADY, sticky='w')
        # TODO: Display left/right margins that are left after this setting
        # TODO: Optional set-by-LR-margin.
        next_avail_row += 1

        cb_text = (
            'Size of area to clear at center of each '
            'section for writing section number'
        )
        self.centerbox_wh = self.IntVarSetter(
            self, var_name='centerbox_wh', display_name=cb_text,
            start_val=ls.centerbox_wh)
        self.centerbox_wh.grid(row=next_avail_row, column=1, sticky='w', padx=self.MW_PADX,
            pady=self.MW_PADY)
        next_avail_row += 1

        #################################
        # CONFIGURE LINES / FILL
        #################################

        self.qq_fill_RGBA = self.QQColorSetter(self, RGBA=ls.qq_fill_RGBA)
        self.qq_fill_RGBA.grid(
            row=next_avail_row, column=1, sticky='w', padx=self.MW_PADX,
            pady=self.MW_PADY)
        next_avail_row += 1

        next_avail_row = self.LINE_CONFIG_FIRST_ROW
        self.sec_line = self.LineSetter(
            self, var_name='sec_line', display_name='Section Line',
            stroke=ls.sec_line_stroke, RGBA=ls.sec_line_RGBA)
        self.sec_line.grid(row=next_avail_row, column=1, sticky='w')
        next_avail_row += 1

        self.ql_line = self.LineSetter(
            self, var_name='ql', display_name='Half-Dividing Line',
            stroke=ls.ql_stroke, RGBA=ls.ql_RGBA)
        self.ql_line.grid(row=next_avail_row, column=1, sticky='w')
        next_avail_row += 1

        self.qql_line = self.LineSetter(
            self, var_name='qql', display_name='Quarter-Dividing Line',
            stroke=ls.qql_stroke, RGBA=ls.qql_RGBA)
        self.qql_line.grid(row=next_avail_row, column=1, sticky='w')
        next_avail_row += 1

        #################################
        # WHAT TO WRITE / FONTS / TEXT CONFIGURE
        #################################
        self.write_header = tk.BooleanVar(
            self, value=ls.write_header, name='write_header')
        self.write_header_chkbtn = Checkbutton(
            self, text='Write Header in Top Margin', onvalue=True,
            offvalue=False, variable=self.write_header)
        self.write_header_chkbtn.grid(
            row=next_avail_row, column=1, sticky='w', padx=self.MW_PADX,
            pady=self.MW_PADY)
        next_avail_row += 1

        tf = _EditorFrame.TYPEFACES_BY_FP.get(
            ls.headerfont_typeface, _EditorFrame.DEFAULT_FONT_KEY)
        self.header_font = self.FontSetter(
            self, font_size=ls.headerfont_size, display_name='Header Font',
            var_name='headerfont', typeface=tf, RGBA=ls.headerfont_RGBA)
        self.header_font.grid( row=next_avail_row, column=1, sticky='w')
        next_avail_row += 1

        self.y_header_marg = self.IntVarSetter(
            self, var_name='y_header_marg', start_val=ls.y_header_marg,
            display_name='How far above grid to write header (within top margin)')
        self.y_header_marg.grid(
            row=next_avail_row, column=1, padx=self.MW_PADX, pady=self.MW_PADY,
            sticky='w')
        next_avail_row += 1

        self.write_section_numbers = tk.BooleanVar(
            self, value=ls.write_section_numbers, name='write_section_numbers')
        self.write_section_numbers_chkbtn = Checkbutton(
            self, text='Write Section Numbers', onvalue=True,
            offvalue=False, variable=self.write_section_numbers)
        self.write_section_numbers_chkbtn.grid(
            row=next_avail_row, column=1, sticky='w', padx=self.MW_PADX,
            pady=self.MW_PADY)
        next_avail_row += 1

        tf = _EditorFrame.TYPEFACES_BY_FP.get(
            ls.secfont_typeface, _EditorFrame.DEFAULT_FONT_KEY)
        self.section_numbers_font = self.FontSetter(
            self, font_size=ls.secfont_size, display_name='Section Number Font',
            var_name='secfont', typeface=tf, RGBA=ls.secfont_RGBA)
        self.section_numbers_font.grid(row=next_avail_row, column=1, sticky='w')
        next_avail_row += 1

        self.write_lot_numbers = tk.BooleanVar(
            self, value=ls.write_lot_numbers, name='write_lot_numbers')
        self.write_lot_numbers_chkbtn = Checkbutton(
            self, text='Write lot numbers within the appropriate QQ(s)',
            onvalue=True, offvalue=False, variable=self.write_lot_numbers)
        self.write_lot_numbers_chkbtn.grid(
            row=next_avail_row, column=1, sticky='w', padx=self.MW_PADX,
            pady=self.MW_PADY)
        next_avail_row += 1

        tf = _EditorFrame.TYPEFACES_BY_FP.get(
            ls.lotfont_typeface, _EditorFrame.DEFAULT_FONT_KEY)
        self.lot_font = self.FontSetter(
            self, font_size=ls.lotfont_size, display_name='Lot Number Font',
            var_name='lotfont', typeface=tf, RGBA=ls.lotfont_RGBA)
        self.lot_font.grid(row=next_avail_row, column=1, sticky='w')
        next_avail_row += 1

        self.lot_num_offset_px = self.IntVarSetter(
            self, var_name='lot_num_offset_px', start_val=ls.lot_num_offset_px,
            display_name='Lot number distance from top-left corner of QQ (in px)')
        self.lot_num_offset_px.grid(
            row=next_avail_row, column=1, padx=self.MW_PADX, pady=self.MW_PADY,
            sticky='w')
        next_avail_row += 1

        self.write_tracts = tk.BooleanVar(
            self, value=ls.write_tracts, name='write_tracts')
        self.write_tracts_chkbtn = Checkbutton(
            self, text='Write all tracts at the bottom', onvalue=True,
            offvalue=False, variable=self.write_tracts)
        self.write_tracts_chkbtn.grid(
            row=next_avail_row, column=1, sticky='w', padx=self.MW_PADX,
            pady=self.MW_PADY)
        next_avail_row += 1

        tf = _EditorFrame.TYPEFACES_BY_FP.get(
            ls.tractfont_typeface, _EditorFrame.DEFAULT_FONT_KEY)
        self.tract_font = self.FontSetter(
            self, font_size=ls.tractfont_size, display_name='Tract Font',
            var_name='tractfont', typeface=tf, RGBA=ls.tractfont_RGBA)
        self.tract_font.grid(row=next_avail_row, column=1, sticky='w')
        next_avail_row += 1

        # A customized RGBASetter for warningfont_RGBA, since we don't
        # need to set typeface or size:
        wfont_txt = 'Font color for writing errors/warnings'
        self.warning_font_RGBA = _EditorFrame.RGBASetter(
            self, display_name=wfont_txt, show_opacity=False,
            var_name='warningfont_RGBA', RGBA=ls.warningfont_RGBA)
        self.warning_font_RGBA.rgba_frame.grid(row=0, column=1)
        lbl = tk.Label(self.warning_font_RGBA, text=wfont_txt)
        lbl.grid(row=0, column=0)
        self.warning_font_RGBA.grid(row=next_avail_row, column=1, sticky='w')
        next_avail_row += 1

        #################################
        # TractTextBox margins and other tract-writing configurables
        #################################
        self.y_px_before_tracts = self.IntVarSetter(
            self, var_name='y_px_before_tracts', start_val=ls.y_px_before_tracts,
            display_name='Distance between bottom of the grid and the first written tract')
        self.y_px_before_tracts.grid(
            row=next_avail_row, column=1, padx=self.MW_PADX, pady=self.MW_PADY,
            sticky='w')
        next_avail_row += 1

        self.x_text_left_marg = self.IntVarSetter(
            self, var_name='x_text_left_marg', start_val=ls.x_text_left_marg,
            display_name='Left Margin (for tract text below grid)')
        self.x_text_left_marg.grid(
            row=next_avail_row, column=1, padx=self.MW_PADX, pady=self.MW_PADY,
            sticky='w')
        next_avail_row += 1

        self.x_text_right_marg = self.IntVarSetter(
            self, var_name='x_text_right_marg', start_val=ls.x_text_right_marg,
            display_name='Right Margin (for tract text below grid)')
        self.x_text_right_marg.grid(
            row=next_avail_row, column=1, padx=self.MW_PADX, pady=self.MW_PADY,
            sticky='w')
        next_avail_row += 1

        self.y_px_between_tracts = self.IntVarSetter(
            self, var_name='y_px_between_tracts',
            start_val=ls.y_px_between_tracts,
            display_name='Space between lines of text')
        self.y_px_between_tracts.grid(
            row=next_avail_row, column=1, padx=self.MW_PADX, pady=self.MW_PADY,
            sticky='w')
        next_avail_row += 1

        self.paragraph_indent = self.IntVarSetter(
            self, var_name='paragraph_indent', start_val=ls.paragraph_indent,
            display_name='Paragraph indent (in spaces, not pixels or inches)')
        self.paragraph_indent.grid(
            row=next_avail_row, column=1, padx=self.MW_PADX, pady=self.MW_PADY,
            sticky='w')
        next_avail_row += 1

        self.new_line_indent = self.IntVarSetter(
            self, var_name='new_line_indent', start_val=ls.new_line_indent,
            display_name='Linebreak indent (in spaces, not pixels or inches)')
        self.new_line_indent.grid(
            row=next_avail_row, column=1,
            padx=self.MW_PADX, pady=self.MW_PADY, sticky='w')
        next_avail_row += 1

        self.justify_tract_text = tk.BooleanVar(
            self, value=ls.justify_tract_text, name='justify_tract_text')
        self.justify_tract_text_chkbtn = Checkbutton(
            self, text='Justify tract text', onvalue=True, offvalue=False,
            variable=self.justify_tract_text)
        self.justify_tract_text_chkbtn.grid(
            row=next_avail_row, column=1, sticky='w', padx=self.MW_PADX,
            pady=self.MW_PADY)
        next_avail_row += 1

        # Set the bool variables, according to the attributes in `ls`
        # (i.e. enact the settings in the `load_settings` object).
        # Note: This is not optimal design, but it seems to solve a
        # weird bug. Back when these values were set at the time that
        # the variables/checkbuttons themselves were created, the
        # _EditorFrame would fail to actually set them (to either True
        # or False), maybe 5% of the time. When clicking "Load Preset"
        # button repeatedly, with nothing different, would sometimes get
        # different results, and I could not reliably recreate the bug.
        # This is ineligant, but seems(?) to fix it...
        for var_name in ['write_header', 'write_section_numbers',
                    'write_lot_numbers', 'write_tracts', 'justify_tract_text']:
            getattr(self, var_name).set(getattr(ls, var_name))

    def compile_settings(self):
        """
        Compile all of the configured parameters into a Settings object,
        and return that object.
        IMPORTANT: Returns `False` if any fields contained invalid values.
        """

        #TODO: Error-check any impossible parameters (margins too big, etc.)

        settings = []
        w = self.page_width.compile()
        h = self.page_height.compile()
        dim = f"dim={w},{h}"
        settings.append(dim)
        settings.append(self.qq_side.compile())
        settings.append(self.y_bottom_marg.compile())
        settings.append(self.header_font.compile())
        settings.append(self.y_header_marg.compile())
        settings.append(self.tract_font.compile())
        settings.append(self.section_numbers_font.compile())
        settings.append(self.lot_font.compile())
        warning_RGBA = self.warning_font_RGBA.compile_RGBA()
        if warning_RGBA is False:
            settings.append(warning_RGBA)
        else:
            settings.append(
                f"warningfont_RGBA={warning_RGBA}")
        settings.append(self.compile_checkbuttons())
        settings.append(self.y_top_marg.compile())
        settings.append(self.lot_num_offset_px.compile())
        settings.append(self.y_px_before_tracts.compile())
        settings.append(self.sec_line.compile())
        settings.append(self.ql_line.compile())
        settings.append(self.qql_line.compile())
        settings.append(self.qq_fill_RGBA.compile())
        settings.append(self.centerbox_wh.compile())
        settings.append(self.x_text_left_marg.compile())
        settings.append(self.x_text_right_marg.compile())
        settings.append(self.y_px_between_tracts.compile())
        settings.append(self.paragraph_indent.compile())
        settings.append(self.new_line_indent.compile())
        settings.append(self.qq_fill_RGBA.compile())

        # Check for any errors:
        for setting in settings:
            if setting is False:
                return False
        settings_text = '\n'.join(settings)
        set_obj = Settings()
        set_obj._parse_text_to_settings(settings_text)
        return set_obj

    def warning(self, title, message):
        """
        Show a warning, then reset focus on the window.
        """
        tk.messagebox.showwarning(title, message)
        self.focus()

    def compile_checkbuttons(self) -> str:
        """
        Compile parameters that are configured in Checkbuttons within
        the main window. Return as string.
        """
        txt = ''
        # For each of these var_names, check the state of the checkbutton
        # and set the val accordingly.
        #
        # Note: This is not optimal design, but it seems to solve a
        # weird bug. Checking the BooleanVar values with .get() seemed
        # to set the state of the checkboxes to 'alternate' maybe 5% of
        # the time, and I couldn't recreate it reliably to debug it.
        # This is ineligant, but seems(?) to fix it...
        for var_name in ['write_header', 'write_section_numbers',
                    'write_lot_numbers', 'write_tracts', 'justify_tract_text']:
            chkbtn = getattr(self, var_name + '_chkbtn')
            val = False
            if 'selected' in chkbtn.state():
                val = True
                chkbtn.state(['selected'])
            else:
                chkbtn.state(['!selected'])
            chkbtn.state(['!alternate'])

            txt = f"{txt}{var_name}={val}\n"

        return txt

    class RGBASetter(tk.Frame):
        """
        The skeleton of a class that uses RGBAWidget. Not used directly,
        but allows child classes to inherit `.compile_RGBA()` method.

        IMPORTANT:
        Creates `self.rgba_frame` but does NOT place it on the grid;
        must call `rgba_frame.grid(...)` for every subclass!
        """

        def __init__(
                self, master=None, display_name='', var_name='',
                RGBA=(0, 0, 0, 255), show_opacity=True):
            """
            :param display_name: The public display name of the variable
            (for warning message purposes).
            :param var_name: The name of the variable (corresponding to
            the attribute name of a Settings object).
            :param RGBA: The starting RGBA values.
            :param show_opacity: Whether to give the option to set
            opacity.
            """

            tk.Frame.__init__(self, master=master)
            self.master = master
            self.display_name = display_name
            self.var_name = var_name
            self.show_opacity = show_opacity

            # RGBA
            self.R, self.G, self.B, self.A = None, None, None, None
            self.rgba_frame = self.RGBAWidget(self, RGBA=RGBA)
            self.rgba_frame.grid(row=0, column=0)

        def compile_RGBA(self) -> str:
            """
            Compile the entered RGBA values into a string, formatted
            '(0,0,0,0)'. If invalid values have been entered, will
            instead show a popup error message and return `False`.
            """
            try:
                r = int(self.R.get())
                g = int(self.G.get())
                b = int(self.B.get())
                a = int(self.A.get())
                for i in [r, g, b, a]:
                    if i < 0 or i > 255:
                        raise ValueError
            except ValueError:
                opacity_txt = ''
                if self.show_opacity:
                    opacity_txt = ' and Opacity'
                self.master.warning(
                    'Invalid RGBA',
                    "Error: Enter numerical values (0 to 255) for "
                    f"RGB{opacity_txt} for <{self.display_name}>.")
                return False
            return f"{r},{g},{b},{a}"

        def rgb_to_hex(self) -> str:
            """
            Convert the current RGB values to a hex string.
            """
            try:
                r = int(self.R.get())
                g = int(self.G.get())
                b = int(self.B.get())
                rgb_as_hex = '#'
                for i in [r, g, b]:
                    if i < 0 or i > 255:
                        raise ValueError
                    h = hex(i).split('x')[-1]
                    h = h.rjust(2, '0')
                    rgb_as_hex = rgb_as_hex + h
                return rgb_as_hex
            except:
                return False

        class RGBAWidget(tk.Frame):
            """
            A frame for setting RGBA values.  (Note: `.R`, `.G`, `.B`,
            and `A.` are set for `master`, not for `self`.)
            """
            DISPLAY_COLOR_PREVIEW = True

            def __init__(
                    self, master=None, RGBA=(0, 0, 0, 255)):
                tk.Frame.__init__(self, master)
                self.master = master
                lbl = tk.Label(self, text='RGB color values (0-255):')
                lbl.grid(
                    row=0, column=0, sticky='w',
                    padx=_EditorFrame.INNER_LBL_PADX)
                self.show_opacity = master.show_opacity

                self.master.R = tk.Entry(
                    self, width=_EditorFrame.SM_ENTRYBOX_WIDTH)
                self.master.R.grid(
                    row=0, column=1, sticky='w',
                    padx=_EditorFrame.ENTRYBOX_PADX)
                self.master.R.insert(tk.END, str(RGBA[0]))

                self.master.G = tk.Entry(
                    self, width=_EditorFrame.SM_ENTRYBOX_WIDTH)
                self.master.G.grid(
                    row=0, column=2, sticky='w',
                    padx=_EditorFrame.ENTRYBOX_PADX)
                self.master.G.insert(tk.END, str(RGBA[1]))

                self.master.B = tk.Entry(
                    self, width=_EditorFrame.SM_ENTRYBOX_WIDTH)
                self.master.B.grid(
                    row=0, column=3, sticky='w',
                    padx=_EditorFrame.ENTRYBOX_PADX)
                self.master.B.insert(tk.END, str(RGBA[2]))

                if self.DISPLAY_COLOR_PREVIEW:
                    preview_btn = tk.Button(
                        self, text='Preview:', command=self.update_preview)
                    preview_btn.grid(row=0, column=4, padx=1)

                    self.preview_label = tk.Label(
                        self, bg=master.rgb_to_hex(), width=2)
                    self.preview_label.grid(row=0, column=5, sticky='w')

                lbl = tk.Label(self, text='Opacity (0-255):')
                self.master.A = tk.Entry(
                    self, width=_EditorFrame.SM_ENTRYBOX_WIDTH)
                self.master.A.insert(tk.END, str(RGBA[3]))
                if self.show_opacity:
                    lbl.grid(
                        row=0, column=6, sticky='w',
                        padx=_EditorFrame.INNER_LBL_PADX)
                    self.master.A.grid(
                        row=0, column=7, sticky='w',
                        padx=_EditorFrame.ENTRYBOX_PADX)

            def update_preview(self):
                rgb_as_hex = self.master.rgb_to_hex()
                if rgb_as_hex is False:
                    return
                self.preview_label.config(bg=rgb_as_hex)

    class IntVarSetter(tk.Frame):
        """
        A frame for setting a single-integer type variable.
        """
        def __init__(
                self, master=None, var_name='', display_name='',
                start_val=0):
            tk.Frame.__init__(self, master=master)
            self.editor = master
            self.var_name = var_name
            self.display_name = display_name
            self.v = tk.Entry(master=self,
                              width=_EditorFrame.MID_ENTRYBOX_WIDTH)
            self.v.grid(row=0, column=0, sticky='w',
                        padx=_EditorFrame.ENTRYBOX_PADX)
            self.v.insert(tk.END, str(start_val))
            lbl = tk.Label(self, text=display_name)
            lbl.grid(row=0, column=1, sticky='w',
                     padx=_EditorFrame.INNER_LBL_PADX)

        def compile(self):
            try:
                if self.var_name.startswith('RAW'):
                    return int(self.v.get())
                return f"{self.var_name}={int(self.v.get())}\n"
            except:
                self.master.warning(
                    'Invalid Number',
                    "Error: Enter a numerical value for "
                    f"<{self.display_name}>")
                return False

    class QQSideSetter(IntVarSetter):
        """
        A frame for setting qq_side variable, while also showing the
        resulting margins.
        """
        def __init__(self, master=None, var_name='', display_name='',
                start_val=0):
            _EditorFrame.IntVarSetter.__init__(
                self, master, var_name, display_name, start_val)

            marg_per_qq_btn = tk.Button(
                self, text="Calculate Left/Right Page Margins:", padx=3,
                command=self.marg_per_qq)
            marg_per_qq_btn.grid(row=0, column=3, sticky='e')
            self.lr_marg = tk.Entry(self, width=_EditorFrame.MID_ENTRYBOX_WIDTH)
            self.marg_per_qq()
            self.lr_marg.grid(row=0, column=4, sticky='w')

            qq_per_margin_btn = tk.Button(
                self, text="Calculate QQ side length per specified L/R margins", padx=3,
                command=self.qq_per_margin)
            qq_per_margin_btn.grid(row=0, column=5, sticky='e')

        def qq_per_margin(self):
            """Calculate the qq_side, per lr_marg."""
            try:
                w = int(self.master.page_width.v.get())
                lr_marg = int(self.lr_marg.get())
            except ValueError:
                return False
            qq_side = (w - (lr_marg * 2)) // 24
            if qq_side <= 0:
                return False
            self.v.delete(0, 'end')
            self.v.insert(tk.END, qq_side)

        def marg_per_qq(self):
            """Calculate the lr_marg, per qq_side and width."""
            try:
                w = int(self.master.page_width.v.get())
                qq_side = int(self.v.get())
            except ValueError:
                return False
            lr_marg = (w - (qq_side * 4 * 6)) // 2
            if lr_marg <= 0:
                return False
            self.lr_marg.delete(0, 'end')
            self.lr_marg.insert(tk.END, lr_marg)

    class QQColorSetter(RGBASetter):
        """
        A frame for setting QQ fill color.
        """

        def __init__(
                self, master=None, display_name='QQ Fill',
                var_name='qq_fill_RGBA', RGBA=Settings.RGBA_BLUE_OVERLAY):
            _EditorFrame.RGBASetter.__init__(
                self, master, display_name, var_name, RGBA, show_opacity=True)
            lbl = tk.Label(self, text=display_name, anchor='e')
            lbl.grid(row=0, column=0)

            # This frame is created by the parent class. Only needs to be
            # placed on grid here.
            self.rgba_frame.grid(row=0, column=1, sticky='w')

        def compile(self) -> str:
            """
            Compile the RGBA into the appropriate string.

            :return: A string with the appropriate text.
            """

            # get RGBA
            rgba = self.compile_RGBA()
            if rgba is False:
                return False

            return f"{self.var_name}={rgba}\n"

    class FontSetter(RGBASetter):
        """
        A frame for setting font size, color, and typeface.
        """

        AVAIL_FONTS = list(Settings.TYPEFACES.keys())

        def __init__(
                self, master=None, font_size=12, display_name='', var_name='',
                typeface='Sans-Serif', RGBA=(0,0,0,255)):
            _EditorFrame.RGBASetter.__init__(
                self, master, display_name, var_name, RGBA, show_opacity=False)

            # Font size
            lbl = tk.Label(self, text='Font size:', anchor='e')
            lbl.grid(row=0, column=0)
            self.font_size = tk.Entry(self, width=_EditorFrame.SM_ENTRYBOX_WIDTH)
            self.font_size.grid(
                row=0, column=1, sticky='w', padx=_EditorFrame.ENTRYBOX_PADX)
            self.font_size.insert(tk.END, font_size)

            # Typeface
            lbl = tk.Label(self, text="'Liberation' Font:", anchor='e')
            lbl.grid(row=0, column=2)
            self.typeface = Combobox(self, width=18)
            self.typeface.grid(
                row=0, column=3, sticky='w', padx=_EditorFrame.ENTRYBOX_PADX)

            self.typeface['values'] = self.AVAIL_FONTS
            try:
                typeface_index = self.AVAIL_FONTS.index(typeface)
            except:
                typeface_index = 0
            self.typeface.current(typeface_index)

            # RGBA
            # This frame is created by the parent class. Only needs to be
            # placed on grid here.
            # TODO: Bugfix: why isn't rgba_frame showing up in grid?
            self.rgba_frame.grid(row=0, column=4, sticky='w')

        def compile(self) -> str:
            """
            Compile the size, typeface, and RGBA into the appropriate
            string.

            :return: A string with the appropriate text.
            """

            # Get font size
            try:
                font_size = int(self.font_size.get())
                if font_size < 1:
                    raise ValueError
            except (ValueError, TypeError):
                self.master.warning(
                    'Invalid Stroke',
                    "Error: Enter a positive numerical value for 'size' for "
                    f"<{self.display_name}>")
                return False
            txt = f"{self.var_name}_size={font_size}\n"

            # Get typeface
            typeface_fp = Settings.TYPEFACES.get(self.typeface.get())
            if typeface_fp is False:
                self.master.warning(
                    'Invalid Font',
                    "Error: Choose one of the available fonts for "
                    f"<{self.display_name}>")
                return False
            txt = (
                f"{txt}{self.var_name}_typeface="
                f"{Settings.TYPEFACES[self.typeface.get()]}\n"
            )

            # get RGBA
            rgba = self.compile_RGBA()
            if rgba is False:
                return False

            return f"{txt}{self.var_name}_RGBA={rgba}\n"

    class LineSetter(RGBASetter):
        """
        A frame for setting a line (Section, Half, Quarter).
        Possible `var_name` options: 'sec_line', 'ql', 'qql'
        """
        MAIN_LBL_WID = 18

        def __init__(
                self, master=None, var_name='', display_name='', stroke=1,
                RGBA=(0, 0, 0, 255)):
            _EditorFrame.RGBASetter.__init__(
                self, master, display_name, var_name, RGBA, show_opacity=False)
            self.master = master
            lbl = tk.Label(
                self, text=display_name + ':', width=self.MAIN_LBL_WID, anchor='w')
            lbl.grid(
                row=0, column=0, sticky='w', padx=_EditorFrame.INNER_LBL_PADX)

            # Stroke
            lbl = tk.Label(self, text='stroke (px):')
            lbl.grid(
                row=0, column=1, sticky='w', padx=_EditorFrame.INNER_LBL_PADX)
            self.stroke = tk.Entry(self, width=_EditorFrame.SM_ENTRYBOX_WIDTH)
            self.stroke.grid(
                row=0, column=2, sticky='w', padx=_EditorFrame.ENTRYBOX_PADX)
            self.stroke.insert(tk.END, str(stroke))

            # RGBA
            # This frame is created by the parent class. Only needs to be
            # placed on grid here.
            self.rgba_frame.grid(row=0, column=3)

        def compile(self):
            """
            Compile stroke and RGBA into the appropriate string. Returns
            `False` if either contained invalid values.
            """

            try:
                strk = int(self.stroke.get())
                if strk < 1:
                    raise ValueError
            except (ValueError, TypeError):
                self.master.warning(
                    'Invalid Stroke',
                    "Error: Enter a positive numerical value for 'stroke' for "
                    f"<{self.display_name}>")
                return False
            txt = f"{self.var_name}_stroke={strk}\n"
            rgba = self.compile_RGBA()
            if rgba is False:
                return False
            return f"{txt}{self.var_name}_RGBA={rgba}\n"


def launch_settings_editor():
    main = tk.Tk()
    main.title('pyTRSplat - Settings Editor')
    setwindow = SettingsEditor(main, first_settings_obj=Settings())
    setwindow.grid(row=0, column=0, sticky='w', pady=5)
    main.mainloop()

if __name__ == '__main__':
    launch_settings_editor()
