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
from io import BytesIO
from urllib.parse import quote
import traceback
import subprocess

MODULE_PATH = os.path.join(*os.path.split(__file__)[:-1])
DEBUG = False  # weather to print debug information


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
    if isinstance(v, bool):
        return v
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


# The main function:


def main(md_origin, origin_type="file", website_root=None, destination=None, image_paths=None, css_paths=None,
         output_name="<name>.html", output_pdf=None, style_pdf="True", footer=None, math="True",
         formulas_supporting_darkreader=False, extra_css=None, core_converter=markdown_to_html_via_github_api):
    # set all to defaults:
    style_pdf = str2bool(style_pdf)
    math = str2bool(math)
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
    images = [
        str(image, encoding="UTF-8") for image in
        re.compile(rb'<img [^>]*src="([^"]+)').findall(bytes(html_rendered, encoding="UTF-8"))
    ]

    # ensure we have all the images in the images path:
    saved_image_names = set(  # <-- defines which images we already have within our image directory
        image_name.rsplit(".", 1)[0]
        for image_name in os.listdir(abs_image_paths)
        if os.path.isfile(os.path.join(abs_image_paths, image_name))
    )
    for image_src in images:  # <-- Iterates over all images referenced in the markdown file
        # print(image_src)
        original_markdown_image_src = image_src
        save_image_as = re.split("[/\\\]", image_src)[-1]  # <--  take only the last element of the path
        save_image_as = save_image_as.rsplit(".", 1)[0]  # <-- remove the extension
        save_image_as = re.sub(r'(?u)[^-\w.]', '', save_image_as)  # <-- remove disallowed characters
        while save_image_as in saved_image_names or not save_image_as:
            save_image_as += "_"
        saved_image_names.add(save_image_as)
        if image_src.startswith("./"):
            image_src = image_src[2:]

        # actually get the image:

        load_from_web = False
        if image_src.startswith("https://") or image_src.startswith("http://"):
            # it is clearly an absolute url:
            load_from_web = True
        else:
            if origin_type == "string":
                # This is a security risk since web content might get one to embed local images from ones disk
                # into ones website when automatically cloning .md-files found online.
                input("""press enter if you are sure you trust that string. Remove this line if this is always
the case when inputting strings.""")

            if origin_type in ("repo", "web"):
                # create website domain name and specific path from md_origin depending on whether we pull from
                # a repo or the web:
                if origin_type == "repo":
                    user_name, repo_name, branch_name, *path = md_origin.split("/")
                    url_root = (
                            "https://github.com/" + user_name
                            + "/" + repo_name +
                            "/raw/" + branch_name
                    )
                    url_full = url_root + "/" + "/".join(path[:-1]) + "/"
                else:  # origin_type == "web":
                    url_root = "/".join(md_origin.split("/")[:3])
                    url_full = md_origin.rsplit("/", 1)[0] + "/"
                # Create full web image path depending on weather we have an absolute relative link or just a regular
                # relative link:
                if image_src.startswith("/"):
                    image_src = url_root + image_src
                else:
                    image_src = url_full + image_src
                load_from_web = True

            elif origin_type in ("file", "string"):
                # get the current directory (for relative file paths) depending on the origin_type
                if origin_type == "file":
                    location = md_origin.rsplit(os.sep, 1)[0]
                    if not os.path.isabs(location):
                        location = os.path.join(os.getcwd(), location)
                else:  # elif origin_type == "string":
                    location = os.getcwd()
                # check if we have an absolute or a non-absolute path
                if os.path.isabs(image_src):
                    image_src = image_src
                else:
                    image_src = os.path.join(location, image_src.replace("/", os.sep))
                load_from_web = False

        # load with a method appropriate for the type of source
        if load_from_web:
            try:
                img_object = Image.open(BytesIO(requests.get(image_src).content))
            except OSError:
                img_object = requests.get(image_src).content
        else:
            img_object = Image.open(image_src)

        # save the image:
        try:
            extension = "." + img_object.format.lower()
        except AttributeError:
            extension = ".svg"
        save_image_as += extension
        cached_image_path = os.path.join(abs_image_paths, save_image_as)
        try:
            img_object.save(cached_image_path)
        except AttributeError:
            with open(cached_image_path, "wb+") as f:
                f.write(img_object)
        # replace the link to the image with the link to the stored image:
        # print("original_image:", original_image, ":")
        # print("caged image path:", cached_image_path, ":")
        # print("in:", original_image in html_rendered)
        html_rendered = html_rendered.replace(
            '<img src="' + original_markdown_image_src + '"',
            '<img src="' + ("/" if website_root != "." else "") + image_paths + "/" + save_image_as + '"'
        )
        html_rendered = html_rendered.replace(
            '<a href="' + original_markdown_image_src + '"',
            '<a href="' + ("/" if website_root != "." else "") + image_paths + "/" + save_image_as + '"'
        )

    if DEBUG:
        print("\n------------\nHtml with image links:\n------------\n\n", html_rendered)

    # ensure we have the css where we want it to be:
    with open_local("github-css.min.css", "r") as from_f:
        with open(os.path.join(abs_css_paths, "github-css.css"), "w") as to_f:
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

    parser.add_argument('-x', '--extra-css', nargs="+", help="""
    A path to a file containing additional css to embed into the final html, as an absolute path or relative to the
    working directory. This file should contain css between two <style>-tags, so it is actually a html file, and can
    contain javascript as well. It's worth mentioning and might be useful for your css/js that every element of the
    generated html is a child element of an element with id xxx, where xxx is "article-" plus the filename (without
    extension) of:
    * output-name, if output-name is not "print" and not the default value.
    * the input markdown file, if output-name is "print", and the input type is not string.
    * the file with the extra-css otherwise.
    If none of these cases applies, no id is given.""")

    parser.add_argument('-o', '--core-converter', nargs="+", default=markdown_to_html_via_github_api, help="""
    The converter to use to convert the given markdown to html, before additional modifications such as formula support
    and image downloading are applied; this can be
    * on Unix/ any system with a cmd: a command containing the string "{md}", where "{md}" will be replaced with an
      escaped version of the markdown file's content, and which returns the finished html. Please note that commands for
      Unix-system won't work on Windows systems, and vice versa etc.
    * when using gh-md-to-html in python: A callable which converts markdown to html, or a string as described above.
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
