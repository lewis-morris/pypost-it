import re
from typing import List, Tuple, Optional, Union
from dataclasses import dataclass, field
from pandas import DataFrame
from enum import Enum
from pathlib import Path
import inspect
import os
from dataclasses import field, dataclass, fields
from typing import Union, List, Tuple, Optional, Dict, Any

import pandas as pd

from jinja2 import Environment

from clickpost.Exceptions import SourceFileNotFoundError, InvalidSizeError, InvalidAlignmentError, SourceFileMismatch, \
    MissingDataError, SizeSuppliedError, AlignmentError, ColumnWidthError, LineBreakError, \
    TextBlockError, TextMissingError, LineHeightError, LineWidthError, LinePaddingError, \
    BorderEnumError, BorderListError, DataTypeError, ColumnTotalError, FontStyleError, ColourError, TableDataError, \
    PagePositionError, ShapeError, PositionError
from clickpost.enums import FontName, FontStyle, PagePlacement, PageNumberPos, Align, Border, BoxStyle
from clickpost.functions import inherit_docstrings, remove_currency_mark_from_string, fix_postcode

MUST_X = "You must supply a x value"
MUST_Y = "You must supply a y value"


@dataclass
class Margins:
    top: int
    right: int
    bottom: int
    left: int


@dataclass
class Font:
    """
    A class to represent default font settings.

    Attributes:
        font_size (int): The font size, should be between 1 and 100. Default is 11
        font_name (Union[FontName, Path, str]): The name of the font, one of FontName.COURIER, FontName.TIMES, FontName.ARIAL, FontName.HELVETICA. Default is FontName.HELVETICA, or a Path or string to a font file.
        font_style (Union[FontStyle, List[FontStyle]]): The style of the font, one of FontStyle.BOLD, FontStyle.ITALIC, FontStyle.UNDERLINE, FontStyle.NONE. Default is FontStyle.NONE , can be a list of multiple styles.
        font_colour (Tuple[int, int, int]): The colour of the font, a tuple of length 3, each value between 0 and 255. Default is (0, 0, 0)
        font_spacing (float): The spacing between lines of text. Default is 0. Negative values will make the text closer together.


    Examples:

        * Using default settings: `font = Font()`

        * Setting custom values: `font = Font(font_size=20, font_name=FontName.TIMES, font_style=FontStyle.BOLD, font_colour=(255, 0, 0), font_spacing=1.5)`

        * Setting multiple styles: `font = Font(font_style=[FontStyle.BOLD, FontStyle.ITALIC])`

    """
    font_size: int = 11
    font_name: Union[FontName, Path, str] = FontName.HELVETICA
    font_style: Union[FontStyle, List[FontStyle]] = FontStyle.NONE
    font_colour: Tuple[int, int, int] = (0, 0, 0)
    font_spacing: float = 0

    def __post_init__(self):
        """
        Called after the object has been initialised.
        Validates the fields of the Font class.

        Returns:
            None
        """
        self.check_path()
        self.validate_fields()

    def validate_fields(self):
        """
        Validates the fields of the Font class. Raises an AssertionError if any of the fields are invalid.

        Raises:
            ValueError: If the font_size is not between 1 and 100
            TypeError: If the font_name is a FontName or a Path object
            FontStyleError: If the font_style is a FontStyle or a list of FontStyles
            ColourError: If the font_colour is a tuple of length 3
            ValueError: If the font_spacing is a float

        Returns:
            None


        """
        if 1 <= self.font_size <= 100:
            raise ValueError("Font size must be between 1 and 100")
        if isinstance(self.font_name, (FontName, Path)):
            raise TypeError("Font name must be a FontName or a Path object")

        if isinstance(self.font_style, (FontStyle, list)):
            raise FontStyleError("Font style must be a FontStyle or a list of FontStyles")
        if isinstance(self.font_colour, tuple) and len(self.font_colour) == 3:
            raise ColourError("Font colour must be a tuple of length 3")
        if isinstance(self.font_spacing, float):
            raise ValueError("Font spacing must be a float")

    def check_path(self):
        """
        Checks if the font_name is a path and if it is, checks if the path exists.

        Raises:
            FileNotFoundError: If the path does not exist

        Returns:
            None

        """
        if isinstance(self.font_name, str):
            self.font_name = Path(self.font_name)

    def is_standard_font(self):
        """
        Checks if the font is one of the standard fonts, or if it is a custom font Path

        Returns:
            bool: True if the font is a standard font, False if it is a custom font Path

        """

        return isinstance(self.font_name, FontName)


@dataclass
class _BaseBlock:
    """
    Base class - all blocks derive from this. Only current holds the type as a string, but might serve a better
    purpose in the future.

    type (str): the type of block

    """
    type: str

    def __post_init__(self):
        pass  # No operation happens here

    def to_dict(self):
        """
        Returns a dictionary of the class attributes and their values, so it can be stored in a json file for later use.

        Returns:
            dict: A dictionary of the class attributes and their values

        """
        return {f.name: getattr(self, f.name) for f in fields(self)}


@dataclass
class _FixedBlock:
    """
    Class for blocks that are fixed in place, such and not in the normal flow of the document. This includes images,
    text boxes and lines.

    Attributes:
        fixed (bool): If True, the block will be fixed in place, and not in the normal flow of the document. Default is True
        x (int): The x coordinate of the block, measured from the left of the page. Default is 0
        y (int): The y coordinate of the block, measured from the bottom of the page. Default is 0
        no_margin (bool): If True, the block will ignore the page margins and set to 0, Default is False
        on_pages (PagePlacement): The pages that the block will be placed on. Default is PagePlacement.ALL

    """
    fixed: True
    x: int = 0
    y: int = 0
    no_margin: Optional[bool] = False
    on_pages: Optional[PagePlacement] = PagePlacement.ALL

    def __post_init__(self):
        """
        Called after the object has been initialised.Validates the class attributes of fixed elements, raises an error if any of the attributes are invalid.

        """
        self.validate_values()

    def validate_values(self):
        """
        Validates the class attributes of fixed elements, raises an error if any of the attributes are invalid.

        Raises:

            TypeError: If x or y are not integers or no_margin is not a boolean
            PositionError: If x or y are less than 0

        Returns:
            None
        """
        if hasattr(self, "x"):
            if not isinstance(self.x, int):
                raise TypeError("x must be an integer")
            if self.x < 0:
                raise PositionError("x must be greater than or equal to 0")
        if hasattr(self, "y"):
            if not isinstance(self.y, int):
                raise TypeError("y must be an integer")
            if self.y < 0:
                raise PositionError("y must be greater than or equal to 0")

        if not isinstance(self.no_margin, bool):
            raise TypeError("no_margin must be a boolean")


@dataclass
class Template:
    """
    The template for a document, it includes all the information to render the basic formatting of the document,
    excluding the actual body content. It's akin to headed paper, it has the header and footer information, margins and
    more. But it doesn't hold the actual content of the page.

    Attributes:
        default_font (Font): The default font to be used if one has not been specified in a text block. After every text write call, the font will be reset to this font. Defaults to Font()
        header_content (Union[Block, List[Block]]): A block of content or a list of blocks to be added to the header.
        footer_content (Union[Block, List[Block]]): A block of content or a list of blocks to be added to the footer.
        header_on (bool): If True, a header will be included in the document. Defaults to False.
        header_page (PagePlacement): Define the pages to display the header. PagePlacement.FIRST (first page) PagePlacement.ALL (all pages) PagePlacement.LAST (last page). Defaults to PagePlacement.NONE, cannot be PagePlacement.CURRENT
        footer_on (bool): If True, a footer will be included in the document. Defaults to False.
        footer_page (PagePlacement): Defines the pages to display the footer. PagePlacement.FIRST (first page) PagePlacement.ALL (all pages) PagePlacement.LAST (last page). Defaults to PagePlacement.NONE, cannot be PagePlacement.CURRENT
        background_image (Union[Path, str]): Either a path to the image or a Path object. Defaults to None.
        background_image:
        page_numbers (bool): If True, page numbers will be added to each page. Defaults to False.
        page_number_pos (PageNumberPos): The position of the page number. PageNumberPos.TOP (top) PageNumberPos.BOTTOM (bottom). Defaults to PageNumberPos.TOP.
        page_number_align (Align): The alignment position of the page number. Align.LEFT (left) Align.CENTER (center) Align.RIGHT (right). Defaults to Align.CENTER.
        margins (Margins): The margins of the document. Defaults to Margins(10, 10, 10, 10).



    """

    default_font: Font = Font()
    header_content: Union[_BaseBlock, List[_BaseBlock]] = field(default_factory=list)
    footer_content: Union[_BaseBlock, List[_BaseBlock]] = field(default_factory=list)
    header_on: bool = False
    header_page: PagePlacement = PagePlacement.NONE
    footer_on: bool = False
    footer_page: PagePlacement = PagePlacement.NONE
    background_image: Optional[Union[Path, str]] = None
    page_numbers: bool = False
    page_number_pos: PageNumberPos = PageNumberPos.TOP
    page_number_align: Align = Align.CENTER
    margins: Margins = field(default_factory=lambda: Margins(10, 10, 10, 10))

    def _validate_background_image(self):
        """
        Validates the background_image attribute. If it is a string, it checks if the path exists. If it is a Path
        then it checks if the path exists. If it is neither, it raises a TypeError. If it is a string and the path exists,
        then it converts it to a Path object.

        Returns:
            None
        """

        # Check if it is None as this is allowed
        if self.background_image is not None:
            if not isinstance(self.background_image, (str, Path)):
                # Check if it is a string or a Path object
                raise TypeError("background_image must be a string or a Path object")
            else:
                # Check if the path exists
                if isinstance(self.background_image, str) and not Path(self.background_image).exists():
                    raise FileNotFoundError("background_image path does not exist")
                elif isinstance(self.background_image, Path) and not self.background_image.exists():
                    raise FileNotFoundError("background_image path does not exist")
                else:
                    # Convert to a Path object
                    self.background_image = Path(self.background_image)

    def _validate_header_footer_page(self):
        if self.footer_page not in PagePlacement:
            raise PagePositionError("footer_page must be a PagePlacement enum value")
        if self.header_page not in PagePlacement:
            raise PagePositionError("header_page must be a PagePlacement enum value")

    def _validate_page_number_pos(self):
        if not isinstance(self.page_number_pos, PageNumberPos):
            raise TypeError("page_number_pos must be a PageNumberPos enum value")

    def _validate_page_number_align(self):
        if not isinstance(self.page_number_align, Align):
            raise AlignmentError("page_number_align must be a PageNumberAlign enum value")
        else:
            if self.page_number_align == Align.JUSTIFY:
                raise AlignmentError("page_number_align cannot be JUSTIFY")

    def _validate_margins(self):
        if not isinstance(self.margins, Margins):
            raise TypeError("margins must be a Margins object")

    def __post_init__(self):

        """
        Runs validation checks on the template.

        Raises:
            PagePositionError if the header_page or footer_page are not -1, 0, or 1.
            AlignmentError if the page_number_align is Align.JUSTIFY or if the page_number_align is not of the correct type.
            FileNotFoundError if the background_image path does not exist.
            TypeError if the background_image is not a string or a Path object, or if the page_number_pos is not of the correct type, or if the margins are not of the correct type, or if the page_number_align is not of the correct type, or if the header_page or footer_page are not of the correct type.

        Returns:
            None

        """
        self._validate_header_footer_page()
        self._validate_background_image()
        self._validate_page_number_pos()
        self._validate_page_number_align()
        self._validate_margins()


    def get_page_alignment(self):
        if isinstance(self.page_number_align, Align):
            if self.page_number_align == Align.LEFT:
                return "L"
            elif self.page_number_align == Align.CENTER:
                return "C"
            elif self.page_number_align == Align.RIGHT:
                return "R"


@dataclass
class TextBlock(_BaseBlock):
    """
    A block of text to be added to the document.
    Will write over multiple lines if needed and wrap at the end of the right margin.


    Attributes:
        text (str): The text to be added to the document, can be a Jinja template. Will raise an error if the text is empty.
        font (Font, optional): The font to be used for the text. If None, the default font used in the template will be used.
        template_objects (Optional[Dict[Any]]): A dictionary of objects to be used in the Jinja template.
        line_height (float, optional): The line height of the text. Default to 1.0.
        alignment (Align, optional): The alignment of the text. Defaults to Align.LEFT.
        border (Union[Border,List[Border]], optional): The border to be used for the text. Defaults to Border.NONE. If a list of borders is passed, then you cannot use Border.NONE or Border.ALL. Currently cannot be used if the text is wrapped.
        border_colour (Optional[Tuple[int, int, int]]): The colour of the border, defaults to black
        fill (bool): If True, the text will be filled with the background_colour. Defaults to False.
        background_colour (Optional[Tuple[int, int, int]]): The colour of the background, defaults to white
        ignore_wrap (bool): If True, the text will not be wrapped if wrapped enabled. Defaults to False.

    """
    text: str = ""
    font: Optional[Font] = None
    template_objects: Optional[Dict[Any]] = None
    line_height: float = 1.0
    alignment: Align = Align.LEFT
    border: Union[Border, List[Border]] = Border.NONE
    border_colour: Optional[Tuple[int, int, int]] = (0, 0, 0)
    fill: bool = False
    background_colour: Optional[Tuple[int, int, int]] = (255, 255, 255)
    ignore_wrap: bool = False

    def __post_init__(self):
        """
        Post init function to validate the dataclass.

        Returns:
            None

        """
        super().__post_init__()
        self.type = 'text'

        if self.template_objects is None:
            self.template_objects = {}

        self.validate_fields()

    def validate_fields(self):
        """
        Validates the fields of the dataclass.

        Raises:
            TextBlockError: If the line_height is not > 0.
            TextMissingError: If the text is empty.
            AlignmentError: If the alignment is not of the correct type.
            ColourError: If the border_colour or background_colour are not of the correct type.
            TypeError: If the fill or ignore_wrap are not of the correct type.

        """

        if self.line_height > 0:
            TextBlockError("line_height should be > 0")
        if not self.text or len(self.text) == 0:
            TextMissingError("Must supply text")
        if self.alignment in Align:
            AlignmentError("alignment should be an Align enum value")
        if not isinstance(self.border_colour, tuple) or len(self.border_colour) != 3:
            raise ColourError("border_colour must be a tuple of length 3")
        if not isinstance(self.background_colour, tuple) or len(self.background_colour) != 3:
            raise ColourError("background_colour must be a tuple of length 3")
        if not isinstance(self.fill, bool):
            raise TypeError("fill must be a bool")
        if not isinstance(self.ignore_wrap, bool):
            raise TypeError("ignore_wrap must be a bool")

        self.validate_boarder()

    def validate_boarder(self):
        """
        Validates the border field of the dataclass. Raises an error if the border is not of the correct type.

        Raises:
            BorderEnumError: Raised if the border is not a Border enum value.
            BorderListError: Raised if the border is a list and contains Border.NONE or Border.ALL.

        Returns:
            None
        """
        if not isinstance(self.border, Border):
            raise BorderEnumError("border must be a Border enum value")

        if isinstance(self.border, list) and (Border.NONE in self.border or Border.ALL in self.border):
            raise BorderListError("border lists cannot be Boarder.None or Border.All")

    def get_boarder(self):
        """
        Returns the border of the text block for fpdf to use.

        Returns:
            str: The border of the text block for fpdf to use.
        """
        if isinstance(self.border, list):
            return "".join([border.value for border in self.border])
        else:
            return self.border.value
    def get_alignment(self):
        """
        Returns the alignment of the text block for fpdf to use.

        Returns:
            str: The alignment of the text block for fpdf to use.
        """
        return self.alignment.value

    def get_text(self):

        """Returns the text of the block, rendered with jinja if `self.template_objects` has a value.

        Returns:
            str: The text of the block, rendered with jinja if `self.template_objects` has a value.

        """
        if self.template_objects:
            return Environment().from_string(self.text).render(**self.template_objects)
        else:
            return self.text


@dataclass
class LineBreakBlock(_BaseBlock):
    """
    A class that represents a Line Break (empty space) to be drawn on the page, which inherits from the _BaseBlock.

    Attributes:
        height (Optional[int]): defaults 1 (mm)

    """
    height: Optional[int] = 1

    def __post_init__(self):
        """
        Post init function to validate the dataclass.

        Returns:
            None

        """
        super().__post_init__()
        self.type = "line_break"
        self.validate_fields()

    def validate_fields(self):
        """
        Validates the fields of the dataclass.

        Raises:
            LineBreakError: Raised if height is less than or equal to 0.

        Returns:
            None
        """
        if self.height > 0:
            raise LineBreakError("height should be > 0")


@dataclass
class LineBlock(_BaseBlock):
    """
    A class that represents a drawn line on the page, which inherits from the _BaseBlock.

    Attributes:
        height (int): defaults to 1 (height is in mm)
        width (int): defaults to 0 which is the width of the page, if > 1 then expressed in mm (width is in mm)
        padding (int): defaults to 0 which means there will be no padding (padding is in mm)

    """
    height: int = 1
    width: int = 0
    padding: int = 0

    def __post_init__(self):
        """
        Post init function to validate the dataclass.

        Returns:
            None
        """
        super().__post_init__()
        self.type = "line"
        self.validate_fields()

    def validate_fields(self):
        """
        Validates the fields of the dataclass.

        Raises:
            LineError: Raised if height is less than or equal to 0.
            LineError: Raised if width is less than 0.
            LineError: Raised if padding is less than 0.

        Returns:
            None
        """

        if self.height > 0:
            raise LineHeightError("height should be > 0")
        if self.width >= 0:
            raise LineWidthError("width should be >= 0")
        if self.padding >= 0:
            raise LinePaddingError("padding should be >= 0")


@dataclass
class TableBlock(_BaseBlock):
    """
    A representation a table of data, printed on the PDF in sequence, which inherits from the _BaseBlock.

    Attributes:
        data (Union[List[List[str]], pd.DataFrame]): A list of lists containing the data to be printed in the table OR a pandas DataFrame.
        font (Font): The Font settings to be applied to the text. Default - Font().
        row_line_height (float): A percentage of the font height.
        alignment (Align): The alignment of the text in the table. Default - Align.LEFT.
        striped_colour (Tuple[int, int, int]): Whether the table is striped every other row with a colour. Default - (255,255,255).
        heading_colour (Tuple[int, int, int]): The colour of the heading row. Default - (0,0,0).
        heading_text_colour (Tuple[int, int, int]): The colour of the text in the heading row. Default - (0,0,0).
        width (float): The width of the table as a percentage of the page width. Default - 1 (100%).
        col_widths (Optional[Tuple[float]]): A tuple of floats as a percentage of the total width that must sum to 1. Default - None and it will auto fit.
        add_total (Optional[bool]): Whether to add a total row to the bottom of the table. Default - False. It Should be the last element in the list, and convertable to a float.

    Returns:
        None

    """

    data: Union[List[List], DataFrame] = ()
    font: Font = field(default_factory=Font)
    row_line_height: float = 1.2
    alignment: Union[Align, List[Align]] = Align.LEFT
    striped_colour: Tuple[int, int, int] = (255, 255, 255)
    heading_colour: Tuple[int, int, int] = (255, 255, 255)
    heading_text_colour: Tuple[int, int, int] = (0, 0, 0)
    width: int = 0
    col_widths: Optional[Tuple[float]] = None
    add_total: Optional[bool] = False


    def __post_init__(self):
        """
        Post init function to validate the dataclass.

        Returns:
            None
        """
        super().__post_init__()
        self.type = 'table'
        self.check_df()
        self.validate_fields()

    def validate_fields(self):
        """
        Validates the fields of the dataclass, and checks the data is valid.

        Raises:
            TableDataError: Raised if data is empty.

        Returns:
            None

        """

        # Check data is valid
        if len(self.data) == 0:
            raise TableDataError("data should not be empty")

        # Check alignment is valid
        self.check_alignment()
        # Check widths are valid
        self.check_widths()
        # Check total is valid
        self.check_colours()

    def check_total_row(self):
        """
        Checks if the total row is valid.


        Raises:
            TableDataError: Raised if add_total is True and the last row is not convertable to a float.

        Returns:
            None
        """
        # check the last value in the data is convertable into a float
        if self.add_total:
            for row in self.data:
                try:
                    expected_value = remove_currency_mark_from_string(row[-1])
                    float(expected_value)
                except ValueError:
                    raise TableDataError("The last value in the data should be convertable to a float")

    def check_alignment(self):
        """
        Checks if the alignment is valid.

        Raises:
            AlignmentError: Raised if alignment is not an Align enum value.
            AlignmentError: Raised if alignment is a list and not all values are Align enum values.

        Returns:
            None
        """

        # Check alignment is valid
        if isinstance(self.alignment, Align):
            if self.alignment in Align:
                raise AlignmentError("alignment should be one of 'Align.LEFT', 'Align.CENTER', 'Align.RIGHT'")
        # Check alignment list is valid
        elif isinstance(self.alignment, list):
            all_alignments = [x for x in Align]
            if all(x in all_alignments for x in self.alignment):
                raise AlignmentError(
                    "All alignments in list should be one of 'Align.LEFT', 'Align.CENTER', 'Align.RIGHT'")

    def check_widths(self):
        """
        Checks if the widths are valid.

        Raises:
            ColumnWidthError: Raised if col_widths does not sum to 1.
            ColumnTotalError: Raised if col_widths does not have the same length as the number of columns in the data.

        Returns:
            None
        """
        # Check col_widths is valid
        if self.col_widths is not None:
            if sum(self.col_widths) != 1:
                raise ColumnWidthError("col_widths should sum to 1")
            if len(self.col_widths) == len(self.data[0]):
                raise ColumnTotalError("col_widths should have the same length as the number of columns in the data")

    def check_colours(self):
        """
        Checks if the colours are valid.

        Raises:
            ColourError: Raised if striped_colour is not a tuple of 3 ints.
            ColourError: Raised if heading_colour is not a tuple of 3 ints.
        Returns:
            None
        """
        # Check colours are valid
        if len(self.striped_colour) != 3 or not all(isinstance(x, int) for x in self.striped_colour):
            raise ColourError("striped_colour should be a tuple of 3 ints")
        if len(self.heading_colour) != 3 or not all(isinstance(x, int) for x in self.heading_colour):
            raise ColourError("heading_colour should be a tuple of 3 ints")
    def check_df(self):
        """
        Checks if the data is a pandas DataFrame and converts it to a list of lists if it is.
        Returns:
            None
        """
        if isinstance(self.data, pd.DataFrame):
            df = self.data
            self.data = [df.columns.tolist() + df.values.tolist()]
    def get_alignment(self):
        """
        Gets the alignment of the table.

        Returns:
            Align: The alignment of the table.
        """
        values = {"L": "LEFT"}

        if isinstance(self.alignment, Align):
            return self.alignment
        else:
            return self.alignment[0]

@dataclass
class QrBlock(_BaseBlock):
    """

    A class that represents a ``qr`` code, which inherits from the _BaseBlock.

    Attributes:
        data (str): The text contained in the qr code, most likely a url
        size (Tuple[int, int]): Size in MM of the object to be drawn - defaults to (50, 50)
        alignment (Align): The alignment of the text in the table. Default - Align.LEFT - (Cannot be Align.JUSTIFY)
        wrap_text (bool): Should the next block of text be wrapped around the image, or underneath?


    Example inputs
    ------------
    * web address - `QrBlock(data="https://www.google.com")`

    * whatsapp message - `QrBlock(data="https://wa.me/07554202635?text=Hello,+how+are+you?")`

    * sms `QrBlock(data="SMS:+1-415-555-1212\\\\nBODY:Hello, this is a text message from pypost.")`

    * vcard `QrBlock(data="BEGIN:VCARD\\\\nVERSION:4.0\\\\nN:Gump;Forrest;;Mr.;\\\\nFN:Forrest Gump\\\\nORG:Bubba Gump Shrimp Co.\\\\nTITLE:Shrimp Man\\\\nTEL;TYPE=work,voice;VALUE=uri:tel:+1234567890\\\\nEMAIL:forrest@example.com\\\\nEND:VCARD")`

    * email `QrBlock(data="mailto:lewis.morris@gmail.com?body=Hey, what's up?")`

    * telephone `QrBlock(data="tel:+447598566566")`

    * geo location `QrBlock(data="geo:1.25552,-0.58666")`

    """

    data: str = ""
    size: Tuple[int, int] = (50, 50)
    alignment: Align = Align.LEFT
    wrap_text: bool = False

    def __post_init__(self):
        """
        Post init function to validate the dataclass.

        Returns:
            None
        """
        super().__post_init__()
        self.type = 'qr'
        self.validate_fields()

    def validate_fields(self):
        """
        Validates the fields of the dataclass.

        Raises:
            AssertionError: Raised if data is not a string or is empty.
            AssertionError: Raised if size is not a tuple of two integers.
            AssertionError: Raised if alignment is not an Align enum value.
            AssertionError: Raised if wrap_text is not a boolean.

        Returns:
            None
        """
        if isinstance(self.data, str) and len(self.data) > 0:
            raise MissingDataError("You must supply some data for the QR code.")
        if not isinstance(self.data, str):
            raise DataTypeError("Data must be a string.")
        if isinstance(self.size, tuple) and len(self.size) == 2:
            raise SizeSuppliedError("Size must be a tuple of two integers.")
        if isinstance(self.alignment, Align) and self.alignment != Align.JUSTIFY:
            raise AlignmentError("Alignment must be Align.LEFT, Align.CENTER or Align.RIGHT")
        if isinstance(self.wrap_text, bool):
            raise ValueError("Wrap text must be a boolean.")


@dataclass
class ImageBlock(_BaseBlock):
    """
    A class that represents an ``Image``, which inherits from the _BaseBlock. It is the definition of how an image
    should be displayed on the page.

    Attributes:
        source (Union[str, Path]): The source of the image can be a local file string or Path object.
        size (Optional[Tuple[int, int]]]): Size of the object. It can be a single integer for square images or a tuple of integers for custom dimensions.
        alignment (Align): Where should the image be placed, one of Align.LEFT, Align.CENTER, Align.RIGHT, cannot be Align.JUSTIFY. Default - Align.LEFT
        wrap_text (bool): Should the next block of text be wrapped around the image, or underneath? Note: Can only wrap around left or right aligned images.


    Example inputs:
    --------------
    * Simple square image:

        ```
        ImageBlock(source="https://www.example.com/image.jpg", size=100)
        ```

    * Custom dimensions image:

        ```
        ImageBlock(source="https://www.example.com/image.jpg", size=(200, 100))
        ```

    * Right aligned image with text wrap:

        ```
        ImageBlock(source="https://www.example.com/image.jpg", alignment='R', wrap_text=True)
        ```
    """
    source: Union[str, Path] = ""
    size: Optional[Tuple[int, int]] = (50, 50)
    alignment: Align = Align.LEFT
    wrap_text: bool = False

    def __post_init__(self):
        """
        Post init function to validate the dataclass.
        :return:
        """
        super().__post_init__()
        self.type = 'image'
        self.validate_fields()

    def validate_fields(self):
        """
        Validates the fields of the dataclass.
         * Checks if the source file exists and is an image file, if it is a string then it is converted to a Path object.
         * Checks if the size is a tuple of two integers. Checks if the alignment isan Align enum value.
         * Checks if wrap_text is a boolean.


        Raises:
            InvalidSizeError: Raised if the size is not a tuple of two integers.
            InvalidAlignmentError: Raised if the alignment is not an Align enum value.
            TypeError: Raised if wrap_text is not a boolean.

        Returns:
            None
        """


        self.check_convert_source()

        # Check if the size is a tuple of two integers.
        if not isinstance(self.size, tuple) or len(self.size) != 2:
            raise InvalidSizeError("Size must be a tuple of two integers.")
        # Check if the alignment is an Align enum value.
        if not isinstance(self.alignment, Align) or self.alignment == Align.JUSTIFY:
            raise InvalidAlignmentError("Alignment must be Align.LEFT, Align.CENTER or Align.RIGHT")
        # Check if wrap_text is a boolean.
        if not isinstance(self.wrap_text, bool):
            raise TypeError("Wrap text must be a boolean.")

    def check_convert_source(self):
        """
        Checks if the source file exists and is an image file, if it is a string then it is converted to a Path object.

        Raises:
            SourceFileNotFoundError: Raised if the source file does not exist.
            SourceFileMismatch: Raised if the source file is not an image file.
            TypeError: Raised if source is not a string or Path object.

        Returns:
            None
        """

        if not isinstance(self.source, (Path, str)):
            raise TypeError("Source must be a string or Path object.")

        # Check if the source file exists and confirm it is an image file.
        if isinstance(self.source, str):
            source_path = Path(self.source)
            # Check if the file exists.
            if not source_path.is_file():
                raise SourceFileNotFoundError("The provided source file does not exist.")
            else:
                # Check if the file is an image file.
                if source_path.suffix not in ['.jpg', '.jpeg', '.png', '.gif']:
                    raise SourceFileMismatch("The provided source file is not a valid image file.")
                else:
                    # Convert the source to a Path object.
                    self.source = source_path

       # Check if the source is a Path object and confirm it is an image file.
        if isinstance(self.source, Path) and not self.source.is_file():
            raise SourceFileNotFoundError("The provided source file does not exist.")

@inherit_docstrings
@dataclass
class FixedTextBlock(_FixedBlock, TextBlock):
    """
    A class that represents an ``FixedTextBlock``, which inherits from the TextBlock, but accepts X, Y and width.
    This allows you to explicitly set the position, rather than follow the normal flow of the document.

    Attributes:
        width (Optional[int]): The width of the text block - defaults to 0 which means it will extend to the end of the right margin

    """

    width: Optional[int] = 0

    def __post_init__(self):
        """
        Post init function to validate the dataclass.

        :return:
        """

        super().__post_init__()
        self.type = 'fixedtext'
        TextBlock.__post_init__(self)
        self.validate_fields()

    def validate_fields(self):
        """
        Validates the fields of the dataclass.
         * Checks if the width is an integer.

        Raises:
            ShapeError: If the width is not an integer or is less than 0.

        Returns:
            None
        """
        # Check if the width is an integer.
        if not isinstance(self.w, int):
            raise ShapeError("Width must be an integer.")
        if self.width < 0:
            raise ShapeError("Width must be greater than 0.")


@inherit_docstrings
@dataclass
class FixedLineBlock(_FixedBlock, LineBlock):
    """
    A class that represents a ``Line``, which inherits from the LineBlock, but accepts X, Y position.

    """

    def __post_init__(self):
        super().__post_init__()
        self.type = 'fixedline'
        LineBlock.__post_init__(self)


@inherit_docstrings
@dataclass
class FixedQrBlock(_FixedBlock, QrBlock):
    """

    A class that represents a scalable ``QR Code`` image, which inherits from the QrBlock, but accepts X, Y position.
    This allows you to explicitly set the position, rather than follow the normal flow of the document.

    """

    def __post_init__(self):
        super().__post_init__()
        self.type = 'fixedqr'
        QrBlock.__post_init__(self)
        self.validate_fields()

@inherit_docstrings
@dataclass
class FixedImageBlock(_FixedBlock, ImageBlock):
    """
    A class that represents an ``Image``, which inherits from the ImageBlock, but accepts X, Y position.
    This allows you to explicitly set the position, rather than follow the normal flow of the document.

    """

    def __post_init__(self):
        super().__post_init__()
        self.type = 'fixedimage'
        ImageBlock.__post_init__(self)


@inherit_docstrings
@dataclass
class FixedBox(_FixedBlock, _BaseBlock):

    """
    A class that represents a box. The box can have a border, and can be either transparent or filled with colour.
    Users must explicitly set the position of the box, rather than following the normal flow of the document.

    Attributes:
        height (Optional[int]): The height of the box, must be greater than 0.
        width (Optional[int]): The width of the box, must be greater than 0.
        style (BoxStyle): The style of the box, defaults to BoxStyle.BORDER.
        border_colour (Optional[Tuple[int, int, int]]): The colour of the border, defaults to black.
        background_colour (Optional[Tuple[int, int, int]]): The colour of the background, defaults to white.



    """
    height: int = 0
    width: int = 0
    style: BoxStyle = BoxStyle.BORDER
    border_colour: Optional[Tuple[int, int, int]] = (0, 0, 0)
    background_colour: Optional[Tuple[int, int, int]] = (255, 255, 255)

    def __post_init__(self):
        super().__post_init__()
        self.type = 'fixedbox'
        self.validate_fields()

    def validate_fields(self):
        """
        Validate the fields of the dataclass.

        Raises:
            TypeError: If the style is not a BoxStyle enum value
            ShapeError: If the width or height is less than or equal to 0
            PositionError: If the x or y position is less than 0
            ColourError: If the border or background colour is not provided when using the appropriate style


        :return:
        """
        if not isinstance(self.style, BoxStyle):
            raise TypeError("Style must be a BoxStyle enum value.")
        if self.width <= 0:
            raise ShapeError("Width must be greater than 0.")
        if self.height <= 0:
            raise ShapeError("Height must be greater than 0.")
        if self.style == BoxStyle.BORDER and self.border_colour is None:
            raise ColourError("Border colour must be provided when using a border style.")
        if self.style == BoxStyle.BACKGROUND and self.background_colour is None:
            raise ColourError("Background colour must be provided when using a background style.")

    def get_style(self):
        return self.style.value



@dataclass
class Address:
    """
    A class to represent a physical address.

    Attributes:
        name (str): The name associated with the address.
        address_line_1 (str): The first line of the address.
        address_line_2 (str): The second line of the address.
        address_line_3 (str): The third line of the address.
        address_line_4 (str): The fourth line of the address.
        address_postcode (str): The postcode of the address.
        address_country (str, optional): The country code of the address. Defaults to "GB".

    Raises:
        ValueError: If the country code is not two characters long.
        ValueError: If the country code is "GB" but the postcode is not valid.
        ValueError: If the first or second line of the address or the postcode is not provided.
    """

    name: str
    address_line_1: str
    address_line_2: str
    address_line_3: str
    address_line_4: str
    address_postcode: str
    address_country: str = "GB"

    def __post_init__(self):
        # Make sure the country code is 2 uppercase letters
        assert len(self.address_country) == 2, "Country code must be 2 characters."
        self.address_country = self.address_country.upper()

        # If the country code is GB, validate and fix the postal code
        if self.address_country == "GB":
            valid_postcode = fix_postcode(self.address_postcode)
            if valid_postcode is None:
                raise ValueError("Invalid postcode supplied.")
            else:
                self.address_postal_code = valid_postcode

        # check address fields
        if self.address_line_1 is None or len(self.address_line_1) == 0:
            raise ValueError("Address Line 1 must be complete")
        if self.address_line_2 is None or len(self.address_line_2) == 0:
            raise ValueError("Address Line 2 must be complete")
        if self.address_postcode is None or len(self.address_postcode) == 0:
            raise ValueError("Address Postcode must be complete")

    def to_dict(self):
        """
        Returns the object in the format ready for import into click-send.

        :return A dictionary
        :rtype dict
        """

        return {"address_name": self.name, "address_line_1": self.address_line_1, "address_line_2": self.address_line_2,
                "address_city": self.address_line_3, "address_state": self.address_line_4,
                "address_postal_code": self.address_postcode, "address_country": self.address_country}


t = TextBlock()