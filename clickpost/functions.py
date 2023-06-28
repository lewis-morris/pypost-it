from functools import wraps
from inspect import getdoc


def inherit_docstrings(cls):
    """A class decorator that appends parent class docstrings to the class docstring."""

    # Get parent docstrings
    parent_docstrings = []
    for parent in cls.__bases__:
        # Skip _FixedBlock class
        if parent.__name__ == '_BaseBlock':
            continue

        doc = getdoc(parent)
        if doc:
            # use repr to properly escape special characters
            parent_docstrings.append(f"{parent.__name__}: {repr(doc)}")

    # Format the class docstring
    cls.__doc__ = f"{getdoc(cls)}\n\nParent Class Docstrings:\n------------------------\n"
    cls.__doc__ += "\n\n".join(parent_docstrings)

    return cls


def remove_currency_mark_from_string(input_string):
    """
    Remove currency mark from string

    :param input_string:
    :type input_string: str
    :return: fixed string
    :rtype: str
    """
    currency_mark_set = {"£", "$", "€"}
    str_input = input_string
    for mark in currency_mark_set:
        str_input = str_input.replace(mark, "")
    return str_input.strip()

def fix_postcode(input_string, re=None):
    """
    Attempts to fix a postcode by removing spaces and adding a space in the correct place.
    :param input_string:
    :return:
    """
    try:
        pattern = re.compile(r"^([a-zA-Z]{1,2}[0-9][a-zA-Z0-9]?)([0-9][a-zA-Z]{2})$")
        match = pattern.match(input_string.replace(" ", "").upper())
        if match:
            part1, part2 = match.groups()
            return f"{part1.strip()} {part2.strip()}"
    except Exception as e:
        return input_string