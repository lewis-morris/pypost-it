class BlockError(Exception):
    pass


class SourceFileNotFoundError(BlockError):
    pass


class InvalidSizeError(BlockError):
    pass


class InvalidAlignmentError(BlockError):
    pass


class SourceFileMismatch(BlockError):
    pass

class MissingDataError(BlockError):
    pass
class SizeSuppliedError(BlockError):
    pass
class AlignmentError(BlockError):
    pass
class ColumnWidthError(BlockError):
    pass
class ColumnTotalError(BlockError):
    pass

class FontStyleError(BlockError):
    pass
class TableDataError(BlockError):
    pass

class ColourError(BlockError):
    pass

class ShapeError(BlockError):
    pass
class PositionError(BlockError):
    pass

class PagePositionError(BlockError):
    pass

class LineHeightError(BlockError):
    pass
class LineWidthError(BlockError):
    pass
class LinePaddingError(BlockError):
    pass
class LineBreakError(BlockError):
    pass
class TextBlockError(BlockError):
    pass
class TextMissingError(BlockError):
    pass
class BorderEnumError(BlockError):
    pass
class BorderListError(BlockError):
    pass
class DataTypeError(BlockError):
    pass