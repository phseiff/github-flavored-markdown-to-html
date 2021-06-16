"""
This updated help.txt (the help text shown by the program), updates README-md to include said help text, commits and
pushes everything. Call with sudo!
"""

import subprocess
import sys
from css_html_js_minify import process_single_css_file

process_single_css_file("src/github-css.css")

with open("setup.py") as setup_file:
    setup_file_content = setup_file.read()
    version = setup_file_content.split("version='")[1].split("'")[0]
    assert (len(version.split(".")) == 3
            and version.split(".")[0].isnumeric()
            and version.split(".")[1].isnumeric()
            and version.split(".")[2].isnumeric())
    version = "v" + version
    tags = subprocess.getoutput("git tag --list").split()
    add_version = version not in tags

for command in [
    "python3 -m pip uninstall -y gh-md-to-html",
    "sudo python3 -m pip uninstall -y gh-md-to-html",
    "sudo python3 setup.py install",
    "gh-md-to-html --help",
    "git add *",
    "git commit -m \"" + sys.argv[1] + "\"",
    ("git tag -a " + version + " -m \"" + sys.argv[1] + "\"") if add_version else "echo 'no new version to be tagged.'",
    "git push",
    "git push --tags",
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
