import os
from dataclasses import field
from typing import Union, List, Tuple, Optional, Dict, Any
from jinja2 import Environment
from dataclasses import dataclass

from clickpost.letter import PDF


@dataclass
class Font:
    """
    A class to represent default font settings.

    Attributes:
        font_size (int): The size of the font, should be between 1 and 100. Default is 11.
        font (str): The font name, should be one of "Courier", "Times", "Arial", "Helvetica". Default is "Courier" OR a file path to a font ttf
        font_style (Union[str, List[str]]): The style of the font, can be a string or a list of strings. B (bold) I (italic) U (underline), if nothing is passed it will render normally. Default is "" (empty string).
        font_colour (Tuple[int, int, int]): The RGB values for the font color. Default is (0, 0, 0) (Black).
        font_spacing (float): spacing between the letters of text blocks, 0 = standard, positive values increase the spacing, negative, decrease it.
    """
    font_size: int = 11
    font_name: str = "Courier"
    font_style: Union[str, List[str]] = ""
    font_colour: Tuple[int, int, int] = (0, 0, 0)
    font_spacing: float = 0

    def __post_init__(self):
        assert 1 <= self.font_size <= 100, "font_size should be between 1 and 100"
        if self.font_name not in ["Courier", "Times", "Arial", "Helvetica"]:
            assert os.path.isfile(self.font_name), "Font should be one of 'Courier', 'Times', 'Arial', 'Helvetica' or a valid TrueType or OpenType font path"
        assert isinstance(self.font_style, (str, list)), "font_style should be a string or a list of strings"
        assert all(0 <= channel <= 255 for channel in self.font_colour), "Each channel in font_colour should be between 0 and 255"

    def needs_load(self, pdf: PDF):
        if self.font_name not in pdf.loaded_fonts:
            pdf.add_font(fname=self.font_name)
            self.font_name = os.path.split(self.font_name)[-1].replace(".ttf")

@dataclass
class _BaseBlock:
    """
    A class the base of a block of content - all blocks derive from this.

    Attributes:
        type (String): the type of block
    """
    type: str

    def __post_init__(self):
        pass  # No operation happens here

@dataclass
class TextBlock(_BaseBlock):
    """
    A class that represents a text content block, which inherits from the _BaseBlock.

    Attributes:
        text (str): The text to be included in the block.
        font (Font): The Font settings to be applied to the text. Defaults to Font().
        template_objects (Optional[Dict]): Optional dictionary of objects to be passed to the Jinja renderer. Defaults to {}.
        line_height (float): A percentage of the text height, should be > 0.
        alignment (str): The text alignment. Options include "J" (justify), "C" (center), "L" (left), "R" (right).
        ignore_wrap (bool): If there is a wrap in place just ignore it
    """
    text: str
    font: Font = field(default_factory=Font)
    _template_objects: Optional[Dict[Any]] = None
    line_height: float = 2
    alignment: str = "J"
    ignore_wrap: bool = False

    def __post_init__(self):
        super().__post_init__()
        self.type = 'text'
        assert self.line_height > 0, "line_height should be > 0"
        assert self.alignment in ["J", "C", "L", "R"], "alignment should be one of 'J', 'C', 'L', 'R'"
        if self._template_objects is None:
            self._template_objects = {}
        self.text = Environment().from_string(self.text).render(**self._template_objects)

@dataclass
class Template:
    """
    A class representing a template for a document, including headers, footers, and other elements.

    Attributes:
        default_font (Font): The default font to be used if one has not been specified in a text block.
        header_content (Union[_BaseBlock, List[_BaseBlock]]): A block of content or a list of blocks to be added to the header.
        footer_content (Union[_BaseBlock, List[_BaseBlock]]): A block of content or a list of blocks to be added to the footer.
        header (bool, optional): If True, a header will be included in the document. Defaults to False.
        header_page (int, optional): Define the pages to display the header. 1 = First page, 0 = All pages, -1 = Last page. Defaults to 0.
        footer (bool, optional): If True, a footer will be included in the document. Defaults to False.
        footer_page (int, optional): Defines the pages to display the footer. 1 = First page, 0 = All pages, -1 = Last page. Defaults to 0.
        background_image (str, optional): The path to an image file to use as the document background. Defaults to None.
        page_numbers (bool, optional): If True, page numbers will be added to each page. Defaults to False.
        page_number_pos (int, optional): The position of the page number. 1 for the top of the page, 2 for the bottom. Defaults to 1.
        page_number_align (str, optional): The alignment position of the page number. L (left) C (center) R (right)
        margins (Tuple[int, int, int, int], optional): The margins of the document in the order of top, right, bottom, left. Defaults to (10, 10, 10, 10).
    """
    default_font: Font = Font()
    header_content: Union[None, _BaseBlock, List[_BaseBlock]] = None
    footer_content: Union[None, _BaseBlock, List[_BaseBlock]] = None
    header: bool = False
    header_page: int = 0
    footer: bool = False
    footer_page: int = 0
    background_image: Optional[str] = None
    page_numbers: bool = False
    page_number_pos: int = 1
    page_number_align: str = "C"
    margins: Tuple[int, int, int, int] = (10, 10, 10, 10)

@dataclass
class LineBreakBlock(_BaseBlock):
    """
    A class that represents a Line Break (empty space), which inherits from the _BaseBlock.

    Attributes:
        height (int) defaults to None which is the height of the last block, otherwise it is in mm
    """
    height: Union[int, None] = None

@dataclass
class LineBlock(_BaseBlock):
    """
    A class that represents a Line Break (empty space), which inherits from the _BaseBlock.

    Attributes:
        height (int) defaults to 1mm
        width (int) defaults to None which is the width of the page
        padding (int) defaults to None which means there will be no padding
    """
    height: Union[int] = 1
    width: Union[int, None] = None
    padding: Union[int, None] = None
@dataclass
class TableBlock(_BaseBlock):
    """
    A class that represents a table content block, which inherits from the _BaseBlock.

    Attributes:
        data (List[List]): A list of lists where the first item is the header row which will generate the table.
        font (Font): The Font settings to be applied to the text. Defaults to Font().
        row_line_height (float): A percentage of the font height.
        alignment (Union[str, List[str]]): Alignment for each column in the table, a single string applies to all columns. Defaults to "LEFT".
        striped_colour (Tuple[int, int, int]): Whether the table is striped every other row with a colour.
        heading_colour (Tuple[int, int, int]): RGB values for heading row color. Defaults to (0,0,0).
        heading_text_colour (Tuple[int, int, int]): RGB values for heading row text color. Defaults to (0,0,0).
        width (Optional[int]): Width of the table in mm, default is None which means 100%.
        col_widths (Optional[Tuple[float]]): A tuple of floats as a percentage of the total width that must sum to 1. Defaults to None and it will auto fit.
    """
    data: List[List]
    font: Font = field(default_factory=Font)
    row_line_height: float = 1.2
    alignment: Union[str, List[str]] = "LEFT"
    striped_colour: Tuple[int, int, int] = (255,255,255)
    heading_colour: Tuple[int, int, int] = (255,255,255)
    heading_text_colour: Tuple[int, int, int] = (0,0,0)
    width: Optional[int] = None
    col_widths: Optional[Tuple[float, ...]] = None

    def __post_init__(self):
        super().__post_init__()
        self.type = 'table'
        if isinstance(self.alignment, str):
            assert self.alignment in ["LEFT", "CENTER", "RIGHT"], "alignment should be one of 'LEFT', 'CENTER', 'RIGHT'"
        elif isinstance(self.alignment, list):
            assert all(align in ["LEFT", "CENTER", "RIGHT"] for align in
                       self.alignment), "All alignments in list should be one of 'LEFT', 'CENTER', 'RIGHT'"
        if self.col_widths is not None:
            assert sum(self.col_widths) == 1, "col_widths should sum to 1"

@dataclass
class QrBlock(_BaseBlock):
    """
    Example inputs
    ------------
    A class that represents a ``qr`` code, which inherits from the _BaseBlock.

    Attributes:
        data (str): The text contained in the qr code, most likely a url
        size (tuple): Size in MM of the object (it's always square)
        alignment (str): L (left) | R (right) | C (center)
        wrap_text (bool): Should the next block of text be wrapped around the image, or underneath? Can only wrap around left or right aligned QR codes.

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

    data: str
    size: Optional[tuple] = (50,50)
    alignment: str = "L"
    wrap_text: bool = False

    def __post_init__(self):
        super().__post_init__()
        self.type = 'qr'
        assert isinstance(self.data, str) and len(self.data) > 0, "You must supply some data for the QR code."



@dataclass
class ImageBlock(_BaseBlock):
    """
    A class that represents an ``ImageBlock``, which inherits from the _BaseBlock.

    Attributes:
        source (str): The path or url to the image file.
        size (Optional[Union[int, Tuple[int, int]]]): Size of the object. It can be a single integer for square images or a tuple of integers for custom dimensions.
        alignment (str): L (left) | R (right) | C (center)
        wrap_text (bool): Should the next block of text be wrapped around the image, or underneath? Can only wrap around left or right aligned images.

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
    source: str
    size: Optional[Union[int, Tuple[int, int]]] = (50, 50)
    alignment: str = "L"
    wrap_text: bool = False

    def __post_init__(self):
        super().__post_init__()
        self.type = 'image'
        assert os.path.isfile(self.source), "The provided source file does not exist."


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
            valid_postcode = self.fix_postcode(self.address_postal_code)
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
        return {"address_name": self.name, "address_line_1": self.address_line_1, "address_line_2": self.address_line_2,
                "address_city": self.address_line_3, "address_state": self.address_line_4,
                "address_postal_code": self.address_postcode, "address_country": self.address_country}
