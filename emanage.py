#!/usr/bin/python
# vim: ts=4 sw=4 et fdm=marker
# (c) James Laird-Wah 2015
# This file is in the public domain.

import sys
import time
import re
import struct
import socket

# Miniature SNMP query tool ----------------------------------------------{{{1
from binascii import unhexlify

status_query = unhexlify("303002010004067075626c6963a02302040425b62302010002010030153013060f2b06010401896001020201010104010500")
nozzle_query = unhexlify("303302010004067075626c6963a026020149020100020100301b301906152b0601040189600102022c010102016e63020001100500")

def snmpquery(printer, packet):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind(('', 0))
    s.settimeout(60)
    s.sendto(packet, (printer, 161))
    (data, addr) = s.recvfrom(4096)
    return data

def get_status(printer):
    "Ask for the printer status (ST2 type)"
    return snmpquery(printer, status_query)

def get_nozzlecheck(printer):
    "Ask for the nozzle check status (PS type)"
    return snmpquery(printer, nozzle_query)

# Status parsing ---------------------------------------------------------{{{1
# ST2 response {{{2
class StatusParser:
    "Parse an ST2 status response and decode as much as possible."
    colour_ids = {
            0x01: 'Photo Black',
            0x03: 'Cyan',
            0x04: 'Magenta',
            0x05: 'Yellow',
            0x06: 'Light Cyan',
            0x07: 'Light Magenta',
            0x0a: 'Light Black',
            0x0b: 'Matte Black',
            0x0f: 'Light Light Black',
            0x10: 'Orange',
            0x11: 'Green',
    }

    status_ids = {
        0: 'Error',
        1: 'Self Printing',
        2: 'Busy',
        3: 'Waiting',
        4: 'Idle',
        5: 'Paused',
        7: 'Cleaning',
        15: 'Nozzle Check',
    }

    def __init__(self, data):
        "Parse a status in ST2 format."
        m = re.search('@BDC ST2\r?\n(.+)', data, re.DOTALL)
        buf = bytearray(m.group(1)) 
        self.unk = []
        while len(buf):
            (ftype, length) = buf[:2]
            buf = buf[2:]
            item = buf[:length]
            buf = buf[length:]

            if ftype == 0x0f: # ink
                colourlen = item[0]
                offset = 1
                inks = []
                while offset < length:
                    colour = item[offset]
                    level = item[offset+2]
                    offset += colourlen

                    if colour in self.colour_ids:
                        name = self.colour_ids[colour]
                    else:
                        name = "0x%X" % colour
                    
                    inks.append((colour, level, name))

                self.inks = inks

            elif ftype == 0x0d: # maintenance tanks
                (tank1, tank2) = item[0:2]
                self.tanks = (tank1, tank2)

            elif ftype == 0x19: # current job name
                self.jobname = item

            elif ftype == 0x1f: # serial
                self.serial = str(item)

            elif ftype == 0x01: # status
                self.status = item[0]
                if self.status in self.status_ids:
                    self.statustext = self.status_ids[self.status]
                else:
                    self.statustext = 'unknown: %d' % self.status
                if self.status == 3 or self.status == 4:
                    self.ready = True
                else:
                    self.ready = False

            elif ftype == 0x02: # errcode
                self.errcode = item

            elif ftype == 0x04: # warning
                self.warncode = item

            else:   # mystery stuff
                self.unk.append((ftype, item))

# PS (nozzle check) {{{2
def parse_nozzlecheck(data):
    """
    Parse a PS format nozzle check response.
    Returns a list of bools, one for each nozzle. True indicates a blockage.
    """
    m = re.search('@BDC PS\r?\nnc:((\d\d,)+(\d\d));', data)
    return map(lambda x: int(x)>0, m.group(1).split(','))

# Nozzle constants {{{2
# Nozzles: shortname, longname, cleaning group
nozzle_colours = [
    ('GR',  'Green',                3),
    ('LLK', 'Light Light Black',    4),
    ('Y',   'Yellow',               4),
    ('LC',  'Light Cyan',           5),
    ('VLM', 'Vivid Light Magenta',  5),
    ('OR',  'Orange',               3),
    ('MK',  'Matte Black',          2),
    ('VM',  'Vivid Magenta',        1),
    ('LK',  'Light Black',          2),
    ('C',   'Cyan',                 1),
    ('PK',  'Photo Black',          2),
]

# Cleaning group names
nozzle_groups = {
    1: 'C/VM',
    2: 'PK(MK)/LK',
    3: 'OR/GR',
    4: 'LLK/Y',
    5: 'VLM/LC',
}

def nozzlecheck_lookup(nc, element):
    """
    Grab elements from a column of nozzle_colours, according to which elements are true in nc.
    """
    result = []
    for (blocked, row) in zip(nc, nozzle_colours):
        if blocked:
            result.append(row[element])
    return result


# ESC/P2 Remote Mode commander -------------------------------------------{{{1

class ESCRemotePrinter:
    """
    Epson Remote Mode (ESC-based) command issue
    """
    def reset(self):
        self.s.sendall("\x1b@")

    def __init__(self, ip, port=9100):
        "Connect to a printer at a particular address."
        self.s = socket.socket()
        self.s.connect((ip, port))
        self.reset()

    def _cmd(self, cmd, args):
        "Issue a Remote Mode command."
        if len(cmd) != 2:
            raise ValueError("command should be 2 bytes")
        packet = cmd + struct.pack('<H', len(args)) + args
        self.s.sendall(packet)
    
    def start_remote(self):
        "Enter Remote Mode."
        self.s.sendall("\x1b\x40")
        self.s.sendall("\x1b(R\x08\0\0REMOTE1")

    def end_remote(self):
        "Exit Remote Mode."
        self.s.sendall("\x1b\0\0\0")

    # commands ------------------------------
    def start_job(self, name):
        "send Job Start with supplied name"
        self._cmd("JS", '\0\0\0' + name + '\0')

    def end_job(self):
        "send Job End"
        self._cmd("JE", '\0')

    def nozzle_check(self):
        "send Nozzle Check, meaning of parameters unknown"
        self._cmd("NC", "\x00\x10")
        self._cmd("NC", "\x00\x11")

    def group_clean(self, group, power=False):
        """
        Clean a group of nozzles (1-5). Groups are specified as per nozzle_groups.
        If 'power' is True, perform a power cleaning, otherwise normal cleaning.
        """
        if group > 5 or group < 1:
            raise ValueError("Nozzle group must be in range 1..5")
        if power:
            group |= 0x10
        self._cmd("CH", "\0" + chr(group))

# Main program -----------------------------------------------------------{{{1

# Parse arguments {{{2
import optparse
parser = optparse.OptionParser(usage="%prog [options] PRINTERIP", epilog="""
This tool is for checking and cleaning nozzles on the Epson Stylus Pro x900
11-cartridge printers, via a network connection.

The return value is zero only if no problems are indicated. A nozzle check failure 
results in return code 100. Other codes indicate network problems or bugs.
""")
ink_choices = [x[0] for x in nozzle_colours]
parser.add_option("-k", "--clean", help="Clean a nozzle (and others in its group). One of " + ','.join(ink_choices) + '.', choices=ink_choices, metavar="COLOUR")
parser.add_option("-P", "--power", help='Do a power clean. Default is normal clean.', action='store_true')
parser.add_option("-c", "--check", help="Run a nozzle check.", action='store_true')
parser.add_option("-v", "--verbose", help="Print additional information during the run.", action='store_true')
(options, args) = parser.parse_args()
if len(args) != 1:
    parser.error("You need to specify the printer hostname or IP")
printer = args[0]

# Utility functions {{{2
def fetch_status(printer):
    "Fetch and parse ST2 data"
    return StatusParser(get_status(printer))

def wait_busy(printer):
    "Wait until printer becomes busy"
    if options.verbose:
        print "Waiting for printer to start..."
    while True:
        status = fetch_status(printer)
        if not status.ready:
            return
        time.sleep(1)

def wait_idle(printer):
    "Wait until printer becomes idle"
    while True:
        status = fetch_status(printer)
        if options.verbose:
            print "Status:", status.statustext
        if status.ready:
            return
        time.sleep(5)

# Readiness check {{{2
status = fetch_status(printer)
if options.verbose:
    print "Printer status:", status.statustext
if not status.ready:
    print "Printer not ready."
    sys.exit(1)

# Command issue {{{2
premote = ESCRemotePrinter(printer)

if not (options.clean or options.check):
    print "Nothing to do."
    sys.exit(0)

if options.clean:
    premote.start_remote()
    premote.start_job("Nozzle cleaning")
    for nc in nozzle_colours:
        if nc[0] == options.clean:
            group_id = nc[2]
            break
    print "Cleaning nozzles %s..." % nozzle_groups[group_id]
    premote.group_clean(group_id, options.power)
    premote.end_job()
    premote.end_remote()
    wait_busy(printer)
    wait_idle(printer)

if options.check:
    premote.start_remote()
    premote.start_job("Nozzle check")
    premote.nozzle_check()
    premote.end_job()
    premote.end_remote()
    wait_busy(printer)
    wait_idle(printer)

# Response check {{{2
blocked = parse_nozzlecheck(get_nozzlecheck(printer))
if any(blocked):
    blocked_names = nozzlecheck_lookup(blocked, 0)
    print "Blocked:", ", ".join(blocked_names)
    sys.exit(100)
else:
    print "Nozzles OK"
