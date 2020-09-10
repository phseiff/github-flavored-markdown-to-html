"""
This updated help.txt (the help text shown by the program), updates README-md to include said help text, commits and
pushes everything.
"""

import subprocess
import sys

for command in [
    "sudo python3 uninstall gh-md-to-html",
    "sudo python3 setup.py install",
    "gh-md-to-html --help",
    "git add *",
    "git commit -m '" + sys.argv[1] + "'",
    "git push",
]:
    process = subprocess.Popen(command.split(), stdout=subprocess.PIPE)
    output, error = process.communicate()
    if command.startswith("gh-md-to-html"):
        with open("src/help.txt", "wb") as help_text_file:
            help_text_file.write(output)
            with open("README-raw.md", "r") as raw_readme_file:
                with open("README.md", "w") as readme_file:
                    readme_file.write(raw_readme_file.read().replace("{help}", str(output, encoding="UTF-8")))
        print("{" + str(output, encoding="UTF-8") + "}")
