# (c) James Laird-Wah 2015
# This file is in the public domain.

import struct
import socket

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
        Clean a group of nozzles (1-5). Groups are specified as per estatus.nozzle_groups.
        If 'power' is True, perform a power cleaning, otherwise normal cleaning.
        """
        if group > 5 or group < 1:
            raise ValueError("Nozzle group must be in range 1..5")
        if power:
            group |= 0x10
        self._cmd("CH", "\0" + chr(group))
