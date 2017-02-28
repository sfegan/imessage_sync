# imessage_to_mime.py - Convert imessage dictionary to MIME
#
# Stephen Fegan - sfegan@gmail.com - 2017-02-28
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

import email.mime.base
import email.mime.text
import email.mime.image
import email.mime.audio
import email.mime.multipart
import email.utils
import email.encoders
import email
#import BytesIO

def get_handle_name(handle, addressbook):
    name = addressbook.lookup_name(handle)
    if(name is None):
        name = handle['contact']
    return name

def get_chat_names(chat, addressbook):
    s = get_handle_name(chat['handles'][0], addressbook)
    if(len(chat['handles']) > 1):
        for h in chat['handles'][1:-1]:
            s += ', ' + get_handle_name(h, addressbook)
        s += ' and ' + get_handle_name(chat['handles'][-1], addressbook)
    return s

def get_subject(message, addressbook):
    if(message['subject']):
        return message['subject']
    else:
        return message['chat']['service'] + ' with ' \
            + get_chat_names(message['chat'], addressbook)

def get_from(message, addressbook):
    if(message['is_from_me']):
        return addressbook.me()
    elif(not message['handle'] is None):
        return addressbook.lookup_email(message['handle'])
    elif(not message['other_handle'] is None):
        return addressbook.lookup_email(message['other_handle'])
    else:
        return 'unknown@unknown.email'
    pass

def get_to(message, addressbook):
    if(message['is_from_me']):
        return ', '.join(map(addressbook.lookup_email, message['chat']['handles']))
    else:
        fh = None
        if(not message['handle'] is None):
            fh = message['handle']
        elif(not message['other_handle'] is None):
            fh = message['other_handle']
        th = [ addressbook.me() ]
        if(message['chat'] and message['chat']['handles']):
            for to in map(addressbook.lookup_email,
                    filter(lambda h: h != fh, message['chat']['handles'])):
                th.append(to)
        return ', '.join(th)
    pass

def get_message_id(guid):
    return '<'+guid+'@imessage_sync.local>'

def get_text_msg(message):
	return email.mime.text.MIMEText(message['text'])

def get_attachment_msg(attachment):
    maintype, subtype = attachment['mime_type'].split('/')
    path = attachment['filename']
    if maintype == 'text':
        fp = open(path)
        # Note: we should handle calculating the charset
        msg = email.mime.text.MIMEText(fp.read(), _subtype=subtype)
        fp.close()
    elif maintype == 'image':
        fp = open(path, 'rb')
        msg = email.mime.image.MIMEImage(fp.read(), _subtype=subtype)
        fp.close()
    elif maintype == 'audio':
        fp = open(path, 'rb')
        msg = email.mime.audio.MIMEAudio(fp.read(), _subtype=subtype)
        fp.close()
    else:
        fp = open(path, 'rb')
        msg = email.mime.base.MIMEBase(maintype, subtype)
        msg.set_payload(fp.read())
        fp.close()
        # Encode the payload using Base64
        email.encoders.encode_base64(msg)
    if(attachment.get('transfer_name') and attachment.get('created_date')):
        msg.add_header('Content-Disposition', 'attachment',
            creation_date=email.utils.formatdate(attachment['created_date']),
            filename=attachment['transfer_name'])
    elif(attachment.get('transfer_name')):
        msg.add_header('Content-Disposition', 'attachment',
            filename=attachment['transfer_name'])
    elif(attachment.get('created_date')):
        msg.add_header('Content-Disposition', 'attachment',
            creation_date=email.utils.formatdate(attachment['created_date']))
    return msg

def is_valid(message):
    return message.get('chat') and message['chat']['handles'] \
        and (message.get('handle') or message.get('other_handle'))

def get_email(message, addressbook):
    outer = email.mime.multipart.MIMEMultipart()
    outer['Subject']    = get_subject(message, addressbook)
    outer['To']         = get_to(message, addressbook)
    outer['From']       = get_from(message, addressbook)
    outer['Date']       = email.utils.formatdate(message['date'])
    outer['Message-ID'] = get_message_id(message['guid'])
    if(message['chat'].get('_last_message_id')):
        outer['In-Reply-To']                   = \
            get_message_id(message['chat']['_last_message_id'])
    if(message['chat'].get('_first_message_id')):
        outer['References']                    = \
            get_message_id(message['chat']['_first_message_id']) + ' ' + \
            get_message_id(message['chat']['_last_message_id'])
    outer['X-imessagesync-guid']               = message['guid']
    outer['X-imessagesync-chat-guid']          = message['chat']['guid']
    outer['X-imessagesync-chat-contacts']      = \
        ' '.join(map(lambda h: h['contact'], message['chat']['handles']))
    if(message.get('account')):
        outer['X-imessagesync-account']        = message['account']
    if(message['is_delivered']):
        outer['X-imessagesync-date-delivered'] = \
            email.utils.formatdate(message['date_delivered'])
    if(message['is_read']):
        outer['X-imessagesync-date-read']      = \
            email.utils.formatdate(message['date_read'])
    if(message['handle']):
        outer['X-imessagesync-handle-contact'] = message['handle']['contact']
        outer['X-imessagesync-handle-country'] = message['handle']['country']
        outer['X-imessagesync-handle-service'] = message['handle']['service']
    outer.preamble = 'You will not see this in a MIME-aware email reader.\n'
    outer.attach(get_text_msg(message))
    for a in message['attachments']:
        outer.attach(get_attachment_msg(a))
    return outer

def update_chat_thread_ids(message):
    message['chat']['_last_message_id'] = message['guid']
    if(message['chat'].get('_first_message_id') is None):
        message['chat']['_first_message_id'] = message['guid']
