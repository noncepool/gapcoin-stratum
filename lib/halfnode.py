#!/usr/bin/python
# Public Domain
# Original author: ArtForz
# Twisted integration: slush

import struct
import socket
import binascii
import time
import sys
import random
import cStringIO
from Crypto.Hash import SHA256

from twisted.internet.protocol import Protocol
from util import *
import settings

import lib.logger
log = lib.logger.get_logger('halfnode')

#import gapcoin_hash

MY_VERSION = 2
MY_SUBVERSION = ".9"

class COutPoint(object):
    def __init__(self):
        self.hash = 0
        self.n = 0
    def deserialize(self, f):
        self.hash = deser_uint256(f)
        self.n = struct.unpack("<I", f.read(4))[0]
    def serialize(self):
        r = ""
        r += ser_uint256(self.hash)
        r += struct.pack("<I", self.n)
        return r
    def __repr__(self):
        return "COutPoint(hash=%064x n=%i)" % (self.hash, self.n)

class CTxIn(object):
    def __init__(self):
        self.prevout = COutPoint()
        self.scriptSig = ""
        self.nSequence = 0
    def deserialize(self, f):
        self.prevout = COutPoint()
        self.prevout.deserialize(f)
        self.scriptSig = deser_string(f)
        self.nSequence = struct.unpack("<I", f.read(4))[0]
    def serialize(self):
        r = ""
        r += self.prevout.serialize()
        r += ser_string(self.scriptSig)
        r += struct.pack("<I", self.nSequence)
        return r
    def __repr__(self):
        return "CTxIn(prevout=%s scriptSig=%s nSequence=%i)" % (repr(self.prevout), binascii.hexlify(self.scriptSig), self.nSequence)

class CTxOut(object):
    def __init__(self):
        self.nValue = 0
        self.scriptPubKey = ""
    def deserialize(self, f):
        self.nValue = struct.unpack("<q", f.read(8))[0]
        self.scriptPubKey = deser_string(f)
    def serialize(self):
        r = ""
        r += struct.pack("<q", self.nValue)
        r += ser_string(self.scriptPubKey)
        return r
    def __repr__(self):
        return "CTxOut(nValue=%i.%08i scriptPubKey=%s)" % (self.nValue // 100000000, self.nValue % 100000000, binascii.hexlify(self.scriptPubKey))

class CTransaction(object):
    def __init__(self):
            self.nVersion = 1
            self.vin = []
            self.vout = []
            self.nLockTime = 0
            self.sha256 = None

    def deserialize(self, f):
            self.nVersion = struct.unpack("<i", f.read(4))[0]
            self.vin = deser_vector(f, CTxIn)
            self.vout = deser_vector(f, CTxOut)
            self.nLockTime = struct.unpack("<I", f.read(4))[0]
            self.sha256 = None

    def serialize(self):
            r = ""
            r += struct.pack("<i", self.nVersion)
            r += ser_vector(self.vin)
            r += ser_vector(self.vout)
            r += struct.pack("<I", self.nLockTime)
            return r
 
    def calc_sha256(self):
        if self.sha256 is None:
            self.sha256 = uint256_from_str(SHA256.new(SHA256.new(self.serialize()).digest()).digest())
        return self.sha256
    
    def is_valid(self):
        self.calc_sha256()
        for tout in self.vout:
            if tout.nValue < 0 or tout.nValue > 21000000L * 100000000L:
                return False
        return True
    def __repr__(self):
        return "CTransaction(nVersion=%i vin=%s vout=%s nLockTime=%i)" % (self.nVersion, repr(self.vin), repr(self.vout), self.nLockTime)

class CBlock(object):
    def __init__(self):
        self.nVersion = 1
        self.hashPrevBlock = 0
        self.hashMerkleRoot = 0
        self.nTime = 0
        self.nBits = 0
        self.nNonce = 0
        self.vtx = []
        self.sha256 = None
        self.gapcoin = None

    def deserialize(self, f):
        self.nVersion = struct.unpack("<i", f.read(4))[0]
        self.hashPrevBlock = deser_uint256(f)
        self.hashMerkleRoot = deser_uint256(f)
        self.nTime = struct.unpack("<I", f.read(4))[0]
        self.nBits = struct.unpack("<I", f.read(4))[0]
        self.nNonce = struct.unpack("<I", f.read(4))[0]
        self.vtx = deser_vector(f, CTransaction)

    def serialize(self):
        r = []
        r.append(struct.pack("<i", self.nVersion))
        r.append(ser_uint256(self.hashPrevBlock))
        r.append(ser_uint256(self.hashMerkleRoot))
        r.append(struct.pack("<I", self.nTime))
        r.append(struct.pack("<I", self.nBits))
        r.append(struct.pack("<I", self.nNonce))
        r.append(ser_vector(self.vtx))
        return ''.join(r)

    def calc_gapcoin(self):
        if self.gapcoin is None:
            r = []
            r.append(struct.pack("<i", self.nVersion))
            r.append(ser_uint256(self.hashPrevBlock))
            r.append(ser_uint256(self.hashMerkleRoot))
            r.append(struct.pack("<I", self.nTime))
            r.append(struct.pack("<Q", self.nBits))
            r.append(struct.pack("<I", self.nNonce))
            self.gapcoin = uint256_from_str(gapcoin_hash.getpowdiff(''.join(r)))
            return self.gapcoin

    def calc_sha256(self):
        if self.sha256 is None:
            r = []
            r.append(struct.pack("<i", self.nVersion))
            r.append(ser_uint256(self.hashPrevBlock))
            r.append(ser_uint256(self.hashMerkleRoot))
            r.append(struct.pack("<I", self.nTime))
            r.append(struct.pack("<I", self.nBits))
            r.append(struct.pack("<I", self.nNonce))
            self.sha256 = uint256_from_str(SHA256.new(SHA256.new(''.join(r)).digest()).digest())
            return self.sha256

    def is_valid(self):
        if True:
            self.calc_gapcoin()
        else:
            self.calc_sha256()

        target = self.nBits

        if True:
            if self.gapcoin < target:
                return False
        else:
            if self.sha256 > target:
                return False

        hashes = []
        for tx in self.vtx:
            tx.sha256 = None
            if not tx.is_valid():
                return False
            tx.calc_sha256()
            hashes.append(ser_uint256(tx.sha256))
        
        while len(hashes) > 1:
            newhashes = []
            for i in xrange(0, len(hashes), 2):
                i2 = min(i+1, len(hashes)-1)
                newhashes.append(SHA256.new(SHA256.new(hashes[i] + hashes[i2]).digest()).digest())
            hashes = newhashes
        
        if uint256_from_str(hashes[0]) != self.hashMerkleRoot:
            return False
        return True
    def __repr__(self):
        return "CBlock(nVersion=%i hashPrevBlock=%064x hashMerkleRoot=%064x nTime=%s nBits=%08x nNonce=%08x vtx=%s)" % (self.nVersion, self.hashPrevBlock, self.hashMerkleRoot, time.ctime(self.nTime), self.nBits, self.nNonce, repr(self.vtx))


