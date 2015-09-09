# (c) James Laird-Wah 2015
# This file is in the public domain.

# The bare minimum necessary to obtain SNMP status data from the printer.

from binascii import unhexlify

status_query = unhexlify("303002010004067075626c6963a02302040425b62302010002010030153013060f2b06010401896001020201010104010500")
nozzle_query = unhexlify("303302010004067075626c6963a026020149020100020100301b301906152b0601040189600102022c010102016e63020001100500")

import socket

def query(printer, packet):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind(('', 0))
    s.settimeout(60)
    s.sendto(packet, (printer, 161))
    (data, addr) = s.recvfrom(4096)
    return data

def get_status(printer):
    return query(printer, status_query)

def get_nozzlecheck(printer):
    return query(printer, nozzle_query)
