#!/usr/bin/env python3
import argparse
import datetime
import imessage_sync

parser = argparse.ArgumentParser(description='Syncronise iMessages to GMail or other IMAP mail system.')

parser.add_argument('-v', '--verbose', dest='verbose', action='store_const',
                    default=False, const=True,
                    help='print out verbose list of message to upload')
parser.add_argument('--no_upload', dest='do_upload', action='store_const',
                    default=True, const=False,
                    help='do not upload messages, instead do all prior steps')
parser.add_argument('--since', dest='start_date', action='store', default=None,
                    help='process messages since given date. Specify as YYYY-MM-DD')
parser.add_argument('--db', dest='db', action='append', default=None,
                    help='specify iMessage database(s) to use')

args = parser.parse_args()

start_date = None
if(args.start_date is not None):
    start_date = datetime.datetime.strptime(args.start_date,'%Y-%m-%d')
    start_date = start_date and start_date.timestamp()

imessage_sync.sync_all_messages(finder_or_base_path=args.db,
    start_date=start_date, verbose=args.verbose,
    do_upload=args.do_upload)
