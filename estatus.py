# (c) James Laird-Wah 2015
# This file is in the public domain.

"""
Tools for parsing status responses from the printer.
"""

import re

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

def parse_nozzlecheck(data):
    """
    Parse a PS format nozzle check response.
    Returns a list of bools, one for each nozzle. True indicates a blockage.
    """
    m = re.search('@BDC PS\r?\nnc:((\d\d,)+(\d\d));', data)
    return map(lambda x: int(x)>0, m.group(1).split(','))

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
