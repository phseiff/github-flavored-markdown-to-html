"""This file contains some helpers that are used by both core_converter.py and __main__.py."""

import re
import html

# strip html tags from a string (taken from https://stackoverflow.com/a/925630/9816158 by StackOverflow user Eloff):

from io import StringIO
from html.parser import HTMLParser


class MLStripper(HTMLParser):
    def __init__(self):
        super().__init__()
        self.reset()
        self.strict = False
        self.convert_charrefs= True
        self.text = StringIO()

    def handle_data(self, d):
        self.text.write(d)

    def get_data(self):
        return self.text.getvalue()


def strip_tags(html_code):
    s = MLStripper()
    s.feed(html_code)
    return s.get_data()


# helper function to convert headings to id-values:

pattern = re.compile("[^\\w-]+")


def heading_name_to_id_value(header_name: str) -> str:
    """Converts a heading name to an id value in accordance with the GitHub REST API's way of doing this."""
    if "<" in header_name:  # <-- we spare a lot of time by doing this check first
        header_name = strip_tags(header_name)
    return "-".join(
        [pattern.sub('', html.unescape(word).strip()).lower() for word in header_name.strip().split()])
