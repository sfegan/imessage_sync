# imaplib_connect.py

import imaplib
import os
import addressbook
import imessage_sync_config

def open_connection(verbose=False, config=None):
    # Read the config file
    if(not config):
        config = imessage_sync_config.get_config()

    # Connect to the server
    hostname = config.get('server', 'hostname')
    if verbose:
        print('Connecting to', hostname)
    connection = imaplib.IMAP4_SSL(hostname)

    # Login to our account
    username = config.get('account', 'username')
    password = config.get('account', 'password')
    if verbose:
        print('Logging in as', username)
    connection.login(username, password)

    return connection

if __name__ == '__main__':
    c = open_connection(verbose=True)
    print(c)
