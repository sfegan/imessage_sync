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

class AddressBook:
    def __init__(self, me):
        self._me = me

    def me(self):
        return self._me

    def lookup_email(self, handle):
        return handle['contact'] + ' <' + handle['contact'] + '@unknown.email.local>'

    def lookup_name(self, handle):
        return handle['contact']
