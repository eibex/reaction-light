import re
from typing import Dict, List
import json
import attr
import os
import pytest


PARAMETER_REGEX = r"\{(\w+)\}"


@attr.s(auto_attribs=True, slots=True)
class StringLimitations:
    max_length: int
    parameters: List[str]

    @classmethod
    def from_json(cls, _json: dict) -> "StringLimitations":
        return cls(max_length=_json["max_length"], parameters=_json["parameters"])


@attr.s(auto_attribs=True, slots=True)
class StringData:
    length: int
    parameters: List[str]

    @classmethod
    def from_string(cls, string: str) -> "StringData":
        return cls(length=len(string), parameters=re.findall(PARAMETER_REGEX, string))


with open("tests/language_structure.json") as f:
    language_structure = json.load(f)

LANGUAGE_STRUCTURE: Dict[str, StringLimitations] = {k: StringLimitations.from_json(v) for k, v in language_structure.items()}


def get_language_packs() -> List[str]:
    i18n_dir = os.path.join(os.path.dirname(__file__), "..", "i18n")
    language_packs = []
    for _, _, files in os.walk(i18n_dir):
        for file in files:
            if file.endswith(".json"):
                language_packs.append(file)
    return language_packs


def get_language_pack(language_pack: str):
    i18n_dir = os.path.join(os.path.dirname(__file__), "..", "i18n")
    with open(os.path.join(i18n_dir, language_pack)) as f:
        _json = json.load(f)
    return _json


def pytest_generate_tests(metafunc):
    # TODO: Is it possible to group language_string to each language_pack?
    if "language_pack" in metafunc.fixturenames:
        if "language_string" in metafunc.fixturenames:
            language_packs = get_language_packs()
            metafunc.parametrize(
                ["language_pack", "language_string"],
                [(lp, ls) for lp in language_packs for ls in get_language_pack(lp).keys() if ls in LANGUAGE_STRUCTURE],
            )
        else:
            metafunc.parametrize("language_pack", get_language_packs())


class TestLanguagePack:
    def test_validate_json(self, language_pack):
        get_language_pack(language_pack)

    def test_all_strings(self, language_pack):
        if set(get_language_pack(language_pack).keys()) != set(LANGUAGE_STRUCTURE.keys()):
            pytest.skip(f"{language_pack}: {set(LANGUAGE_STRUCTURE.keys() - set(get_language_pack(language_pack).keys()))}")


class TestLanguageString:
    @staticmethod
    def get_string_data(language_pack: str, language_string: str):
        return StringData.from_string(get_language_pack(language_pack)[language_string])

    def test_length(self, language_pack: str, language_string: str):
        length = self.get_string_data(language_pack, language_string).length
        max_length = LANGUAGE_STRUCTURE[language_string].max_length
        assert length <= max_length, f"Must be {max_length} or fewer in length, got {length}."

    def test_parameters(self, language_pack: str, language_string: str):
        parameters = self.get_string_data(language_pack, language_string).parameters
        wanted_parameters = LANGUAGE_STRUCTURE[language_string].parameters
        assert parameters == wanted_parameters, f"Must have parameters {wanted_parameters}, got {parameters}."
