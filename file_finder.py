# file_finder.py - Locate chat database and attachments
#
# Stephen Fegan - sfegan@gmail.com - 2017-03-03
#
# Portions of this code adapted from : https://gist.github.com/aliou/4448630

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

import os
import sys
import hashlib

def getint(data, offset, intsize):
    """Retrieve an integer (big-endian) and new offset from the current offset"""
    value = 0
    while intsize > 0:
        value = (value<<8) + data[offset]
        offset = offset + 1
        intsize = intsize - 1
    return value, offset

def getstring(data, offset, encoding='utf-8'):
    """Retrieve a string and new offset from the current offset into the data"""
    if data[offset] == 0xFF and data[offset+1] == 0xFF:
        return '', offset+2 # Blank string
    length, offset = getint(data, offset, 2) # 2-byte length
    value = data[offset:offset+length]
    return value.decode(encoding), (offset + length)

def getbytes(data, offset):
    """Retrieve a bytes string and new offset from the current offset into the data"""
    if data[offset] == 0xFF and data[offset+1] == 0xFF:
        return '', offset+2 # Blank string
    length, offset = getint(data, offset, 2) # 2-byte length
    value = data[offset:offset+length]
    return value, (offset + length)

class NativeDBFilename:
    native_db_path = '~/Library/Messages'
    native_chat_db = 'chat.db'

    def __init__(self, db_path = None, chat_db = None):
        self._db_path = db_path or NativeDBFilename.native_db_path
        self._chat_db = chat_db or NativeDBFilename.native_chat_db

    def chat_db(self):
        return os.path.expanduser(self._db_path + '/' + self._chat_db)

    def filename(self, f):
        return f

class RelocatedDBFilename:
    def __init__(self, relocated_db_path, native_db_path = None, chat_db = None):
        self._relocated_db_path = relocated_db_path
        self._native_db_path = native_db_path or NativeDBFilename.native_db_path
        self._chat_db = chat_db or NativeDBFilename.native_chat_db

    def chat_db(self):
        return os.path.expanduser(self._relocated_db_path + '/' + self._chat_db)

    def filename(self, f):
        if len(f)>len(self._native_db_path) and \
                f[0:len(self._native_db_path)]==self._native_db_path:
            return self._relocated_db_path + f[len(self._native_db_path):]
        else:
            return f

class IPhoneBackupFilename:
    native_db_path = 'Library/SMS'
    native_chat_db = 'sms.db'
    native_manifest = 'Manifest.mbdb'

    def __init__(self, backup_path, manifest = None, db_path = None, chat_db = None):
        self._backup_path = backup_path
        self._manifest    = manifest or IPhoneBackupFilename.native_manifest
        self._db_path     = db_path or IPhoneBackupFilename.native_db_path
        self._chat_db     = chat_db or IPhoneBackupFilename.native_chat_db
        self._mbdx        = {}
        self._mbdb        = self.load_manifest()
        self._ff          = self.make_fast_find(self._mbdb)

    def chat_db(self):
        return self.filename(self._db_path + '/' + self._chat_db)

    def filename(self, f):
        len_f = len(f)
        if(f[0] == '/'):
            index = 0
        else:
            index = -1
        while(True):
            iff = self._ff[len_f - index - 1]
            fsub = f[(index+1):]
            for ifn in iff:
                if(fsub == ifn):
                    return os.path.expanduser(self._backup_path + '/' + iff[ifn])
            index = f.find('/', index+1)
            if(index < 0):
                return None

    def make_fast_find(self, mdbd):
        index = dict()
        for imdbd in mdbd:
            fn = mdbd[imdbd]['filename']
            len_fn = len(fn)
            if(len_fn not in index):
                index[len_fn] = dict()
            index[len_fn][fn] = mdbd[imdbd]['fileID']
        return index

    def load_manifest(self):
        mbdb = self.process_mbdb_file(os.path.expanduser( \
            self._backup_path + '/' + self._manifest))
        for offset, fileinfo in mbdb.items():
            if offset in self._mbdx:
                fileinfo['fileID'] = self._mbdx[offset]
            else:
                fileinfo['fileID'] = "<nofileID>"
                print("No fileID found for %s" % fileinfo['filename'], file=sys.stderr)
        return mbdb

    def process_mbdb_file(self, filename):
        mbdb = {} # Map offset of info in this file => file info
        data = open(filename,'br').read()
        if data[0:4] != b'mbdb': raise Exception("This does not look like an MBDB file")
        offset = 4
        offset = offset + 2 # value x05 x00, not sure what this is
        while offset < len(data):
            fileinfo = {}
            fileinfo['start_offset'] = offset
            fileinfo['domain'], offset = getstring(data, offset)
            fileinfo['filename'], offset = getstring(data, offset)
            fileinfo['linktarget'], offset = getbytes(data, offset)
            fileinfo['datahash'], offset = getbytes(data, offset)
            fileinfo['unknown1'], offset = getbytes(data, offset)
            fileinfo['mode'], offset = getint(data, offset, 2)
            fileinfo['unknown2'], offset = getint(data, offset, 4)
            fileinfo['unknown3'], offset = getint(data, offset, 4)
            fileinfo['userid'], offset = getint(data, offset, 4)
            fileinfo['groupid'], offset = getint(data, offset, 4)
            fileinfo['mtime'], offset = getint(data, offset, 4)
            fileinfo['atime'], offset = getint(data, offset, 4)
            fileinfo['ctime'], offset = getint(data, offset, 4)
            fileinfo['filelen'], offset = getint(data, offset, 8)
            fileinfo['flag'], offset = getint(data, offset, 1)
            fileinfo['numprops'], offset = getint(data, offset, 1)
            fileinfo['properties'] = {}
            for ii in range(fileinfo['numprops']):
                propname, offset = getstring(data, offset)
                propval, offset = getbytes(data, offset)
                fileinfo['properties'][propname] = propval
            mbdb[fileinfo['start_offset']] = fileinfo
            fullpath = fileinfo['domain'] + '-' + fileinfo['filename']
            id = hashlib.sha1(fullpath.encode())
            self._mbdx[fileinfo['start_offset']] = id.hexdigest()
        return mbdb
