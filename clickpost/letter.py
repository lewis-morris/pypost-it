import os
from dataclasses import dataclass, field
from io import BytesIO
from pathlib import Path
from typing import Union, List, Tuple, Optional, Dict, Any

import qrcode
from fpdf import FPDF, Align, YPos, XPos
from fpdf.enums import MethodReturnValue
from fpdf.fonts import FontFace
from jinja2 import Environment

from clickpost.block_models import Template, QrBlock, ImageBlock, TableBlock, TextBlock, LineBreakBlock, LineBlock, \
    Font, \
    _BaseBlock, FixedQrBlock, FixedImageBlock, FixedLineBlock, FixedTextBlock, FontName, FixedBox


class PDF(FPDF):
    loaded_fonts = []
    original_margins = []
    wrap_on = False
    wrap_y_end = None
    wrap_x = None
    wrap_dir = None
    current_page = 0
    dry_total = 0
    def __init__(self, template=Template()):
        """
        Args:
            template (Template): a template that defines how the document is styled.
        """
        super().__init__(format="A4")
        self.template = template
        self.template_setup()
        self.original_margins = [self.template.margins]

    def template_setup(self):
        """
        Sets up any template-related options.

        Returns: None

        """
        if self.template.background_image:
            self.set_page_background(self.template.background_image)

    def _reset_margin(self):
        """
        Resets the margin of the document to its original margin after a wrap

        Returns: None

        """

        # actually resets margin to the normal margin.
        l_margin, r_margin, t_margin, _ = self.original_margins
        self.set_margins(l_margin, r_margin, t_margin)

        # resets the wrap settings
        self.wrap_y_end = None
        self.wrap_x = None
        self.wrap_on = False


    def header(self):
        """
        Includes the header content if needed into the document based on the template, it will either do no header
        multiple headers or just one.

        Returns: None

        """
        if self.template.header:
            if self.template.header_page == 0:
                self._header_all()
            else:
                self._footer_one()

    def _header_all(self):
        """
        This function is used when the template specifies a header should be on every page
        Returns: None
        """
        pass

    def _header_one(self):
        """
        This function is used when the template specifies only one header

        Returns: None

        """
        if self.page_no() == 1:
            pass

    def footer(self):

        # On last page and not on first page if there's only one page
        # if self.page_no() == self.alias_nb_pages and self.alias_nb_pages != 1:
        if self.template.footer:
            if self.template.footer_page == 0:
                self._footer_all()
            else:
                self._footer_one()

    def _footer_all(self):
        """
        This function is used when the template specifies a footer should be on every page
        Returns: None
        """
        if self.page_no() == 1:
            pass

    def _footer_one(self):
        """
        This function is used when the template specifies only one footer

        Returns: None

        """

    def insert_qrcode(self, qr_code: QrBlock, dry: bool = False):
        """
        Inserts a QR code onto the page

        Args:
            qr_code (QrBlock): predefined qr_code block
            dry (bool): for a dryrun test - accumulates the height for testing.

        """

        # Generate QR code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_Q,
            box_size=10,
            border=4,
        )
        qr.add_data(qr_code.data)
        # gets the pil image
        qr_img = qr.make(fit=True)

        # Get the (x, y) position to center the QR code

        if qr_code.alignment == "L":
            x = self.l_margin
        elif qr_code.alignment == "R":
            x = self.r_margin - qr_code.size
        elif qr_code.alignment == "C":
            x = (self.default_page_dimensions[0] - qr_code.size) / 2
        y = self.get_y()
        # Insert the QR code image
        out = self.image(qr_img, x=x, y=y, w=qr_code.size, h=qr_code.size)

        # sets the wrap if it needs it
        self._sort_wrap(qr_img)

    def insert_image(self, img: ImageBlock, dry: bool = False):

        """
        Writes an image into the document

        Args:
            img: (ImageBlock) predefined img block

        """
        pass

    def _sort_wrap(self, obj: Union[ImageBlock, QrBlock], dry: bool = False):
        """
        When an object is set to wrap, the text is meant to go alongside it, until the point that it passes it. So....
        This should set the new margin, and then we will check the length of each word with multicell dry run and then
        check where to split. Once done, add the text, and then reset the margin to the original

        Args:
            obj: Union[ImageBlock, QrBlock] Sets the pdf to wrap the next item if needed by amending the margin on a temp basis.
            dry: (bool) for a dryrun test - accumulates the height for testing.

        Returns: None

        """

        self.wrap_y_end = self.get_y() + obj.size[1]
        self.wrap_x = self.get_x() + obj.size[0]

        if obj.wrap_text and obj.alignment in ["L", "R"]:

            self.wrap_on = True
            # this sets a new margin

            l_margin, r_margin, t_margin, _ = self.original_margins

            if obj.alignment == "L":
                self.wrap_dir = "L"
                self.set_margins(l_margin + obj.size, t_margin, r_margin)
            else:
                self.wrap_dir = "R"
                self.set_margins(l_margin, t_margin, r_margin - obj.size[0])

    def insert_table(self, table: TableBlock, dry: bool = False):
        """
        Inserts a table with the predefined information

        Args:
            table: (TableBlock)
            dry: (bool) for a dryrun test - accumulates the height for testing.
        """

        # set all the parameters for the table

        params = {"headings_style": FontFace(emphasis="BOLD",
                                             color=table.heading_text_colour if table.heading_text_colour else (
                                             2255, 255, 255),
                                             fill_color=table.heading_colour if table.heading_colour else (0, 0, 0)),
                  "line_height": table.row_line_height,
                  "align": table.alignment,
                  "cell_fill_color": table.striped_colour}

        if table.striped_colour:
            params["cell_fill_mode"] = "ROWS"
        if table.width:
            params["width"] = table.width
        if table.col_widths:
            params["col_widths"] = table.col_widths

        self._set_font(table.font)

        with self.table(**params) as _table:
            for data_row in table.data:
                row = _table.row()
                for datum in data_row:
                    row.cell(datum)

    def insert_text(self, text: Union[TextBlock, FixedTextBlock], dry: bool = False):
        """
        Writes text into the document - if the last element sets the `self.wrap_on` flag then it will attempt to wrap
        the next around the element.


        :param text: Predefined text block that holds text for writing to the page
        :type text: TextBlock
        :param dry: For a dryrun test - accumulates the height for testing.
        :type dry: bool

        """

        # sets the font for this text
        self._set_font(text.font)

        if self.wrap_on and not text.ignore_wrap:
            # wraps round the image if its there.
            self.insert_wrapped(text, dry)

        elif isinstance(text, FixedTextBlock):
            self.multi_cell(0, 0, txt=text, border=text.get_boarder(), align=getattr(Align, text.alignment.value),
                            max_line_height=text.line_height, dry_run=dry, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        else:
            if self.wrap_on:
                self._reset_margin()
            # writes the text
            self.multi_cell(0, 0, txt=text, border=text.get_boarder(), align=getattr(Align, text.alignment.value),
                            max_line_height=text.line_height, dry_run=dry, new_x=XPos.LMARGIN, new_y=YPos.NEXT)



    def insert_wrapped(self, text: TextBlock, dry: bool = False):
        """
        Inserts text into the document, but wrapped round the last object that assigned the `self.wrap_on` to true.
        Splits the text up into chunks until the y position of the wrapped element is passed, then resets the margin
        and writes the rest of the text. If the wrapped y position is not met, the flag is not removed and the next
        written element will also wrap.

        :param text: Rhe text we need to wrap around the image
        :type text: str
        :param dry: For a dryrun test - accumulates the height for testing.
        :type dry: bool

        :return: None
        :rtype: None

        """

        # split the words into a list so we can try work by work.
        words = text.text.split(" ")
        # get the array to hold each work we've checked
        split_string = []

        # set some other vars needed to make this baby work.
        x = self.get_x()
        last_string = ""
        hit_end_y = False


        for i, word in enumerate(words):
            # add the string to the list then join it into a new string
            split_string.append(word)
            check_string = " ".join(split_string)
            # dry run on the new string and return its height, becuase its a dry run it wont actualy write it.
            out = self.multi_cell(0, 0, txt=check_string, border=0, align=getattr(Align, text.alignment),
                                  max_line_height=text.line_height, dry_run=True, output=MethodReturnValue.HEIGHT)
            # check that we've actually gone over
            if x + out > self.wrap_y_end:
                hit_end_y = True
                break
            # set the last string so we can use it when we go over.
            last_string = check_string


        self.multi_cell(0, 0, txt=last_string, border=0, align=getattr(Align, text.alignment),
                        max_line_height=text.line_height, dry_run=dry, new_x=XPos.LMARGIN, new_y=YPos.NEXT)

        # onlt need to reset if we've hit the y max - otherwise the next string will need to wrap too.
        if hit_end_y:
            self._reset_margin()
            new_text = " ".join(words[i:])
            self.multi_cell(0, 0, txt=new_text, border=0, align=getattr(Align, text.alignment), max_line_height=text.line_height, dry_run=dry, new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    def insert_line_break(self, line_break: LineBreakBlock, dry: bool = False):
        """
        Writes blank space into the document

        :param line_break: predefined line_break (space) in the document
        :type line_break: LineBreakBlock
        :param dry: for a dryrun test - accumulates the height for testing.
        :type dry: bool
        """
        # writes the text
        if line_break.height:
            self.ln(line_break.height)
        else:
            self.ln()

    def insert_line(self, line: LineBlock, dry: bool = False):
        """
        Writes a solid line into the document, including padding if needed.

        :param line: predefined solid line
        :type line: LineBlock
        :param dry: predefined solid line
        :type dry: bool

        :return: None
        :rtype: None

        """

        def padd(padding):
            # just does blank spaces
            if padding:
                self.ln(padding)

        y = self.get_y()

        # padds if needed
        padd(line.padding)
        for i in range(line.height):
            # sets a solid line
            self.line(self.l_margin, y, self.r_margin, y)
            y += 1
        # bottom padding
        padd(line.padding)
        # becuase lines done change the current y value, it needs updating here.
        self.set_y(y)

    def insert_box(self, box: FixedBox, dry: bool = False):
        """

        Inserts a box into the document, with border and fill colour.

        :param box:  solid line
        :type box: LineBlock
        :param dry: predefined solid line
        :type dry: bool

        :return: None
        :rtype: None

        """

        #set_draw_color
        #set_fill_color
        #reset after




    def _font_needs_load(self, font: Font):
        """
        Checks if the font has been loaded into the system, if not, it loads it.

        :param font: An instance of the Font class which contains font settings.
        :type font: Font

        :return: font name
        :rtype: str

        """

        if isinstance(font.font_name, Path) and font.font_name.stem not in self.loaded_fonts:
            # need to load the font into the system
            self.add_font(fname=str(font.font_name.absolute()))
            # add the font name to the fonts `font_name` attribute
            font_name_from_stem = font.font_name.stem
            font.font_name = font_name_from_stem
            # add the font name to the list of loaded fonts
            self.loaded_fonts.append(font.font_name)
            # return the font name
            return font_name_from_stem

        return font.font_name


    def _set_font(self, font: Optional[Font] = None):
        """
        Set the font attributes for the text.

        :param font: An instance of the Font class which contains font settings. If None, the default font settings are used.
        :type font: Optional[Font]

        :return: None
        :rtype: None

        """


        if font is None:
            font = self.template.default_font

        # need to check if this item needs to be loaded into the system, as you can pass custom fonts.

        # set the font size
        self.set_font(size=font.font_size)

        # set the font name - it can be a string or a Path object, so we need to check.
        if isinstance(font.font_name, FontName):
            font_name = font.font_name.value
        else:
            font_name = self._font_needs_load(font)

        # set the font name
        self.set_font(family=font_name)

        # set the font style, check if it's a list or not.
        if isinstance(font.font_style, list):
            self.set_font(style=[x.value for x in font.font_style])
        else:
            self.set_font(style=font.font_style.value)

        # set the font colour
        self.set_text_color(*font.font_colour)

    def _add_content(self, content: List[Union[_BaseBlock]], dry=True):
        """
        This actually writes the content to the page.

        Args:
            content: (List[Union[_BaseBlock]]) a list of blocks that are to be rendered.

        Returns: None

        """
        for cont in content:
            if isinstance(cont, TextBlock):
                self.insert_text(cont, dry)
            elif isinstance(cont, ImageBlock):
                self.insert_image(cont, dry)
            elif isinstance(cont, QrBlock):
                self.insert_qrcode(cont, dry)
            elif isinstance(cont, LineBlock):
                self.insert_line(cont, dry)
            elif isinstance(cont, LineBreakBlock):
                self.insert_line_break(cont, dry)
            elif isinstance(cont, TableBlock):
                self.insert_table(cont, dry)
            # check if the margin needs resetting

    def create_pdf(self, content: List[_BaseBlock], output: Optional[Union[str, bytearray]]):
        """
        Call this function to generate the PDF.

        Args:
            content: (List[_BaseBlock]) a list of content that will be rendered on the page
            output: the output file name

        Returns:
            If 'output' is a str, the method will save the PDF to the specified file path and return None.
            If 'output' is a bytearray, the method will return the PDF as a bytearray.

        """
        # gets the margins
        margin_l, margin_r, margin_b, margin_t = self.template.margins
        # sets the auto page break to we don't need to define a new page each time
        self.set_auto_page_break(auto=True, margin=margin_b)
        # set the current margins
        self.set_margins(margin_l, margin_t, margin_r)
        # this is incase we need total pages at the end.
        self.alias_nb_pages(alias='{total_pages}')  # placeholder for total number of pages
        # start the process by creating a page.
        self.add_page()
        # set the default font from the template.
        self._set_font(self.template.default_font)  # set font and size
        # loop the content
        self._add_content(content)
        # output the pdf
        self.output(output)
