"""
MIT License

Copyright (c) 2019-2021 eibex

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


import aiohttp


async def get_latest():
    # Get latest version string from GitHub
    async with aiohttp.ClientSession() as cs:
        async with cs.get(
            "https://raw.githubusercontent.com/eibex/reaction-light/master/.version"
        ) as r:
            latest = await r.text()

    return latest.rstrip("\n").rstrip("\r")


async def check_for_updates(version):
    # Get latest version from GitHub repo and checks it against the current one
    latest = await get_latest()
    if latest > version:
        return latest

    return False


async def latest_changelog():
    # Get the changes for the latest version
    async with aiohttp.ClientSession() as cs:
        async with cs.get(
            "https://raw.githubusercontent.com/eibex/reaction-light/master/CHANGELOG.md"
        ) as r:
            changelog = await r.text()

    changelog = changelog.split("###")[1].rstrip(
        "\n"
    )  # Only get the latest version changes
    changelog = changelog[
        changelog.index("-") :
    ]  # Remove every character up to the first bullet point
    changelog += "\n\n[View more](https://github.com/eibex/reaction-light/blob/master/CHANGELOG.md)"

    return changelog
