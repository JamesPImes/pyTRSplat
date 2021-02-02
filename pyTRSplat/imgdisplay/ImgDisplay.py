# Copyright (c) 2020, James P. Imes, all rights reserved.

import tkinter as tk
from tkinter import messagebox, filedialog

from PIL import ImageTk

class ScrollResizeDisplay(tk.Frame):
    """
    A frame that displays an image, which can be scaled and scrolled
    with built-in controls and scrollers.
    """

    def __init__(self, master=None, img=None, **kw):
        tk.Frame.__init__(self, master=master, **kw)
        self.master = master

        #########################################
        # Control Frame / Buttons
        #########################################

        control_frame = tk.Frame(master=self)
        control_frame.grid(row=1, column=1, sticky='w')

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
        self.canvas_w_max = 800
        self.canvas_w_min = 800
        self.canvas_h_max = 600
        self.canvas_h_min = 600

        self.img = img
        self.shown_img = ImageTk.PhotoImage(img, master=self)

        ###################
        # A subframe for holding the canvas and its scrollbars
        ###################
        self.cvs_frame = tk.Frame(
            self, width=self.canvas_w, height=self.canvas_h)
        self.cvs_frame.grid(row=2, column=1, sticky='n')

        self.cvs = tk.Canvas(
            self.cvs_frame, height=self.canvas_h, width=self.canvas_w)
        self.cvs.create_image(
            0, 0, tags='displayed_preview', anchor='nw', image=self.shown_img)
        self.cvs.grid(row=0, column=0, sticky='n')

        self.v_scroller = tk.Scrollbar(
            self.cvs_frame, orient='vertical', width=24)
        self.v_scroller.grid(row=0, column=1, sticky='ns')
        self.h_scroller = tk.Scrollbar(
            self.cvs_frame, orient='horizontal', width=24)
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
        w = new_img.width
        h = new_img.height
        if w > self.canvas_w_max:
            w = self.canvas_w_max
        if w < self.canvas_w_min:
            w = self.canvas_w_min
        if h > self.canvas_h_max:
            h = self.canvas_h_max
        if h < self.canvas_h_min:
            h = self.canvas_h_min

        self.shown_img = ImageTk.PhotoImage(new_img, master=self)
        self.cvs.itemconfig('displayed_preview', image=self.shown_img)
        self.cvs.config(width=w, height=h)
        self.cvs.config(scrollregion=self.cvs.bbox('all'))
        #self.cvs_frame.config(width=new_img.width, height=new_img.height)

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