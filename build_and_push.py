"""
This updated help.txt (the help text shown by the program), updates README-md to include said help text, commits and
pushes everything. Call with sudo!
"""

import subprocess
import sys
from css_html_js_minify import process_single_css_file

process_single_css_file("src/github-css.css")

for command in [
    "python3 -m pip uninstall -y gh-md-to-html",
    "sudo python3 -m pip uninstall -y gh-md-to-html",
    "sudo python3 setup.py install",
    "gh-md-to-html --help",
    "git add *",
    "git commit -m \"" + sys.argv[1] + "\"",
    "git push",
    "pip3 install ."
]:
    print("command:", command)
    process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE)
    output, error = process.communicate()
    if command.startswith("gh-md-to-html"):
        print("help text:", str(output, encoding="UTF-8"))
        with open("src/help.txt", "wb") as help_text_file:
            help_text_file.write(output)
            with open("README-raw.md", "r") as raw_readme_file:
                with open("README.md", "w") as readme_file:
                    readme_file.write(raw_readme_file.read().replace("{help}", str(output, encoding="UTF-8")))
