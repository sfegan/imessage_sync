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
import email.mime.multipart
import email.utils
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
    s = message['service'] + ' with ' \
        + get_chat_names(message['chat'], addressbook)
    return s

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
    return '<'+guid+'@imessage_to_gmail.local>'

def get_text_msg(message):
	return email.mime.text.MIMEText(message['text'])

def get_email(message, addressbook):
    outer = email.mime.multipart.MIMEMultipart()
    outer['Subject']    = get_subject(message, addressbook)
    outer['To']         = get_to(message, addressbook)
    outer['From']       = get_from(message, addressbook)
    outer['Date']       = email.utils.formatdate(message['date'])
    outer['Message-ID'] = get_message_id(message['guid'])
    if(message['chat'].get('_last_message_id')):
        outer['In-Reply-To'] = \
            get_message_id(message['chat']['_last_message_id'])
    if(message['chat'].get('_first_message_id')):
        outer['References'] = \
            get_message_id(message['chat']['_first_message_id']) + ', ' + \
            get_message_id(message['chat']['_last_message_id'])
    outer['X-imessagetogmail-']
    outer.preamble = 'You will not see this in a MIME-aware email reader.\n'
    outer.attach(get_text_msg(message))
    return outer
