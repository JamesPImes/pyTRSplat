# Copyright (c) 2020, James P. Imes. All rights reserved.

from PIL import Image, ImageDraw, ImageFont

"""
TextBox - For streamlining writing text on a PIL.Image object.
"""

__version__ = '0.1'
__version_date__ = '9/17/2020'
__author__ = 'James P. Imes'
__email__ = 'jamesimes@gmail.com'

class TextBox:
    """
    An object containing a PIL.Image object with added functionality for
    streamlined text writing. (Currently in 'RGBA' mode only.)

    Access the PIL.Image object of the textbox in `.im` attribute.
    Access a PIL.ImageDraw object of the textbox in `.text_draw`
    attribute.

    Use `.write_paragraph()` to write paragraphs (or paragraph-like
    text) with automatic linebreaks and indents.

    Use `.write_line()` to write individual lines, with optional indent.

    IMPORTANT: If changing the font size or font typeface, use the
    `.set_truetype_font()` method. Alternatively, any PIL.ImageFont can
    be set to the `self.font` attribute; but then be sure to call
    `.deduce_chars_per_line()`.
    """

    def __init__(
            self, size: tuple, typeface=None, font_size=None,
            bg_RGBA=(255, 255, 255, 255), font_RGBA=(0, 0, 0, 255),
            paragraph_indent=0, new_line_indent=0, spacing=4):
        """
        :param size: 2-tuple of (width, height).
        :param typeface: The filepath to a truetype font (.ttf file)
        :param font_size: The size of the font to create.
        :param bg_RGBA: 4-tuple of the background color. (Defaults to
        white, full opacity.)
        :param font_RGBA: 4-tuple of the font color. (Defaults to black,
        full opacity.)
        :param paragraph_indent: How many spaces (i.e. characters, not
        px) to write before the first line of a new paragraph.
        :param new_line_indent: How many spaces (i.e. characters, not
        px) to write before every subsequent line of a paragraph.
        :param spacing: How many px between each line.
        """

        self.im = Image.new(mode='RGBA', size=size, color=bg_RGBA)
        self.text_draw = ImageDraw.Draw(self.im, 'RGBA')

        # IMPORTANT: Set font with `.set_truetype_font()` method.
        self.font = ImageFont.load_default()
        self.typeface = typeface
        self.font_size = font_size
        self.font_RGBA = font_RGBA
        if None not in [typeface, font_size]:
            self.set_truetype_font(font_size, typeface)

        # How many characters we can safely fit per line, using our font
        self.text_line_width = self.deduce_chars_per_line()

        # How many spaces (i.e. characters, not px) before the first
        # line of a new paragraph
        self.paragraph_indent = paragraph_indent
        # How many spaces (i.e. characters, not px) before each
        # subsequent line
        self.new_line_indent = new_line_indent

        # How many px between lines
        self.spacing = spacing

        # The main cursor (coord location where text can be written)
        self.text_cursor = (0, 0)

    ################################
    # Properties / Configuring the TextBox
    ################################

    @property
    def text_line_height(self):
        """
        The height (in px) needed to write a line of text (not including
        space between lines).
        """
        return self.text_draw.textsize('X,j', font=self.font)[1]

    def on_last_line(self, cursor='text_cursor'):
        """
        Whether we're on the last line, at the specified cursor
        (defaults to 'text_cursor'), using the currently set font.
        """

        # nested getattr() call to fall back to the default `.text_cursor`
        y_current = getattr(self, cursor, getattr(self, 'text_cursor'))[1]
        y_max = self.im.height
        y_remain = y_max - y_current

        # TODO: This calculation probably leaves room for some edge
        #   cases to slip through the cracks -- e.g., where
        #   `self.spacing` > `self.text_line_height`
        # Check if there's room for only one_line (ignoring spacer)
        return y_remain // self.text_line_height == 1

    def is_exhausted(self, cursor='text_cursor') -> bool:
        """
        Whether there's room to write at least one more line with the
        currently set font, at the specified cursor (defaults to
        'text_cursor').
        """
        # Check if `.text_cursor` would be illegal if moved down one
        # line of text
        return self._check_legal_cursor(
            (0, self.text_line_height), cursor=cursor)

    def set_truetype_font(self, size=None, typeface=None, RGBA=None):
        """
        Modify the size, typeface, and/or RGBA of the font. (Any
        unspecified parameters will leave the current attributes alone.)

        :param size: An int specifying the size of the font.
        :param typeface: Filepath to the .ttf font file to use.
        NOTE: Must be a filepath to a truetype font! If a valid filepath
        to a truetype font has not been specified (either during this
        call, or previously), then neither `typeface` nor `size` will
        have any effect, and the PIL default font will be (re)loaded.
        However, if a truetype font was previously provided, then it
        need not be provided again.
        :param RGBA: A 4-tuple of the color for the font.
        :return: None
        """

        # Check for errors in the specified `RGBA`, and then set it.
        if RGBA is not None:
            if not isinstance(RGBA, tuple):
                raise TypeError('`RGBA` must be tuple containing 4 ints from '
                                f'0 to 255. (Argument of type \'{type(RGBA)}\' '
                                'was passed)')
            elif len(RGBA) != 4:
                raise ValueError(f"`RGBA` must be tuple containing 4 ints from "
                                 f"0 to 255. "
                                 f"(Passed tuple contained {len(RGBA)} elements.")
            for val in RGBA:
                if not isinstance(val, int):
                    raise TypeError('`RGBA` must be tuple containing 4 ints '
                                    'from 0 to 255. (Passed tuple contained '
                                    f'element of type \'{type(val)}\')')
                if val < 0 or val > 255:
                    raise ValueError('`RGBA` must contain ints from 0 to 255. '
                                     f'(Passed tuple contained int {val})')
            # If it passes the checks, set it.
            self.font_RGBA = RGBA

        # If `typeface` and `size` are BOTH None, then the ImageFont
        # object won't change. So if we don't need to create a new
        # ImageFont obj, we can return now. (RGBA does not get encoded
        # in an ImageFont obj)
        if typeface is None and size is None:
            return

        if typeface is None:
            typeface = self.typeface
        if typeface is None:
            # If still None, load the default PIL font.
            self.font = ImageFont.load_default()
            return

        if size is None:
            size = self.font_size

        self.font = ImageFont.truetype(typeface, size)

        # We only want to change the respective typeface attribute AFTER
        # creating an ImageFont object, so that that has now had the
        # chance to raise any appropriate errors.
        self.font_size = size
        self.typeface = typeface

        # And recalculate how many characters we can fit in a line.
        self.deduce_chars_per_line()

    def deduce_chars_per_line(
            self, commit=True, harder_limit=False, w_limit=None):
        """
        Deduce (roughly) how many characters we can allow to be written
        in a single line, using the currently set `.font`.

        :param commit: Save the deduced max line-length to
        `self.text_line_width`
        :type commit: bool
        :param w_limit: Provide a custom width limit (in px) to check
        against. If not specified, we will check against the width of
        the textbox. (Will result in shorter lines.)
        written, but less likely to encroach on margins.
        :type w_limit: int
        :param harder_limit: Will check how many of a 'wider' character
        can fit in a single line. (False by default.)
        :type harder_limit: bool
        """

        font = self.font

        if w_limit is None:
            w_limit = self.im.width
        base = 'The Quick Brown Fox Jumps Over The Lazy Dog'
        if harder_limit:
            # If using `harder_limit`, will take the widest known
            # character in the font and only check how many of those
            # will fit in a line within our textbox.

            test = Image.new('RGBA', (1, 1))
            test_draw = ImageDraw.Draw(test, 'RGBA')

            # Check every char to see if it's the widest currently known
            consideration_set = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_='
            widest = 0
            biggest_char = None
            for char in consideration_set:
                w, h = test_draw.textsize(text=char, font=font)
                if w > widest:
                    widest = w
                    biggest_char = char
            base = biggest_char

        test = base[0]
        num_chars = 1
        while True:
            # Add the next char from base to test (and wrap around).
            test = test + base[num_chars % len(base)]
            w, h = self.text_draw.textsize(text=test, font=font)

            # Check if we've gone past the width of our textbox
            if w > w_limit:
                break
            else:
                num_chars += 1

        if commit:
            self.text_line_width = num_chars
        return num_chars

    ################################
    # Writing Text
    ################################

    def continue_paragraph(
            self, continue_lines, cursor='text_cursor', font_RGBA=None,
            reserve_last_line=False, override_legal_check=False,
            justify=False):
        """Continue writing the unwritten lines returned by
        `.write_paragraph()`, now beginning at the specified cursor.

        IMPORTANT: `continue_lines` must be a list. It should be exactly
        as returned as unwritten by `.write_paragraph()`. If you do need
        to modify something, each dict in the list should still contain
        two keys:
            'txt' -> The text to be written for that line.
            'justifiable' -> Whether that line is justifiable.
        (Modifying lines may cause them to break the boundaries of the
        textbox.)

        NOTE: Text will not be re-wrapped. This assumes that the TextBox
        being written in is configured identically to the one that
        returned the unwritten lines.

        All other applicable parameters have the same effect as in
        `.write_paragraph()`. (Parameters that affect indents and text
        wrapping have no effect here.)

        :param continue_lines: A list of lines to be written. (Each
        element in the list must be a dict, as discussed above.)
        :return: Returns a list of the lines that could NOT be written.
        """

        unwrit_lines = self.write_paragraph(
            continue_lines=continue_lines, cursor=cursor, font_RGBA=font_RGBA,
            reserve_last_line=reserve_last_line,
            override_legal_check=override_legal_check, justify=justify)
        return unwrit_lines

    def write_paragraph(
            self, text='', cursor='text_cursor', font_RGBA=None,
            reserve_last_line=False, override_legal_check=False,
            paragraph_indent=None, new_line_indent=None,
            wrap_method='thorough', justify=False, continue_lines=None) -> list:
        """
        Write the text as though it is a paragraph, with linebreaks
        inserted where necessary. Any lines that could not be fit within
        this textbox will be returned as a list of lines. (Optionally
        use the `.continue_writing()` method to write these lines into a
        new TextBox object, configured with identical font and width.)

        :param text: Text to be written (a string).
        :param cursor: Which cursor to begin writing at.
        :param font_RGBA: A 4-tuple specifying the font color. (If not
        specified, will fall back on whatever is in this object's
        `.font_RGBA` attrib.)
        :param reserve_last_line: If reached, leave the last line in the
        textbox empty (and return a list of any unwritten lines).
        (Defaults to `False`)
        :param override_legal_check: Disregard whether the written text
        would go beyond the boundaries of this TextBox. (Defaults to
        `False`)
        :param paragraph_indent: How many leading spaces (i.e.
        characters, not px) before the first line. (If not specified,
        defaults to `self.paragraph_indent`.)
        :param new_line_indent: How many leading spaces (i.e.
        characters, not px) before each subsequent line. (If not
        specified, defaults to `self.new_line_indent`.)
        :param wrap_method: 'thorough' (the default) or 'quick'.
        (Thorough maximizes line length, but takes longer.)
        :param justify: A bool, whether the written text should be
        justified -- i.e. stretched between the left indent and the
        right edge of the textbox. If used, all lines in the paragraph
        will be justified, except the final line, and any line that ends
        with a linebreak or return character. (Defaults to `False`)
        :param continue_lines: Continue writing lines that were returned
        as unwritten by a previous call of `.write_paragraph()`.
        IMPORTANT: If `continue_lines` is specified, then `text` is
        completely ignored. The lines will not be re-wrapped, and it is
        assumed that this TextBox object is identical in configuration
        to the TextBox object that returned the lines as unwritten.
        :return: Returns a list of the lines that could NOT be written.
        """

        font = self.font

        # If any of these parameters were not spec'd, pull from attribs
        if font_RGBA is None:
            font_RGBA = self.font_RGBA

        if paragraph_indent is None:
            paragraph_indent = self.paragraph_indent

        if new_line_indent is None:
            new_line_indent = self.new_line_indent

        # Check if text has already been broken into lines (e.g., if this
        # was called from `.continue_paragraph()` method.)
        already_lines = continue_lines is not None

        if already_lines:
            self._paragraph_lines_error_check(continue_lines)
            lines = continue_lines
        else:
            # Break text into lines (actually a list of dicts)
            if wrap_method == 'quick':
                lines = self._wrap_text(
                    text, paragraph_indent=paragraph_indent,
                    new_line_indent=new_line_indent)
            elif wrap_method == 'thorough':
                lines = self._wrap_text_thorough(
                    text, paragraph_indent=paragraph_indent,
                    new_line_indent=new_line_indent)

            else:
                raise ValueError(
                    "`wrap_method` must be either 'quick' or 'thorough'. "
                    f"Argument passed: {wrap_method}")

        attempt = 1

        # Write each line (until we can't anymore)
        while len(lines) > 0:
            if reserve_last_line and self.on_last_line(cursor=cursor):
                return lines
            attempt += 1
            line = lines.pop(0)

            # Write the line. Store the resulting list, to see if everything
            # got written.
            unwrit_line = self.write_line(
                line, cursor=cursor, font_RGBA=font_RGBA, indent=None,
                reserve_last_line=reserve_last_line,
                override_legal_check=override_legal_check, justify=justify)

            if unwrit_line != []:
                # Something couldn't be written. Put the last line back
                # in and return.
                return [line] + lines

        return lines

    def write_line(
            self, text, cursor='text_cursor', font_RGBA=None,
            reserve_last_line=False, override_legal_check=False,
            indent=None, justify=False) -> list:
        """
        Write a line of text at the specified cursor, after first
        confirming that the line can fit within the textbox. (May
        optionally override the legality check.) Any line that could
        not be fit within this textbox will be returned as a list of
        containing that line (in the same format as it was passed in).

        IMPORTANT: `text` can be passed as a string, OR as a dict with
        two keys as follows:
            'txt' -> The text to write (a string);
            'justifiable' -> A bool, whether the text is justifiable.

        If a string is passed as parameter `text`, then parameter
        `justify=True` will justify the line. However, if a 2-key dict
        is passed as `text` (as discussed below), then both `justify`
        parameter must be True, AND 'justifiable' must be set to True in
        the dict as well -- or the line will NOT be justified.
            ex:
                # Will justify the line (passed a str-type):
                line_1 = 'Testing Ex 1'
                tb_obj.write_line(line_1, justify=True)

                # Will NOT justify the line (passed a str-type):
                line_2 = 'Testing Ex 2'
                tb_obj.write_line(line_2, justify=False)

                # Will justify the line:
                line_3 = {'txt': 'Testing Ex 3', 'justifiable' = True}
                tb_obj.write_line(line_3, justify=True)

                # Will NOT justify the line:
                line_4 = {'txt': 'Testing Ex 4', 'justifiable' = False}
                tb_obj.write_line(line_4, justify=True)

                # Will NOT justify the line:
                line_5 = {'txt': 'Testing Ex 5', 'justifiable' = True}
                tb_obj.write_line(line_5, justify=False)

        :param text: The text to write (a string).
        NOTE: May optionally pass a dict containing these two keys:
            'txt' -> The text to write (a string);
            'justifiable' -> A bool, whether the text is justifiable.
            ('justifiable' has no effect in this method. Instead, use
            `.write_justified_line()` if that is desired.)
        :param indent: An int specifying how many leading spaces (i.e.
        characters, not px) to write before the `text`.
        (Defaults to None)
        :return: Returns a list of the text that was NOT written (i.e.
        either an empty list, or a single-element list containing the
        original text -- to mirror the `.write_paragraph()` method).
        IMPORTANT: If a 2-key dict was passed as `text` (as discussed
        above) and could not be written, a list containing that dict is
        returned.
        """

        bad_text_error = TypeError(
            'Must pass `text` as str (or a dict containing 2 keys, with '
            'value-types as follows: \'txt\' -> str; \'justify\' -> bool'
        )

        orig_text = text

        if reserve_last_line and self.on_last_line(cursor=cursor):
            return [orig_text]

        # Check whether `text` is a plain string, or if it was passed as
        # a dict (with appropriate 'txt' and 'justifiable' keys). Unpack
        # as needed.
        if isinstance(text, str):
            justifiable = True
        elif isinstance(text, dict):
            try:
                justifiable = text['justifiable']
                if not isinstance(justifiable, bool):
                    raise bad_text_error
                text = text['txt']
            except KeyError:
                raise bad_text_error
        else:
            raise bad_text_error

        if justify and justifiable:
            # If the line must be justified, pass everything on to the
            # method that handles it (which returns the line in a list,
            # if it couldn't be written -- same as this method).
            unwrit_line = self.write_justified_line(
                text=text, cursor=cursor, font_RGBA=font_RGBA,
                reserve_last_line=reserve_last_line,
                override_legal_check=override_legal_check, indent=indent)
            # If sucessful (i.e. unwrit_line is an empty list), return
            # that. Otherwise, return the orig_text inside a list.
            if unwrit_line == []:
                return unwrit_line
            else:
                return [orig_text]

        font = self.font

        indented_text = text
        if indent is not None:
            indented_text = f"{' ' * indent}{text}"

        if font_RGBA is None:
            font_RGBA = self.font_RGBA

        # Try to get the specified cursor, but fall back to
        # `.text_cursor`, if it doesn't exist
        coord = getattr(self, cursor, getattr(self, 'text_cursor'))
        legal = self._check_legal_textwrite(indented_text, font, cursor)
        if legal or override_legal_check:
            # Write the text and get the width and height of the text written.
            xy_delta = self._write_text(coord, indented_text, font, font_RGBA)
        else:
            return [text]

        self.next_line_cursor(xy_delta, cursor=cursor, commit=True)

        return []

    def write_justified_line(
            self, text, cursor='text_cursor', font_RGBA=None,
            reserve_last_line=False, override_legal_check=False,
            indent=None) -> list:
        """
        Write a justified line of text at the specified cursor, after
        first confirming that the line can fit within the textbox. (May
        optionally override the legality check, but only as to height.)

        NOTE: Unlike, `.write_line()`, this method allows only a string
        to be passed as `text`. It will force any text to be justified,
        whether it was deduced as 'justifiable' or not. Use the
        `.write_line()` method, if you need guardrails for that purpose.
        :param text: The text to be written (str only).
        :param indent: An int specifying how many leading spaces (i.e.
        characters, not px) to write before the `text`.
        (Defaults to None)
        :return: Returns a list of the text that was NOT written (i.e.
        either an empty list, or a single-element list containing the
        original text -- to mirror the `.write_paragraph()` method).
        """

        def update_coord(coord, xy_delta, new_xy_delta) -> tuple:
            """
            Update the coord and xy_delta, per new_xy_delta.
            """

            x0, y0 = coord
            x_delta, y_delta = xy_delta
            new_x_delta, new_y_delta = new_xy_delta

            coord = (x0 + new_x_delta, y0)

            if new_y_delta > y_delta:
                y_delta = new_y_delta

            x_delta += new_x_delta

            return coord, (x_delta, y_delta)

        if reserve_last_line and self.on_last_line(cursor=cursor):
            return[text]

        orig_text = text

        font = self.font
        if font_RGBA is None:
            font_RGBA = self.font_RGBA

        if indent is None:
            # Deduce the length of the indent (in space characters), and
            # remove them from the text
            indent = 0
            i = 1
            while True:
                if text.startswith(' ' * i):
                    indent = i
                else:
                    break
                i += 1
            text = text[indent:]

        # Convert indent (int) to space chars (str)
        indent = ' ' * indent

        # Get the width of our indent in px
        indent_w, indent_h = self.text_draw.textsize(indent, font=font)

        # The number of pixels we have available to write all words:
        w_remain = self.im.width - indent_w

        words = text.split(' ')

        # Get the width, height (in px) of each word, and the total for
        # all words
        word_px_dict = {}
        total_word_w = 0
        total_word_h = 0
        for word in words:
            word_w, word_h = self.text_draw.textsize(word, font=font)
            word_px_dict[word] = (word_w, word_h)
            total_word_w += word_w
            if word_h > total_word_h:
                total_word_h = word_h

        # Deduce px available for all spaces in this line.
        px_all_spaces = w_remain - total_word_w

        # De-facto width legality check (cannot be overridden):
        if px_all_spaces < 0:
            # Not enough room to write this text on this line.
            return [orig_text]

        # Space (in px) per word boundary
        if len(words) in [0, 1]:
            spwd = 0
            bonus_sp_px = 0
        else:
            spwd = px_all_spaces // (len(words) - 1)
            bonus_sp_px = px_all_spaces % (len(words) - 1)

        # Handle legality check for height.
        is_legal = True
        if not override_legal_check:
            is_legal = self._check_legal_cursor(
                (0, total_word_h), cursor=cursor)
        if not is_legal:
            return [orig_text]

        # Write the indent.
        coord = getattr(self, cursor, getattr(self, 'text_cursor'))
        coord, xy_delta = update_coord(coord, (0, 0), (indent_w, indent_h))

        words_left = len(words)
        for word in words:
            # Write the word
            self.text_draw.text(coord, word, font=font, fill=font_RGBA)

            # We already calculated each word's width, height, so pull
            # that, and update the cursor
            new_xy_delta = word_px_dict[word]
            coord, xy_delta = update_coord(coord, xy_delta, new_xy_delta)

            # Unless it's the last word, write a space (i.e. move cursor right).
            if words_left > 1:
                space = spwd
                if bonus_sp_px > 0:
                    # Spend each extra space px, one at a time.
                    space += 1
                    bonus_sp_px -= 1
                coord, xy_delta = update_coord(coord, xy_delta, (space, 0))

            words_left -= 1

        self.next_line_cursor(xy_delta, cursor=cursor, commit=True)
        return []

    @staticmethod
    def simplify_unwritten_lines(unwritten_lines) -> list:
        """
        For lines that were returned unwritten by any of the TextBox
        writing methods, this will 'unpack' the list into a single-level
        list of lines of text (i.e. a list of simple strings). However,
        it will destroy any data regarding whether those lines are
        'justifiable', or if they originally ended in a linebreak or
        return character.

        :param unwritten_lines: Any list returned by any of the TextBox
        writing methods.
        :return: A list of lines of text (i.e. simple strings).
        """
        final_lines = []
        for line in unwritten_lines:
            if isinstance(line, str):
                final_lines.append(line)
            else:
                final_lines.append(line['txt'])
        return final_lines

    def _write_text(self, coord: tuple, text: str, font, font_RGBA) -> tuple:
        """
        INTERNAL USE:
        Write `text` at the specified `coord`. Returns a tuple of the
        width and height of the written text. Does NOT update a cursor.
        NOTE: This method does not care whether it goes outside the
            textbox, so be sure to handle `._check_legal_textwrite()`
            before calling this method.

        (End users should use `.write_line()` and `.write_paragraph()`,
        which have built-in legality checks that will prevent writing
        beyond textbox boundaries.)

        :param coord: Where to write the text.
        :param text: What text to write.
        :param font: PIL.ImageFont object that should be used.
        :param font_RGBA: A 4-tuple specifying the font color. (If not
        specified, will fall back on whatever is in this object's
        `.font_RGBA` attrib.)
        :return: Returns a 2-tuple of the (width, height) of the text
        written.
        """

        w, h = self.text_draw.textsize(text, font=font)
        self.text_draw.text(coord, text, font=font, fill=font_RGBA)
        return (w, h)

    ################################
    # Manipulating / Checking Text Before Writing
    ################################

    def _check_legal_textwrite(self, text, font, cursor='text_cursor') -> bool:
        """
        INTERNAL USE:
        Check if there is enough room to write the specified text at the
        specified cursor (defaulting to 'text_cursor'), using the
        specified font.

        :param text: The text to check.
        :param font: The font that will be used to write the text.
        :type font: PIL.ImageFont
        :param cursor: The name of the cursor at which the text will be
        written. (Defaults to 'text_cursor')
        :return: A bool, whether or not the text can be written within
        the bounds of the textbox.
        """

        w, h = self.text_draw.textsize(text, font=font)

        # Only `legal` matters for this method.
        legal = self._check_legal_cursor((w, h), cursor=cursor)
        return legal

    def _wrap_text(
            self, text, paragraph_indent=None, new_line_indent=None,
            custom_line_width=None) -> list:
        """
        INTERNAL USE:
        Break down the `text` into a list of lines that will fit within
        the currently set `self.text_line_width`.
        Returns a list containing a dict for each resulting line,
        with keys:
            'txt'     -> The text of the line
            'justifiable' -> Whether the line can be justified**

        **'Justifiable' here means whether it can be stretched from the
        left indent to the right edge of the textbox. (All lines will be
        justifiable, except the final line in the text, and except lines
        that originally ended in a linebreak or return character.)

        (Expands on Python's built-in `textwrap` module, in that
        linebreaks and line returns are given effect, while also keeping
        the desired indents.)

        :param custom_line_width: If specified, will use this as the
        line width, rather than `self.text_line_width`.
        :param paragraph_indent: How many leading spaces (i.e.
        characters, not px) before the first line. (If not specified,
        defaults to `self.paragraph_indent`.)
        :param new_line_indent: How many leading spaces (i.e.
        characters, not px) before each subsequent line. (If not
        specified, defaults to `self.new_line_indent`.)
        :return: A list containing a dict for each resulting line,
        with keys:
            'txt'     -> The text of the line
            'justifiable' -> Whether the line can be justified.
        """

        import textwrap

        final_line_dicts = []
        width = custom_line_width
        if width is None:
            width = self.text_line_width

        if paragraph_indent is None:
            paragraph_indent = self.paragraph_indent

        if new_line_indent is None:
            new_line_indent = self.new_line_indent

        # In order to maintain linebreaks/returns, but also have desired
        # indents, we need to manually break our text by linebreak first,
        # and only then run textwrap on each resulting line.

        # First split our text by returns and linebreaks.
        text = text.strip('\r\n')
        text = text.replace('\r', '\n')
        rough_lines = text.split('\n')

        i = 0
        for rough_line in rough_lines:

            justifiable = True
            # Strip any pre-existing whitespace
            stripped_line = rough_line.strip()

            # Construct the initial_indent. Keep in mind that we've
            # already broken the text into rough lines (by linebreak),
            # so the `initial_indent` that we pass to textwrap will
            # be identical to `subsequent_indent` for every line except
            # the first rough_line.

            # For the first rough_line, we use the paragraph_indent
            initial_indent = ' ' * paragraph_indent

            if i > 0:
                # For all others, we use new_line_indent.
                initial_indent = ' ' * new_line_indent

            subsequent_indent = ' ' * new_line_indent

            # Wrap rough_line into neater lines and add to final lines
            neater_lines = textwrap.wrap(
                stripped_line, initial_indent=initial_indent,
                subsequent_indent=subsequent_indent, width=width)

            rl_line_dicts = []
            for line in neater_lines:
                line_dict = {'txt': line, 'justifiable': True}
                rl_line_dicts.append(line_dict)
            if len(rl_line_dicts) > 0:
                # Don't justify the final line (if any lines exist)
                rl_line_dicts[-1]['justifiable'] = False

            final_line_dicts.extend(rl_line_dicts)

            i += 1

        return final_line_dicts

    def _paragraph_lines_error_check(self, lines: list):
        """
        INTERNAL USE:
        Check the first element in a list of lines to see if it is
        formatted appropriately. (Should be fine, so long as the list
        elements have not been modified since returned by a writer
        method.)

        :return: Returns nothing if it passes, but will throw off a
        TypeError as appropriate.
        """

        bad_lines_error = TypeError(
            'Must pass `continue_lines` as a list, '
            'containing only strings, or only dicts. If it contains '
            'dicts, each dict must contain 2 keys, with value-types as '
            'follows: \'txt\' -> str; \'justify\' -> bool'
        )

        if not isinstance(lines, list):
            raise bad_lines_error

        if not isinstance(lines[0], dict):
            raise bad_lines_error
        # Check the first element to ensure it's the right dict format.
        try:
            if isinstance(lines[0]['txt'], str):
                pass
            if isinstance(lines[0]['justifiable'], bool):
                pass
        except (TypeError, KeyError):
            raise bad_lines_error

    def _wrap_text_thorough(
            self, text, paragraph_indent: int, new_line_indent: int):
        """
        INTERNAL USE:
        Wrap the text to be written, using a more thorough algorithm,
        which is slower but ensures that lines are as long as they can
        be. Returns a list containing a dict for each resulting line,
        with keys:
            'txt'     -> The text of the line
            'justifiable' -> Whether the line can be justified**

        **'Justifiable' here means whether it can be stretched from the
        left indent to the right edge of the textbox. (All lines will be
        justifiable, except the final line in the text, and except lines
        that originally ended in a linebreak or return character.)

        :param paragraph_indent: How many leading spaces (i.e.
        characters, not px) before the first line. (If not specified,
        defaults to `self.paragraph_indent`.)
        :param new_line_indent: How many leading spaces (i.e.
        characters, not px) before each subsequent line. (If not
        specified, defaults to `self.new_line_indent`.)
        :return: A list containing a dict for each resulting line,
        with keys:
            'txt'     -> The text of the line
            'justifiable' -> Whether the line can be justified.
        """
        # TODO: Handle extra-long words (i.e. a single word can't fit
        #   on a single line by itself -- just break the word at
        #   whatever char that is, onto the next line).

        # TODO: Make a more efficient algorithm. We currently brute-
        #   strength our way through, starting at a single word and
        #   adding one at a time. It works, but is relatively slow,
        #   considering we have to call PIL's .textsize() every time we
        #   add a word. May be more efficient to try chunks and/or start
        #   at an assumed safe point (e.g., 75% of the 'expected' length
        #   and then start adding single words or chunks -- and
        #   backtrack as necessary).

        font = self.font

        final_line_dicts = []
        max_w = self.im.width

        # In order to maintain linebreaks/returns, but also have desired
        # indents (and whether a line is justifiable), we need to
        # manually break our text by linebreak first, and only then run
        # the algorithm.

        # First split our text by returns and linebreaks.
        text = text.strip('\r\n')
        text = text.replace('\r', '\n')
        rough_lines = text.split('\n')

        first_indent = ' ' * paragraph_indent
        later_indent = ' ' * new_line_indent

        # Construct lines word-by-word, until they are longer than can
        # be printed within the width of the image. At that point,
        # approve the last safe line, and start a new line with the word
        # that put it over the edge.
        # For each line, also encode whether it is 'justifiable', i.e.
        # whether it can be stretched from the left indent to the right
        # edge of the textbox. (All lines will be justifiable, except
        # the final line in the text, and except lines that originally
        # ended in a linebreak or return character.)
        #
        # Specifically, we constructs a list containing a dict for each
        # line, with keys:
        #    'txt'     -> The text of the line
        #    'justifiable' -> Whether the line can be justified

        rl_count = 0
        for rough_line in rough_lines:

            justifiable = True
            indent = later_indent
            if rl_count == 0:
                indent = first_indent

            # Strip any pre-existing whitespace
            rough_line = rough_line.strip()
            words = rough_line.split(' ')
            if len(words) == 0:
                # No words in this rough_line. Move on.
                continue

            current_line_to_add = indent + words.pop(0)
            candidate_line = current_line_to_add
            last_word_is_candidate = False
            while len(words) > 0:
                new_word = words.pop(0)
                candidate_line = current_line_to_add + ' ' + new_word
                w, h = self.text_draw.textsize(candidate_line, font=font)
                if w > max_w:
                    line_dict = {'txt': current_line_to_add,
                                 'justifiable': justifiable}
                    final_line_dicts.append(line_dict)
                    indent = later_indent
                    current_line_to_add = indent + new_word
                    last_word_is_candidate = True
                else:
                    last_word_is_candidate = False
                    current_line_to_add = candidate_line
            if current_line_to_add == candidate_line or last_word_is_candidate:
                justifiable = False
                line_dict = {'txt': current_line_to_add,
                             'justifiable': justifiable}
                final_line_dicts.append(line_dict)
            rl_count += 1

        return final_line_dicts


    ################################
    # Cursor Methods
    ################################

    def reset_cursor(self, cursor='text_cursor') -> tuple:
        """
        Set the specified cursor (defaults to 'text_cursor') to (0, 0).

        :param cursor: The name of the cursor to be set to (0, 0).
        The named cursor will be stored as an attribute in `self`.
        Specifically, if a string is NOT passed as `cursor=`, the
        stored coord will be set to the default `.text_cursor`. However,
        if the particular cursor IS specified, it will save the
        resulting coord to that attribute name.
        Be careful not to overwrite other required attributes.
        :return: (0, 0)
        :Example:

        ex: 'tb_obj.reset_cursor()  # The default
            -> tb_obj.text_cursor == (0, 0)
            -> and returns (0, 0)
        ex: 'tb_obj.reset_cursor(cursor='highlight')
            -> tb_obj.highlight == (0, 0)
            -> and returns (0, 0)
        """
        self.set_cursor((0, 0), cursor)
        return (0, 0)

    def set_cursor(self, coord, cursor='text_cursor'):
        """
        Set the cursor to the specified x and y coord. If a string
        is NOT passed as `cursor=`, the committed coord will be set to
        the default `.text_cursor`. However, if the particular cursor
        IS specified, it will save the resulting coord to that attribute
        name.
            ex: 'tb_obj.set_cursor((200, 1200))
                -> tb_obj.text_cursor == (200, 1200)
            ex: 'tb_obj.set_cursor((200, 1200), cursor='highlight')
                -> tb_obj.highlight == (200, 1200)
        Be careful not to overwrite other required attributes.
        """
        setattr(self, cursor, coord)

    def next_line_cursor(
            self, xy_delta=None, cursor='text_cursor', commit=True) -> tuple:
        """
        Move the specified `cursor` to the so-called 'next line', after
        having written some text at that cursor.

        :param xy_delta: A 2-tuple of (width, height) of text that was
        just written. If not specified, will rely on the px height in
        `self.text_line_height` attribute.
        IMPORTANT: Assumes a single line of text was written!
        :param cursor:
        If a string is NOT passed as `cursor=`, the returned (and
        optionally committed) coord will be set to the default
        `.text_cursor`. However, if the particular cursor IS specified,
        it will save the resulting coord to that attribute name (so long
        as `commit=True`).
        NOTE: If the cursor is specified but does not yet exist, this
        will read from `.text_cursor` (to calculate the updated coord)
        but save to the specified cursor.
        Be careful not to overwrite other required attributes!
        :param commit: A bool, whether to store the calculated coord to
        the specified cursor.
        :return: Returns the resulting coord.
        """

        # Set x to the left edge of the textbox
        x = 0

        # Discard the x from xy_delta, but get the y_delta.
        _, y_delta = xy_delta

        # Discard the x0 from the cursor, but get y0.  (Nested `getattr`
        # calls ensures we get `.text_cursor`, if `cursor=` was
        # specified as a string that wasn't already set; but this won't
        # overwrite the specified `cursor` for committing the coord
        # shortly.)
        _, y0 = getattr(self, cursor, getattr(self, 'text_cursor'))

        # We will add to our y-value the `.spacing`.
        coord = (x, y0 + y_delta + self.spacing)

        if commit:
            self.set_cursor(coord, cursor=cursor)

        return coord

    def update_cursor(
            self, xy_delta, cursor='text_cursor', commit=True) -> tuple:
        """
        Update the coord of the cursor, by adding the `x_delta` and
        `y_delta` to the current coord of the specified `cursor`.

        :param xy_delta: A tuple of (x, y) values, being how far (in px)
        the cursor has traveled from its currently set coord.
        :param cursor: The name of the cursor being updated. (Defaults
        to 'text_cursor'.)
        If a string is NOT passed as `cursor=`, the committed coord will
        be set to the default `.text_cursor`. However, if the particular
        cursor IS specified, it will save the resulting coord to that
        attribute name (so long as `commit=True`).

        Further, if the cursor is specified but does not yet exist, this
        will read from `.text_cursor` (to calculate the updated coord)
        but save to the specified cursor.
        Be careful not to overwrite other required attributes.
        :param commit: Whether to store the new coord to the cursor
        attribute in `self`.
        :return: Returns the updated coord, and optionally stores it to the
        cursor attribute with `commit=True` (on by default).
        """

        # Pull the specified cursor. If it does not already exist as an
        # attribute in this object, it will fall back to `.text_cursor`,
        # which exists for every TextBox object, per init.
        x_delta, y_delta = xy_delta
        x0, y0 = getattr(self, cursor, getattr(self, 'text_cursor'))
        coord = (x0 + x_delta, y0 + y_delta)

        # Only if `commit=True` do we set this.
        if commit:
            setattr(self, cursor, coord)

        return coord

    ###############
    # Checking Cursor Movements
    ###############

    def _check_cursor_overshoot(
            self, xy_delta: tuple, cursor='text_cursor') -> tuple:
        """
        Check how many px the cursor has gone beyond right and bottom
        edges of the textbox. (Assumes that it is starting from a legal
        coord.)

        :param xy_delta: A tuple of (x, y) values, being how far (in px)
        the cursor has traveled from its currently set coord.
        :param cursor: The name of the cursor being checked. (Defaults
        to 'text_cursor'.)
        :return: Returns an (x, y) tuple of how many px past the margins
        the cursor has gone. (Negative numbers mean that it is within
        the right/bottom margins, but is agnostic as to the top/left
        margins.)
        """

        # Confirm `cursor` points to an existing tuple in self's
        # attributes. If not, we'll use the `.text_cursor` attribute.
        cursor_check = getattr(self, cursor, None)
        if not isinstance(cursor_check, tuple):
            cursor = 'text_cursor'

        # Get the hypothetical resulting cursor location if xy_delta is
        # applied. (`commit=False` means it won't be stored yet.)
        x, y = self.update_cursor(xy_delta, cursor, commit=False)

        x_overshot = x - self.im.width
        y_overshot = y - self.im.height

        return (x_overshot, y_overshot)

    def _check_legal_cursor(
            self, xy_delta: tuple, cursor='text_cursor') -> bool:
        """
        Check if there is enough room to move the cursor from its
        current position by `xy_delta` (a tuple of x,y value) before
        going outside the dimensions of the textbox.
        (Assumes that it is starting from a legal coord.)

        :param xy_delta: A tuple of (x, y) values, being how far (in px)
        the cursor has traveled from its currently set coord.
        :param cursor: The name of the cursor at which the text will be
        written. (Defaults to 'text_cursor')
        :return: A bool, whether or not the resulting coord will fall
        within the bounds of the textbox.
        """

        x_overshot, y_overshot = self._check_cursor_overshoot(xy_delta, cursor)

        legal = True
        if x_overshot > 0 or y_overshot > 0:
            legal = False

        return legal
