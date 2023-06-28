from enum import Enum


class FontName(Enum):
    COURIER = "Courier"
    TIMES = "Times"
    ARIAL = "Arial"
    HELVETICA = "Helvetica"


class PageNumberPos(Enum):
    TOP = 1
    BOTTOM = 2


class PagePlacement(Enum):
    FIRST = 1
    LAST = 2
    ALL = 3
    NONE = 4
    CURRENT = 5


class Align(Enum):
    LEFT = "L"
    CENTER = "C"
    RIGHT = "R"
    JUSTIFY = "J"


class FontStyle(Enum):
    BOLD = "B"
    ITALIC = "C"
    UNDERLINE = "R"
    NONE = ""


class BoxStyle(Enum):
    BORDER = "D"
    BACKGROUND = "F"
    BORDER_BACKGROUND = "DF"


class Border(Enum):
    NONE = 0
    ALL = 1
    TOP = "T"
    BOTTOM = "B"
    LEFT = "L"
    RIGHT = "R"

