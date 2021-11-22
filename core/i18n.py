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
import json


class Response:
    def __init__(self, directory, language, prefix):
        self.directory = directory
        self.language = language
        self.prefix = prefix
        self.responses = self.load()

    def load(self):
        data = {}
        for file in os.listdir(self.directory):
            if file.endswith(".json"):
                with open(f"{self.directory}/{file}", encoding="utf-8") as f:
                    data[file.replace(".json", "")] = json.load(f)
        return data

    def languages(self):
        available_languages = {}
        for language in self.responses:
            long_language = self.responses[language]["LANGUAGE"]
            available_languages[long_language] = language
        return available_languages

    def get(self, item):
        try:
            response = self.responses[self.language][item]
        except KeyError:
            response = self.responses["en-gb"][item]
            print(
                f"Could not find a translation ({self.language}) for the requested i18n item: {item}. Please file an issue on GitHub."
            )
        return response
