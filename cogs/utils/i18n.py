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

import configparser
import json
import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional


class BaseResponse(ABC):
    def __init__(self, directory, global_language):
        self.directory = directory
        self.global_language = global_language
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

    def _get_translation(self, language: str, item: str):
        try:
            response = self.responses[language][item]
        except KeyError:
            response = self.responses["en-gb"][item]
            print(
                f"Could not find a translation ({language}) for the requested i18n item: {item}. Please file an issue on GitHub."
            )
        return response

    @abstractmethod
    def get(self, item: str, *, guild_id: Optional[int] = None) -> str:
        ...

class Response(BaseResponse):
    def __init__(self, bot, directory, global_language):
        self.bot = bot
        super().__init__(directory, global_language)

    def get(self, item, *, guild_id: Optional[int] = None):
        if guild_id is not None:
            language = self.bot.db.get_language(guild_id)
            language = language if language else self.global_language
        else:
            language = self.global_language
        
        return self._get_translation(language, item)
    
class StaticResponse(BaseResponse):
    """Get language keys without the context of a bot instance."""
    def __init__(self):
        directory = Path(__file__).parents[2]

        config = configparser.ConfigParser()
        config.read(f"{directory}/config.ini")

        language = str(config.get("server", "language", fallback="en-gb"))

        super().__init__(f"{directory}/i18n", language)

    def get(self, item, *, guild_id: Optional[int] = None):
        return self._get_translation(self.global_language, item)