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
import imessage_db_reader
import imessage_to_mime
import addressbook
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

    def upload_message(self, message, in_reply_to = dict(), upload_max=25000000):
        while(True):
            email_msg = imessage_to_mime.get_email(message, self.addressbook, in_reply_to)
            email_str = email_msg.as_bytes()
            if(upload_max is None or upload_max<=0 or len(email_str)<upload_max):
                break
            amaxsize = None
            maxsize = None
            for ia, a in enumerate(message['attachments']):
                if(maxsize is None or a['total_bytes']>maxsize):
                    maxsize = a['total_bytes']
                    amaxsize = a
            action = 'terminating'
            if(amaxsize):
                action = 'deleting attachment %s'%amaxsize['filename']
            print('Message %s %s, index: %d, size: %d, exceeds limit: %s'%( \
                'to' if message['is_from_me'] else 'from',
                message['handle']['contact'] if message.get('handle') else 'unknown',
                message['message_rowid'],
                len(email_str), action))
            if(amaxsize):
                amaxsize['suppress'] = True
            else:
                return false, 'TOOBIG'
            # try again!

        if self.verbose:
            print('Uploading message %s %s, index: %d, size: %d'%( \
                'to' if message['is_from_me'] else 'from',
                message['handle']['contact'] if message.get('handle') else 'unknown',
                message['message_rowid'],
                len(email_str)))
        resp, data = self.connection.append(self.mailbox,
            '(\\Seen)' if message['is_read'] or message['is_from_me'] else None,
            imaplib.Time2Internaldate(message['date']), email_str)
        if self.verbose:
            print('  ',resp,data)
        if resp == 'OK':
            return True, resp
        else:
            if(len(data)>0):
                data0 = data[0].decode()
                g = re.match(r'\[(.*)\].*',data0)
                if(g):
                    return False, g.groups()[0]
                else:
                    return False, data0;
        return False, resp

    def upload_all_messages(self, messages, guids_to_skip = set()):
        in_reply_to = dict()
        for id in messages.keys():
            message = messages[id]
            if(not imessage_to_mime.is_valid(message)):
                continue
            if(not guids_to_skip or message['guid'] not in guids_to_skip):
                good, status = self.upload_message(message, in_reply_to)
            elif self.verbose:
                print('Skipping message %s %s, index: %d'%( \
                    'to' if message['is_from_me'] else 'from',
                    message['handle']['contact'] if message.get('handle') else 'unknown',
                    message['message_rowid']))
            imessage_to_mime.update_chat_thread_ids(message, in_reply_to)

def get_all_messages():
    db = imessage_db_reader.IMessageDBReader()
    return db.get_messages()

def sync_all_messages(verbose = True):
    x = get_all_messages()
    c, me = imaplib_connect.open_connection(verbose = verbose)
    a = addressbook.AddressBook(me)
    sync = IMessageSync(c,a,verbose=verbose)
    guids_to_skip = sync.fetch_all_guids()
    sync.upload_all_messages(x, guids_to_skip)
    return x, sync
