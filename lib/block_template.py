import StringIO
import binascii
import struct

import util
import merkletree
import halfnode
from coinbasetx import CoinbaseTransaction
import lib.logger
log = lib.logger.get_logger('block_template')

import settings

class BlockTemplate(halfnode.CBlock):
    '''Template is used for generating new jobs for clients.
    Let's iterate extranonce1, extranonce2, ntime and nonce
    to find out valid coin block!'''
    
    coinbase_transaction_class = CoinbaseTransaction
    
    def __init__(self, timestamper, coinbaser, job_id):
        super(BlockTemplate, self).__init__()
        
        self.job_id = job_id 
        self.timestamper = timestamper
        self.coinbaser = coinbaser
        
        self.prevhash_bin = '' # reversed binary form of prevhash
        self.prevhash_hex = ''
        self.timedelta = 0
        self.curtime = 0
        self.target = 0
        self.merkletree = None
                
        self.broadcast_args = []
        self.submits = [] 
                
    def fill_from_rpc(self, data):
        '''Convert getblocktemplate result into BlockTemplate instance'''
        
        txhashes = [None] + [ util.ser_uint256(int(t['hash'], 16)) for t in data['transactions'] ]
        mt = merkletree.MerkleTree(txhashes)
        coinbase = CoinbaseTransaction(self.timestamper, self.coinbaser, data['coinbasevalue'],
                                              data['coinbaseaux']['flags'], data['height'],
                                              settings.COINBASE_EXTRAS)

        self.height = data['height']
        self.nVersion = data['version']
        self.hashPrevBlock = int(data['previousblockhash'], 16)
        self.nBits = int(data['bits'], 16)

        self.hashMerkleRoot = 0
        self.nTime = 0
        self.nNonce = 0
        self.vtx = [ coinbase, ]
        
        for tx in data['transactions']:
            t = halfnode.CTransaction()
            t.deserialize(StringIO.StringIO(binascii.unhexlify(tx['data'])))
            self.vtx.append(t)
            
        self.curtime = data['curtime']
        self.timedelta = self.curtime - int(self.timestamper.time()) 
        self.merkletree = mt
        self.target = int(data['bits'], 16)
        self.network_diff = round(float(self.target) / float(pow(2, 48)), 8)
        log.info("Block: %i network difficulty: %0.8f" % (self.height, self.network_diff))

        # Reversed prevhash
        self.prevhash_bin = binascii.unhexlify(util.rev(data['previousblockhash']))
        self.prevhash_hex = "%064x" % self.hashPrevBlock
        
        self.broadcast_args = self.build_broadcast_args()
                
    def register_submit(self, data):
        '''Client submitted some solution. Let's register it to
        prevent double submissions.'''
        if data not in self.submits:
            self.submits.append(data)
            return True
        return False
            
    def build_broadcast_args(self):
        job_id = self.job_id
        prevhash = binascii.hexlify(self.prevhash_bin)
        version = binascii.hexlify(struct.pack("<i", self.nVersion))
        nbits = binascii.hexlify(struct.pack("<Q", self.nBits))
        ntime = binascii.hexlify(struct.pack("<I", self.curtime))
        clean_jobs = True
        #log.info("%s %s %s %s %s %s" % (job_id, prevhash, version, nbits, ntime, clean_jobs))
        return (job_id, prevhash, version, nbits, ntime, clean_jobs)

    def serialize_coinbase(self, extranonce1, extranonce2):
        '''Serialize coinbase with given extranonce1 and extranonce2
        in binary form'''
        (part1, part2) = self.vtx[0]._serialized
        return part1 + extranonce1 + extranonce2 + part2
    
    def check_ntime(self, ntime):
        '''Check for ntime restrictions.'''
        if ntime < self.curtime:
            return False        
        if ntime > (self.timestamper.time() + 7200):
            # Be strict on ntime into the near future
            # may be unnecessary
            return False        
        return True      

