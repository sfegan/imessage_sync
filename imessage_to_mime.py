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
import email.charset
import email.header
import email
import hashlib
import copy
#import BytesIO

email.charset.Charset('utf-8').body_encoding = email.charset.QP
email.charset.Charset('utf-8').header_encoding = email.charset.QP

Xheader_base = 'X-imessagesync-'
def Xheader(ext): return Xheader_base + ext
Xheader_guid = Xheader('guid')
message_id_fqdn = '@imessage_sync.local'

def get_handle_name(handle, addressbook):
    name = addressbook.lookup_name(handle)
    if(name is None):
        name = handle['contact']
    return name

def get_chat_contacts(chat):
    return ','.join(map(lambda h: h['contact'], chat['handles']))

def get_chat_names(chat, addressbook):
    names = sorted(map(lambda h: get_handle_name(h, addressbook), chat['handles']))
    if(len(names) > 1):
        s = ', '.join(names[0:-1])
        s += ' and ' + names[-1]
        return s
    else:
        return names[0]

def get_subject(message, addressbook):
    return 'Chat with ' + get_chat_names(message['chat'], addressbook)

def make_email_header(all_emails):
    h = email.header.Header()
    if(type(all_emails[0]) is not list):
        all_emails = [ all_emails ]
    first = True
    for one_email in all_emails:
        if(not first):
            h.append(', ')
        first = False
        h.append(one_email[0])
        h.append('<' + one_email[1] + '>')
    return h

def get_from(message, addressbook):
    if(message['is_from_me']):
        return make_email_header(addressbook.me())
    elif(not message['handle'] is None):
        return make_email_header(addressbook.lookup_email(message['handle']))
    elif(not message['other_handle'] is None):
        return make_email_header(addressbook.lookup_email(message['other_handle']))
    else:
        return make_email_header(['Unknown person', 'unknown@unknown.email'])
    pass

def get_to(message, addressbook):
    th = []
    if(message['is_from_me']):
        th = list(map(addressbook.lookup_email, message['chat']['handles']))
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
    return make_email_header(th)

def get_rfc3501_id(id):
    return '<'+id+message_id_fqdn+'>'

def get_message_id(message):
    return get_rfc3501_id(message['guid'])

def get_chat_id(chat, addressbook):
    id = hashlib.sha1(get_chat_names(chat, addressbook).encode()).hexdigest()
    return get_rfc3501_id(id)

def get_text_msg(message):
    text = message['text']
    try:
        text.encode('us-ascii')
    except:
        msg = email.mime.text.MIMEText('', _charset='utf-8')
        msg.replace_header('content-transfer-encoding', 'quoted-printable')
        msg.set_payload(text, 'utf-8')
        return msg
    return email.mime.text.MIMEText(text, _charset='us-ascii')

def get_attachment_msg(attachment):
    if(not attachment['mime_type']):
        return None
    path = attachment['filename']
    maintype, subtype = attachment['mime_type'].split('/')
    fp = None
    if(path):
        try:
            fp = open(path, 'r' if maintype=='text' else 'rb')
        except:
            fp = None
    if(fp is None):
        return email.mime.text.MIMEText('Attachment "%s" not found on server'%
            attachment['raw_filename'])
    if maintype == 'text':
        # Note: we should handle calculating the charset
        msg = email.mime.text.MIMEText(fp.read(), _subtype=subtype)
        fp.close()
    elif maintype == 'image':
        msg = email.mime.image.MIMEImage(fp.read(), _subtype=subtype)
        fp.close()
    elif maintype == 'audio':
        msg = email.mime.audio.MIMEAudio(fp.read(), _subtype=subtype)
        fp.close()
    else:
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
    return (message.get('chat') is not None and \
        len(message['chat']['handles'])>0 and \
        (message['is_from_me']==True or message.get('handle') is not None or message.get('other_handle') is not None) and \
        (message['text'] is not None or len(message['attachments'])>0))

def set_headers(outer, message, addressbook, in_reply_to, sync_time=None):
    outer['Subject']    = email.header.Header(get_subject(message, addressbook))
    outer['To']         = get_to(message, addressbook)
    outer['From']       = get_from(message, addressbook)
    outer['Date']       = email.utils.formatdate(message['date'])
    outer['Message-ID'] = get_message_id(message)
    chat_id = get_chat_id(message['chat'], addressbook)
    if(chat_id in in_reply_to):
        outer['In-Reply-To']             = in_reply_to[chat_id]
        outer['References']              = chat_id + ' ' + in_reply_to[chat_id]
    else:
        outer['References']              = chat_id
    outer[Xheader_guid]                  = message['guid']
    #outer[Xheader('chat-guid')]          = message['chat']['guid']
    outer[Xheader('contacts')]           = \
        ' '.join(map(lambda h: h['contact'], message['chat']['handles']))
    outer[Xheader('my-contact')]         = \
        message['chat']['last_addressed_handle']
    outer[Xheader('service')]            = message['service']
    if(message.get('account') and message['account'] != 'e:'):
        outer[Xheader('account')]        = message['account']
    if(message['date_delivered'] and message['is_delivered']):
        outer[Xheader('date-delivered')] = \
            email.utils.formatdate(message['date_delivered'])
    if(message['date_read'] and message['is_read']):
        outer[Xheader('date-read')]      = \
            email.utils.formatdate(message['date_read'])
    if(not message['is_from_me'] and message['handle']):
        outer[Xheader('from-contact')]   = message['handle']['contact']
#        outer[Xheader('handle-country')] = message['handle']['country']
#        outer[Xheader('handle-service')] = message['handle']['service']
    if(sync_time):
        outer[Xheader('upload-date')]    = \
            email.utils.formatdate(sync_time)

def get_email(message, addressbook, in_reply_to = dict(), max_attachment_size = None, sync_time = None):
    if(message['attachments']):
        emails = []
        outer = email.mime.multipart.MIMEMultipart()
        set_headers(outer, message, addressbook, in_reply_to, sync_time)
        outer.preamble = 'You will not see this in a MIME-aware email reader.\n'
        outer.attach(get_text_msg(message))
        attachments = []
        for a in message['attachments']:
            attachments.append(get_attachment_msg(a))
        if(max_attachment_size is not None and max_attachment_size > 0):
            total_asize = 0
            for ia, a in enumerate(attachments):
                if(not a):
                    continue
                asize = len(a.as_bytes())
                if(asize > max_attachment_size):
                    a = email.mime.text.MIMEText('Attachment "%s" suppressed due to '
                        'file-size constraints'%message['attachments'][ia]['raw_filename'])
                    asize = len(a.as_bytes())
                elif(total_asize + asize > max_attachment_size):
                    outer[Xheader('fragment')] = str(len(emails))
                    emails.append(outer)
                    new_message = copy.copy(message)
                    new_message['guid'] = \
                        message['guid'] + '-FRAGMENT-' + str(len(emails))
                    outer = email.mime.multipart.MIMEMultipart()
                    set_headers(outer, new_message, addressbook, in_reply_to, sync_time)
                    outer.preamble = 'You will not see this in a MIME-aware email reader.\n'
                    total_asize = 0
                outer.attach(a)
                total_asize += asize
        else:
            for a in attachments:
                if(a):
                    outer.attach(a)
        if(emails):
            outer[Xheader('fragment')] = str(len(emails))
            emails.append(outer)
            return emails
        else:
            return outer
    else:
        outer = get_text_msg(message)
        set_headers(outer, message, addressbook, in_reply_to, sync_time)
    return outer

def update_chat_thread_ids(message, addressbook, in_reply_to):
    chat_id = get_chat_id(message['chat'], addressbook)
    in_reply_to[chat_id] = get_message_id(message)
