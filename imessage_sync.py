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
import imessage_sync_config
import imessage_db_reader
import imessage_to_mime
import file_finder
import addressbook
import re
import time
import calendar
import os
import os.path
import email.utils

class IMessageSync:
    def __init__(self, connection, addressbook, config=None, verbose=False, sync_time=time.time()):
        if(not config):
            config = imessage_sync_config.get_config()
        self.connection   = connection
        self.addressbook  = addressbook
        self.mailbox      = config.get('server', 'mailbox', fallback='iMessage')
        self.max_attach   = int(config.get('server', 'max_attachment_size', fallback=25000000))
        self.verbose      = verbose
        self.mailbox_size = None
        self.sync_time    = sync_time
        if(self.connection and not self.connect_to_mailbox()):
            return None

    def get_mailbox_size(self):
        resp, data = self.connection.status(self.mailbox,'(MESSAGES)')
        if(resp != 'OK'):
            return None
        mb, el, n = re.match(r'"(.*)" \((.*) (.*)\)',data[0].decode()).groups()
        self.mailbox_size = int(n)
        return self.mailbox_size

    def connect_to_mailbox(self):
        resp, data = self.connection.create(self.mailbox)
        resp, data = self.connection.select(self.mailbox)
        if(resp != 'OK'):
            print(data[0].decode())
            return False
        self.mailbox_size = int(data[0].decode())
        return True

    def fetch_all_guids(self, block_size=1000):
        i = 0
        guids = set()
        print("Querying previously uploaded messages",end='',flush=True)
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
            print('.',end='',flush=True)
            i += block_size
        print('',flush=True)
        return guids

    def fetch_all_guids_since(self, start_date, block_size=1000):
        start_date = time.strftime('%d-%b-%Y',time.gmtime(start_date-86400))
        print('Querying messages uploaded since %s'%start_date,end='',flush=True)
        resp, data = self.connection.search(None, 'SENTSINCE %s'%start_date)
        if(resp != 'OK'):
            print('',flush=True)
            print(resp, data[0].decode())
            return None
        if(not data[0]):
            print('',flush=True)
            return set()
        first_id = None
        last_id = None
        all_id = []
        num_id = 0
        for cur_id in map(int, data[0].decode().split(' ')):
            if(not first_id):
                first_id = cur_id
            else:
                if(cur_id != last_id+1):
                    all_id.append('%d'%first_id if first_id==last_id else \
                        '%d:%d'%(first_id,last_id))
                    first_id = cur_id
            last_id = cur_id
            num_id += 1
            if(num_id == block_size):
                all_id.append('%d'%first_id if first_id==last_id else \
                    '%d:%d'%(first_id,last_id))
                first_id = None
                last_id = None
                num_id = 0
        if(first_id):
            all_id.append('%d'%first_id if first_id==last_id else \
                '%d:%d'%(first_id,last_id))
        guids = set()
        for qrange in all_id:
            qfilter = 'BODY.PEEK[HEADER.FIELDS (%s)]'%imessage_to_mime.Xheader_guid
            #print(qrange, qfilter)
            resp, data = self.connection.fetch(qrange, qfilter)
            #print (resp, len(data))
            if(resp != 'OK'):
                print(resp, data[0].decode())
                return None
            for line in data:
                if(type(line) == tuple):
                    guid = re.match(r'^.*:\s+([^\s]*)\s*$',line[1].decode())
                    if(guid):
                        guids.add(guid.groups()[0])
            print('.',end='',flush=True)
        print('',flush=True)
        return guids

    def fetch_internal_dates(self, start_index=-100, end_index=0):
        if(start_index < 0):
            start_index += self.mailbox_size
            end_index += self.mailbox_size
        elif(start_index < 0):
            end_index += self.mailbox_size
        start_index = min(max(start_index, 0), self.mailbox_size)
        end_index = min(max(end_index, 0), self.mailbox_size)
        if(start_index > end_index):
            raise Exception("start_index must be smaller than end_index")
        qrange = '%d:%d'%(start_index,end_index)
        qfilter = 'INTERNALDATE'
        resp, data = self.connection.fetch(qrange, qfilter)
        if(resp != 'OK'):
            print(resp, data[0].decode())
            return None
        internal_dates = []
        for line in data:
            date = re.match(r'^.*\s+\(INTERNALDATE "(.*)"\)$',line.decode())
            if(date):
                internal_dates.append(
                    time.mktime(email.utils.parsedate(date.groups()[0])))
        return internal_dates

    def guess_last_sync_time(self):
        message_dates = self.fetch_internal_dates()
        return max(message_dates) if message_dates else 0

    def message_summary(self, message, before_gid = None):
        address = 'unknown'
        if(message['is_from_me']):
            address = imessage_to_mime.get_chat_names(message['chat'], self.addressbook)
        elif(message.get('handle')):
            address = imessage_to_mime.get_handle_name(message['handle'], self.addressbook)
        s = 'to' if message['is_from_me'] else 'from'
        s += ' ' + address
        s+= ' (' + time.strftime('%Y-%m-%d %H:%M:%S',time.gmtime(message['date'])) + ')'
        if before_gid:
            s+= ', ' + before_gid
        s += ', index: %s'%str(message['message_rowid'])
        s += ', guid: ' + message['guid']
        return s

    def upload_message(self, message, in_reply_to = dict()):
        emails = imessage_to_mime.get_email(message, self.addressbook, in_reply_to,
            max_attachment_size = self.max_attach, sync_time = self.sync_time)
        if(type(emails) is not list):
            emails = [ emails ]
        for iemail, email_msg in enumerate(emails):
            email_str = email_msg.as_bytes()
            if True or self.verbose:
                info = 'size: %d'%len(email_str)
                if(len(emails)>1):
                    info = 'frag: %d/%d, '%(iemail+1,len(emails)) + info
                print('Uploading message',
                    self.message_summary(message, info))
            resp, data = self.connection.append(self.mailbox,
                '(\\Seen)' if message['is_read'] or message['is_from_me'] else None,
                imaplib.Time2Internaldate(message['date']), email_str)
            if self.verbose:
                print('  ',resp,data)
            if(resp == 'OK'):
                self.mailbox_size += 1
        return True, 'OK'

    def upload_all_messages(self, messages, guids_to_skip = set(), do_upload = True):
        in_reply_to = dict()
        for id in sorted(messages, key=lambda im: messages[im]['date']):
            message = messages[id]
            if(not imessage_to_mime.is_valid(message)):
                continue
            if(not guids_to_skip or message['guid'] not in guids_to_skip):
                if(do_upload):
                    good, status = self.upload_message(message, in_reply_to)
                elif True or self.verbose:
                    print('Not uploading message', self.message_summary(message))
            elif self.verbose:
                print('Skipping message', self.message_summary(message))
            imessage_to_mime.update_chat_thread_ids(message, self.addressbook, in_reply_to)

    def print_all_messages(self, messages):
        in_reply_to = dict()
        for id in sorted(messages, key=lambda im: messages[im]['date']):
            message = messages[id]
            print(self.message_summary(message))

    def full_message_email(self, message, in_reply_to = dict()):
        emails = imessage_to_mime.get_email(message, self.addressbook, in_reply_to,
            max_attachment_size = self.max_attach, sync_time = self.sync_time)
        if(type(emails) is not list):
            emails = [ emails ]
        emails_str = []
        for iemail, email_msg in enumerate(emails):
            email_str = email_msg.as_bytes()
            emails_str.append(email_str)
        return emails_str

def num_attachments(m):
    nfound = 0
    for a in m['attachments']:
        fn = a['filename']
        if(fn and os.path.isfile(fn)):
            nfound += 1
    return nfound

def best_message_copy(m1, m2):
    return m1 if num_attachments(m1)>=num_attachments(m2) else m2

def get_all_messages(finder_or_base_path = None):
    if(type(finder_or_base_path) is list):
        all_guid = dict()
        for ifobp, fobp in enumerate(finder_or_base_path):
            db = imessage_db_reader.IMessageDBReader(finder_or_base_path = fobp)
            messages = db.get_messages()
            for im, m in messages.items():
                m['message_rowid'] = str(ifobp)+'_'+str(im)
                if(m['guid'] not in all_guid):
                    all_guid[m['guid']] = m
                else:
                    all_guid[m['guid']] = best_message_copy(all_guid[m['guid']], m)
        all_messages = dict()
        for m in all_guid.values():
            all_messages[m['message_rowid']] = m
        return all_messages
    else:
        db = imessage_db_reader.IMessageDBReader(finder_or_base_path = finder_or_base_path)
        return db.get_messages()

def verify_all_messages(finder_or_base_path = None, verbose = False):
    config = imessage_sync_config.get_config()
    x = get_all_messages(finder_or_base_path = finder_or_base_path)
    a = addressbook.AddressBook(config = config)
    sync = IMessageSync(None,a)
    nfound = 0
    nmissing = 0
    for ix in sorted(x, key=lambda ix: x[ix]['date']):
        if(verbose):
            print('Verifying message', sync.message_summary(x[ix]))
        all_found = True
        for ia in x[ix]['attachments']:
            fn = ia['filename']
            if(fn):
                if os.path.isfile(fn):
                    nfound += 1
                    if(verbose):
                        print('- OK :', fn)
                else:
                    if(all_found and not verbose):
                        print('Verifying message', sync.message_summary(x[ix]))
                    nmissing + 1
                    all_found = False
                    print('- NOT FOUND :', fn)
            else:
                if(all_found and not verbose):
                    print('Verifying message', sync.message_summary(x[ix]))
                nmissing += 1
                all_found = False
                print('- NO PATH FOUND :', ia)
    print('Found:', nfound, '; not found:', nmissing)

def sync_all_messages(finder_or_base_path = None, verbose = True,
        start_date = None, stop_date = None, do_upload = True):
    config = imessage_sync_config.get_config()
    sync_time = time.time()
    x = get_all_messages(finder_or_base_path = finder_or_base_path)
    if(start_date):
        xx = dict()
        for ix in filter(lambda ix: x[ix]['date']>=start_date, x):
            xx[ix] = x[ix]
        x = xx
    if(stop_date):
        xx = dict()
        for ix in filter(lambda ix: x[ix]['date']<=stop_date, x):
            xx[ix] = x[ix]
        x = xx
    if(len(x) == 0):
        print('Found no messages in iMessages database(s), exiting')
        return
    print('Found %d messages in iMessages database(s)'%len(x))
    c = imaplib_connect.open_connection(config = config, verbose = verbose)
    a = addressbook.AddressBook(config = config)
    sync = IMessageSync(c,a,verbose=verbose,sync_time=sync_time)
    guids_to_skip = sync.fetch_all_guids_since( \
        min(map(lambda ix: ix['date'], x.values())))

    nupload = 0
    for id in sorted(x, key=lambda im: x[im]['date']):
        message = x[id]
        if(not imessage_to_mime.is_valid(message)):
            continue
        if(not guids_to_skip or message['guid'] not in guids_to_skip):
            nupload += 1
    if(nupload == 0):
        print('No new messages to upload, exiting')
        return
    print('Number of new messages to upload : %d'%nupload)

    sync.upload_all_messages(x, guids_to_skip, do_upload=do_upload)

def print_all_messages(finder_or_base_path = None):
    config = imessage_sync_config.get_config()
    x = get_all_messages(finder_or_base_path = finder_or_base_path)
    a = addressbook.AddressBook(config = config)
    sync = IMessageSync(None,a)
    sync.print_all_messages(x)

def recipient_histogram(finder_or_base_path = None):
    config = imessage_sync_config.get_config()
    x = get_all_messages(finder_or_base_path = finder_or_base_path)
    a = addressbook.AddressBook(config = config)
    sync = IMessageSync(None,a)
    count = dict()
    for ix in x:
        if(x[ix]['chat']):
            n = imessage_to_mime.get_chat_names(x[ix]['chat'], a)
            count[n] = count.get(n,0) + 1
    return count
