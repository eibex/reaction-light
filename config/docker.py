"""
MIT License

Copyright (c) 2019-present eibex

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""


import os
from shutil import copy
import configparser


def setup(directory):
    token = os.environ.get("TOKEN")
    bot_folder = os.path.dirname(directory)

    if token and not os.path.isfile(f"{bot_folder}/config/config.ini"):
        if os.path.isdir(f"{bot_folder}/config/config.ini"):
            if not os.listdir(f"{bot_folder}/config/config.ini"):
                # If config.ini was created as a directory by mistake (e.g. Unraid), delete it (only if empty)
                os.remove(f"{bot_folder}/config/config.ini")

        config = configparser.ConfigParser()
        config.read(f"{bot_folder}/config/config.ini.sample")
        config["server"]["token"] = token
        with open(f"{bot_folder}/config/config.ini", "w") as f:
            config.write(f)
