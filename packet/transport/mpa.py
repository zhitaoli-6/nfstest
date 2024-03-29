#===============================================================================
# Copyright 2021 NetApp, Inc. All Rights Reserved,
# contribution by Jorge Mora <mora@netapp.com>
#
# This program is free software; you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation; either version 2 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#===============================================================================
"""
MPA module

Decode MPA layer.

RFC 5044 Marker PDU Aligned Framing for TCP Specification
"""
import nfstest_config as c
from baseobj import BaseObj
from packet.unpack import Unpack
from packet.transport.ddp import DDP
from packet.utils import IntHex, Enum

# Module constants
__author__    = "Jorge Mora (%s)" % c.NFSTEST_AUTHOR_EMAIL
__copyright__ = "Copyright (C) 2021 NetApp, Inc."
__license__   = "GPL v2"
__version__   = "1.1"

MPA_Request_Frame = 0
MPA_Reply_Frame   = 1

mpa_frame_type = {
    0 : "MPA_Request_Frame",
    1 : "MPA_Reply_Frame",
}

class FrameType(Enum):
    """enum OpCode"""
    _enumdict = mpa_frame_type

class MPA(BaseObj):
    """MPA object

       Usage:
           from packet.transport.mpa import MPA

           x = MPA(pktt)

       Object definition:

       MPA(
           [
               # MPA Full Operation Phase
               psize = int,  # Length of ULPDU
               pad   = int,  # Length of Padding bytes
               crc   = int,  # CRC 32 check value
           ] | [
               # Connection Setup
               ftype    = int,   # Frame type
               marker   = int,   # Marker usage required
               use_crc  = int,   # CRC usage
               reject   = int,   # Rejected connection
               revision = int,   # Revision of MPA
               psize    = int,   # Size of private data
               data     = bytes, # Private data
           ]
       )
    """
    # Class attributes
    _attrlist = ("psize", "pad", "crc",
                 "ftype", "marker", "use_crc", "reject", "revision")
    _strfmt1  = "MPA   crc: {2}, pad: {1}, len: {0}"
    _strfmt2  = "crc: {2}, pad: {1}, len: {0}"

    def __init__(self, pktt):
        """Constructor

           Initialize object's private data.

           pktt:
               Packet trace object (packet.pktt.Pktt) so this layer has
               access to the parent layers.
        """
        unpack = pktt.unpack
        record = pktt.pkt.record
        offset = unpack.tell()
        self.psize = 0
        self.rpsize = 0
        if unpack.size() < 8:
            return

        # Decode the MPA length
        mpalen = unpack.unpack_ushort()
        self.psize = mpalen

        # MPA payload size: excluding the MPA CRC (4 bytes)
        if record.length_orig < len(unpack):
            # Reassembled message of TCP fragments
            size = unpack.size()
        else:
            size = record.length_orig - unpack.tell() - 4
        # Do not include any padding
        self.pad = ((4 - ((mpalen+2) & 0x03)) & 0x03)
        size -= self.pad
        self.rpsize = size

        # Check if valid MPA layer
        # XXX FIXME This check does not include any markers
        if mpalen > size:
            # Not an MPA Full Operation Phase packet,
            # try if this is an MPA Connection Setup
            self._mpa_setup(pktt, mpalen, offset)
            return

        # This is an MPA packet
        pktt.pkt.add_layer("mpa", self)

        # Get the CRC only if the whole frame was captured
        delta = record.length_orig - record.length_inc
        size = unpack.size() - ((4-delta) if delta < 4 else 0)
        data = bytes(0)
        if size > 0:
            # Use min between mpalen and size since size could be smaller
            # than mpalen if this is a truncated frame. It could be larger
            # if there is a full capture and there is padding
            data = unpack.read(min(mpalen, size))

        if self.pad and delta == 0 and unpack.size():
            # Get padding bytes
            unpack.read(min(self.pad, unpack.size()))

        unpack_save = None
        if delta == 0 and unpack.size() >= 4:
            # Get the CRC-32
            self.crc = IntHex(unpack.unpack_uint())
            if unpack.size() > 0:
                # Save original Unpack object right after this MPA packet
                # so it is ready if there is another MPA packet within
                # this TCP packet
                unpack_save = unpack

        if len(data) > 0:
            # Replace Unpack object with just the payload data
            # -- no padding and no CRC
            unpack = Unpack(data)
            pktt.unpack = unpack

            # Decode payload
            DDP(pktt)

            # Get the un-dissected bytes
            if unpack.size() > 0:
                self.data = unpack.read(unpack.size())
            if unpack_save is not None:
                # Restore Unpack object
                pktt.unpack = unpack_save

    def _mpa_frame(self, pktt):
        """Dissect MPA Req/Rep Frame"""
        unpack = pktt.unpack
        ulist  = unpack.unpack(4, "!BBH")
        self.marker   = (ulist[0] >> 7) & 0x01
        self.use_crc  = (ulist[0] >> 6) & 0x01
        self.reject   = (ulist[0] >> 5) & 0x01
        self.revision = ulist[1]
        self.psize    = ulist[2]
        self.data     = unpack.read(self.psize)
        pktt.pkt.add_layer("mpa", self)

    def _mpa_setup(self, pktt, mpalen, offset):
        """Dissect MPA Connection Setup"""
        unpack = pktt.unpack
        if mpalen == 0x4d50: # Could be the start of req/rep key: "MP"
            # Check if this is an MPA Request or Reply frame
            unpack.seek(offset)
            key = unpack.read(16)
            if key == b"MPA ID Req Frame":
                # MPA Request Frame
                # key = 0x4d504120494420526571204672616d65
                self._mpa_frame(pktt)
                self.ftype    = FrameType(MPA_Request_Frame)
                self._strfmt1 = "MPA   v{7:<3} {3}, marker: {4}, use_crc: {5}, len: {0}"
                self._strfmt2 = "{3}, revision: {7}, marker: {4}, use_crc: {5}, len: {0}"
            elif key == b"MPA ID Rep Frame":
                # MPA Reply Frame
                # key = 0x4d504120494420526570204672616d65
                self._mpa_frame(pktt)
                self.ftype    = FrameType(MPA_Reply_Frame)
                self._strfmt1 = "MPA   v{7:<3} {3},   marker: {4}, use_crc: {5}, len: {0}, reject: {6}"
                self._strfmt2 = "{3}, revision: {7}, marker: {4}, use_crc: {5}, reject: {6}, len: {0}"
        if self.ftype is None:
            # No MPA Req/Rep Frame
            unpack.seek(offset)
