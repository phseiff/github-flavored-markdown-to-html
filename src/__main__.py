"""Convert Markdown to html via python or with a command line interface."""


import textwrap
from abc import ABC

import requests
import re
import argparse
import sys
import os
from PIL import Image
from io import BytesIO
import html
from urllib.parse import quote
from html.parser import HTMLParser

MODULE_PATH = os.path.join(*os.path.split(__file__)[:-1])


def open_local(path, mode):
    return open(os.path.join(MODULE_PATH, path), mode)


HELP = open_local("help.txt", "r").read()


# A parser to find formulas within an html file:


class FindFormulasInHtml(HTMLParser, ABC):
    def __init__(self):
        HTMLParser.__init__(self)
        self.is_in_code = False
        self.results = []

    def parse(self, html_rendered):
        self.feed(html_rendered)
        html_rendered_in_lines = html_rendered.split("\n")
        # print("results:", self.results)
        for r in range(len(self.results)):
            result = self.results[r]
            if result[0][0][0] == result[0][1][0]:  # ensure we don't have multiline formulas!
                # print("result:", result)
                line_number = result[0][0][0]
                char_range = slice(result[0][0][1], result[0][1][1])
                line_center = html_rendered_in_lines[line_number][char_range]
                line_left = html_rendered_in_lines[line_number][:result[0][0][1]]
                line_right = html_rendered_in_lines[line_number][result[0][1][1]:]
                line_growth = 0
                # print("line_left:", line_left)
                # print("line_center:", line_center)
                # print("line_right:", line_right)
                while line_center.count("$") >= 2:
                    line_center_left, line_center = line_center.split("$", 1)
                    line_center, line_center_right = line_center.split("$", 1)
                    line_center = html.unescape(line_center)
                    old_line_center_length = len(line_center)
                    svg_image_code = requests.get(
                        url="https://latex.codecogs.com/svg.latex?" + quote(line_center)
                    ).text
                    svg_image_code = svg_image_code.split("<?xml version='1.0' encoding='UTF-8'?>", 1)[1]
                    svg_image_code = svg_image_code.replace('<svg', '<svg style="vertical-align: middle"')
                    line_center = svg_image_code.replace('<path', '<path class="formula"')
                    new_line_center_length = len(line_center)
                    line_growth += new_line_center_length - old_line_center_length
                    line_center = line_center_left + line_center + line_center_right
                    # print("new line center:", line_center)
                for result in self.results:
                    if result[0][0][0] == line_number:
                        result[0][0] = (result[0][0][0], result[0][0][1] + line_growth)
                        # result[0][1] = (result[0][1][0], result[0][1][1] + line_growth)
                html_rendered_in_lines[line_number] = line_left + line_center + line_right
                # print("new line:", html_rendered_in_lines[line_number])
        return "\n".join(html_rendered_in_lines)

    def handle_starttag(self, tag, attrs):
        if self.results and self.results[-1][0][1] == "?":
            self.results[-1][0][1] = (self.getpos()[0] - 1, self.getpos()[1])
        if tag == "code":
            self.is_in_code = True

    def handle_endtag(self, tag):
        if self.results and self.results[-1][0][1] == "?":
            self.results[-1][0][1] = (self.getpos()[0] - 1, self.getpos()[1])
        if tag == "code":
            self.is_in_code = False

    def handle_data(self, data):
        if not self.is_in_code:
            # print("We got:", self.getpos(), data)
            self.results.append([[(self.getpos()[0] - 1, self.getpos()[1]), "?"], data])


# The main function:


def main(md_origin, origin_type="file", website_root=None, destination=None, image_paths=None, css_paths=None,
         output_name="<name>.html", output_pdf=None, style_pdf=True, footer=None, math=True,
         formulas_supporting_darkreader=False):
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

    # request markdown-to-html-conversion from the github api:
    headers = {"Content-Type": "text/plain"}
    data = md_content
    html_content = requests.post("https://api.github.com/markdown/raw", headers=headers, data=data).text

    # maybe create a footer:
    if footer:
        footer = '<div class="gist-meta">\n' + footer + '</div>'
    else:
        footer = ""

    # fill it into our template:
    with open_local("prototype.html", "r") as f:
        html_rendered = f.read().format(
            article=html_content,
            css_paths=("/" if website_root != "." else "") + css_paths.replace(os.sep, "/"),
            footer=footer
        )

    # render math formulas:
    if math:
        html_with_math = FindFormulasInHtml().parse(html_rendered)
        if not (html_with_math != html_rendered and formulas_supporting_darkreader):
            formulas_supporting_darkreader = False
        html_rendered = html_with_math
        if formulas_supporting_darkreader:
            with open_local("svg-color-changer.html", "r") as f:
                html_rendered += "\n\n" + f.read().replace("{script_name}", darkreader_src)

    # find the images in there:
    images = [
        str(image, encoding="UTF-8") for image in
        re.compile(rb'<img [^>]*src="([^"]+)').findall(bytes(html_rendered, encoding="UTF-8"))
    ]

    # ensure we have them all in the images path:
    saved_image_names = set()
    for image_src in images:
        print(image_src)
        original_markdown_image_src = image_src
        save_image_as = re.split("[/\\\]", image_src)[-1]  # <--  take only the last element of the path
        save_image_as = save_image_as.rsplit(".", 1)[0]  # <-- remove the extension
        save_image_as = re.sub(r'(?u)[^-\w.]', '', save_image_as)  # <-- remove disallowed characters
        while save_image_as in saved_image_names or not save_image_as:
            save_image_as += "_"
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
                    url_full = url_root + "/" + "/".join(path) + "/"
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
                elif origin_type == "string":
                    location = os.getcwd()
                # check if we have an absolute or a non-absolute path
                if os.path.abspath(image_src):
                    image_src = image_src
                else:
                    image_src = os.path.join(location, image_src.replace("/", os.sep))
                load_from_web = False

        # load with a mothod appropriate for the type of source
        if load_from_web:
            try:
                img_object = Image.open(BytesIO(requests.get(image_src).content))
            except OSError:
                img_object = requests.get(image_src).content
        else:
            img_object = Image.open(image_src)

        # save the image:
        try:
            extension = "." + img_object.format
        except AttributeError:
            extension = ".svg"
        save_image_as += extension
        saved_image_names.add(save_image_as)
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
            original_markdown_image_src,
            ("/" if website_root != "." else "") + image_paths + "/" + save_image_as
        )

    # ensure we have the css where we want it to be:
    with open_local("github-css.css", "r") as from_f:
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
        except:
            raise Exception("""\
Unfortunately, you need to have pdfkit installed to save as pdf. Find out how to install it here:
https://pypi.org/project/pdfkit/""")
        # ensure the image links are absolute
        links = [
                    str(image, encoding="UTF-8") for image in
                    re.compile(rb'src="/([^"]+)').findall(bytes(html_rendered, encoding="UTF-8"))
                ] + [
                    str(image, encoding="UTF-8") for image in
                    re.compile(rb'href="/([^"]+)').findall(bytes(html_rendered, encoding="UTF-8"))
                ] + [
                    str(image, encoding="UTF-8") for image in
                    re.compile(rb'src="\./([^"]+)').findall(bytes(html_rendered, encoding="UTF-8"))
                ] + [
                    str(image, encoding="UTF-8") for image in
                    re.compile(rb'href="\./([^"]+)').findall(bytes(html_rendered, encoding="UTF-8"))
                ]
        for link in links:
            abs_path = os.path.join(os.getcwd(), abs_website_root.lstrip("./"), link)
            if abs_path[1:3] == ":\\":
                abs_path = (abs_path[0].lower() + "/" + abs_path[3:]).replace("\\", "/")
            abs_path = "file://" + abs_path

            html_rendered = html_rendered.replace('src="/' + link, 'src="' + abs_path)
            html_rendered = html_rendered.replace('href="/' + link, 'href="' + abs_path)
            html_rendered = html_rendered.replace('src="./' + link, 'src="' + abs_path)
            html_rendered = html_rendered.replace('href="./' + link, 'href="' + abs_path)

        # remove the css if we want to save it without css:
        if not style_pdf:
            html_rendered = "\n".join(html_rendered.split("\n")[2:])

        # use <name>-variable in the name
        if "<name>" in output_pdf and origin_type == "string":
            raise Exception("You can't use <name> in your pdf name if you enter the input with the '-t string option'.")
        else:
            output_pdf.replace("<name>", file_name_origin)

        # finally convert it:
        pdfkit.from_string(
            html_rendered, os.path.join(destination, output_pdf),
        )

        # return the result
        return html_rendered


# Something I used to test this module out:
# main(md_origin="wowo `code $blabla$ ` wuwu $wiwi <wuwu $ test2 $formula$ \n```\n\n wiwi \n $LaTeX$ \n\nmm\n```",
#      origin_type="string",
#      website_root=".", output_name="math_test.html", formulas_supporting_darkreader=True)

main.__doc__ = """\
Use this function like the command line interface:
--------------------------------------------------
""" + HELP


def str2bool(v):
    if isinstance(v, bool):
        return v
    if v.lower() in ('yes', 'true', 't', 'y', '1'):
        return True
    elif v.lower() in ('no', 'false', 'f', 'n', '0'):
        return False
    else:
        raise argparse.ArgumentTypeError('Boolean value expected.')


if __name__ == "__main__":
    # argparse:
    parser = argparse.ArgumentParser(
        description='Convert markdown to HTML using the GitHub API and some additional tweaks with python.',
    )
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

    parser.add_argument('-w', '--website-root', help="""
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

    parser.add_argument('-d', '--destination', help="""
    Where to store the generated html. This path is relative to --website-root. Defaults to "".""")

    parser.add_argument('-i', '--image-paths', help="""
    Where to store the images needed or generated for the html. This path is relative to website-root. Defaults to the
    "images"-folder within the destination folder.""")

    parser.add_argument('-c', '--css-paths', help="""
    Where to store the css needed for the html (as a path relative to the website root). Defaults to the
    "<WEBSITE_ROOT>/github-markdown-css"-folder.""")

    parser.add_argument('-n', '--output-name', default="<name>.html", help="""
    What the generated html file should be called like. Use <name> within the value to refer to the name of the markdown
    file that is being converted (if you don't use "-t string"). You can use '-n print' to print the file (if using
    the command line interface) or return it (if using the python module), both without saving it.""")

    parser.add_argument('-p', '--output-pdf', help="""
    If set, the file will also be saved as a pdf file in the same directory as the html file, using pdfkit, a python
    library which will also need to be installed for this to work. You may use the <name> variable in this value like
    you did in --output-name.""")

    parser.add_argument('-s', '--style-pdf', default="true", help="""
    If set to false, the generated pdf (only relevant if you use --output-pdf) will not be styled using github's css.
    """)

    parser.add_argument('-f', '--footer', help="""
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

    # change help text
    help_text = parser.format_help()
    help_text_lines = help_text.split("\n")
    l = -1
    while l < len(help_text_lines) - 1:
        l += 1
        if "* " in help_text_lines[l]:
            left, right = help_text_lines[l].split("* ", 1)
            if left != "                        ":
                help_text_lines.insert(l + 1, "                        * " + right)
                help_text_lines[l] = left
        if l < len(help_text_lines) - 1 and help_text_lines[l].startswith("                        "):
            if (help_text_lines[l + 1].startswith("                        ")
                    and not help_text_lines[l + 1].startswith("                        * ")):
                text_next_line = help_text_lines[l + 1].split("                        ")[1].split(" ")
                while 80 - len(help_text_lines[l]) > len(text_next_line[0]):
                    text_this_line = help_text_lines[l].split(" ")
                    text_this_line.append(text_next_line.pop(0))
                    help_text_lines[l] = " ".join(text_this_line)
                    help_text_lines[l + 1] = "                        " + " ".join(text_next_line)
                    if not help_text_lines[l + 1].strip():
                        del help_text_lines[l + 1]
                    if (help_text_lines[l + 1].startswith("                        ")
                            and not help_text_lines[l + 1].startswith("                        * ")):
                        text_next_line = help_text_lines[l + 1].split("                        ")[1].split(" ")
                    else:
                        break
    help_text = "\n".join(help_text_lines)

    with open_local("help.txt", "w") as help_file:
        help_file.write(help_text)

    # This hackish ensures the bullet points in the help menu generated by argparse get printed correctly.
    if "-h" in sys.argv or "--help" in sys.argv:
        print(HELP)
        sys.exit()

    # pass these inputs to the main-function:
    result = main(**vars(parser.parse_args()))
    if parser.parse_args().output_name == "print":
        print(result)
