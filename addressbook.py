# addressbook.py - Address book - lookup names and emails for phobe numbers
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
import glob
import imessage_sync_config

sys_ab_base_dir = '~/Library/Application Support/AddressBook'
sys_ab_source_dir = 'Sources'
sys_ab_db_file = 'AddressBook-v22.abcddb'

class AddressBook:
    def __init__(self, config=None, ab_base_dir=None):
        # Read the config file
        if(not config):
            config = imessage_sync_config.get_config()

        self._me = config.get('identity', 'address')
        self._cc = config.get('identity', 'default_country', fallback='US')
        self._ab_base_dir = ab_base_dir or \
            config.get('address_book', 'base_dir', fallback=sys_ab_base_dir)
        self._ab_source_dir = \
            config.get('address_book', 'source_dir', fallback=sys_ab_source_dir)
        self._ab_db_file = \
            config.get('address_book', 'db_file', fallback=sys_ab_db_file)
        self._lu = self.make_lookup_table()

    def me(self):
        return self._me

    def read_address_db(self, filename = None):
        if(not filename):
            filename = self._ab_base_dir + '/' + self._ab_db_file
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

    def glob_address_book_filenames(self):
        files = [ os.path.expanduser(self._ab_base_dir) + '/' + self._ab_db_file ]
        for f in glob.glob(os.path.expanduser(self._ab_base_dir) + '/' + self._ab_source_dir + '/*/' + self._ab_db_file):
            files.append(f)
        return files

    def make_lookup_table(self):
        lu = dict()
        for f in self.glob_address_book_filenames():
            ab = self.read_address_db(f)
            for iab in ab:
                a = ab[iab]
                email = None
                if a['email_addresses']:
                    ea = a['email_addresses']
                    email = ea[min(ea)]
                name = None
                nc = []
                if(a['first_name']):
                    nc.append(a['first_name'])
                if(a['middle_name']):
                    nc.append(a['middle_name'])
                if(a['last_name']):
                    nc.append(a['last_name'])
                if(not nc and a['nick_name']):
                    nc.append(a['nick_name'])
                if(not nc and a['organization']):
                    nc.append(a['organization'])
                if(nc):
                    name = ' '.join(nc)
                if(name is None and email is None):
                    continue
                for ipn in a['phone_numbers']:
                    pn = a['phone_numbers'][ipn]
                    if(pn not in lu):
                        lu[pn] = dict()
                    if email:
                        lu[pn]['email'] = email
                    if name:
                        lu[pn]['name'] = name
                for iea in a['email_addresses']:
                    ea = a['email_addresses'][iea]
                    if(ea not in lu):
                        lu[ea] = dict()
                    lu[ea]['email'] = email or ea
                    if name:
                        lu[ea]['name'] = name
        return lu

    def lookup_email(self, handle):
        c = handle['contact']
        email = self._lu.get(c, dict()).get('email') or c+'@unknown.email.local'
        return self.lookup_name(handle) + ' <' + email + '>'

    def lookup_name(self, handle):
        c = handle['contact']
        return self._lu.get(c, dict()).get('name') or c
