#===============================================================================
# Copyright 2017 NetApp, Inc. All Rights Reserved,
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
# Generated by process_xdr.py from rpcordma.x on Sun Feb 04 09:51:38 2018
"""
RPCORDMA decoding module
"""
import nfstest_config as c
from packet.utils import *
from baseobj import BaseObj
import rpcordma_const as const
from packet.unpack import Unpack

# Module constants
__author__    = "Jorge Mora (%s)" % c.NFSTEST_AUTHOR_EMAIL
__copyright__ = "Copyright (C) 2017 NetApp, Inc."
__license__   = "GPL v2"
__version__   = "1.0"

# RFC 8166 Remote Direct Memory Access Transport for Remote Procedure Call
#
# Basic data types
int32  = Unpack.unpack_int
uint32 = Unpack.unpack_uint
int64  = Unpack.unpack_int64
uint64 = Unpack.unpack_uint64

# Plain RDMA segment
class xdr_rdma_segment(BaseObj):
    """
       struct xdr_rdma_segment {
           uint32 handle;  /* Registered memory handle */
           uint32 length;  /* Length of the chunk in bytes */
           uint64 offset;  /* Chunk virtual address or offset */
       };
    """
    # Class attributes
    _attrlist = ("handle", "length", "offset")

    def __init__(self, unpack):
        self.handle = IntHex(uint32(unpack))
        self.length = uint32(unpack)
        self.offset = uint64(unpack)

# RDMA read segment
class xdr_read_chunk(BaseObj):
    """
       struct xdr_read_chunk {
           uint32           position;  /* Position in XDR stream */
           xdr_rdma_segment target;
       };
    """
    # Class attributes
    _fattrs   = ("target",)
    _attrlist = ("position", "target")

    def __init__(self, unpack):
        self.position = uint32(unpack)
        self.target   = xdr_rdma_segment(unpack)

# Read list
class xdr_read_list(BaseObj):
    """
       struct xdr_read_list {
           xdr_read_chunk entry;
           xdr_read_list  *next;
       };
    """
    # Class attributes
    _attrlist = ("entry",)

    def __init__(self, unpack):
        self.entry = xdr_read_chunk(unpack)

# Write chunk
class xdr_write_chunk(BaseObj):
    """
       struct xdr_write_chunk {
           xdr_rdma_segment target<>;
       };
    """
    # Class attributes
    _strfmt2  = "{0:len}"
    _attrlist = ("target",)

    def __init__(self, unpack):
        self.target = unpack.unpack_array(xdr_rdma_segment)

# Write list
class xdr_write_list(BaseObj):
    """
       struct xdr_write_list {
           xdr_write_chunk entry;
           xdr_write_list  *next;
       };
    """
    # Class attributes
    _attrlist = ("entry",)

    def __init__(self, unpack):
        self.entry = xdr_write_chunk(unpack)

# Chunk lists
class rpc_rdma_header(BaseObj):
    """
       struct rpc_rdma_header {
           xdr_read_list   *reads;
           xdr_write_list  *writes;
           xdr_write_chunk *reply;
       };
    """
    # Class attributes
    _strfmt2  = "reads: {0:len}, writes: {1:len}, reply: {2:?{2}:0}"
    _attrlist = ("reads", "writes", "reply")

    def __init__(self, unpack):
        self.reads  = unpack.unpack_list(xdr_read_chunk)
        self.writes = unpack.unpack_list(xdr_write_chunk)
        self.reply  = unpack.unpack_conditional(xdr_write_chunk)

class rpc_rdma_header_nomsg(BaseObj):
    """
       struct rpc_rdma_header_nomsg {
           xdr_read_list   *reads;
           xdr_write_list  *writes;
           xdr_write_chunk *reply;
       };
    """
    # Class attributes
    _strfmt2  = "reads: {0:len}, writes: {1:len}, reply: {2:?{2}:0}"
    _attrlist = ("reads", "writes", "reply")

    def __init__(self, unpack):
        self.reads  = unpack.unpack_list(xdr_read_chunk)
        self.writes = unpack.unpack_list(xdr_write_chunk)
        self.reply  = unpack.unpack_conditional(xdr_write_chunk)

# Not to be used: obsoleted by RFC 8166
class rpc_rdma_header_padded(BaseObj):
    """
       struct rpc_rdma_header_padded {
           uint32          align;    /* Padding alignment */
           uint32          thresh;   /* Padding threshold */
           xdr_read_list   *reads;
           xdr_write_list  *writes;
           xdr_write_chunk *reply;
       };
    """
    # Class attributes
    _strfmt2  = "reads: {2:len}, writes: {3:len}, reply: {4:?{4}:0}"
    _attrlist = ("align", "thresh", "reads", "writes", "reply")

    def __init__(self, unpack):
        self.align  = uint32(unpack)
        self.thresh = uint32(unpack)
        self.reads  = unpack.unpack_list(xdr_read_chunk)
        self.writes = unpack.unpack_list(xdr_write_chunk)
        self.reply  = unpack.unpack_conditional(xdr_write_chunk)

# Error handling
class rpc_rdma_errcode(Enum):
    """enum rpc_rdma_errcode"""
    _enumdict = const.rpc_rdma_errcode

# Structure fixed for all versions
class rpc_rdma_errvers(BaseObj):
    """
       struct rpc_rdma_errvers {
           uint32 low;
           uint32 high;
       };
    """
    # Class attributes
    _strfmt2  = "low: {0}, high: {1}"
    _attrlist = ("low", "high")

    def __init__(self, unpack):
        self.low  = uint32(unpack)
        self.high = uint32(unpack)

class rpc_rdma_error(BaseObj):
    """
       union switch rpc_rdma_error (rpc_rdma_errcode err) {
           case const.ERR_VERS:
               rpc_rdma_errvers range;
           case const.ERR_CHUNK:
               void;
       };
    """
    # Class attributes
    _strfmt2 = "{0}"

    def __init__(self, unpack):
        self.set_attr("err", rpc_rdma_errcode(unpack))
        if self.err == const.ERR_VERS:
            self.set_attr("range", rpc_rdma_errvers(unpack), switch=True)
            self.set_strfmt(2, "{0} {1}")

# Procedures
class rdma_proc(Enum):
    """enum rdma_proc"""
    _enumdict = const.rdma_proc

# The position of the proc discriminator field is
# fixed for all versions
class rdma_body(BaseObj):
    """
       union switch rdma_body (rdma_proc proc) {
           case const.RDMA_MSG:
               rpc_rdma_header rdma_msg;
           case const.RDMA_NOMSG:
               rpc_rdma_header_nomsg rdma_nomsg;
           case const.RDMA_MSGP:                 /* Not to be used */
               rpc_rdma_header_padded rdma_msgp;
           case const.RDMA_DONE:                 /* Not to be used */
               void;
           case const.RDMA_ERROR:
               rpc_rdma_error rdma_error;
       };
    """
    # Class attributes
    _strfmt2 = "{1}"

    def __init__(self, unpack):
        self.set_attr("proc", rdma_proc(unpack))
        if self.proc == const.RDMA_MSG:
            self.set_attr("rdma_msg", rpc_rdma_header(unpack), switch=True)
        elif self.proc == const.RDMA_NOMSG:
            self.set_attr("rdma_nomsg", rpc_rdma_header_nomsg(unpack), switch=True)
        elif self.proc == const.RDMA_MSGP:
            self.set_attr("rdma_msgp", rpc_rdma_header_padded(unpack), switch=True)
        elif self.proc == const.RDMA_ERROR:
            self.set_attr("rdma_error", rpc_rdma_error(unpack), switch=True)

# Fixed header fields
class RPCoRDMA(BaseObj):
    """
       struct RPCoRDMA {
           uint32    xid;     /* Mirrors the RPC header xid */
           uint32    vers;    /* Version of this protocol */
           uint32    credit;  /* Buffers requested/granted */
           rdma_body body;
       };
    """
    # Class attributes
    _strname  = "RPCoRDMA"
    _fattrs   = ("body",)
    _strfmt1  = "RPCoRDMA {3.proc} xid: {0}"
    _strfmt2  = "{3.proc}, xid: {0}, credits: {2} {3}"
    _attrlist = ("xid", "vers", "credit", "body")

    def __init__(self, unpack):
        self.xid    = IntHex(uint32(unpack))
        self.vers   = uint32(unpack)
        self.credit = uint32(unpack)
        self.body   = rdma_body(unpack)
