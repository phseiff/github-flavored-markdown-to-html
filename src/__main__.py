"""Convert Markdown to html via python or with a command line interface."""

import textwrap
import requests
import string
import random
import re
import argparse
import sys
import os
import shellescape
from PIL import Image
import PIL
from io import BytesIO
from urllib.parse import quote
import traceback
import subprocess
import json
import webcolors
from ast import literal_eval as make_tuple
from bs4 import BeautifulSoup
import io
import hashlib
import math as math_module

MODULE_PATH = os.path.join(*os.path.split(__file__)[:-1])
DEBUG = False  # weather to print debug information
HASH_FUNCTION_TO_USE_ON_IMAGES = lambda x: hashlib.md5(x.encode() if type(x) is str else x)


def open_local(path, mode):
    return open(os.path.join(MODULE_PATH, path), mode)


HELP = open_local("help.txt", "r").read()


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


def find_and_replace_formulas_in_markdown(md: str, replace_formulas=True):
    """Takes markdown as a string and returns the markdown, but every formula is replaced with a random string, as well
    as a dict to translate these strings back to the formulas. This is done to evade the problem that special characters
    in formulas should not be escaped and that they should not be interpreted, e.g. as code etc.
    Non-ascii characters in multiline code blocks also get replaced with random strings, and the third return
    parameter is a dict mapping these replacements back to these non-ascii characters; otherwise, they would not be
    transmitted correctly over to the github REST api and ultimately be lost. Replacing them with html encodings is
    not possible either since GitHub's api uses <pre>-blocks for multiline code.
    If replace_formulas is set to false, formula replacement wil be omitted and only special characters in code blocks
    will be replaced."""
    md_lines = md.splitlines()
    formulas = dict()
    special_characters_in_code = dict()
    inside_multiline_code = False
    for l_num in range(len(md_lines)):
        line = md_lines[l_num]
        if line.strip().startswith("```"):
            inside_multiline_code = not inside_multiline_code
            continue
        if not inside_multiline_code:
            inside_inline_code = False
            formula_start = 0
            in_formula = False
            if replace_formulas:
                i = -1
                while i < len(line) - 1:
                    i += 1
                    if not inside_multiline_code:
                        if line[i] == "$" and is_not_escaped(line, i) and not inside_inline_code:
                            if not in_formula:
                                in_formula = True
                                formula_start = i + 1
                            else:
                                in_formula = False
                                formula_close = i
                                # store formula and start iterating over the line again:
                                formula = line[formula_start:formula_close]
                                replacement = get_fitting_replacement(formula, formulas, md, "f")
                                formulas[replacement] = formula
                                line = line[:formula_start - 1] + replacement + line[formula_close + 1:]
                                i = -1
                        elif line[i] == "`" and is_not_escaped(line, i) and not in_formula:
                            inside_inline_code = not inside_inline_code
                line = line.replace("\\$", "$")
            line = str(line.encode('ascii', 'xmlcharrefreplace'), encoding="utf-8")
        else:
            for character in set(line):
                if character not in string.printable:
                    replacement = get_fitting_replacement(character, special_characters_in_code, md, "c")
                    special_characters_in_code[replacement] = character
                    line = line.replace(character, replacement)
        md_lines[l_num] = line

    return "\n".join(md_lines), formulas, special_characters_in_code


def find_and_render_formulas_in_html(html_text: str, formulas: dict, special_characters_in_code: dict):
    """Takes some html (generated from markdown by the online github API) and a dictionary which maps a number of
    sequences to a number of formulas, and replaces each sequence with a LaTeX-rendering of the corresponding formula.
    The third parameter is a dictionary mapping replacements to special characters for use in code blocks.
    """

    # replace formulas:
    client = requests.session()
    svg_re_pattern = re.compile(r"""<path[^>]+id\s*=\s*['\"]([^'\"]+)['\"][^>]*>""")
    amount_of_svg_formulas = 0
    for sequence, formula in formulas.items():
        formula_rendered = client.get(
            url="https://latex.codecogs.com/svg.latex?" + quote(formula)
        ).text
        svg_path_ids = [path_id for path_id in svg_re_pattern.findall(formula_rendered)]
        for svg_path_id in svg_path_ids:
            new_svg_path_id = svg_path_id + "n" + str(amount_of_svg_formulas)
            formula_rendered = formula_rendered.replace("id='" + svg_path_id + "'", "id='" + new_svg_path_id + "'")
            formula_rendered = formula_rendered.replace("xlink:href='#" + svg_path_id + "'", "xlink:href='#"
                                                        + new_svg_path_id + "'")
        if DEBUG:
            print(" ---    FORMULA:", formula, " --- quoted:", quote(formula), " --- url:",
                  "https://latex.codecogs.com/svg.latex?" + quote(formula), " --- svg-paths:", svg_path_ids)
        formula_rendered = formula_rendered.split("<?xml version='1.0' encoding='UTF-8'?>", 1)[-1]
        formula_rendered = formula_rendered.replace('<svg', '<svg style="vertical-align: middle"')
        formula_rendered = formula_rendered.replace('<path', '<path class="formula"')
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
        requests.post("https://api.github.com/markdown/raw", headers=headers, data=markdown).content,
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


def hash_image(img):
    if type(img) in (str, bytes):
        return HASH_FUNCTION_TO_USE_ON_IMAGES(img)

    pixel_data = list()
    for pixel in list(img.getdata()):
        pixel_data += list(pixel)
    pixel_data_string = str(bytes(pixel_data), encoding="iso-8859-1")
    pixel_data_string += "||" + str(img.size) + "||" + (str(img.format.lower() if img.format else None))

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
    if hash_of_image in hashes_to_filenames:
        return hashes_to_filenames[hash_of_image]
    if not ending:
        ending = "." + base_file_name.rsplit(".", 1)[-1]
    base_file_name = base_file_name.rsplit(".", 1)[0] + ending
    while make_final_filename(base_file_name, file_name_addition) in already_used_filenames:
        base_file_name = make_final_filename(base_file_name, "_")
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

# The main function:


def main(md_origin, origin_type="file", website_root=None, destination=None, image_paths=None, css_paths=None,
         output_name="<name>.html", output_pdf=None, style_pdf="True", footer=None, math="True",
         formulas_supporting_darkreader=False, extra_css=None, core_converter=markdown_to_html_via_github_api,
         compress_images=False, enable_image_downloading=True):
    # set all to defaults:
    style_pdf = str2bool(style_pdf)
    math = str2bool(math)
    compression_information = compress_images_input_to_dict(compress_images)
    if website_root is None:
        website_root = ""
    if destination is None:
        destination = ""
    if image_paths is None:
        image_paths = destination + (os.sep if destination else "") + "images"
    if css_paths is None:
        css_paths = "github-markdown-css"
    if formulas_supporting_darkreader in ("false", False):
        darkreader_src = ""
        formulas_supporting_darkreader = False
    elif formulas_supporting_darkreader in ("true", True):
        darkreader_src = "*darkreader.js"
        formulas_supporting_darkreader = True
    else:
        darkreader_src = formulas_supporting_darkreader
        formulas_supporting_darkreader = True

    # set all to paths instead of paths relative to website_root:
    abs_website_root = ("/" if not website_root.startswith(".") else "") + website_root
    abs_destination = website_root + (os.sep if website_root else "") + destination
    abs_image_paths = website_root + (os.sep if website_root else "") + image_paths
    abs_css_paths = website_root + (os.sep if website_root else "") + css_paths

    # make sure all paths exist:
    for path in [abs_website_root, abs_destination, abs_image_paths, abs_css_paths]:
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
    md_content, formula_mapper, special_chars_in_code_blocks = find_and_replace_formulas_in_markdown(md_content, math)

    if DEBUG:
        print("\n------------\nOriginal Content (Formulas replaced):\n------------\n\n", md_content)
        print("\n------------\nFormula Map:\n------------\n\n", formula_mapper)

    # request markdown-to-html-conversion from our preferred method:

    if type(core_converter) is str:  # execute the command:
        out = subprocess.Popen(
            core_converter.format(md=shellescape.quote(md_content)),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            shell=True,
        )
        stdout, stderr = out.communicate()
        if stderr:
            raise Exception("An exception with the used command occurred\n" + traceback.print_exc())
        else:
            html_content = stdout
    else:  # call the function:
        html_content = core_converter(md_content)

    if DEBUG:
        print("\n------------\nHtml content:\n------------\n\n", html_content)

    # re-insert formulas in html, this time as proper svg images:
    html_content = find_and_render_formulas_in_html(html_content, formula_mapper, special_chars_in_code_blocks)

    if DEBUG:
        print("\n------------\nHtml content (with properly rendered formulas):\n------------\n\n", html_content)

    # maybe create a footer:
    if footer:
        footer = '<div class="gist-meta">\n' + footer + '</div>'
    else:
        footer = ""

    # fill everything into our template, to link the html to the .css-file etc.:
    with open_local("prototype.html", "r") as f:
        possible_id_for_essay = (
            (output_name.split("/")[-1].split(os.sep)[-1].split(".")[0] if output_name not in ("print", "<name>.html")
             else (md_origin.split("/")[-1].split(os.sep)[-1].rsplit(".")[0] if origin_type != "string"
                   else (extra_css.split("/")[-1].split(os.sep)[-1].split(".")[0] if extra_css else "")))
        )
        html_rendered = f.read().format(
            article=html_content,
            css_paths=("/" if website_root != "." else "") + css_paths.replace(os.sep, "/"),
            footer=footer,
            extra_css=open(extra_css, "r").read() if extra_css else "",
            id='id="article-' + (possible_id_for_essay if possible_id_for_essay else "") + '"'
        )

    if DEBUG:
        print("\n------------\nHtml rendered:\n------------\n\n", html_rendered)

    # ensure darkreader is supported if we have formulas:
    if formulas_supporting_darkreader and formula_mapper:
        with open_local("svg-color-changer.html", "r") as f:
            html_rendered += "\n\n" + f.read().replace("{script_name}", darkreader_src)

    if DEBUG:
        print("\n------------\nHtml rendered (with darkreader support):\n------------\n\n", html_rendered)

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
            save_image_as = re.split("[/\\\]", image_src)[-1]  # <--  take only the last element of the path
            save_image_as = save_image_as.rsplit(".", 1)[0]  # <-- remove the extension
            save_image_as = re.sub(r'(?u)[^-\w.]', '', save_image_as)  # <-- remove disallowed characters
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
            cached_image_path = os.path.join(abs_image_paths, save_image_as)  # <-- path where we save it
            location_of_full_sized_image = image_name_to_image_src(save_image_as)  # <-how we call that path in the html
            if extension != ".svg":
                img_object.save(cached_image_path)
            else:
                with open(cached_image_path, "wb") as img_out_file:
                    img_out_file.write(img_object)

            # Open the final image and do compression, if it was specified to do so:
            height = None
            if compression_information and extension != ".svg":
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
                if height and not width:
                    width = math_module.ceil(height * full_image.width / full_image.height)
                # If no size is specified and srcset is set, generate a set of resolutions:
                if compression_information["srcset"] and not width:
                    srcset = compression_information["srcset"]
                    srcset.sort()
                    srcset = list(filter((lambda x: x < full_image.width), srcset))
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

    if DEBUG:
        print("\n------------\nHtml with image links:\n------------\n\n", html_rendered)

    # ensure we have the css and the code navigation banner where we want it to be:
    with open_local("github-css.min.css", "r") as from_f:
        with open(os.path.join(abs_css_paths, "github-css.css"), "w") as to_f:
            to_f.write(from_f.read())
    with open_local("code-navigation-banner-illo.svg", "r") as from_f:
        with open(os.path.join(abs_css_paths, "code-navigation-banner-illo.svg"), "w") as to_f:
            to_f.write(from_f.read())

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
https://pypi.org/project/pdfkit/""")
        # ensure the image links are absolute
        links_in_general = [
                               str(image, encoding="UTF-8") for image in
                               re.compile(rb'src="([^"]+)').findall(bytes(html_rendered, encoding="UTF-8"))
                           ] + [
                               str(image, encoding="UTF-8") for image in
                               re.compile(rb'href="([^"]+)').findall(bytes(html_rendered, encoding="UTF-8"))
                           ]
        absolute_relative_links = [link[1:] for link in links_in_general if link.startswith("/")]
        relative_links = [link for link in links_in_general if not link.startswith("/")]
        links = absolute_relative_links + relative_links
        links = filter(lambda link: not (link.startswith("https://") or link.startswith("http://")), links)

        for link in links:
            abs_path = os.path.join(os.getcwd(), abs_website_root.lstrip("/"), link)
            if abs_path[1:3] == ":\\":  # <-- special treatment for windows paths
                abs_path = (abs_path[0].lower() + "/" + abs_path[3:]).replace("\\", "/")
            abs_path = "file://" + abs_path

            if link in absolute_relative_links:
                html_rendered = html_rendered.replace('src="/' + link, 'src="' + abs_path)
                html_rendered = html_rendered.replace('href="/' + link, 'href="' + abs_path)
            elif link in relative_links:
                html_rendered = html_rendered.replace('src="' + link, 'src="' + abs_path)
                html_rendered = html_rendered.replace('href="' + link, 'href="' + abs_path)

        # remove the css if we want to save it without css:
        if not style_pdf:
            html_rendered = "\n".join(html_rendered.split("\n")[2:])

        # use <name>-variable in the name
        if "<name>" in output_pdf and origin_type == "string":
            raise Exception("You can't use <name> in your pdf name if you enter the input with the '-t string option'.")
        else:
            output_pdf = output_pdf.replace("<name>", file_name_origin)

        # Finally convert it:
        # (this saving and then converting ensures we don't convert links like https:foo to
        # absolute_path_to_file_location/https://foo)
        with open(os.path.join(abs_destination, output_name + ".html"), "w+") as f:
            f.write(html_rendered)
        pdfkit.from_file(
            os.path.join(abs_destination, output_name + ".html"),
            os.path.join(destination, output_pdf),
            options=dict() if DEBUG else {'quiet': ''},
        )
        os.remove(os.path.join(abs_destination, output_name + ".html"))

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

# Reacting appropriately if code is called from command line interface:


if __name__ == "__main__":
    # argparse:
    parser = argparse.ArgumentParser(
        description='Convert markdown to HTML using the GitHub API and some additional tweaks with python.',
    )


    class FuseInputString(argparse.Action):
        """Ugly workaround because argparse seems to not take input with spaces just as it is (as long as it is
        properly quoted in the shell and passed to sys.argv as a whole), but instead fuses all elements of sys.argv
        and parses them afterwords 🙄"""

        def __call__(self, p, namespace, values, option_string=""):
            setattr(namespace, self.dest, " ".join(values))


    parser.add_argument('md_origin', nargs="+", metavar='MD-origin', action=FuseInputString,
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

    parser.add_argument('-w', '--website-root', nargs="+", action=FuseInputString, help="""
    Only relevant if you are creating the html for a static website which you manage using git or something similar.
    --html-root is the directory from which you serve your website (which is needed to correctly generate the links
    within the generated html, such as the link pointing to the css, since they are all root-relative),
    and can be a relative as well as an absolute path. Defaults to the directory you called this script from.
    If you intent to view the html file on your laptop instead of hosting it on a static site, website-root should be
    a dot and destination not set. The reason the generated html files use root-relative links to embed images is that
    on many static websites, https://foo/bar/index.html can be accessed via https://foo/bar, in which case relative
    (non-root-relative) links in index.html will be interpreted as relative to foo instead of bar, which can cause
    images not to load.
    """)
    # ToDo: Allow the use of any --website-root even if one wants to view the files locally, as long as destination is
    #  a dot.

    parser.add_argument('-d', '--destination', nargs="+", action=FuseInputString, help="""
    Where to store the generated html. This path is relative to --website-root. Defaults to "".""")

    parser.add_argument('-i', '--image-paths', nargs="+", action=FuseInputString, help="""
    Where to store the images needed or generated for the html. This path is relative to website-root. Defaults to the
    "images"-folder within the destination folder.""")

    parser.add_argument('-c', '--css-paths', nargs="+", action=FuseInputString, help="""
    Where to store the css needed for the html (as a path relative to the website root). Defaults to the
    "<WEBSITE_ROOT>/github-markdown-css"-folder.""")

    parser.add_argument('-n', '--output-name', nargs="+", action=FuseInputString, default="<name>.html", help="""
    What the generated html file should be called like. Use <name> within the value to refer to the name of the markdown
    file that is being converted (if you don't use "-t string"). You can use '-n print' to print the file (if using
    the command line interface) or return it (if using the python module), both without saving it. Default is 
    '<name>.html'.""")

    parser.add_argument('-p', '--output-pdf', nargs="+", action=FuseInputString, help="""
    If set, the file will also be saved as a pdf file in the same directory as the html file, using pdfkit, a python
    library which will also need to be installed for this to work. You may use the <name> variable in this value like
    you did in --output-name.""")

    parser.add_argument('-s', '--style-pdf', default="true", help="""
    If set to false, the generated pdf (only relevant if you use --output-pdf) will not be styled using github's css.
    """)

    parser.add_argument('-f', '--footer', nargs="+", action=FuseInputString, help="""
    An optional piece of html which will be included as a footer where the 'hosted with <3 by github'-footer usually is.
    Defaults to None, meaning that the section usually containing said footer will be omitted altogether.
    """)

    parser.add_argument('-m', '--math', default="true", help="""
    If set to True, which is the default, LaTeX-formulas using $formula$-notation will be rendered.""")

    parser.add_argument('-r', '--formulas-supporting-darkreader', default="false", type=bool, help="""
    If set to true, formulas will be shown light if the darkreader .js library is included in the html and the
    user prefers darkmode. This is checked by looking for a script embedded from a src ending with "darkreader.js" and
    by checking the prefers-color-scheme option in the browser. You can also supply any other script src to look for.
    Please note that this won't have any effect unless you inject the darkreader .js library into the generated html;
    doing so is not included in this module.""")

    parser.add_argument('-x', '--extra-css', nargs="+", action=FuseInputString, help="""
    A path to a file containing additional css to embed into the final html, as an absolute path or relative to the
    working directory. This file should contain css between two <style>-tags, so it is actually a html file, and can
    contain javascript as well. It's worth mentioning and might be useful for your css/js that every element of the
    generated html is a child element of an element with id xxx, where xxx is "article-" plus the filename (without
    extension) of:
    * output-name, if output-name is not "print" and not the default value.
    * the input markdown file, if output-name is "print", and the input type is not string.
    * the file with the extra-css otherwise.
    If none of these cases applies, no id is given.""")

    parser.add_argument('-o', '--core-converter', nargs="+", action=FuseInputString,
                        default=markdown_to_html_via_github_api, help="""
    The converter to use to convert the given markdown to html, before additional modifications such as formula support
    and image downloading are applied; this can be
    * on Unix/ any system with a cmd: a command containing the string "{md}", where "{md}" will be replaced with an
      escaped version of the markdown file's content, and which returns the finished html. Please note that commands for
      Unix-system won't work on Windows systems, and vice versa etc.
    * when using gh-md-to-html in python: A callable which converts markdown to html, or a string as described above.
    """)

    parser.add_argument('-e', '--compress-images', nargs="+", action=FuseInputString, help="""
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
    If this argument is left empty, no compression is down at all. If this argument is set to True, all default values
    are used. If it is set to json data and values are omitted, the defaults are also used. If a dict is passed instead
    of json data (when using the tool as a python module), the dict is used as the result of the json data.
    """)

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
        with open_local("help.txt", "w") as help_file:
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
have deleted autogenerated files during the convertion process.")
        exit(1)
    except requests.exceptions.ConnectionError:
        traceback.print_exc()
        print("\nAn Error occurred because a web page could not be accessed. This is probably because you either have\n\
no internet, or you the page used to render the formulas or github is down, or because an image-link within your\n\
input markdown directs to a non-accessible page.")
        exit(1)
