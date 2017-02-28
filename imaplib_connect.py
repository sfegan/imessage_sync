# imaplib_connect.py

import imaplib
import configparser
import os

def open_connection(verbose=False):
    # Read the config file
    config = configparser.ConfigParser()
    config.read([os.path.expanduser('~/.imessage_to_gmail')])

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
    return connection, config.get('account', 'identity')

if __name__ == '__main__':
    c = open_connection(verbose=True)
    print(c)
