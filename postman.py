#!/usr/bin/python

# config section STARTS
# These are the sender's account info you can modify

SMTP_SERVER = 'localhost'
SMTP_PORT = 25
SMTP_ENCRYPTION = None # tls/ssl/None
SMTP_USER = 'gitpatchbot@gmail.com'
SMTP_PASSWORD = 'mypass'
SENDER = 'gitpatchbot@gmail.com'
RECIPIENTS_PER_MAIL = 10

# config section ENDS

from email import encoders
from email.mime.audio import MIMEAudio
from email.mime.base import MIMEBase
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import mimetypes
import os
import re
import smtplib
import sys


def usage():
    print >>sys.stderr, 'Usage:', sys.argv[0], '<subject> <recipients> <message> [<attachment>, ...]\n'
    print >>sys.stderr, '       recipients should be a plain text file contain a list of recipients, one per line'
    print >>sys.stderr, '       message should be a plain text file with .txt suffix or a HTML file with .html suffix'


def main():
    if len(sys.argv) < 4:
        usage()
        sys.exit(-1)

    outer = MIMEMultipart()
    outer['From'] = SENDER
    outer['Subject'] = sys.argv[1]

    recipients_file = sys.argv[2]
    if not os.path.isfile(recipients_file):
        print >>sys.stderr, 'recipients file (%s) not found' % recipients_file
        sys.exit(-1)
    recipients = []
    email_regex = re.compile(r'@')
    with open(recipients_file, 'r') as f:
        for line in f:
            line = line.strip()
            if not email_regex.search(line):
                print >>sys.stderr, 'Ignored illegal recipient %s' % line
                continue
            if line not in recipients:
                recipients.append(line)

    message_file = sys.argv[3]
    if not os.path.isfile(message_file):
        print >>sys.stderr, 'Message file (%s) not found' % message_file
        sys.exit(-1)
    ctype, _ = mimetypes.guess_type(message_file)
    if ctype is None or not ctype.startswith('text'):
        print >>sys.stderr, 'Message file (%s) is not in text' % message_file
        sys.exit(-1)
    maintype, subtype = ctype.split('/', 1)
    with open(message_file, 'r') as f:
        msg = MIMEText(f.read(), _subtype=subtype)
        outer.attach(msg)

    for attach_file in sys.argv[4:]:
        if not os.path.isfile(attach_file):
            print >>sys.stderr, 'Attachment file (%s) not found' % attach_file
            sys.exit(-1)
        ctype, encoding = mimetypes.guess_type(attach_file)
        if ctype is None or encoding is not None:
            # No guess could be made, or the file is encoded (compressed), so
            # use a generic bag-of-bits type.
            ctype = 'application/octet-stream'
        maintype, subtype = ctype.split('/', 1)
        if maintype == 'text':
            with open(attach_file) as f:
                msg = MIMEText(f.read(), _subtype=subtype)
        elif maintype == 'image':
            with open(attach_file, 'rb') as f:
                msg = MIMEImage(f.read(), _subtype=subtype)
        elif maintype == 'audio':
            with open(attach_file, 'rb') as f:
                msg = MIMEAudio(f.read(), _subtype=subtype)
        else:
            msg = MIMEBase(maintype, subtype)
            with open(attach_file, 'rb') as f:
                msg.set_payload(f.read())
            # Encode the payload using Base64
            encoders.encode_base64(msg)
        # Set the filename parameter
        msg.add_header('Content-Disposition', 'attachment', filename=attach_file)
        outer.attach(msg)

    choice = raw_input('Proceed with sending mail to %d recipients? (Y/n): ' % len(recipients))
    if choice != 'Y':
        print >>sys.stderr, 'Aborted'
        sys.exit(-1)

    if SMTP_SERVER == 'localhost':
        smtp = smtplib.SMTP_SSL(SMTP_SERVER)
    elif SMTP_ENCRYPTION == 'ssl':
        smtp = smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT)
    else:
        smtp = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)

    try:
        if SMTP_SERVER != 'localhost':
            smtp.ehlo()
            if SMTP_ENCRYPTION is not None and SMTP_ENCRYPTION == 'tls' and smtp.has_extn('STARTTLS'):
                smtp.starttls()
                smtp.ehlo()
            smtp.login(SMTP_USER, SMTP_PASSWORD)
        n = len(recipients)/RECIPIENTS_PER_MAIL + 1
        for i in range(n):
            starti = i * RECIPIENTS_PER_MAIL
            endi = (i+1) * RECIPIENTS_PER_MAIL
            r = recipients[starti:endi]
            del outer['To']
            outer['To'] = ', '.join(r)
            composed = outer.as_string()
            print >>sys.stderr, 'Sending mail to recipient %d to %d (%d%%), total %d' % (starti, starti + len(r), i * 100 / n, len(recipients))
            smtp.sendmail(SENDER, r, composed)
    finally:
        smtp.quit()

if __name__ == '__main__':
    main()
