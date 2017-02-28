# imessage_sync.py - Backup messages from iMessage under Mac OS to IMAP
#
# Stephen Fegan - sfegan@gmail.com - 2017-01-06
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

import imaplib
import imaplib_connect
import imessage_to_mime
import re

class IMessageSync:
    def __init__(self, connection, addressbook, mailbox='iMessage', verbose=False):
        self.connection   = connection
        self.addressbook  = addressbook
        self.mailbox      = mailbox
        self.verbose      = verbose

    def mailbox_size(self):
        resp, data = self.connection.status('iMessage','(MESSAGES)')
        if(resp != 'OK'):
            return None
        mb, el, n = re.match(r'"(.*)" \((.*) (.*)\)',data[0].decode()).groups()
        return int(n)

    def connect_to_mailbox(self):
        resp, data = self.connection.create(self.mailbox)
        resp, data = self.connection.select(self.mailbox)
        if(resp != 'OK'):
            print(b.decode())
            return False
        return True

    def fetch_all_guids(self, block_size=1000):
        if(not self.connect_to_mailbox()):
            return None
        i = 0
        guids = set()
        while(True):
            qrange = '%d:%d'%(i+1,i+block_size)
            qfilter = 'BODY.PEEK[HEADER.FIELDS (%s)]'%imessage_to_mime.Xheader_guid
            #print(qrange, qfilter)
            resp, data = self.connection.fetch(qrange, qfilter)
            #print (resp, len(data))
            if(resp != 'OK'):
                print(resp, data[0].decode())
                return None
            if(data == [None]):
                break
            for line in data:
                if(type(line) == tuple):
                    guid = re.match(r'^.*:\s+([^\s]*)\s*$',line[1].decode())
                    if(guid):
                        guids.add(guid.groups()[0])
            i += block_size
        return guids

    def upload_message(self, message):
        email_msg = imessage_to_mime.get_email(message, self.addressbook)
        email_str = email_msg.as_bytes()
        if self.verbose:
            to_from = 'from'
            print('Uploading message %s %s, index: %d, size: %d'%( \
                'to' if message['is_from_me'] else 'from',
                message['handle']['contact'] if message.get('handle') else 'unknown',
                message['message_rowid'],
                len(email_str)))
        resp, data = self.connection.append(self.mailbox,
            '(\\Seen)' if message['is_read'] else None,
            imaplib.Time2Internaldate(message['date']), email_str)
        if self.verbose:
            print('  ',resp,data)
        return resp == 'OK'

    def upload_all_messages(self, messages):
        for id in messages.keys():
            message = messages[id]
            if(not imessage_to_mime.is_valid(message)):
                continue
            self.upload_message(message)
            imessage_to_mime.update_chat_thread_ids(message)
