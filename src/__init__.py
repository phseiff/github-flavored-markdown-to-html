"""Convert Markdown to html via python or with a command line interface."""

import textwrap
import urllib

import requests
import string
import random
import re
import argparse
import sys
import os
import shellescape
from PIL import Image, ImageSequence
import PIL
from io import BytesIO
from urllib.parse import quote
import traceback
import subprocess
import json
import webcolors
import emoji
from ast import literal_eval as make_tuple
import bs4
from bs4 import BeautifulSoup
import hashlib
import math as math_module
import shutil
import typing
import html
from . import windows_shellescape
import uuid
import warnings
from .latex2svg import latex2svg
from .helpers import heading_name_to_id_value
try:
    import tidylib
    imported_tidylib = True
except (ImportError, ModuleNotFoundError):
    imported_tidylib = False
try:
    import difflib
    imported_difflib = True
except (ImportError, ModuleNotFoundError):
    imported_difflib = False

MODULE_PATH = os.path.join(*os.path.split(__file__)[:-1])
DEBUG = False  # whether to print debug information
DEBUG_HASHES = False
HASH_FUNCTION_TO_USE_ON_IMAGES = lambda x: hashlib.md5(x.encode() if type(x) is str else x)


def open_local(path, *args, **kwargs):
    return open(os.path.join(MODULE_PATH, path), *args, **kwargs)


HELP = open_local("help.txt", "r", encoding="utf-8").read()


def is_not_escaped(s: str, i: int):
    """Returns True if the i-th character of the string s is not escaped using a "\\"-symbol"""
    return i == 0 or s[i - 1] != "\\"


def get_key_of_item(d: dict, i: str) -> str:
    """Returns the key of item (string) i in dict d, or None if i is not in d."""
    for key, item in d.items():
        if item == i:
            return key
    return ""


def get_random_string(starting_letter: str):
    """Returns a random string starting with starting_letter, consisting of letters (uppercase and lowercase) and
    numbers."""
    return starting_letter + ''.join(random.choices(string.ascii_uppercase + string.digits, k=20))


def get_fitting_replacement(thing_to_replace: str, table_of_replacement: dict, text_to_replace_in: str, s: str):
    """Takes a thing for which a replacement is searched, a table mapping replacements to the things they stand for,
    and a string in which the replacement should be done. Returns a string to replace with, which is either the key
    of thing_to_replace_with in table_of_replacements, if it already exists in there, or a completely newly generated
    random string if not. s is a string with which every replacement has to start."""
    replacement = get_key_of_item(table_of_replacement, thing_to_replace)
    if not replacement:
        while replacement in table_of_replacement or replacement in text_to_replace_in:
            replacement = get_random_string(s)
    return replacement


def shortcode_to_emoji(shortcode: str, emoji_support_level):
    if emoji_support_level == 0:
        return shortcode
    else:
        if "." not in shortcode:
            # we take this as a hint that this is a non-custom emoji:
            if shortcode not in emoji.EMOJI_ALIAS_UNICODE_ENGLISH:
                warnings.warn("`" + shortcode + "` is not a valid emoji shortcode.\n"
                              + "This does no harm; we are just letting you know in case you intended it to be an emoji"
                              + " shortcode and mistyped it accidentally."
                              + "")
            return emoji.emojize(shortcode, use_aliases=True, variant="emoji_type")
        else:
            # we take this as a hint that this is a custom emoji:
            escaped_shortcode = shortcode[1:-1].replace("'", "\'").replace('"', '\"')
            emoji_name = escaped_shortcode.split("/")[-1].split("?")[0].split("&")[0]
            title = emoji_name.rsplit(".", 1)[0].replace("-", " ").replace("_", " ")
            for i in range(len(title)-1, -1, -1):
                if title[i].isupper():
                    title = title[:i] + " " + title[i:]
            return ("<img src='" + escaped_shortcode + "' "
                    + "title=':" + emoji_name + ":' "
                    + 'alt="' + title + '" style="width:1em; height:1em;" is_emoji="true">')


STD_EMOJI_CHARS = "-" + "_" + string.ascii_uppercase + string.ascii_lowercase + string.digits
EXT_EMOJI_CHARS = "-._~/?#[]@!$&'()*+,;=" + string.ascii_uppercase + string.ascii_lowercase + string.digits  # <- no :
EMOJI_WHITESPACE = ("\n", "\t", " ")


def proceed_emoji_parsing(line, i, emoji_replacements, emoji_start, emoji_state, md, support_custom_emojis=False):
    # values for emoji_state:
    #  0: not within an emoji and not a whitespace
    #  1: in whitespace
    #  2: at : in front of an emoji
    #  3: within text of emoji
    #  4: at closing : of emoji
    success = False
    if emoji_state == 0:  # <- was not within an emoji and not a whitespace
        if line[i] in EMOJI_WHITESPACE:
            emoji_state = 1
    elif emoji_state == 1:  # <- was in whitespace
        if line[i] == ":" and is_not_escaped(line, i):
            emoji_state = 2
            emoji_start = i
        elif line[i] not in EMOJI_WHITESPACE:
            emoji_state = 0
    elif emoji_state == 2:  # <- was at a : sign
        if line[i] in (STD_EMOJI_CHARS if not support_custom_emojis else EXT_EMOJI_CHARS):
            emoji_state = 3
        elif line[i] in EMOJI_WHITESPACE:
            emoji_state = 1
        else:
            emoji_state = 0
    elif emoji_state == 3:  # <- was within an emoji
        if line[i] in (STD_EMOJI_CHARS if not support_custom_emojis else EXT_EMOJI_CHARS):
            emoji_state = 3
        elif line[i] == ":" and support_custom_emojis and (i != len(line)-1) and (line[i+1] in EXT_EMOJI_CHARS + ":"):
            emoji_state = 3  # <- support : in extended emojis
        elif line[i] in EMOJI_WHITESPACE:
            emoji_state = 1
        elif line[i] == ":":
            if i == len(line) - 1:
                i += 1
                success = True
            else:
                emoji_state = 4
        else:
            emoji_state = 0
    elif emoji_state == 4:  # <- was at the trailing : of an emoji
        if line[i] in EMOJI_WHITESPACE:
            success = True
        else:
            emoji_state = 0
    if success:
        emoji_state = 1
        emoji_shortcode = line[emoji_start:i]
        replacement = get_fitting_replacement(emoji_shortcode, emoji_replacements, md, "e")
        emoji_replacements[replacement] = emoji_shortcode
        line_new = line[:emoji_start] + replacement + line[i:]
        i += len(line_new) - len(line)
        line = line_new
        if i == len(line):
            i -= 1
    return line, i, emoji_replacements, emoji_start, emoji_state


def find_and_replace_formulas_in_markdown(md: str, support_formulas=True, support_custom_emojis=False):
    """Takes markdown as a string and returns the markdown, but every formula is replaced with a random string, as well
    as a dict to translate these strings back to the formulas. This is done to evade the problem that special characters
    in formulas should not be escaped and that they should not be interpreted, e.g. as code etc.
    Non-ascii characters in multiline code blocks also get replaced with random strings, and the third return
    value is a dict mapping these replacements back to these non-ascii characters; otherwise, they would not be
    transmitted correctly over to the github REST api and ultimately be lost. Replacing them with html encodings is
    not possible either since GitHub's api uses <pre>-blocks for multiline code.
    If support_formulas is set to false, formula replacement wil be omitted and only special characters in code blocks
    will be replaced; the second return value is the mapping of replacement strings to formulas.
    The fourth return value is a list of headings in order of appearance, each one as a depth-name-tuple."""
    md_lines = md.splitlines()
    formulas = dict()
    special_characters_in_code = dict()
    headings = list()
    inside_multiline_code = False
    # specifically for emojis:
    emoji_replacements = dict()

    # iterate over the document's lines:
    for l_num in range(len(md_lines)):
        emoji_state = 1  # 1 because the -1st letter of ever line is considered to be whitespace.
        emoji_start = 0
        line = md_lines[l_num]
        # switch between multiline code blocks and things that aren't multiline code blocks:
        if line.strip().startswith("```"):
            inside_multiline_code = not inside_multiline_code
            continue
        # we need to look for formulas, inline code blocks and table of content indicators outside:
        if not inside_multiline_code:
            if DEBUG:
                print(line)
            inside_inline_code = False
            formula_start = 0
            in_formula = False
            # are we at a heading? if yes, register that and move on to the next line.
            if line.strip().startswith("#") and " " in line and line.split(" ")[0] == "#" * len(line.split(" ")[0]):
                # search for emojis:
                i = -1
                if DEBUG:
                    print("\n" + line)
                while i < len(line) - 1:
                    i += 1
                    if line[i] == "`" and is_not_escaped(line, i):
                        inside_inline_code = not inside_inline_code
                    if not inside_inline_code:
                        line, i, emoji_replacements, emoji_start, emoji_state = proceed_emoji_parsing(
                            line, i, emoji_replacements, emoji_start, emoji_state, md, support_custom_emojis)

                headings.append((len(line.split(" ")[0]), line.split(" ", 1)[1]))
                md_lines[l_num] = line
                continue
            # we simply iterate over all characters of the line now, setting and unsetting flags as we pass them.
            i = -1
            while i < len(line) - 1:
                i += 1
                # do emoji checks:
                if not inside_inline_code and not in_formula:
                    line, i, emoji_replacements, emoji_start, emoji_state = proceed_emoji_parsing(
                        line, i, emoji_replacements, emoji_start, emoji_state, md, support_custom_emojis)
                # check whether a formula starts or ends here (only if formulas support is activated):
                if support_formulas and line[i] == "$" and is_not_escaped(line, i) and not inside_inline_code:
                    if not in_formula:
                        # become aware of the beginning of a formula:
                        in_formula = True
                        formula_start = i + 1
                    else:
                        # at the end of the formula, store it and replace it with a replacement string:
                        in_formula = False
                        formula_close = i
                        formula = line[formula_start:formula_close]
                        replacement = get_fitting_replacement(formula, formulas, md, "f")
                        formulas[replacement] = formula
                        line = line[:formula_start - 1] + replacement + line[formula_close + 1:]
                        i += len(replacement) - ((formula_close+1) - (formula_start-1))
                # end or start an inline code block:
                elif line[i] == "`" and is_not_escaped(line, i) and not in_formula:
                    inside_inline_code = not inside_inline_code
                # store special characters in inline code blocks and replace them with a replacement string:
                elif inside_inline_code and not in_formula:
                    character = line[i]
                    if character not in string.printable:
                        replacement = get_fitting_replacement(character, special_characters_in_code, md, "c")
                        special_characters_in_code[replacement] = character
                        line = line[:i] + replacement + line[i+1:]
                        i += len(replacement) - 1
                # handle escaped formula-signs if formula support is activated:
                if support_formulas:
                    line = line.replace("\\$", "$")
                if DEBUG:
                    print(emoji_state, end="")
            # encode umlauts outside of inline code blocks:
            line = str(line.encode('ascii', 'xmlcharrefreplace'), encoding="utf-8")
            if DEBUG:
                print("\n")
        # search for non-ascii characters if we are in a multiline code block:
        else:
            for character in set(line):
                if character not in string.printable:
                    # store special characters in multiline code blocks and replace them with a replacement string:
                    replacement = get_fitting_replacement(character, special_characters_in_code, md, "c")
                    special_characters_in_code[replacement] = character
                    line = line.replace(character, replacement)
        md_lines[l_num] = line

    return "\n".join(md_lines), formulas, special_characters_in_code, headings, emoji_replacements


def header_name_to_link_to_header(header_name: str) -> str:
    """Takes the name of a header and creates a link to said header in markdown format."""
    id_from_title = heading_name_to_id_value(header_name)
    link = "[" + header_name.strip() + "](#" + id_from_title + ")"
    # We do NOT add `#user-content` here! This is on purpose since this is done at another place later.
    return link


def render_toc(md_content: str, headings: typing.List[typing.Tuple[int, str]]) -> str:
    """Takes the md-file's content and a list of headings in the same format in which they are output by
    find_and_replace_formulas_in_markdown, and renders toc-tags (`[[_TOC_]]`, `[toc]` and `{:toc}`) to content sections.
    """

    # stop if we have no headings:
    if not headings:
        return md_content

    # find how deep we nestle:
    highest_depth_in_headers = 0
    for depth, _ in headings:
        if depth > highest_depth_in_headers:
            highest_depth_in_headers = depth

    # find the depth in which the nestling begin:
    for depth in range(1, highest_depth_in_headers + 1):
        number_of_headings_with_this_deph = 0
        for heading_depth, _ in headings:
            if heading_depth == depth:
                number_of_headings_with_this_deph += 1
        if number_of_headings_with_this_deph >= 2:
            lowest_depth_of_which_several_exist = depth
            break
    else:
        # apparently, there is no depth of which more than one heading exists.
        return md_content

    # actually create the toc:
    toc = list()
    top_level_count = 0
    base_indention = 0
    for header_depth, header_text in headings:
        if header_depth < lowest_depth_of_which_several_exist:
            continue
        if header_depth == lowest_depth_of_which_several_exist:
            top_level_count += 1
            toc.append(str(top_level_count) + ". " + header_name_to_link_to_header(header_text))
            base_indention = len(str(top_level_count)) + 2
        elif header_depth > lowest_depth_of_which_several_exist:
            indention = base_indention + 2 * (header_depth - lowest_depth_of_which_several_exist - 1)
            toc.append(" " * indention + "* " + header_name_to_link_to_header(header_text))
    toc = "\n" + "\n".join(toc) + "\n"

    # replace toc in document:
    md_content = md_content.split("\n")
    for toc_token in ("[[_TOC_]]", "[toc]", "{:toc}"):
        i = -1
        while i < len(md_content) - 1:
            i += 1
            if md_content[i].rstrip() == toc_token:
                md_content[i] = toc
    md_content = "\n".join(md_content)

    return md_content


# a stand-alone function to render tocs in markdown files in case one wants to do just that:

def render_toc_in_md_file_stand_alone(md_content: str, support_custom_emojis=False) -> str:
    _, _, _, headers, _ = find_and_replace_formulas_in_markdown(md_content, support_custom_emojis)
    return render_toc(md_content, headers)


# Decide which function to convert latex formulas to svg is preferable:


formula2svg_client = None


def raw_formula2svg_offline(formula):
    return latex2svg(formula)["svg"]


def raw_formula2svg_online(formula):
    return formula2svg_client.get(
        url="https://latex.codecogs.com/svg.latex?" + quote(formula)
    ).text


if shutil.which("latex") and shutil.which("dvisvgm"):
    try:
        raw_formula2svg_offline("w")
        raw_formula2svg = raw_formula2svg_offline
    except (RuntimeError, subprocess.CalledProcessError):
        raw_formula2svg = raw_formula2svg_online
else:
    raw_formula2svg = raw_formula2svg_online

# Function to convert latex formulas to svg:


def formula2svg(formula, amount_of_svg_formulas):
    """Takes a LaTeX-Formula and converts it to a svg."""
    global formula2svg_client
    formula2svg_client = requests.session()
    formula_rendered = raw_formula2svg(formula)
    formula_rendered_soup = BeautifulSoup(formula_rendered, 'html.parser')

    # Remove xml declaration:
    for e in formula_rendered_soup:
        if isinstance(e, bs4.element.ProcessingInstruction) or isinstance(e, bs4.Comment):
            e.extract()

    # Add style and class to svg element:
    svg_element_soup_representation = formula_rendered_soup.find("svg")
    svg_element_soup_representation["class"] = "gh-md-to-html-formula"
    svg_element_soup_representation["style"] = "vertical-align: middle;"

    # Correct all elements with path attribute:
    for element_with_id_soup_representation in formula_rendered_soup.find_all(lambda tag: tag.has_attr("id")):
        element_with_id_soup_representation["id"] += "n" + str(amount_of_svg_formulas)

    # Correct every reference to them:
    for element_referencing_id_soup_representation in formula_rendered_soup.find_all(
            lambda tag: tag.has_attr("xlink:href")):
        element_referencing_id_soup_representation["xlink:href"] += "n" + str(amount_of_svg_formulas)

    if DEBUG:
        print(" ---    FORMULA:", formula, " --- quoted:", quote(formula), " --- url:",
              "https://latex.codecogs.com/svg.latex?" + quote(formula))

    return formula_rendered_soup.__str__()

# Find and render formulas in the html code, and replace them correctly:


def find_and_render_formulas_in_html(html_text: str, formulas: dict, special_characters_in_code: dict,
                                     emoji_replacements: dict, emoji_support: int):
    """Takes some html (generated from markdown by the online github API) and a dictionary which maps a number of
    sequences to a number of formulas, and replaces each sequence with a LaTeX-rendering of the corresponding formula.
    The third parameter is a dictionary mapping replacements to special characters for use in code blocks.
    """

    # replace formulas:
    amount_of_svg_formulas = 0
    for sequence, formula in formulas.items():
        formula_rendered = formula2svg(formula, amount_of_svg_formulas)
        html_text = html_text.replace(
            sequence,
            formula_rendered
        )
        amount_of_svg_formulas += 1

    # replace special characters:
    for sequence, special_character in special_characters_in_code.items():
        html_text = html_text.replace(
            sequence,
            special_character
        )

    # replace emojis:
    for sequence, emoji_shortcode in emoji_replacements.items():
        if DEBUG:
            print("replace:", sequence, shortcode_to_emoji(emoji_shortcode, emoji_support))
        html_text = html_text.replace(
            sequence,
            shortcode_to_emoji(emoji_shortcode, emoji_support)
        )

    return html_text


def str2bool(v):
    """Convert a string taken as a confirmation or objection to a bool."""
    if type(v) not in (bool, str, int):
        raise argparse.ArgumentTypeError('Boolean value expected.')
    if isinstance(v, bool):
        return v
    if v in (0, 1):
        return bool(v)
    if v.lower() in ('yes', 'true', 't', 'y', '1'):
        return True
    elif v.lower() in ('no', 'false', 'f', 'n', '0'):
        return False
    else:
        raise argparse.ArgumentTypeError('Boolean value expected.')


def markdown_to_html_via_github_api(markdown):
    """Converts markdown to html, using the github api and nothing else."""
    headers = {"Content-Type": "text/plain", "charset": "utf-8"}
    return str(
        requests.post("https://api.github.com/markdown/raw", headers=headers, data=markdown.encode("utf-8")).content,
        encoding="utf-8"
    )


def compress_images_input_to_dict(compress_images) -> dict:
    """Parse the input of the compress-images-parameter to a python dict (empty if we should not do compression at all)
    according to the specification in the help text.

    --------
    Doctests:
    --------

    Entering Bools for True:

    >>> compress_images_input_to_dict("False")
    {}

    >>> compress_images_input_to_dict(False)
    {}

    Entering Bools for True:

    >>> compress_images_input_to_dict("True") == {'bg-color': (255, 255, 255), 'progressive': False, 'srcset': False, 'quality': 90}
    True

    >>> compress_images_input_to_dict(True) == {'bg-color': (255, 255, 255), 'progressive': False, 'srcset': False, 'quality': 90}
    True

    Entering a dict (check if it is correctly extended with the omitted attributes, and no given ones are overwritten):

    >>> compress_images_input_to_dict({'quality': 80}) == {'bg-color': (255, 255, 255), 'progressive': False, 'srcset': False, 'quality': 80}
    True

    Entering some json data (check if it is correctly converted to a dict, extended with the omitted attributes, and
    no given ones are overwritten):

    >>> compress_images_input_to_dict("{\\"quality\\": 80, \\"progressive\\": \\"yes\\"}") == {'bg-color': (255, 255, 255), 'progressive': True, 'srcset': False, 'quality': 80}
    True

    Setting the srcset-attribute to True and checking if the right default value is chosen:

    >>> compress_images_input_to_dict("{\\"srcset\\": \\"y\\"}") == {'bg-color': (255, 255, 255), 'progressive': False, 'srcset': [500, 800, 1200, 1500, 1800, 2000], 'quality': 90}
    True

    Specify some sizes for srcset to ensure they aren't overwritten:

    >>> compress_images_input_to_dict("{\\"srcset\\": [80]}") == {'bg-color': (255, 255, 255), 'progressive': False, 'srcset': [80], 'quality': 90}
    True

    """
    # Return an empty dict if nothing was specified:
    if not compress_images:
        return dict()

    # Define default dict to use when input is True:
    default_dict = {
        "bg-color": "white",
        "progressive": "False",
        "srcset": "False",
        "quality": 90,
    }
    # Choose default dict if input is a True-string and return an empty dict if it is a False-string:
    try:
        if str2bool(compress_images) is True:
            compress_images = json.dumps(default_dict)
        elif str2bool(compress_images) is False:
            return dict()
    except argparse.ArgumentTypeError:
        pass

    # Convert the compression-info-dict to an actual dict:
    try:
        if type(compress_images) is dict:  # <-- Use the given input if its type is dict.
            compression_information = compress_images
        else:
            compression_information = json.loads(compress_images)
    except (json.decoder.JSONDecodeError, TypeError) as e:
        raise ValueError("Apparently, your compression information was not valid json data.")

    # Fill in default values for all omitted fields:
    for default_key, default_value in default_dict.items():
        if default_key not in compression_information:
            compression_information[default_key] = default_value

    # Convert string descriptions of boolean values to actual boolean values:
    for boolean_key in ("progressive", "srcset"):
        try:
            compression_information[boolean_key] = str2bool(compression_information[boolean_key])
        except argparse.ArgumentTypeError:
            if bool == "progressive":
                raise argparse.ArgumentTypeError(
                    "The 'progress'-value of the compress-images-input must be boolean!")

    # Set the default for srcset if srcset is True:
    if compression_information["srcset"] is True:
        compression_information["srcset"] = [500, 800, 1200, 1500, 1800, 2000]

    # Convert the color given to bg-color to a three-tuple:
    compression_information["bg-color"] = compression_information["bg-color"].strip()  # <-- Remove whitespace
    if compression_information["bg-color"].startswith("rgb"):
        try:  # <-- rgb-tuple
            compression_information["bg-color"] = make_tuple(compression_information["bg-color"].replace("rgb", ""))
        except ValueError:
            raise argparse.ArgumentTypeError("Invalid rgb tuple for compress-images->bg-color given.")
    elif compression_information["bg-color"].startswith("#"):
        try:  # <-- hex-color
            compression_information["bg-color"] = webcolors.hex_to_rgb(compression_information["bg-color"])
        except ValueError:
            raise argparse.ArgumentTypeError("Invalid hex color value for compress-images->bg-color given.")
    else:
        try:  # <-- color name
            compression_information["bg-color"] = webcolors.name_to_rgb(compression_information["bg-color"])
        except ValueError:
            raise argparse.ArgumentTypeError("Invalid color name for compress-images->bg-color given.")
    # Convert the color tuple to a tuple:
    compression_information["bg-color"] = tuple(compression_information["bg-color"])

    # return the result:
    return compression_information

# Find a fitting hash function for the amount of images we plan to hash:


def find_fitting_hash_function(amount_of_images):
    global HASH_FUNCTION_TO_USE_ON_IMAGES
    if amount_of_images <= 1000:
        HASH_FUNCTION_TO_USE_ON_IMAGES = hash
    else:
        HASH_FUNCTION_TO_USE_ON_IMAGES = lambda x: hashlib.md5(x.encode() if type(x) is str else x)

# Hash an image:


def hash_image(img, return_unhashed=False):
    if type(img) in (str, bytes):
        return HASH_FUNCTION_TO_USE_ON_IMAGES(img)

    pixel_data = list()
    frames_durations = list()
    for frame in ImageSequence.Iterator(img):
        frame = frame.convert("RGBA")
        if "duration" in frame.info:
            frames_durations.append(str(frame.info["duration"]))
        for pixel in list(frame.getdata()):
            pixel_data += list(pixel)
    pixel_data_string = str(bytes(pixel_data), encoding="iso-8859-1")
    pixel_data_string += "||" + str(img.size) + "||" + (str(img.format.lower() if img.format else None)) + (
        ("||" + str(",".join(frames_durations))) if frames_durations else ""
    )

    if return_unhashed:
        return pixel_data_string
    return HASH_FUNCTION_TO_USE_ON_IMAGES(pixel_data_string)


# def test_image_hashing():
#     import time
#     t = time.time()
#     hash_image(Image.open("images/68747470733a2f2f706873656966662e636f6d2f696d616765732f69636f6e2e6a706567.jpeg"))
#     print("t:", time.time() - t)
# test_image_hashing()

# Find a filename from a name, a set of names that are already taken, and an appendix to add before the extension:


def make_unused_name(base_file_name, file_name_addition, already_used_filenames, hashes_to_filenames, hash_of_image,
                     ending=None):
    """Takes a base_file_name foo.x, a file_name_addition .bar, and a set of already used filenames.
    Returns foo.bar.x, if foo.bar.x is not yet in already_used_filenames, and otherwise, adds enough
    underscored to foo to make the file name unique. The result is returned and added to already_used_filenames.

    If ending is specified (in the form .y), the generated file name will be foo.bar.y instead of foo.bar.x."""
    def make_final_filename(name, add):
        return name.rsplit(".", 1)[0] + add + "." + name.rsplit(".", 1)[1]
    def resulting_name_too_long(name, add):
        return len(name) + len(add) > 260
    def resulting_name_already_used(name, add):
        return make_final_filename(name, add) in already_used_filenames

    if hash_of_image in hashes_to_filenames:
        if DEBUG_HASHES:
            print("image already present as", hashes_to_filenames[hash_of_image])
        return hashes_to_filenames[hash_of_image]
    if ending is None:
        ending = "." + base_file_name.rsplit(".", 1)[-1]
    base_file_name = base_file_name.rsplit(".", 1)[0] + ending
    while (
            resulting_name_already_used(base_file_name, file_name_addition)
            or resulting_name_too_long(base_file_name, file_name_addition)
    ):
        if resulting_name_already_used(base_file_name, file_name_addition):
            base_file_name = make_final_filename(base_file_name, "_")
        if resulting_name_too_long(base_file_name, file_name_addition):
            base_file_name = base_file_name[:32] + "-" + uuid.uuid4().hex + "." + ending
    base_file_name = make_final_filename(base_file_name, file_name_addition)
    already_used_filenames.add(base_file_name)
    hashes_to_filenames[hash_of_image] = base_file_name

    return base_file_name


# Compress and save image according to some arguments:


def compress_image(full_image, width, bg_color, quality, progressive,
                   base_file_name, file_name_addition, already_used_filenames, abs_image_paths,
                   hashes_to_images) -> str:
    thumbnail = full_image.copy()
    size = (width, int(thumbnail.size[1] * width/thumbnail.size[0]))
    thumbnail.thumbnail(size, Image.ANTIALIAS)

    offset_x = max((size[0] - thumbnail.size[0]) / 2, 0)
    offset_y = max((size[1] - thumbnail.size[1]) / 2, 0)
    offset_tuple = (int(offset_x), int(offset_y))

    final_thumb_rgba = Image.new(mode='RGBA', size=size, color=bg_color+(255,))
    final_thumb_rgba.paste(thumbnail, offset_tuple, thumbnail.convert('RGBA'))

    final_thumb = Image.new(mode='RGB', size=size, color=bg_color)
    final_thumb.paste(final_thumb_rgba, offset_tuple)

    base_file_name = make_unused_name(base_file_name, file_name_addition, already_used_filenames, hashes_to_images,
                                      hash_image(final_thumb), ".jpeg")
    final_thumb.save(os.path.join(abs_image_paths, base_file_name), 'JPEG',
                     quality=quality, optimize=True, progressive=progressive)

    return base_file_name


# a constant:

CSS_TO_MAKE_CODE_BOXES_WRAP = """
        .gist pre {
             white-space: pre-wrap !important;
             white-space: -moz-pre-wrap !important;
             white-space: -pre-wrap !important;
             white-space: -o-pre-wrap !important;
             word-wrap: break-word !important;
        }
        .gist code {
             white-space: pre-wrap !important;
             white-space: -moz-pre-wrap !important;
             white-space: -pre-wrap !important;
             white-space: -o-pre-wrap !important;
             word-wrap: break-word !important;
        }
"""


# The main function:

def main(md_origin, origin_type="file", website_root=None, destination=None, image_paths=None, css_paths=None,
         output_name="<name>.html", output_pdf=None, style_pdf="True", footer=None, math="True",
         formulas_supporting_darkreader=False, extra_css=None,
         core_converter: typing.Union[str, typing.Callable] = markdown_to_html_via_github_api,
         compress_images=False, enable_image_downloading=True, box_width=None, toc=False, dont_make_images_links=False,
         soft_wrap_in_code_boxes=False, suppress_online_fallbacks=False, validate_html=False, emoji_support=1,
         enable_css_saving =True):
    # check emoji_support parameter:
    if emoji_support not in (0, 1, 2):
        raise Exception("--emoji-support must be one of 0, 1 and 2.")
    # set all to defaults:
    style_pdf = str2bool(style_pdf)
    math = str2bool(math)
    compression_information = compress_images_input_to_dict(compress_images)
    if output_pdf == "":
        output_pdf = "<name>.pdf"
    if website_root == "":
        website_root = "."
    if website_root is None:
        website_root = ""
    if destination is None:
        destination = ""
    if not image_paths:
        if image_paths == "":
            enable_image_downloading = False
        image_paths = destination + (os.sep if destination else "") + "images"
    if not css_paths:
        if css_paths == "":
            enable_css_saving = False
        css_paths = "github-markdown-css"

    # set all to paths instead of paths relative to website_root:
    abs_website_root = ("/" if not website_root.startswith(".") else "") + website_root
    abs_destination = website_root + (os.sep if website_root else "") + destination
    abs_image_paths = website_root + (os.sep if website_root else "") + image_paths
    abs_css_paths = website_root + (os.sep if website_root else "") + css_paths

    # make sure all paths exist:
    paths_to_create = [abs_website_root, abs_destination, abs_image_paths, abs_css_paths if enable_css_saving else None]
    for path in paths_to_create:
        if path:
            os.makedirs(path, exist_ok=True)

    # get the markdown file's content:
    if origin_type == "file":
        with open(md_origin, "r") as f:
            md_content = f.read()
    elif origin_type == "web":
        md_content = requests.get(md_origin).text
    elif origin_type == "repo":
        md_content = requests.get("https://raw.githubusercontent.com/" + md_origin).text
    elif origin_type == "string":
        md_content = md_origin
    else:
        raise Exception("origin_type must be either file, web, repo or string.")

    if DEBUG:
        print("\n------------\nOriginal content:\n------------\n\n", md_content)

    # replace formulas with random sequences and get a dict to map them back:
    support_custom_emojis = (emoji_support >= 2)
    md_content, formula_mapper, special_chars_in_code_blocks, headings, emoji_replacements = (
        find_and_replace_formulas_in_markdown(md_content, math, support_custom_emojis))
    if DEBUG:
        print("emoji replacements:", emoji_replacements)

    # fail if we need to convert formulas, don't have the necessary dependencies and are suppressing online fallbacks:
    if suppress_online_fallbacks and formula_mapper and raw_formula2svg_online == raw_formula2svg:
        raise Exception("You are trying to convert a document with formulas in it, but you don't have the necessary\n"
                        + "dependencies installed and you have disabled the use of online fallbacks.")

    if DEBUG:
        print("\n------------\nOriginal Content (Formulas replaced):\n------------\n\n", md_content)
        print("\n------------\nFormula Map:\n------------\n\n", formula_mapper)
        print("\n------------\nSpecial Char Map:\n------------\n\n", special_chars_in_code_blocks)

    # render toc if that option is enabled:
    if toc:
        md_content = render_toc(md_content, headings)

    if DEBUG:
        print("\n------------\nHeadings in file:\n------------\n\n", headings)
        print("\n------------\nOriginal Content (TOCs rendered):\n------------\n\n", md_content)

    # request markdown-to-html-conversion from our preferred method:

    if core_converter in ("OFFLINE", "OFFLINE+"):
        from . import core_converter as cc
        if core_converter == "OFFLINE":
            cc.INTERNAL_USE = False
        else:
            cc.INTERNAL_USE = True
        html_content = cc.markdown(md_content)
    elif type(core_converter) is str:  # execute the command:
        # find out how to run the command:
        if sys.platform.startswith('win'):
            how_to_run_this = "cmd.exe"
        elif shutil.which("bash") is not None:
            how_to_run_this = "bash"
        else:
            raise Exception("You tried to use --core-converter (-o) with a custom command, but you are neither on"
                            "Windows (cmd.exe), nor does your platform support bash.")

        # escape the ms content in the right way:
        if how_to_run_this == "cmd.exe":
            md_content_shellescaped = windows_shellescape.escape_argument(md_content)
        elif how_to_run_this == "bash":
            md_content_shellescaped = shellescape.quote(md_content)
        else:
            raise

        # finally convert:
        out = subprocess.Popen(
            (
                core_converter.replace("{md}", md_content_shellescaped)
                if how_to_run_this == "cmd.exe"
                else [shutil.which("bash"), "-c", core_converter.replace("{md}", md_content_shellescaped)]
            ),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            shell=(how_to_run_this == "cmd.exe"),
        )
        stdout, stderr = out.communicate()
        if out.returncode != 0:
            # Create a simplified version of the md content to put into the error message:
            md_content_split_into_lines = md_content.split("\n")
            if len(md_content_split_into_lines) == 1 and len(md_content_split_into_lines[0]) <= 40:
                md_content_simplified = md_content_split_into_lines[0]
            elif len(md_content_split_into_lines) > 1 and len(md_content_split_into_lines[0]) <= 37:
                md_content_simplified = md_content_split_into_lines[0] + "..."
            elif len(md_content_split_into_lines) > 1 and len(md_content_split_into_lines[0]) > 37:
                md_content_simplified = md_content_split_into_lines[0][:36] + "..."
            else:
                raise
            # escape the simplified ms content in the right way:
            if how_to_run_this == "cmd.exe":
                md_content_simplified_shellescaped = windows_shellescape.escape_argument(md_content_simplified)
            elif how_to_run_this == "bash":
                md_content_simplified_shellescaped = shellescape.quote(md_content_simplified)
            else:
                raise
            print("md_content_simplified_shellescaped:", md_content_simplified_shellescaped)
            print("end")
            # raise exception:
            raise Exception("An exception with the core converter occurred:\n\n"
                            + (("STDERR:\n" + stderr.decode(encoding=sys.stdout.encoding) + "\n\n") if stderr else "")
                            + (("STDOUT:\n" + stdout.decode(encoding=sys.stdout.encoding) + "\n\n") if stdout else "")
                            + "with your command (displayed slightly shortened here):\n\n"
                            + core_converter.replace("{md}", md_content_simplified_shellescaped))
        else:
            html_content = stdout.decode(encoding=sys.stdout.encoding)
    else:
        # call the core converter as a function in case it is one:
        try:
            html_content = core_converter(md_content)
        except Exception as e:
            # raise exception:
            e.args = ("An exception with the core converter occurred:\n\n" + e.args[0],) + e.args[1:]
            raise e
            # raise type(e)("An exception with the core converter occurred:\n\n" + str(e))

    if DEBUG:
        print("\n------------\nHtml content:\n------------\n\n", html_content)

    # remove links around images if requested:
    if dont_make_images_links:
        html_bs4 = BeautifulSoup(html_content, "html.parser")
        for img_bs4 in html_bs4.find_all("img"):
            if img_bs4.parent.name == "a":
                if img_bs4.parent["href"] == img_bs4["src"]:
                    img_bs4.parent.unwrap()
        html_content = html_bs4.__str__()

    # re-insert formulas in html, this time as proper svg images:
    html_content = find_and_render_formulas_in_html(html_content, formula_mapper, special_chars_in_code_blocks,
                                                    emoji_replacements, emoji_support)

    if DEBUG:
        print("\n------------\nHtml content (with properly rendered formulas):\n------------\n\n", html_content)

    # maybe create a footer:
    if footer:
        footer = '<div class="gist-meta">\n' + footer + '</div>'
    else:
        footer = ""

    # ensure we have the css and the code navigation banner where we want it to be (anyone knows what this is for?):
    with open_local("github-css.min.css", "r") as from_f:
        github_min_css = from_f.read()
        if core_converter in ("OFFLINE+", "OFFLINE"):
            # add syntax highlighting css if we use OFFLINE or OFFLINE+ for conversion:
            from pygments.formatters import html as pygments_html
            github_min_css += pygments_html.HtmlFormatter().get_style_defs('.highlight') \
                .replace("\n", "").replace(";", " !important;").replace(" }", " !important }")
        if soft_wrap_in_code_boxes:
            # add css to make code boxes soft wrap:
            github_min_css += CSS_TO_MAKE_CODE_BOXES_WRAP.replace("\n", "").replace("    ", "").replace(": ", ":")
    if enable_css_saving:
        with open(os.path.join(abs_css_paths, "github-css.css"), "w") as to_f:
            to_f.write(github_min_css)
        with open_local("code-navigation-banner-illo.svg", "r") as from_f:
            with open(os.path.join(abs_css_paths, "code-navigation-banner-illo.svg"), "w") as to_f:
                to_f.write(from_f.read())

    # fill everything into our template, to link the html to the .css-file etc.:
    with open_local("prototype.html", "r") as f:
        # get an id for the page we create:
        possible_id_for_essay = (
            (output_name.split("/")[-1].split(os.sep)[-1].split(".")[0] if output_name not in ("print", "<name>.html")
             else (md_origin.split("/")[-1].split(os.sep)[-1].rsplit(".")[0] if origin_type != "string"
                   else (extra_css.split("/")[-1].split(os.sep)[-1].split(".")[0] if extra_css else "")))
        )
        # convert markdown to html:
        html_rendered = f.read().format(
            article=html_content,
            css_paths=("/" if website_root != "." else "") + css_paths.replace(os.sep, "/"),
            footer=footer,
            width_css=(('<style> .gist-file { max-width: ' + box_width + '; margin: 0 auto; } </style>\n')
                       if box_width else ""),
            extra_css=((open(extra_css, "r").read() if extra_css else "")
                       + (("<!-- ~~~~github-flavored css start~~~~ --><style>" + github_min_css
                           + "</style> <!-- ~~~~github-flavored css end~~~~ -->") if not enable_css_saving else "")),
            id='id="article-' + (possible_id_for_essay if possible_id_for_essay else "") + '"'
        )

    if not enable_css_saving:  # <- do not link to css if we don't want to save it:
        html_rendered = "\n".join(html_rendered.split("\n")[2:])

    if DEBUG:
        print("\n------------\nHtml rendered:\n------------\n\n", html_rendered)

    # find the images referenced within the file:
    # images = [
    #     str(image, encoding="UTF-8") for image in
    #     re.compile(rb'<img [^>]*src="([^"]+)').findall(bytes(html_rendered, encoding="UTF-8"))
    # ]

    # ensure we have all the images in the images path:
    if enable_image_downloading:
        hashes_to_images = dict()
        saved_image_names = set(  # <-- defines which images we already have within our image directory
            image_name for image_name in os.listdir(abs_image_paths)
            if os.path.isfile(os.path.join(abs_image_paths, image_name))
        )
        html_soup = BeautifulSoup(html_rendered, 'html.parser')
        find_fitting_hash_function(len(saved_image_names) + len(html_soup.find_all("img")))
        for image_name in saved_image_names:
            hashes_to_images[hash_image(
                Image.open(os.path.join(abs_image_paths, image_name))
                if not image_name.endswith(".svg")
                else open(os.path.join(abs_image_paths, image_name), "rb").read()
            )] = image_name
        if DEBUG:
            print("already existent images:", saved_image_names)

        for img_soup_representation in html_soup.find_all("img"):
            # ^Iterate over all images referenced in the markdown file
            image_src = original_markdown_image_src = img_soup_representation.get("src")
            if image_src == "":
                continue  # <-- In case some images with no source where injected for some reason
            if img_soup_representation.has_attr("data-canonical-src"):
                # work around for GitHub's image caching, which results in absurdly long image names.
                save_image_as = img_soup_representation.get("data-canonical-src")
            else:
                save_image_as = image_src
            if DEBUG:
                print("new image_src:", save_image_as)
            save_image_as = save_image_as.split("?")[0]  # <-- remove the extra url parts
            save_image_as = re.split("[/\\\]", save_image_as)[-1]  # <--  take only the last element of the path
            save_image_as = save_image_as.rsplit(".", 1)[0]  # <-- remove the extension
            save_image_as = re.sub(r'(?u)[^-\w.]', '', save_image_as)  # <-- remove disallowed characters
            if DEBUG:
                print("-> original_save_image_s:", save_image_as)
            if image_src.startswith("./"):
                image_src = image_src[2:]

            # actually get the image:

            load_from_web = False
            if image_src.startswith("https://") or image_src.startswith("http://"):
                # it is clearly an absolute url:
                load_from_web = True
            else:
                if origin_type == "string":
                    # This is a security risk since web content might get one to embed local images from one's disk
                    # into one's website when automatically cloning .md-files found online.
                    input("""press enter if you are sure you trust that string. Remove this line if this is always
    the case when inputting strings.""")

                if origin_type in ("repo", "web"):
                    # create website domain name and specific path from md_origin depending on whether we pull from
                    # a repo or the web:
                    if origin_type == "repo":
                        user_name, repo_name, branch_name, *path = md_origin.split("/")
                        url_root = (
                                "https://github.com/" + user_name
                                + "/" + repo_name
                                + "/raw/" + branch_name
                        )
                        url_full = url_root + "/" + "/".join(path[:-1]) + "/"
                    else:  # origin_type == "web":
                        url_root = "/".join(md_origin.split("/")[:3])
                        url_full = md_origin.rsplit("/", 1)[0] + "/"
                    # Create full web image path depending on weather we have an absolute relative link or just a
                    # regular relative link:
                    if image_src.startswith("/"):
                        image_src = url_root + image_src
                    else:
                        image_src = url_full + image_src
                    load_from_web = True

                elif origin_type in ("file", "string"):
                    # get an absolute path to the image in case the image path is relative to the file location:
                    if not os.path.isabs(image_src):
                        # get the current directory (for relative file paths) depending on the origin_type
                        location = os.getcwd()
                        if origin_type == "file" and os.sep in md_origin:
                            location = md_origin.rsplit(os.sep, 1)[0]
                            if not os.path.abspath(location):
                                location = os.path.join(os.getcwd(), location)
                        image_src = os.path.join(location, image_src.replace("/", os.sep))
                    load_from_web = False

            # load with a method appropriate for the type of source
            if load_from_web:
                try:
                    img_object = Image.open(BytesIO(requests.get(image_src).content))
                except (OSError, PIL.UnidentifiedImageError):
                    img_object = requests.get(image_src).content
            else:
                try:
                    img_object = Image.open(image_src)
                except (OSError, PIL.UnidentifiedImageError):
                    img_object = open(image_src, "rb").read()

            # Utility to create a path from an image name:
            def image_name_to_image_src(img_name):
                return ("/" if website_root != "." else "") + image_paths + "/" + img_name

            # save the image:
            try:  # determine extension:
                extension = "." + img_object.format.lower()
            except AttributeError:
                extension = ".svg"
            # ensure we use no image name twice & finally save the image:
            save_image_as = make_unused_name(save_image_as + extension, "", saved_image_names, hashes_to_images,
                                             hash_image(img_object))  # <-- file name to save as
            if DEBUG:
                print("-> save_image_as:", save_image_as)
                print("")
            cached_image_path = os.path.join(abs_image_paths, save_image_as)  # <-- path where we save it
            location_of_full_sized_image = image_name_to_image_src(save_image_as)  # <-how we call that path in the html
            if extension != ".svg":
                # if extension == ".gif":
                #     print(cached_image_path)
                img_object.save(cached_image_path, save_all=(extension == ".gif"))
            else:
                with open(cached_image_path, "wb") as img_out_file:
                    img_out_file.write(img_object)

            # Check if hashing worked correctly:
            if DEBUG_HASHES:
                import time
                t = time.time()
                if extension != ".svg":
                    hash1 = hash_image(Image.open(cached_image_path), return_unhashed=True)
                else:
                    hash1 = hash_image(open(cached_image_path, "rb").read(), return_unhashed=True)
                hash2 = hash_image(img_object, return_unhashed=True)
                if hash1 != hash2:
                    warnings.warn(
                        "image " + cached_image_path + " hashed incorrectly (not dramatic, but you cans till raise an\
                        issue for this)."
                        + (("hash difference:\n" + "".join(difflib.ndiff(hash1, hash2))) if imported_difflib else "")
                        + "\n"
                    )
                print("time to compare hashes:", time.time() - t)

            # Open the final image and do compression, if it was specified to do so:
            height = None
            if compression_information and extension not in (".svg", ".gif"):
                full_image = Image.open(cached_image_path)
                # Determine the images' width if any is specified:
                width = (
                    int(img_soup_representation["width"].strip().replace("px", ""))
                    if img_soup_representation.has_attr("width") and img_soup_representation["width"].endswith("px")
                    else None
                )
                height = (
                    int(img_soup_representation["height"].strip().replace("px", ""))
                    if img_soup_representation.has_attr("height") and img_soup_representation["height"].endswith("px")
                    else None
                )
                if img_soup_representation.has_attr("is_emoji") and img_soup_representation["is_emoji"] == "true":
                    height = 128
                    width = 128
                if height and not width:
                    width = math_module.ceil(height * full_image.width / full_image.height)
                # If no size is specified and srcset is set, generate a set of resolutions:
                if compression_information["srcset"] and not width:
                    srcset = compression_information["srcset"]
                    srcset.sort()
                    srcset = [x for x in srcset if x < full_image.width]
                    srcset.append(full_image.width)
                    # Create all the compressed images and a srcset-attribute for them:
                    srcset_attribute = str()
                    for size in srcset:
                        srcset_attribute += image_name_to_image_src(compress_image(
                            full_image,
                            width=size,
                            bg_color=compression_information["bg-color"],
                            quality=compression_information["quality"],
                            progressive=compression_information["progressive"],
                            base_file_name=save_image_as,
                            file_name_addition="." + str(size) + "px",
                            already_used_filenames=saved_image_names,
                            abs_image_paths=abs_image_paths,
                            hashes_to_images=hashes_to_images,
                        )) + " " + str(size) + "w, "
                    img_soup_representation["srcset"] = srcset_attribute  # .rsplit(" ", 2)[0] + " 3000w"
                # If width is specified, or we just don't plan to use srcset, create only one image:
                else:
                    if not width:
                        width = full_image.width
                    save_image_as = compress_image(
                        full_image,
                        width=width,
                        bg_color=compression_information["bg-color"],
                        quality=compression_information["quality"],
                        progressive=compression_information["progressive"],
                        base_file_name=save_image_as,
                        file_name_addition=".min",
                        already_used_filenames=saved_image_names,
                        abs_image_paths=abs_image_paths,
                        hashes_to_images=hashes_to_images,
                    )
            # Calculate the images max height, and add it as an attribute if it can be determined:
            if extension != ".svg":
                if not height:
                    height = img_object.height
                max_height_css_information = "max-height: " + str(height) + "px;"
                if img_soup_representation.has_attr("style"):
                    if ";max-height:" not in ";" + img_soup_representation["style"].replace(" ", ""):
                        img_soup_representation["style"] = (
                            img_soup_representation["style"].strip().rstrip(";") + "; " + max_height_css_information
                        )
                else:
                    img_soup_representation["style"] = max_height_css_information
            # Change src/href tags to ensure we reference the right image:
            new_image_src = image_name_to_image_src(save_image_as)
            img_soup_representation["src"] = new_image_src
            img_soup_representation["data-canonical-src"] = location_of_full_sized_image
            if img_soup_representation.parent.name == "a"\
                    and img_soup_representation.parent["href"] == original_markdown_image_src:
                img_soup_representation.parent["href"] = location_of_full_sized_image

        html_rendered = html_soup.__str__()

        if DEBUG:
            print("dict of image hashes:", hashes_to_images)
    else:
        # if image caching is disabled, change image's `src` to their `data-canonical-src` to revert GitHub's caching.
        html_soup = BeautifulSoup(html_rendered, 'html.parser')
        for img_soup_representation in html_soup.find_all("img"):
            if img_soup_representation.has_attr("data-canonical-src"):
                if (img_soup_representation.parent.has_attr("href")
                        and img_soup_representation.parent["href"] == img_soup_representation["src"]):
                    img_soup_representation.parent["href"] = img_soup_representation["data-canonical-src"]
                img_soup_representation["src"] = img_soup_representation["data-canonical-src"]
        html_rendered = html_soup.__str__()

    if DEBUG:
        print("\n------------\nHtml with image links:\n------------\n\n", html_rendered)

    # Add "user-content-" to anchors and internal links.

    contains_file_internal_links = False
    html_soup = BeautifulSoup(html_rendered, 'html.parser')
    for element_soup_representation in html_soup.select("[id]"):
        id_name = element_soup_representation.get("id")
        if id_name and not id_name.startswith("user-content-"):
            element_soup_representation["id"] = "user-content-" + id_name
    for link_soup_representation in html_soup.find_all("a"):
        # "user-content-"-ify the href-attributes
        link_location = link_soup_representation.get("href")
        if link_location and link_location.startswith("#") and not link_location.startswith("#user-content-"):
            # ^ GitHub technically doesn't recognize the last point, but we derive from GitHub's behavior here.
            link_location = "#user-content-" + link_location[1:]
            if not (link_soup_representation.has_attr("class") and link_soup_representation["class"] == ["anchor"]):
                contains_file_internal_links = True
        link_soup_representation["href"] = link_location
        # "user-content-"-ify the id-attribute; note that this has precedence over the name attributes.
        link_id = link_soup_representation.get("id")
        if link_id:
            link_soup_representation["name"] = link_id
            del link_id
        # "user-content-"-ify the name-attributes
        link_name = link_soup_representation.get("name")
        if link_name and not link_name.startswith("user-content-"):
            link_soup_representation["name"] = "user-content-" + link_name
    html_rendered = html_soup.__str__()

    # add correct id to all headings:
    html_soup = BeautifulSoup(html_rendered, 'html.parser')
    for h in ("h1", "h2", "h3", "h4", "h5"):
        for header_soup_representation in html_soup.find_all(h):
            if header_soup_representation.find('a'):
                header_soup_representation['id'] = header_soup_representation.a['id']
            # ToDo: Implement these nice anchor svg icons GitHub displays next to every heading
    #       link_within_header = header_soup_representation.a
    #       link_within_header.append(BeautifulSoup(GITHUB_LINK_ANCHOR, 'html.parser').find("svg"))
    html_rendered = html_soup.__str__()

    if DEBUG:
        print("\n------------\nHtml with fixed internal links:\n------------\n\n", html_rendered)

    # check whether html is valid if we have the necessary dependency installed.
    if imported_tidylib and validate_html:
        _, errors = tidylib.tidy_document(html_rendered, options={'numeric-entities': 1})
        if errors:
            warnings.warn("The generated HTML is not entirely valid. This should not be an issue, but you ca still\n"
                          + "raise an issue on GitHub for it"
                          + "(https://github.com/phseiff/github-flavored-markdown-to-html/issues).\n"
                          + str(errors))

    # save html where we want it to be:
    file_name_origin = md_origin.split("/")[-1].split(os.sep)[-1].rsplit(".", 1)[0]
    if "<name>" in output_name and origin_type == "string":
        raise Exception("You can't use <name> in your output name if you enter the input with the '-t string option'.")
    else:
        output_name = output_name.replace("<name>", file_name_origin)
    if output_name != "print":
        with open(os.path.join(abs_destination, output_name), "w+") as f:
            f.write(html_rendered)

    # save it as pdf if we want to do so:
    if output_pdf:
        try:
            import pdfkit
        except ImportError:
            raise Exception("""\
Unfortunately, you need to have pdfkit installed to save as pdf. Find out how to install it here:
https://pypi.org/project/pdfkit/.""")
        # ensure the image srcs are absolute file paths:
        html_soup_representation = BeautifulSoup(html_rendered, "html.parser")
        for filter, attr in (((lambda tag: tag.has_attr("src")), "src"), ("link", "href")):
            for tag_with_link in html_soup_representation.find_all(filter):
                link = tag_with_link[attr]
                if "://" in link:
                    pass
                else:
                    directory_to_link_to = abs_website_root if link.startswith("/") else abs_destination
                    if directory_to_link_to == "./":
                        directory_to_link_to = ""
                    cwd = str(os.getcwd())
                    abs_path = urllib.parse.quote(os.path.join(cwd, directory_to_link_to.strip("/"), link.strip("/")))
                    if link.startswith("/") and not enable_image_downloading and attr == "src":
                        # link is already absolute
                        abs_path = link
                    tag_with_link[attr] = "file://" + abs_path
        html_rendered = html_soup_representation.__str__()

        # Remove links that link to something that clearly lies on the disk or is a relative link, since these won't
        #  work in a pdf-file anyways or cannot be relied on.
        html_soup_representation = BeautifulSoup(html_rendered, "html.parser")
        for link in html_soup_representation.find_all("a"):
            href = link["href"]
            if (
                    (href.startswith("/") and not href.startswith("//"))
                    or href.startswith("file://")
                    or (not href.startswith("/") and not href.startswith("#") and "://" not in href)
            ):
                for child in link:
                    link.parent.append(child)
                link.decompose()
        html_rendered = html_soup_representation.__str__()

        # remove the css if we want to save it without css:
        if not style_pdf:
            if enable_css_saving:
                html_rendered = "\n".join(html_rendered.split("\n")[2:])
            else:
                html_rendered = (html_rendered.rsplit("~~~~github-flavored css start~~~~", 1)[0]
                                 + html_rendered.rsplit("~~~~github-flavored css end~~~~", 1)[1])

        # use <name>-variable in the name
        if "<name>" in output_pdf and origin_type == "string":
            raise Exception("You can't use <name> in your pdf name if you enter the input with the '-t string option'.")
        else:
            output_pdf = output_pdf.replace("<name>", file_name_origin)

        # check which version of wkhtmltopdf we have installed
        version_str = str(subprocess.check_output(["wkhtmltopdf", "-V"]), encoding="UTF-8").strip()
        if version_str.startswith("wkhtmltopdf "):
            version_str = version_str.split(" ", 1)[1]
        version_number = [int(i) for i in version_str.split()[0].split(".")]
        given_version_as_number = 10**12 * version_number[0] + 10**6 * version_number[1] + version_number[2]
        ideal_version_as_number = 10**12 * 0 + 10**6 * 12 + 6
        options = {'quiet': ''}
        if given_version_as_number >= ideal_version_as_number:
            options['enable-local-file-access'] = ''
            # ^ see https://github.com/wkhtmltopdf/wkhtmltopdf/issues/2660#issuecomment-663063752
        if contains_file_internal_links and "(with patched qt)" not in version_str:
            warning_text = ("Your file contains internal links, but your version of wkhtmltopdf (version \""
                            + version_str + "\") does not support using these,\n\tsince you need a version with the qt"
                            + " patches to use internal links within your file.\n\tYou can download these from"
                            + " https://wkhtmltopdf.org/downloads.html")
            warnings.warn(warning_text, Warning)

        # Make code boxes soft wrap rather than use horizontal scrollbars in the generated pdfs, since pdf doesn't
        #  support using scrollbars in their intended way:
        html_rendered += "\n<style>\n" + CSS_TO_MAKE_CODE_BOXES_WRAP + "\n</style>"

        # Finally convert it:
        # (this saving and then converting ensures we don't convert links like https:foo to
        # absolute_path_to_file_location/https://foo)
        with open(os.path.join(abs_destination, output_pdf + ".html"), "w+") as f:
            f.write(html_rendered)
        try:
            pdfkit.from_file(
                os.path.join(abs_destination, output_pdf + ".html"),
                os.path.join(destination, output_pdf),
                options=dict() if DEBUG else options,
            )
        except OSError:
            raise OSError(
"""\
Saving the pdf faile failed because the saving location was unwriteable.
This can be caused by a read-only file system or many other reasons, but the most probable reason is that you had an
older version of the pdf opened in a pdf viewer whilst gh-md-to-html was trying to write the new version to its
location, and that the pdf viewer you used locks pdf files whilst it has them opened. This is standard behavior with
Adobe Reader, for example.
For pdf viewers that can handle live-upading the pdf, see here, for example:
https://superuser.com/questions/599442/pdf-viewer-that-handles-live-updating-of-pdf-doesnt-lock-the-file\
"""
            )
        os.remove(os.path.join(abs_destination, output_pdf + ".html"))

    # return the result
    return html_rendered


# Setting the doc string for the main function:


main.__doc__ = """\
Use this function like the command line interface:
--------------------------------------------------
""" + HELP

# Some doctests:


def _test():
    import doctest
    doctest.testmod()


# Function to parse command line arguments and pass them to the main function:

def cmd_to_main():
    # argparse:
    parser = argparse.ArgumentParser(
        description=('Convert markdown to HTML using the GitHub API and some additional tweaks with python.\n\n'
                     + 'See https://github.com/phseiff/github-flavored-markdown-to-html#documentation for a more'
                     + 'detailed help text.'),
    )


    class FuseInputString(argparse.Action):
        """Ugly workaround because argparse seems to not take input with spaces just as it is (as long as it is
        properly quoted in the shell and passed to sys.argv as a whole), but instead fuses all elements of sys.argv
        and parses them afterwords 🙄"""

        def __call__(self, p, namespace, values, option_string=""):
            setattr(namespace, self.dest, " ".join(values))


    parser.add_argument('md_origin', metavar='MD-origin',
                        help='Where to find the markdown file that should be converted to html')

    parser.add_argument('-t', '--origin-type', choices=["file", "repo", "web", "string"], default="file",
                        help=textwrap.dedent("""\
    In what way the MD-origin-argument describes the origin of the markdown file to use. Defaults to file. The options
    mean:
    * file: takes a relative or absolute path to a file
    * repo: takes a path to a markdown-file in a github repository, such as
    <user_name>/<repo_name>/<branch-name>/<path_to_markdown>.md
    * web: takes an url to a markdown file
    * string: takes a string containing the files content"""))

    parser.add_argument('-w', '--website-root', nargs="?", help="""
    Only relevant if you are creating the html for a static website which you manage using git or something similar.
    --website-root is the directory from which you serve your website (which is needed to correctly generate the links
    within the generated html, such as the link pointing to the css, since they are all root-relative),
    and can be a relative as well as an absolute path. Defaults to the directory you called this script from.
    If you intent to view the html file on your laptop instead of hosting it on a static site, website-root should be
    left empty and destination not set. The reason the generated html files use root-relative links to embed images is
    that on many static websites, https://foo/bar/index.html can be accessed via https://foo/bar, in which case relative
    (non-root-relative) links in index.html will be interpreted as relative to foo instead of bar, which can cause
    images not to load.
    """)
    # ToDo: Allow the use of any --website-root even if one wants to view the files locally, as long as destination is
    #  a dot.

    parser.add_argument('-d', '--destination', help="""
    Where to store the generated html. This path is relative to --website-root. Defaults to "".""")

    parser.add_argument('-i', '--image-paths', nargs="?", const="", help="""
    Where to store the images needed or generated for the html. This path is relative to website-root. Defaults to the
    "images"-folder within the destination folder.
    Leave this option empty to completely disable image caching/downloading and leave all image links unmodified.""")

    parser.add_argument('-c', '--css-paths', nargs="?", help="""
    Where to store the css needed for the html (as a path relative to the website root). Defaults to the
    "<WEBSITE_ROOT>/github-markdown-css"-folder.
    Leave this option empty to store the CSS inline instead of in an external file.""")

    parser.add_argument('-n', '--output-name', default="<name>.html", help="""
    What the generated html file should be called like. Use <name> within the value to refer to the name of the markdown
    file that is being converted (if you don't use "-t string"). You can use '-n print' to print the file (if using
    the command line interface) or return it (if using the python module), both without saving it. Default is 
    '<name>.html'.""")

    parser.add_argument('-p', '--output-pdf', nargs="?", help="""
    If set, the file will also be saved as a pdf file in the same directory as the html file, using pdfkit, a python
    library which will also need to be installed for this to work. You may use the <name> variable in this value like
    you did in --output-name. If you use `-p` without any input to it, it will use `<name>.pdf` as a sensible default
    for you,
    Do not use this with the -x option if the input of the -x option is not trusted; execution of malicious code might
    be the consequence otherwise!!""")

    parser.add_argument('-m', '--math', default="true", help="""
    If set to True, which is the default, LaTeX-formulas using $formula$-notation will be rendered.""")

    parser.add_argument('-f', '--footer', help="""
    An optional piece of html which will be included as a footer where the 'hosted with <3 by github'-footer in a gist
    usually is.
    Defaults to None, meaning that the section usually containing said footer will be omitted altogether.
    """)

    if "-r" in sys.argv or "--formulas-supporting-darkreader" in sys.argv:
        parser.add_argument('-r', '--formulas-supporting-darkreader', default="false", type=bool, help="""
        THIS OPTION IS DEPRECATED. It used to hackishly ensure that darkreader (the js module as well as the browser
        extension) correctly shift the colors of embedded formulas according to darkreader's colorscheme (usually,
        dark). This is not necessary anymore because this is ALWAYS supported now, and in a clean way without any dirty
        hack. The help text is disabled, but remains in the source code for future reference. Supplying the parameter
        is still supported for reasons of backwards compatibility, but it does not do anything anymore.""")

    parser.add_argument('-x', '--extra-css', help="""
    A path to a file containing additional css to embed into the final html, as an absolute path or relative to the
    working directory. This file should contain css between two <style>-tags, so it is actually a html file, and can
    contain javascript as well. It's worth mentioning and might be useful for your css/js that every element of the
    generated html is a child element of an element with id xxx, where xxx is "article-" plus the filename (without
    extension) of:
    * output-name, if output-name is not "print" and not the default value.
    * the input markdown file, if output-name is "print", and the input type is not string.
    * the file with the extra-css otherwise.
    If none of these cases applies, no id is given.""")

    parser.add_argument('-s', '--style-pdf', default="true", help="""
    If set to false, the generated pdf (only relevant if you use --output-pdf) will not be styled using github's css.
    """)

    parser.add_argument('-o', '--core-converter',
                        default=markdown_to_html_via_github_api, help="""
    The converter to use to convert the given markdown to html, before additional modifications such as formula support
    and image downloading are applied; this defaults to using GitHub's REST API and can be
    * on Unix/ any system with a cmd: a command containing the string "{md}", where "{md}" will be replaced with an
      escaped version of the markdown file's content, and which returns the finished html. Please note that commands for
      Unix-system won't work on Windows systems, and vice versa etc.
    * when using gh-md-to-html in python: A callable which converts markdown to html, or a string as described above.
    * OFFLINE as a value to indicate that gh-md-to-html should imitate the output of their builtin md-to-html-converter
      using mistune. This requires the optional dependencies for "offline_conversion" to be satisfied, by using
      `pip3 install gh-md-to-html[offline_conversion]` or `pip3 install mistune>=2.0.0rc1`.
    * OFFLINE+ behaves identical to OFFLINE, but it doesn't remove potentially harmful content like javascript and css
      like the GitHub REST API usually does. DO NOT USE THIS FEATURE unless you need a way to convert secure
      manually-checked markdown files without having all your inline js stripped away!
    """)

    parser.add_argument('-e', '--compress-images', help="""
    Reduces load time of the generated html by saving all images referenced by the given markdown file as jpeg. This
    argument takes a piece of json data containing the following information; if it is not used, no compression is done:
    * bg-color: the color to use as a background color when converting RGBA-images to jpeg (an RGB-format). Defaults to
      "white" and accepts almost any HTML5 color-value ("#FFFFFF", "#ffffff", "white" and "rgb(255, 255, 255)" would've
      all been valid values).
    * progressive: Save images as progressive jpegs. Default is False.
    * srcset: Save differently scaled versions of the image and provide them to the image in its srcset attribute.
      Defaults to False. Takes an array of different widths or True, which serves as a shortcut for
      "[500, 800, 1200, 1500, 1800, 2000]". 
    * quality: a value from 0 to 100 describing at which quality the images should be saved (this is done after they are
      scaled down, if they are scaled down at all). Defaults to 90.
    If a specific size is specified for a specific image in the html, the image is always converted to the right size.
    If this argument is left empty, no compression is done at all. If this argument is set to True, all default values
    are used. If it is set to json data and values are omitted, the defaults are also used. If a dict is passed instead
    of json data (when using the tool as a python module), the dict is used as the result of the json data.
    """)

    parser.add_argument('-a', '--toc', type=bool, default=False, help="""
    Enables the use of `[[_TOC_]]`, `{:toc}` and `[toc]` at the beginning of an otherwise empty line to create a
    table of content for the document. These syntax are supported by different markdown flavors, the most prominent
    probably being GitLab-flavored markdown (supports `[[_TOC_]]`), and since GitLab displays its READMEs quite similar
    to how GitHub does it, this option was added to improve support for GitLab-flavored markdown.
    """)

    parser.add_argument('--dont-make-images-links', type=bool, default=False, help="""
    By default, like it is on GitHub, every image is hyperlinked to its source, unless the image is explicitly
    hyperlinked to something else.
    Setting this option to True turns this behavior off, so images are only hyperlinked to things if it is explicitely
    done.
    """)

    parser.add_argument("--emoji-support", type=int, default=1, help="""
    Describes which level of emoji shortcode support to use. The available levels are:
    * 1: The default. Allows the use of emoji shortcodes, e.g. `:thumbs_up:` as a shorthand for `👍️`, comparable to what
      Discord, Telegram & Co. are doing.
    * 0: Disable emoji shortcodes.
    * 2: Enables emoji shortcodes, and additionally allows the use of custom emojis, by adding a link to an image in
      between two colons (e.g. `:image.png:` will add image.png downscaled to emoji size into the text). These custom
      emojis are properly affected by the --compress-images option, scaled to a pixel height of max. 128px, and
      displayed with the same height as the surrounding text.
    * Note: In cases where an emoji shortcode isn't valid, a warning is risen;
      in case you want this to raise an error instead, you can catch the warning and do so manually yourself.""")

    parser.add_argument('-b', '--box-width', help="""
    The text of the rendered file is always displayed in a box, like GitHub READMEs and issues are.
    By default, this box fills the entire screen (max-width: 100%%),
    but you can use this option to reduce its max width to be more readable when hosted stand-alone; the resulting box
    is always centered.
    --box-width accepts the same arguments the css max-width attribute accepts, e.g. 25cm or 800px.
    """)

    parser.add_argument('--soft-wrap-in-code-boxes', type=bool, default=False, help="""
    By default, GitHub-flavored markdown adds horizontal scrollbars to code blocks if they contain lines that are too
    long. Setting --soft-wrap-in-code-boxes to true turns this behavior off, and soft-wraps code boxes instead.
    Note that this is already the default behavior in generated pdf files, and that this will modify the generated CSS
    file.
    """)

    parser.add_argument('--suppress-online-fallbacks', type=bool, default=False, help="""
    gh-md-to-html uses online APIs as fallbacks for some things if the necessary dependencies are not installed, e.g. 
    LaTeX for formula rendering.
    Using this option suppresses these online fallbacks and raises an error instead; use this if the document you are
    working on is of sensible nature.""")

    # This hackish ensures the bullet points in the help text generated by argparse get formatted correctly.
    help_text = parser.format_help()
    help_text_lines = help_text.split("\n")
    line_number = -1
    while line_number < len(help_text_lines) - 1:
        line_number += 1
        if "* " in help_text_lines[line_number]:
            left, right = help_text_lines[line_number].split("* ", 1)
            if left != "                        ":
                help_text_lines.insert(line_number + 1, "                        * " + right)
                help_text_lines[line_number] = left
        if line_number < len(help_text_lines) - 1 and help_text_lines[line_number].startswith(
                "                        "):
            if (help_text_lines[line_number + 1].startswith("                        ")
                    and not help_text_lines[line_number + 1].startswith("                        * ")):
                text_next_line = help_text_lines[line_number + 1].split("                        ")[1].split(" ")
                while 80 - len(help_text_lines[line_number]) > len(text_next_line[0]):
                    text_this_line = help_text_lines[line_number].split(" ")
                    text_this_line.append(text_next_line.pop(0))
                    help_text_lines[line_number] = " ".join(text_this_line)
                    help_text_lines[line_number + 1] = "                        " + " ".join(text_next_line)
                    if not help_text_lines[line_number + 1].strip():
                        del help_text_lines[line_number + 1]
                    if (help_text_lines[line_number + 1].startswith("                        ")
                            and not help_text_lines[line_number + 1].startswith("                        * ")):
                        text_next_line = help_text_lines[line_number + 1].split(
                            "                        ")[1].split(" ")
                    else:
                        break
    help_text = "\n".join(help_text_lines)

    try:
        with open_local("help.txt", "w", encoding='utf-8') as help_file:
            help_file.write(help_text)
    except OSError:
        pass  # running an installation installed with sudo.

    # Print help text if requested.
    if "-h" in sys.argv or "--help" in sys.argv:
        print(help_text)
        sys.exit()

    # pass these inputs to the main-function, and raise an explanation should an error occur:
    try:
        result = main(**vars(parser.parse_args()))
        # print the result if we are in print-mode:
        if parser.parse_args().output_name == "print":
            sys.stdout.write(result)
    except FileNotFoundError:
        traceback.print_exc()
        print("\nAn Error occurred because a file required for the conversion could not be found.\n\
This is probably your input file, but it might also be an image from your disk referenced in your .md, or you might\n\
have deleted autogenerated files during the conversion process.")
        exit(1)
    except requests.exceptions.ConnectionError:
        traceback.print_exc()
        print("\nAn Error occurred because a web page could not be accessed. This is probably because you either have\n\
no internet, or you the page used to render the formulas or github is down, or because an image-link within your\n\
input markdown directs to a non-accessible page.")
        exit(1)


# Reacting appropriately if code is called from command line interface:

if __name__ == "__main__":
    cmd_to_main()
    sys.exit(0)
