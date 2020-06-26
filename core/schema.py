"""
MIT License

Copyright (c) 2019-2020 eibex

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


import sqlite3


class SchemaHandler:
    def __init__(self, database):
        self.database = database
        self.version = self.version_check()

    def version_check(self):
        conn = sqlite3.connect(self.database)
        cursor = conn.cursor()
        cursor.execute("SELECT version FROM dbinfo;")
        version = cursor.fetchall()
        cursor.close()
        conn.close()
        if not version:
            self.set_version(0)
            self.version_check()
            return
        version = version[0][0]
        return version

    def update(self):
        if self.version == 0:
            self.zero_to_one()

    def set_version(self, version):
        conn = sqlite3.connect(self.database)
        cursor = conn.cursor()
        if version > 0:
            previous = version - 1
            cursor.execute(
                "UPDATE dbinfo SET version = ? WHERE version = ?;", (version, previous)
            )
        else:
            cursor.execute("INSERT INTO dbinfo(version) values(?);", (version,))
        conn.commit()
        cursor.close()
        conn.close()
        self.version = version

    def zero_to_one(self):
        conn = sqlite3.connect(self.database)
        cursor = conn.cursor()
        cursor.execute("ALTER TABLE messages ADD COLUMN 'guild_id' INT;")
        conn.commit()
        cursor.close()
        conn.close()
        self.set_version(1)
