# addressbook.py - Address book
#
# Stephen Fegan - sfegan@gmail.com - 2017-02-27
#
# This program is motivated by the author's experience of SMSBackup+ under
# Android, an excellent application to backup SMS/MMS messages to GMail where
# they can be searched etc. This little program tries to do the same thing for
# messages / conversations stored in the iMessage database.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import sqlite3
import phonenumbers
import os

ab_base_dir = '~/Library/Application Support/AddressBook'
ab_source_dir = 'Sources'
ab_db_file = 'AddressBook-v22.abcddb'

class AddressBook:
    def __init__(self, my_identity, default_country_code=None):
        self._me = my_identity
        self._cc = default_country_code or 'FR'

    def me(self):
        return self._me

    def read_address_db(self, filename = ab_base_dir + '/' + ab_db_file):
        ab = dict()
        db = sqlite3.connect('file:'
            + os.path.expanduser(filename)
            + '?mode=ro', uri=True)
        query = db.cursor()

        for entry in query.execute('SELECT Z_PK, ZFIRSTNAME, ZMIDDLENAME, '
                'ZLASTNAME, ZNICKNAME, ZORGANIZATION FROM ZABCDRECORD'):
            ab[entry[0]] = dict(
                owner_id                = entry[0],
                first_name              = entry[1],
                middle_name             = entry[2],
                last_name               = entry[3],
                nick_name               = entry[4],
                organization            = entry[5],
                phone_numbers           = dict(),
                email_addresses         = dict()
                )

        for entry in query.execute('SELECT ZOWNER, ZORDERINGINDEX, '
                'ZFULLNUMBER FROM ZABCDPHONENUMBER'):
            ph = phonenumbers.parse(entry[2], self._cc)
            ph = '+' + str(ph.country_code) + str(ph.national_number)
            ab[entry[0]]['phone_numbers'][entry[1]] = ph

        for entry in query.execute('SELECT ZOWNER, ZORDERINGINDEX, '
                'ZADDRESS FROM ZABCDEMAILADDRESS'):
            ab[entry[0]]['email_addresses'][entry[1]] = entry[2]
        return ab

    def lookup_email(self, handle):
        return handle['contact'] + ' <' + handle['contact'] + '@unknown.email.local>'

    def lookup_name(self, handle):
        return handle['contact']
