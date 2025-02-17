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

import disnake
import configparser


class Config:
    def __init__(self, directory):
        self.directory = directory
        self.config = configparser.ConfigParser()
        self.load()

    def load(self):
        # TODO Expose as public attributes
        self.config.read(f"{self.directory}/config/config.ini")
        self.token = str(self.config.get("server", "token"))
        self.botname = str(self.config.get("server", "name", fallback="Reaction Light"))
        self.botcolour = disnake.Colour(int(self.config.get("server", "colour", fallback="0xffff00"), 16))
        system_channel = self.config.get("server", "system_channel", fallback=None)
        self.system_channel = int(system_channel) if system_channel else None
        self.logo = str(self.config.get("server", "logo", fallback=None))
        self.language = str(self.config.get("server", "language", fallback="en-gb"))

    def update(self, section, option, value):
        self.config[section][option] = value
        with open(f"{self.directory}/config/config.ini", "w") as configfile:
            self.config.write(configfile)
        self.load()

    def get(self, section, option, fallback=None):
        return self.config.get(section, option, fallback=fallback)
