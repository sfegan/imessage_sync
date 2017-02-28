# imessage_reader.py - Read messages from iMessage under Mac OS
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
import os

date_epoch = 978307200

def get_conn(conn = None, chat_db = '~/Library/Messages/chat.db'):
    if(conn is None):
        conn = sqlite3.connect('file:'
            + os.path.expanduser(chat_db)
            + '?mode=ro', uri=True)
    return conn

def get_handles(conn = None):
    conn = get_conn(conn)
    handles = dict()
    query = conn.cursor()
    for handle in query.execute('SELECT ROWID, id, country, service, '
            'uncanonicalized_id FROM handle'):
        handles[handle[0]] = dict(
            handle_rowid            = handle[0],
            contact                 = handle[1],
            country                 = handle[2],
            service                 = handle[3],
            uncanonicalized_contact = handle[4]
            )
    return handles;

def get_chats(conn = None):
    conn = get_conn(conn)
    chats = dict()
    query = conn.cursor()
    for chat in query.execute('SELECT ROWID, guid, chat_identifier, '
            'service_name, room_name, group_id, last_addressed_handle FROM chat'):
        chats[chat[0]] = dict(
            handle_rowid          = chat[0],
            guid                  = chat[1],
            chat_identifier       = chat[2],
            service               = chat[3],
            room                  = chat[4],
            group_id              = chat[5],
            last_addressed_handle = chat[6],
            handles               = []
            )

    handles = get_handles(conn)
    for chat_handle in query.execute('SELECT chat_id, handle_id FROM chat_handle_join'):
        chats[chat_handle[0]]['handles'].append(handles[chat_handle[1]]);
    return chats;

def get_attachments(conn = None):
    conn = get_conn(conn)
    afiles = dict()
    query = conn.cursor()
    for afile in query.execute('SELECT ROWID, guid, created_date, start_date, '
            'filename, mime_type, transfer_name, total_bytes FROM attachment'):
        afiles[afile[0]] = dict(
            attachment_rowid    = afile[0],
            guid                = afile[1],
            created_date        = afile[2] + date_epoch,
            start_date          = afile[3] + date_epoch,
            filename            = os.path.expanduser(afile[4]),
            mime_type           = afile[5],
            transfer_name       = afile[6],
            total_bytes         = afile[7]
            )
    return afiles

def get_messages(conn = None):
    conn = get_conn(conn)
    msgs = dict()
    handles = get_handles()
    query = conn.cursor()
    for msg in query.execute('SELECT ROWID, guid, text, handle_id, subject, '
            'type, service, account, account_guid, date, date_read, '
            'date_delivered, is_delivered, is_finished, is_from_me, is_read, '
            'is_sent, is_audio_message, other_handle FROM message'):
        msgs[msg[0]] = dict(
            message_rowid              = msg[0],
            guid                       = msg[1],
            text                       = msg[2],
            handle_id                  = msg[3],
            subject                    = msg[4],
            type                       = msg[5],
            service                    = msg[6],
            account                    = msg[7],
            account_guid               = msg[8],
            date                       = msg[9] + date_epoch,
            date_read                  = msg[10] + date_epoch,
            date_delivered             = msg[11] + date_epoch,
            is_delivered               = msg[12],
            is_finished                = msg[13],
            is_from_me                 = msg[14],
            is_read                    = msg[15],
            is_sent                    = msg[16],
            is_audio_message           = msg[17],
            other_handle_id            = msg[18],
            handle                     = None,
            other_handle               = None,
            chat                       = None,
            attachments                = []
            )
        if(msgs[msg[0]]['handle_id'] != 0):
            msgs[msg[0]]['handle'] = handles[msgs[msg[0]]['handle_id']];
        if(msgs[msg[0]]['other_handle_id'] != 0):
            msgs[msg[0]]['other_handle'] = handles[msgs[msg[0]]['other_handle_id']];

    chats = get_chats(conn)
    for chat_msg in query.execute('SELECT chat_id, message_id FROM chat_message_join'):
        msgs[chat_msg[1]]['chat'] = chats[chat_msg[0]];

    attachments = get_attachments(conn)
    for msg_attachment in query.execute('SELECT message_id, attachment_id FROM message_attachment_join'):
        msgs[msg_attachment[0]]['attachments'].append(attachments[msg_attachment[1]]);

    return msgs
