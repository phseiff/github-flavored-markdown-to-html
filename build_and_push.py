"""
This updated help.txt (the help text shown by the program), updates README-md to include said help text, commits and
pushes everything.
"""

import subprocess
import sys

for command in [
    "sudo python3 setup.py install",
    "gh-md-to-html --help",
    "git add *",
    "git commit -m '" + sys.argv[1] + "'",
    "git push",
]:
    process = subprocess.Popen(command.split(), stdout=subprocess.PIPE)
    output, error = process.communicate()
    if command.startswith("gh-md-to-html"):
        print("{" + str(output, encoding="UTF-8") + "}")
