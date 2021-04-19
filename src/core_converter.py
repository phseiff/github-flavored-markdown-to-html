
from pygments import highlight
from pygments.lexers import get_lexer_by_name
from pygments.formatters import html as pygments_html
import re
import bs4
import html
from .helpers import heading_name_to_id_value

try:
    import mistune
except ImportError:
    raise ImportError(
        "OFFLINE conversion requires 'mistune' package >= 2.0.0rc1!\n\ttry running: pip3 install mistune>=2.0.0rc1")

if int(mistune.__version__.split(".")[0]) == 0 or mistune.__version__.startswith("2.0.0a"):
    # ^ more specific than testing for the presence of `mistune.scanner`.
    raise ImportError(
        "OFFLINE conversion requires 'mistune' package >= 2.0.0rc1!\n\ttry running: pip3 install mistune>=2.0.0rc1")
from mistune.scanner import escape_html


# This is False, and True enables some things I personally find endearing to have in a converter:
INTERNAL_USE = False


class HighlightRenderer(mistune.HTMLRenderer):
    HARMFUL_PROTOCOLS = {
        'javascript:',
        'vbscript:',
        'data:',
    } if not INTERNAL_USE else set()

    def __init__(self, escape=False, allow_harmful_protocols=None):
        super().__init__()
        self._escape = escape
        self._allow_harmful_protocols = allow_harmful_protocols

    def block_code(self, code, language=None):
        if language:
            lexer = get_lexer_by_name(language, stripall=True)
            formatter = pygments_html.HtmlFormatter()
            highlighted = highlight(code, lexer, formatter)
            highlighted_soup = bs4.BeautifulSoup(highlighted, "html.parser")
            for code_soup_element in highlighted_soup.find_all("span"):
                if code_soup_element.has_attr("class"):
                    code_soup_element["class"] = ["pl-" + code_soup_element["class"][0]]
            highlighted_soup.find("div")["class"].append("highlight-source-" + language.replace("+", "p"))
            return highlighted_soup.__str__()
        return '<pre><code>' + mistune.escape(code) + '</code></pre>'

    def heading(self, text, level):
        tag = 'h' + str(level)
        id_from_title = heading_name_to_id_value(text)
        full_element = (
                "<" + tag  # + " id=\"user-content-" + id_from_title + "\""
                + ">\n<a aria-hidden=\"true\" class=\"anchor\" href=\"" + "#"
                + ("user-content-" if INTERNAL_USE else "") + id_from_title + "\" id=\"user-content-" + id_from_title
                + "\">" + "<span aria-hidden=\"true\" class=\"octicon octicon-link\"></span></a>" + text + "</" + tag
                + ">\n"
        )
        return full_element

    def image(self, src, alt="", title=None):
        return (
                    '<a href="' + self._safe_url(src) + '" rel="nofollow">'
                    '<img alt="' + alt + '"'
                    + ((' title="' + escape_html(title) + '"') if title else "")
                    + ' data-canonical-src="' + self._safe_url(src) + '"'
                    + ' src="' + self._safe_url(src) + '"'
                    + ' style="max-width:100%;"/>'
                    + '</a>'
        )

    def link(self, link, text=None, title=None):
        if text is None:
            text = link
        elif text.startswith("<a "):
            return (text.split(' href="')[0]
                    + ' href="' + link + '" rel="nofollow">' + text.split('" rel="nofollow">', 1)[1])

        s = '<a href="' + self._safe_url(link) + ('" rel="nofollow"' if not INTERNAL_USE else '"')
        if title:
            s += ' title="' + escape_html(title) + '"'
        return s + '>' + (text or link) + '</a>'

    def list_item(self, text, level):
        return '<li>\n' + text + '</li>\n'

    def paragraph(self, text):
        if "ToDo" in text:
            text1, text2 = text.split("ToDo", 1)
            text = text1 + '<span class="ToDo">ToDo' + text2 + "</span>"
        return "<p>" + text + "</p>\n"


markdown = mistune.create_markdown(renderer=HighlightRenderer(), escape=False,
                                   plugins=['strikethrough', 'url']
                                           + (["footnotes"] if INTERNAL_USE else []) + ["table"])
