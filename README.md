[![brought to you by phseiff](https://phseiff.com/images/brought-to-you-by-phseiff.svg)](https://github.com/phseiff)
[![github flavored markdown to html, aka gh-md-to-html](https://raw.githubusercontent.com/phseiff/github-flavored-markdown-to-html/master/docs/header.svg)](https://github.com/phseiff/github-flavored-markdown-to-html)

<!-- [![HitCount](http://hits.dwyl.com/phseiff/github-flavored-markdown-to-html.svg)](http://hits.dwyl.com/phseiff/github-flavored-markdown-to-html) -->
[![PyPI download total](https://img.shields.io/pypi/dm/gh-md-to-html.svg)](https://pypistats.org/packages/gh-md-to-html)
[![PyPI version shields.io](https://img.shields.io/pypi/v/gh-md-to-html.svg)](https://pypi.python.org/pypi/gh-md-to-html/)
[![PyPI pyversions](https://img.shields.io/pypi/pyversions/gh-md-to-html.svg)](https://pypi.python.org/pypi/gh-md-to-html/)
[![GitHub license](https://img.shields.io/github/license/phseiff/github-flavored-markdown-to-html.svg)](https://github.com/phseiff/github-flavored-markdown-to-html/blob/master/LICENSE.txt)
[![Average time to resolve an issue](http://isitmaintained.com/badge/resolution/phseiff/github-flavored-markdown-to-html.svg)](http://isitmaintained.com/project/phseiff/github-flavored-markdown-to-html)
[![Percentage of issues still open](http://isitmaintained.com/badge/open/phseiff/github-flavored-markdown-to-html.svg)](http://isitmaintained.com/project/phseiff/github-flavored-markdown-to-html)
<!-- ![Health measured by landscape.io](https://landscape.io/github/phseiff/github-flavored-markdown-to-html/master/landscape.png) -->

A user-friendly python-module and command-line frontend to convert markdown to html. It uses
[GitHubs online Markdown-to-html-API](https://docs.github.com/en/rest/reference/markdown) by default (which requires
internet connection), but comes with an option for offline conversion (which closely imitates GitHubs behavior), and any other python- or commandline tool can be plugged into it as well.
Whatever you use it with is automatically extended with a ton of functionality, like more in- and output options,
[github-flavored CSS](https://github.githubassets.com/assets/gist-embed-52b3348036dbd45f4ab76e44de42ebc4.css), formula
support, advanced image caching and optimization, host-ready file- and image-placement, pdf-conversion, emoji shortcode support, TOC support and more.

Whilst its main purpose is the creation of static pages from markdown files, for example in conjunction with a static
website builder or github actions if you host on Github, it can be very well-used for any other purpose.

Here is a (not necessarily extensive) list of its advantages and features:

<details><summary>Advantages & Features</summary>

<!--Advantages include<sup>(sorted by importance; skip the rest as soon as you're convinced!</sup>-->:

* Lets you specify the markdown to convert as a string, as a repository path, as a local
  file name or as a hyperlink.
* Pulls any images referenced in the markdown files from the web/ your local storage and
  places them in a directory relative to your specified website root, so the resulting file structure is host-ready for
  static sites. Multiple arguments allow the customization of the saving locations, but the images will always be
  referenced correctly in the resulting html files. This is especially useful since it reflects GitHub's behavior to serve cached copies of README-images instead of linking to them directly, reducing tracking and possibly downscaling overlarge images in the process.
* Creates all links as root-relative hyperlinks and lets you specify the root directory
  as well as the locations for css and images, but uses smart standard values for
  everything.
* Supports inline LaTeX-formulas (use `$`-formula-`$` to use them), which GitHub usually doesn't. gh-md-to-html uses
  [LaTeX](https://www.tug.org/texlive/) and [dvisvgm](https://dvisvgm.de/) if they are both installed (advantage: fast,
  requires no internet), and otherwise the [Codecogs EqnEditor](https://latex.codecogs.com/) (advantage: doesn't require
  you to install 3 GB of LaTeX libraries) to achieve this.
* Supports exporting to pdf with or without Github styling, using the
  [pdfkit](https://pypi.org/project/pdfkit/) python module (if it is installed).
* Tested and optimized to look good when using [DarkReader](https://github.com/darkreader/darkreader) (the
  .js-module as well as the browser extension). This is especially relevant considering that DarkReader doesn't usually
  shift the colors of svg images, and the formulas added by gh-md-to-html's formula support are embedded as inline svg.
  gh-md-to-html ensured that the formulas are the same color as the text, shifted in accordance with DarkReader's
  current/enabled colorscheme.
* Supports umlauts and other non-ascii-characters in plain text as well as in multiline code blocks, which the github
  REST api usually doesn't.
* Allows you to choose which tool or module to use at its core for the basic markdown to html conversion.
* Styles its output with github's README-css (can be turned off).
* Allows you to choose a width for the box surrounding the text; this can increase readability if you intend to host the
  markdown file stand-alone rather than embedded into a different html file (see
  [#25](https://github.com/phseiff/github-flavored-markdown-to-html/issues/25) and
  [Wikipedia](https://en.wikipedia.org/wiki/Line_length)).
* Comes with an optional support for the use of `[[_TOC_]]`, `{:toc}` and `[toc]` at the beginning of an otherwise empty
  line to create a table of content for the document, like GitLab-flavored markdown does, among others.
* Comes with an option to compress and downscale all images referenced in the markdown file (does not affect the
  original images) with a specified background color (default is white) for converting RGBA to RGB, and a specified
  compression rate (default is 90). Images with a specified width or height attribute in pixels get scaled down to that
  size to reduce loading time. This helps severely reduce the size of generated pages for markdown files with lots of
  images. There is also an option to save all images in multiple sizes and let the html viewer/browser pick the one
  fitting for the viewport size (using the img srcset attribute), thus making gh-md-to-html the only md-to-html
  converter with builtin srcset support for image load reduction.
* If two equal images from equal or different sources are referenced in the given markdown file, and both would be saved
  in the same resolution et cetera, both are pointed to the same copy in the generated html to minimize loading
  overhead.
* Comes with an option to closely imitate GitHub's markdown-to-html-conversion behavior offline!
* Emoji shortcode support.
* Probably even more than that - this list here is no longer maintained, refer to the documentation further down this README for all options.

</details>

In case you are looking for an alternative to Pandoc for converting markdown to PDF, here is a list of reasons why you could want to use gh-md-to-html instead of Pandoc for the job:

<details><summary>Reasons to use this instead of Pandoc</summary>

Whilst using pandoc to convert from markdown to pdf usually yields more beautiful results (pandoc uses LaTeX, after
all), gh-md-to-html has its own set of advantages when it comes to quickly converting complex files for a homework
assignment or other purposes where reliability weights more than beauty:

* pandoc converts .md to LaTeX and then renders it to pdf, which means that images embedded in the .md are shown where
  they fit best in the .pdf and not, as one would expect it from a .md-file, exactly where they were embedded.
* pandoc's pandoc-flavored markdown supports formulas; however, some specific rules apply regarding the amount of
  whitespace cornering the `$`-signs and what characters the formula may start with. These rules do not apply in some
  common markdown editors like MarkText, though, which leads to lots of frustration when formulas that worked in the
  editor don't work anymore when converting with pandoc (MarkText's own export-to-pdf-function sometimes fails on
  formula-heavy files without an error message, though, which makes it even less reliable). The worst part is that,
  whenever pandoc fails converting .md to .pdf because of this, it shows the line number of the error based on the
  intermediate .tex-file instead of the input .md-file, which makes it difficult to find the problem's root.
  As you might have guessed, gh-md-to-html couldn't care less about the amount of whitespace you start your formulas
  with, leaving this decision up to you.
* pandoc supports multiple markdown flavors. The sole formula-supporting one of these is pandoc-flavored markdown, which
  comes with some quite specific requirements regarding the amount of trailing whitespace before a sub-list in a nested
  list, and other requirements to create multi-line bullet point entries. These requirements are not fulfilled my many
  markdown-editors (such as MarkText) and not required by many other markdown flavors, causing pandoc to not render
  multiline bullet point entries and nestled lists correctly in many cases.
  gh-md-to-html, on the other hand, supports **both** nested lists like you would expect it, **and** formulas, releasing
  the burden of having to edit entire markdown files to make then work with pandoc's md-to-html-conversion from your
  shoulders.

To sum it up, pandoc's md-to-pdf-conversion acts quite unusual when it comes to images, nested lists, multiline bullet
point entries, or formulas, and gh-md-to-html does not.

</details>

## Installation

Use `pip3 install gh-md-to-html` to install directly from the python package index, or `python3 -m pip install gh-md-to-html` if
you are on Windows.

Both might require `sudo` on Linux, and you can optionally do

```
python3 -m pip install gh-md-to-html[pdf_export]
```

and [install wkhtmltopdf](https://wkhtmltopdf.org/downloads.html) (v0.12.6 or greater) to get the optional pdf-conversion feature and convert markdown files to pdf, and/or

```
python3 -m pip install gh-md-to-html[offline_conversion]
```

to get the optional offline-conversion feature up and running.

**If you are on Windows**, you might have to add `wkhtmltopdf` to your path in your current working directory in order to get pdf conversion to work, e.g. with `PATH=%PATH%;c:/program files/wkhtmltopdf/bin` or something similar, depending on your installation location.

## Usage

If you want to access the interface with your command line, you can just supply
`gh-md-to-html` with the arguments documented in the help text (accessible with
`gh-md-to-html -h` and shown below). On windows, you must supply `python3 -m gh_md_to_html` with the corresponding
arguments.

If you want to access the interface via python, you can use

```python
import gh_md_to_html
```

and then use `gh_md_to_html.main()` with the same arguments (and default values) you would
supply to the command line interface.

If you only want to imitate the conversion results yield by GitHub's REST API offline, but don't want image caching,
formula support and fancy CSS styling, use

```
html_as_a_string = gh_md_to_html.core_converter.markdown(your_markdown_as_a_string)
```

in Python.

<!--
If you call `gh-md-to-html foo.md` without any additional options, you will get a file called `foo.html` in the same directory as `foo.md`, with all the images referenced in `foo.md` in a folder called `images` and the required CSS in a folder called `github-markdown-css` (both linked by `foo.html` using absolute relative links).
-->

## Documentation

<details><summary>Documentation (throughout introduction for starters - NOT FINISHED YET)</summary>

<br>

* **Usage**: `gh-md-to-html <input_name> <optional_arguments>`

* **Default behavior**:<br>
  By default, gh-md-to-html takes a markdown file name as an argument, and saves the generated HTMl in a file of the same name, with `.html` instead of `.md`.<br>
  Some quirks:
  * The generated CSS is stored in `github-markdown-css/github-css.css` (add `-c` to make it inline instead).
  * All referenced images are cached, stored & referenced in `./images` (add `-i` to disable this).
  * All image & css links assume that you want to host the html file with your current directory as the root directory (add `-w` if you want to directly view it in a browser instead).
  * All `id`s and file-internal links are prefaced by `user-content-`, so you can embed the generated html in a bigger website without risking ID clashes.
  
* **Some common use cases**:<br>
  Through past issues, I realised that there are some very common use cases that most people seem to have for this module. Here are the most common ones, and which options and arguments to use for them:
  * **preview a GitHub README**: use `-i -w --math false --box-width 25cm`, though [grip](https://github.com/joeyespo/grip) might be more efficient for this purpose.
  * **preview a GitLab README**: see above, and add `--toc` to support GitLab's TOC syntax.
  * **as an alternative to pandoc-flavored markdown**: use `--math true --emoji-support 0 --dont-make-images-links true`.
  * **having everything in one file**: use `-i -c` to have everything in one file.

* **Converting markdown files from the web** with `--origin-type`:<br>
  You might want to not only convert a local markdown file, but also a file from a GitHub repository, a web-hosted one, or the contents of a string. Simply downloading these or storing them in a file is often not enough, since their location on the web also influences how the links to images they reference must be resolved. Luckily, gh-md-to-html has got your back!<br>
  There is a number of different arguments you can use to describe what kind of file the input you gave references:
  * `--origin-type file`: The default; takes a (relative or absolute) file path
  * `--origin-type repo`: Takes a pth to a markdown file in a github repository, in the format `<user_name>/<repo_name>/<branch-name>/<path_to_markdown>.md`.
  * `--origin-type web`: Takes the url of a web-hosted markdown file.
  * `--origin-type string`: Takes a string containing markdown.
  Some of these options you use influences how image links within the markdown file are resolved; a later section of this README outlines this in detail.

* **Fine-tuning what goes where**:<br>
  gh-md-to-html is written with the goal of generating a host-ready static website for you, with your current working directory as its root. Aside from using `-w` to disable this and allow you to view the generated file directly in a browser, there are a number of options that allow you to fine-tune what goes where, and most popularly, change the root of the website.
  There is no need to do so unless you want to for some reason, so don't bother reading this if you don't need to!
  * `--website-root`(or `-w`): Leaving this option empty, as discussed above, allows you to preview the generated html file directly in a browser (on most systems by double-clicking it) in case you don't want to host the generated html file, but you can also supply any directory that you want to use as the website's root to this. It defaults to your current working directory.
  * `--destination` (or `-d`): The path, relative to `--website-root`, in which the generated html file is stored. By default, the website root is used for this.
  * `--image-paths` (or `-i`): You can leave this empty to disable image caching, as described above (though this won't work in case you modified `--origin-type`), or supply a path relative to website-root to modify where images are stored. It defaults to `images`.<br>
    Image caching makes sure that two pixel-identical images are stored in the same file location, to minimize loading time for files with multiple identical images.
    The `image-paths`-directory isn't automatically emptied between multiple runs of gh-md-to-html for this reason, to ensure that this optimization can be used cross-file when converting multiple files in a bulk.
    <!-- You will have to manually empty it or wrap your own automization around gh-md-to-html to empty it between every run. -->
  * `--css-paths` (or `-c`): You can leave this empty to disable storing the CSS in an external CSS file (useful e.g. if you want to convert only one file), as described above, or supply a path relative to website-root to modify where the CSS file (called `github-css.css`) will be stored.
    The default is `github-markdown-css`.
  * `--output-name` (or `-n`): The file name under which to store the generated html file in the destination-directory.
    You can use `<name>` anywhere in this string, and it will automatically be replaced with the name of the markdown file, so, for example, `gh-md-to-html inp.md -n "<name>-conv.html"` will store the result in `ino-conv.html` (this doesn't work with `--origin-type string`, of course).<br>
    You can also use `-n print` in order to simply write the output to STDOUT (print it on the console) instead of saving it anywhere.
    The default value is `<name>.html`, so it adapts to your input file name.
  * `--output-pdf` (or `-p`): The file in which to store the generated pdf.
    You can use the `<name>`-syntax here as well. If the `-p`-option isn't used, no pdf will be generated (and you need to have followed the pdfkit & wkhtmltopdf installation instructions above to have this option work), but you can use `-p` without any arguments to have it use `<name>.pdf` as a sensitive file name default.

* **exporting as pdf**:<br>
  As mentioned above, you can export the generated HTML file as a pdf using the `--output-pdf`-option.
  Doing so requires you to have `wkhtmltopdf` installed (the Qt-patched version), to add it to the PATH (if you are on Windows), and to have `pdfkit` installed (e.g. via `pip3 install gh-md-to-html[offline_conversion]`), but all of these requirements are already outlined above in the [installation](#installation) section.<br>
  There are some things worth noting here, though. First of all, DO NOT use this option if you have valuable information in a file called `{yourpdfexportdestination}.html`, where `{yourpdfexportdestination}` is what you supplied to `-p`, since this file will be temporarily overwritten in the process; furthermore, do not use `-p` at all if you are supplying untrusted input to the `-x`-option.<br>
  There are also some options specifically tailored for use with `-p`; these are currently:
  * `--style-pdf` (or `-s`): Set this to `false` to disable styling the generated PDF file with GitHub's CSS. You might want to do this because the border that GitHub's CSS draws around the page can look counterintuitive in PDFs, though doing so can also negatively influence the appearance of other parts, so use this with a grain of salt.

* **changing which core markdown converter to use**:<br>
  gh-md-to-html doesn't actually do all that much heavy lifting itself when it comes to parsing markdown and converting it to PDF; instead, it wraps around a so-called "core converter" that does the basic conversion according to the markdown spec, and builds its own options, features, customizations and styling on top of that. By default, the GitHub markdown REST API is used for that, since it comes closest to what GitHub does with its READMEs, but you can also give gh-md-to-html any other basic markdown converter to work with.

  gh-md-to-html also comes with two build-in alternative core converters to use, that imitate GitHub's REST API as close as possible whilst adding their own personal touch to it.

  Option to decide the core converter:
  * `--core-converter` (or `-o`): You can use this option to choose from a number of pre-defined core converters (see below) in case you want to differ from the default one.
  
    You can also supply a bash command (on UNIX/Linux systems) to this, or a cmd.exe command on Windows, in which `{md}` stands as a placeholder for where the shell-escaped input markdown will be inserted by gh-md-to-html. For example,<br>
    `gh-md-to-html inp.md -o "pandoc -f markdown -t html <<< {md}"`<br>
    will use pandoc as its core converter.<br/>
    You can also do so using multiple commands, like<br>
    `gh-md-to-html -o "printf {md} >> temp.md; pandoc -f markdown -t html temp.md; rm temp.md"`,<br>
    as long as the result is printed to stdout.
  
    If you use the Python-interface to gh-md-to-html, you can also supply any function that converts a markdown string into a html string to this argument. 
  
  Pre-defined core converters that you can easily supply to `--core-converter` as strings:
  * `OFFLINE`: Imitates GitHub's markdown REST API, but offline using mistune. This requires the optional dependencies for "offline_conversion" to be satisfied, by using `pip3 install gh-md-to-html[offline_conversion]` or `pip3 install mistune>=2.0.0rc1`.
  * `OFFLINE+`: Behaves identical to OFFLINE, but it doesn't remove potentially harmful content like javascript and css like the GitHub REST API usually does. DO NOT USE THIS FEATURE unless you need a way to convert secure manually-checked markdown files without having all your inline js/styling stripped away!

* **support for inline-formulas**:<br>
  `gh-md-to-html` supports, by default, inline formulas (no matter which core converter, see above, you use).
  This means that you can write a LaTeX formula between two dollar signs on the same line, and it will be replaced with an SVG image displaying said formula. For example, <br>
  `$e = m \cdot c^2$`<br>
  will add Einstein's famous formula as a svg image, well-aligned with the rest of the text surrounding it, into your document.

  `gh-md-to-html` always tries to use your local LaTeX installation to do this conversion (advantage: fast and doesn't require internet).
  However, if [LaTeX](https://www.tug.org/texlive/) or [dvisvgm](https://dvisvgm.de/) are not installed or it can't find them, it uses [an online converter](https://latex.codecogs.com/) (advantage: doesn't require you to install 3 GB of LaTeX libraries) to achieve this.

  You can use the following options to modify this behavior:
  * `--math` (or `-m`): Set this to `false` to disable formula rendering.
  * `--suppress-online-fallbacks`: Set this to `true` to disable the online fallback for formula rendering, raising an error if its requirements aren't locally installed or can't be found for some reason.

* **image caching and image compression**:<br>
  As explained in-depth above, gh-md-to-html saves images so they can all be loaden from the same folder. This comes with the advantages of
  * potentially reducing tracking (in case the images where hosted on a 3rd-party website)
  * reducing the number of DNS lookups required to show your generated HTMl file (in case the images where hosted on different 3rd-party websites)
  * reducing the number of images to load (if one or multiple md files you intend to host or view as html files contain the same or pixel-identical images)
  
  In addition to these advantages, gh-md-to-html also allows you to set a level of image compression to use for these images. If you decide to do so, every image will be converted to JPEG (using a background color and quality settings of your liking), and images will be downscaled if the generated html states that they won't be needed at their full size anyways (you can make use of this e.g. by using `<img>`-tags directly in your document and supplying them with an explicit `width` or `height` value).

  gh-md-to-html is also the only markdown converter capable of making use of the html `srcset`-attribute, which allows the generated document to reference several differently scaled versions of the same image, of whom the browser will then load the smallest large-enough one on smaller screen sizes, leading to great load reductions e.g. on mobile.
  Enabling this feature can lead to further loading time reductions without sacrificing any visible image quality, which makes gh-md-to-html the best choice if you want to generate fast-loading websites from your image-heavy markdown files.

  The option to use for all of this is
  * `--compress-images`.<br>
    and it accepts a piece of JSON data with the following attributes:
    * `bg-color`: the color to use as a background color when converting RGBA-images to jpeg (an RGB-format).
      Defaults to "`white`" and accepts almost any HTML5 color-value ("`#FFFFFF`", "`#ffffff`", "`white`" and "`rgb(255, 255, 255)`" would've all been valid values).
    * `progressive`: Save images as progressive jpegs.
      Default is False.
    * `srcset`: Save differently scaled versions of the image and provide them to the image in its srcset attribute.
      Defaults to False.
      Takes an array of different widths or `True`, which serves as a shortcut for "`[500, 800, 1200, 1500, 1800, 2000]`".
    * `quality`: a value from 0 to 100 describing at which quality the images should be saved.
      Defaults to 90.
      If a specific size is specified for a specific image in the html, the image is always converted to the right size *before* reducing the quality.
    
    If this argument is left empty, no compression is used at all.
    If this argument is set to True, all default values are used.
    If it is set to json data and some values are omitted, the defaults ones are used for these.
  
    You can also pass a dict instead of a string containing JSON data if you are using this option in the Python frontend.
  
    Image compression won't work, for obvious reasons, if you use `-i` to disable image caching.

* **my personal choices**:<br>
  GitHub-flavored markdown and markdown in general makes some unpopular choices, and gh-md-to-html, imitating it, also makes a lot of these. If your goal isn't to be as close as possible to (github-flavored) markdown, and you want to utilize the full power that gh-md-to-html offers to the fullest, I recommend the following (very opinionated) list of settings and options. Note that some of these aren't safe when converting user-generated content, though.
  * `--math true`: This is already enabled by default, so not really a recommendation, but you'll most likely want to have LaTeX math support in your file.
  * `--core-converter OFFLINE+`: This converts the markdown files offline instead of using GitHub's REST API, and allows the use of unsafe things like inline code and every html you could wish for in your markdown file.
  * `--compress-images`: There are many ways to finetune this options, but it allows for some great optimizations on the cached images, including the use of the HTML  `srcset`-attribute, which no other markdown converter currently supports afaik.
  * `--box-width 25cm`: You'll most likely want to limit the width of the box in which the generated website's content is displayed [for reasons of readability](https://en.wikipedia.org/wiki/Line_length), unless you plan to embed the generated html into a bigger html file.
  * `--toc true`: This allows you to use `[[_TOC_]]` as a shortcut for a table of contents in the generated file.
  * `--dont-make-images-links true`: By default, GitHub wraps every image into a link to the image source, unless the image is already wrapped into a different link. This option disables this behavior for more control over your image's links.
  * `--emoji-support 2`: gh-md-to-html supports using emoji shortcodes, like `:joy:`, which are then replaced with emojis in the generated html file. `--emoji-support 2` takes this one level further this by allowing you to use your own custom emojis, so `:path/to/funny_image.png:` will add `funny_image.png` as an emoji-sized emoji into the text.
  * `--soft-wrap-in-code-boxes true`: By default, GitHub displays its multiline code boxes with a horizontal scrollbar if they are at a risk of overflowing. Use this option to have (imho more reasonable) soft-wrap in code boxes instead.

</details>

<details><summary>Help text (look up what every option does)</summary>
All arguments and how they work are documented in the help text of the program, which looks like the following.

Please note that the options are listed ordered by relevance, and all of them have sensible defaults, so don't feel overwhelmed by how many there are;
you can just read through them until you find what you where looking for, and safely ignore the rest.<br/>
Most of the options are meant to customize default behavior, so none of them are mandatory for most use cases.

```
usage: __main__.py [-h] [-t {file,repo,web,string}]
                   [-w WEBSITE_ROOT [WEBSITE_ROOT ...]]
                   [-d DESTINATION [DESTINATION ...]]
                   [-i [IMAGE_PATHS [IMAGE_PATHS ...]]]
                   [-c CSS_PATHS [CSS_PATHS ...]]
                   [-n OUTPUT_NAME [OUTPUT_NAME ...]]
                   [-p OUTPUT_PDF [OUTPUT_PDF ...]] [-s STYLE_PDF]
                   [-f FOOTER [FOOTER ...]] [-m MATH]
                   [-x EXTRA_CSS [EXTRA_CSS ...]]
                   [-o CORE_CONVERTER [CORE_CONVERTER ...]]
                   [-e COMPRESS_IMAGES [COMPRESS_IMAGES ...]]
                   [-b BOX_WIDTH [BOX_WIDTH ...]] [-a TOC]
                   MD-origin [MD-origin ...]

Convert markdown to HTML using the GitHub API and some additional tweaks with
python.

positional arguments:
  MD-origin             Where to find the markdown file that should be
                        converted to html

optional arguments:
  -h, --help            show this help message and exit
  -t {file,repo,web,string}, --origin-type {file,repo,web,string}
                        In what way the MD-origin-argument describes the origin
                        of the markdown file to use. Defaults to file. The
                        options mean: 
                        * file: takes a relative or absolute path to a file
                        * repo: takes a path to a markdown-file in a github
                        repository, such as <user_name>/<repo_name>/<branch-
                        name>/<path_to_markdown>.md 
                        * web: takes an url to a markdown file
                        * string: takes a string containing the files content
  -w WEBSITE_ROOT [WEBSITE_ROOT ...], --website-root WEBSITE_ROOT [WEBSITE_ROOT ...]
                        Only relevant if you are creating the html for a static
                        website which you manage using git or something similar.
                        --website-root is the directory from which you serve
                        your website (which is needed to correctly generate the
                        links within the generated html, such as the link
                        pointing to the css, since they are all root- relative),
                        and can be a relative as well as an absolute path.
                        Defaults to the directory you called this script from.
                        If you intent to view the html file on your laptop
                        instead of hosting it on a static site, website-root
                        should be a dot and destination not set. The reason the
                        generated html files use root-relative links to embed
                        images is that on many static websites,
                        https://foo/bar/index.html can be accessed via
                        https://foo/bar, in which case relative (non-root-
                        relative) links in index.html will be interpreted as
                        relative to foo instead of bar, which can cause images
                        not to load.
  -d DESTINATION [DESTINATION ...], --destination DESTINATION [DESTINATION ...]
                        Where to store the generated html. This path is relative
                        to --website-root. Defaults to "".
  -i [IMAGE_PATHS [IMAGE_PATHS ...]], --image-paths [IMAGE_PATHS [IMAGE_PATHS ...]]
                        Where to store the images needed or generated for the
                        html. This path is relative to website-root. Defaults to
                        the "images"-folder within the destination folder. Leave
                        this option empty to completely disable image
                        caching/downloading and leave all image links
                        unmodified.
  -c CSS_PATHS [CSS_PATHS ...], --css-paths CSS_PATHS [CSS_PATHS ...]
                        Where to store the css needed for the html (as a path
                        relative to the website root). Defaults to the
                        "<WEBSITE_ROOT>/github-markdown-css"-folder.
  -n OUTPUT_NAME [OUTPUT_NAME ...], --output-name OUTPUT_NAME [OUTPUT_NAME ...]
                        What the generated html file should be called like. Use
                        <name> within the value to refer to the name of the
                        markdown file that is being converted (if you don't use
                        "-t string"). You can use '-n print' to print the file
                        (if using the command line interface) or return it (if
                        using the python module), both without saving it.
                        Default is '<name>.html'.
  -p OUTPUT_PDF [OUTPUT_PDF ...], --output-pdf OUTPUT_PDF [OUTPUT_PDF ...]
                        If set, the file will also be saved as a pdf file in the
                        same directory as the html file, using pdfkit, a python
                        library which will also need to be installed for this to
                        work. You may use the <name> variable in this value like
                        you did in --output-name. Do not use this with the -c
                        option if the input of the -c option is not trusted;
                        execution of malicious code might be the consequence
                        otherwise!!
  -s STYLE_PDF, --style-pdf STYLE_PDF
                        If set to false, the generated pdf (only relevant if you
                        use --output-pdf) will not be styled using github's css.
  -f FOOTER [FOOTER ...], --footer FOOTER [FOOTER ...]
                        An optional piece of html which will be included as a
                        footer where the 'hosted with <3 by github'-footer in a
                        gist usually is. Defaults to None, meaning that the
                        section usually containing said footer will be omitted
                        altogether.
  -m MATH, --math MATH  If set to True, which is the default, LaTeX-formulas
                        using $formula$-notation will be rendered.
  -x EXTRA_CSS [EXTRA_CSS ...], --extra-css EXTRA_CSS [EXTRA_CSS ...]
                        A path to a file containing additional css to embed into
                        the final html, as an absolute path or relative to the
                        working directory. This file should contain css between
                        two <style>-tags, so it is actually a html file, and can
                        contain javascript as well. It's worth mentioning and
                        might be useful for your css/js that every element of
                        the generated html is a child element of an element with
                        id xxx, where xxx is "article-" plus the filename
                        (without extension) of: 
                        * output- name, if output-name is not "print" and not
                        the default value.
                        * the input markdown file, if output- name is "print",
                        and the input type is not string. * the file with the
                        extra-css otherwise. If none of these cases applies, no
                        id is given.
  -o CORE_CONVERTER [CORE_CONVERTER ...], --core-converter CORE_CONVERTER [CORE_CONVERTER ...]
                        The converter to use to convert the given markdown to
                        html, before additional modifications such as formula
                        support and image downloading are applied; this defaults
                        to using GitHub's REST API and can be 
                        * on Unix/ any system with a cmd: a command containing
                        the string "{md}", where "{md}" will be replaced with an
                        escaped version of the markdown file's content, and
                        which returns the finished html. Please note that
                        commands for Unix-system won't work on Windows systems,
                        and vice versa etc. 
                        * when using gh-md-to- html in python: A callable which
                        converts markdown to html, or a string as described
                        above. 
                        * OFFLINE as a value to indicate that gh-md-to-html
                        should imitate the output of their builtin
                        md-to-html-converter using mistune. This requires the
                        optional dependencies for "offline_conversion" to be
                        satisfied, by using `pip3 install
                        gh-md-to-html[offline_conversion]` or `pip3 install
                        mistune>=2.0.0rc1`. 
                        * OFFLINE+ behaves identical to OFFLINE, but it doesn't
                        remove potentially harmful content like javascript and
                        css like the GitHub REST API usually does. DO NOT USE
                        THIS FEATURE unless you need a way to convert secure
                        manually-checked markdown files without having all your
                        inline js stripped away!
  -e COMPRESS_IMAGES [COMPRESS_IMAGES ...], --compress-images COMPRESS_IMAGES [COMPRESS_IMAGES ...]
                        Reduces load time of the generated html by saving all
                        images referenced by the given markdown file as jpeg.
                        This argument takes a piece of json data containing the
                        following information; if it is not used, no compression
                        is done: 
                        * bg-color: the color to use as a background color when
                        converting RGBA-images to jpeg (an RGB-format). Defaults
                        to "white" and accepts almost any HTML5 color-value
                        ("#FFFFFF", "#ffffff", "white" and "rgb(255, 255, 255)"
                        would've all been valid values).
                        * progressive: Save images as progressive jpegs. Default
                        is False. 
                        * srcset: Save differently scaled versions of the image
                        and provide them to the image in its srcset attribute.
                        Defaults to False. Takes an array of different widths or
                        True, which serves as a shortcut for "[500, 800, 1200,
                        1500, 1800, 2000]".
                        * quality: a value from 0 to 100 describing at which
                        quality the images should be saved (this is done after
                        they are scaled down, if they are scaled down at all).
                        Defaults to 90. If a specific size is specified for a
                        specific image in the html, the image is always
                        converted to the right size. If this argument is left
                        empty, no compression is down at all. If this argument
                        is set to True, all default values are used. If it is
                        set to json data and values are omitted, the defaults
                        are also used. If a dict is passed instead of json data
                        (when using the tool as a python module), the dict is
                        used as the result of the json data.
  -b BOX_WIDTH [BOX_WIDTH ...], --box-width BOX_WIDTH [BOX_WIDTH ...]
                        The text of the rendered file is always displayed in a
                        box, like GitHub READMEs and issues are. By default,
                        this box fills the entire screen (max-width: 100%), but
                        you can use this option to reduce its max width to be
                        more readable when hosted stand-alone; the resulting box
                        is always centered. --box-width accepts the same
                        arguments the css max-width attribute accepts, e.g. 25cm
                        or 800px.
  -a TOC, --toc TOC     Enables the use of `[[_TOC_]]`, `{:toc}` and `[toc]`
                        at the beginning of an otherwise empty line to create a
                        table of content for the document. These syntax are
                        supported by different markdown flavors, the most
                        prominent probably being GitLab-flavored markdown
                        (supports `[[_TOC_]]`), and since GitLab displays its
                        READMEs quite similar to how GitHub does it, this option
                        was added to improve support for GitLab- flavored
                        markdown.


```

</details>

#### More detail on image caching paths:

As mentioned above, any image referenced in the markdown file is stored locally and
referenced using a root-relative hyperlinks in the generated html. How the converter
guesses the location of the image is shown in the following table, with the type of imagelink noted on the top and the type of input markdown noted on the left:

|                                     | `https://` or `http://` | abs. filepath                                             | rel. filepath                                                                                 | starting with `/` (e.g. `/imagedir/image.png`) | not starting with `/` (e.g. `imagedir/image.png`) |
| ----------------------------------- | ----------------------- |:---------------------------------------------------------:| --------------------------------------------------------------------------------------------- | ---------------------------------------------- | ------------------------------------------------- |
| `-t file`                           | from the address        | abs. filepath                                             | rel. filepath (from where the `.md`-file lies)                                                | -                                              | -                                                 |
| `-t string`                         | from the address        | abs.filepath, but needs confirmation for security reasons | rel. filepath (to where the tool is called from), but needs confirmation for security reasons | -                                              | -                                                 |
| `username/repo/dir/file.md -t repo` | from the address        | -                                                         | -                                                                                             | `username/repo/imagedir/image.png`             | `username/repo/dir/imagedir/image.png`            |
| `https://foo.com/bar/baz.md -t web` | from the address        | -                                                         | -                                                                                             | `https://foo.com/image.png`                    | `https://foo.com/bar/image.png`                   |

<!--

## Demonstration

I added the following demonstration, whose files where created from the root directory of this projects directory, which relates to the root directory of the site I am hosting them on:

| generated with:                                                                                                                                                                         | view:                                                                                   | demonstrates what:                                                                                                                        | notes:                                                                                                                                                                                                                                                   |
| ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------| --------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| gh-md-to-html github-flavored-markdown-to-html/README.md -d github-flavored-markdown-to-html/docs -c github-flavored-markdown-to-html/docs/css -f "test footer <3"                      | [here](https://phseiff.com/github-flavored-markdown-to-html/docs/README.html)           | html (+footer)                                                                                                                            |                                                                                                                                                                                                                                                          |
| gh-md-to-html github-flavored-markdown-to-html/README.md -n README-darkmode.html -d github-flavored-markdown-to-html/docs -c github-flavored-markdown-to-html/docs/css -r true          | [here](https://phseiff.com/github-flavored-markdown-to-html/docs/README-darkmode.html)  | html (without a footer) and that the html supports embedding the darkreader .js library without showing dark formulas on dark ground etc. | I injected the following into the html: <script type="text/javascript" src="https://phseiff.com/darkreader/darkreader.js"></script><script>DarkReader.setFetchMethod(window.fetch); DarkReader.auto({brightness: 100,contrast: 90, sepia: 10});</script> |
| gh-md-to-html github-flavored-markdown-to-html/README.md -d github-flavored-markdown-to-html/docs -n print -c github-flavored-markdown-to-html/docs/css -p README.pdf                   | [here](https://phseiff.com/github-flavored-markdown-to-html/docs/README.pdf)            | Converting to pdf.                                                                                                                        |                                                                                                                                                                                                                                                          |
| gh-md-to-html github-flavored-markdown-to-html/README.md -d github-flavored-markdown-to-html/docs -n print -c github-flavored-markdown-to-html/docs/css -p README-unstyled.pdf -s false | [here](https://phseiff.com/github-flavored-markdown-to-html/docs/README-unstyled.pdf)   | Converting to pdf without styling.                                                                                                        |                                                                                                                                                                                                                                                          |
| gh-md-to-html github-flavored-markdown-to-html/docs/math_test.md -d github-flavored-markdown-to-html/docs -c github-flavored-markdown-to-html/docs/css                                  | result [here](https://phseiff.com/github-flavored-markdown-to-html/docs/math_test.html) | Formula parsing (rendering is only marginally shown since it is done by a 3rd-party-service)                                              | Markdown source (for comparison) [here](https://phseiff.com/github-flavored-markdown-to-html/docs/math-test.md)                                                                                                                                          |

I also did the following demonstrations for automated image downloading, who where all successful (Note that they where run from the parent directory of my
repository and that instructions on how to run them can be found within the test files themselves. Also note that the test not only shows that images are stored
and embedded correctly, but also that images from different files using the same name stored within the same image directory don't overwrite each other.):

| input file:                                                                                    | output file:                                                                              | demonstrates:
| ---------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------- 
| [here](https://phseiff.com/github-flavored-markdown-to-html/docs/image_test_from_file.md)      | [here](https://phseiff.com/github-flavored-markdown-to-html/docs/image_test_from_file.html)    | loading markdown from a file, which contains images from the web as well as absolute and relative file paths.
| [here](https://phseiff.com/github-flavored-markdown-to-html/docs/image_test_from_string.md)    | [here](https://phseiff.com/github-flavored-markdown-to-html/docs/image_test_from_string.html)  | loading markdown from a string, which contains images from the web as well as absolute and relative file paths.
| [here](https://phseiff.com/github-flavored-markdown-to-html/docs/image_test_from_web.md)       | [here](https://phseiff.com/github-flavored-markdown-to-html/docs/image_test_from_web.html)     | loading markdown from an url, which contains images from the web as well as absolute and relative relative paths.
| [here](https://phseiff.com/github-flavored-markdown-to-html/docs/image_test_from_repo.md)      | [here](https://phseiff.com/github-flavored-markdown-to-html/docs/image_test_fromrepo.html)     | loading markdown from an repo, which contains images from the web as well as absolute and relative file paths (within the repo).

I also added a $formula$ here ($\sum_{i\ge e^2}^{7.3}\frac{4}{5}$) to demonstrate the formula rendering (which you won't see when viewing this README directly on github since, like I said, github usually doesn't support it.)

A directory listing of these example outputs- and inputs can be found
[here](https://phseiff.com/github-flavored-markdown-to-html/docs).

## Some Notes

In case you are not happy with the margin left and right of the text, you can manually adjust it  by modifying the margin-values hardcoded in prototype.html in this repository.
An other thing to note is that, even though gh-md-to-html supports multi line formulas, you may still use one (one!) dollar sign per line without it triggering a formula, since every
formula requires two of these. However, if you use two single dollar signs in two different columns of the same row off a table, your table will break. In the end, you are always better
off properly escaping dollar signs, even though we give you the freedom not to do so on one occasion per line!

When embedding images from disk (not via an url), you should ensure that the path you load the image from does not
contain whitespaces. Otherwise, the markdown code to embed the image will be shown like any other text within the
resulting html/pdf instead of being replaced with an image. I will eventually get to change this; if you want this to
be done ASAP, feel free to drop a comment under the corresponding issue, and I will get to work on it ASAP.

-->

## Feedback

As with all of my projects, feedback (even if it is just something small like telling me your use case for my project, or telling me that you didn't like the README's structure, or telling me that you specifically liked one specific feature) is much appreciated, and helps me make this project better, even if it's something very tiny!
You can just drop an issue with your feedback, short and non-formal, or even email me if you don't want to raise an issue for some reason.
I do not plan on adding features in the future at the moment, but I am always open to fixing and tweaking existing features, documentation et cetera, and I would obviously love to hear your feature suggestions even if I do not plan on adding them in the near future.

## Me supporting you & You supporting me

I am generally very responsive when it comes to GitHub issues, and I take them very serious and try to solve them ASAP.
If you run into bugs, weird behaviors, installation errors and the like whilst using my tool, don't hesitate to [tell me in an issue](https://github.com/phseiff/github-flavored-markdown-to-html/issues/new), so I can fix the problem!

If you found this tool useful, please consider starring it on GitHub to show me your appreciation!
I would also appreciate if you told me about issues you encountered even if you managed to fix them in your own copy of the code, so I can fix them in this repo, too.

<!--

## Known Usages

This tool is already used by

* [myself](https://github.com/phseiff) (for homework assignments in pdf-format four times a week, so you can rest assured that yes, the person
  maintaining it is also using it themselves)
* [my website](https://phseiff.com) (uses it in its website builder, as detailed in [this blog post of mine](https://phseiff.com/e/why-i-like-my-website/))
* feel free to tell me via an issue if you want to be included in this list!

-->

## Further reading

* I wrote a small write-up on Reddit about gh-md-to-html, which doesn't really say anything that isn't somehow said in this README already, but might be an easier read:
  [link](https://www.reddit.com/r/Markdown/comments/lyivyg/ghmdtohtml_convert_githubflavored_markdown_to/)
* Better explanation (by me) on how to use `gh-md-to-html` for md-to-pdf conversion (under a gist about md-to-pdf conversion):
  [link](https://gist.github.com/justincbagley/ec0a6334cc86e854715e459349ab1446#gistcomment-3706145)
* Brief mention of `gh-md-to-html` in another project's documentation:
  [link](https://github.com/bearwalker/GitAtom/blob/42d84449f62f3e0880af49e8b1f3dd8f159062c6/GitAtomDocs.md#markdown-to-html)
* [A blog post about it](https://dev.to/siddharth2016/how-to-convert-markdown-to-html-using-python-4p1b) (on someone else's blog)
* If you are aware of any other mentions or discussions regarding gh-md-to-html, feel free to tell me so I can include them!

## Attribution

The icons were made by

* .md-file.icon: [Freepik](https://www.flaticon.com/authors/freepik) from [flaticon.com](https://www.flaticon.com/)

* .md-file.icon: [Freepik](https://www.flaticon.com/authors/freepik) from [flaticon.com](https://www.flaticon.com/)

* arrow-icon: [Font Awesome by Dave Gandy](https://fortawesome.github.com/Font-Awesome), licensed under
  [Creative Commons](https://en.wikipedia.org/wiki/en:Creative_Commons)
  [Attribution-Share Alike 3.0 Unported](https://creativecommons.org/licenses/by-sa/3.0/deed.en)

* GitHub-icon: [GitHub icon](https://iconscout.com/icons/github) on [Iconscout](https://iconscout.com/)
----

**DISCLAIMER**: This module is neither written by Github, nor is it endorsed with Github,
supported by Github, powered by Github or affiliated with Github. It only uses a public
API provided by Github as well as a .css-file licensed by Github under the MIT license.
