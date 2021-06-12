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

    def get(self, item):
        try:
            response = self.responses[self.language][item]
        except KeyError:
            response = self.responses["en-gb"][item]
            print(
                f"Could not find a translation ({self.language}) for the requested i18n item: {item}. Please file an issue on GitHub."
            )
        response = response.replace("{prefix}", self.prefix)
        return response
