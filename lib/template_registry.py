import weakref
import binascii
import util
import StringIO
import settings
import struct
import gapcoin_hash

from twisted.internet import defer
from lib.exceptions import SubmitException

import lib.logger
log = lib.logger.get_logger('template_registry')
from mining.interfaces import Interfaces
from extranonce_counter import ExtranonceCounter
import lib.settings as settings


class JobIdGenerator(object):
    '''Generate pseudo-unique job_id. It does not need to be absolutely unique,
    because pool sends "clean_jobs" flag to clients and they should drop all previous jobs.'''
    counter = 0
    
    @classmethod
    def get_new_id(cls):
        cls.counter += 1
        if cls.counter % 0xffff == 0:
            cls.counter = 1
        return "%x" % cls.counter
                
class TemplateRegistry(object):
    '''Implements the main logic of the pool. Keep track
    on valid block templates, provide internal interface for stratum
    service and implements block validation and submits.'''
    
    def __init__(self, block_template_class, coinbaser, bitcoin_rpc, instance_id,
                 on_template_callback, on_block_callback):
        self.prevhashes = {}
        self.jobs = weakref.WeakValueDictionary()
        
        self.extranonce_counter = ExtranonceCounter(instance_id)
        self.extranonce2_size = block_template_class.coinbase_transaction_class.extranonce_size \
                - self.extranonce_counter.get_size()

        self.coinbaser = coinbaser
        self.block_template_class = block_template_class
        self.bitcoin_rpc = bitcoin_rpc
        self.on_block_callback = on_block_callback
        self.on_template_callback = on_template_callback
        
        self.last_block = None
        self.update_in_progress = False
        self.last_update = None
        
        # Create first block template on startup
        self.update_block()
        
    def get_new_extranonce1(self):
        '''Generates unique extranonce1 (e.g. for newly
        subscribed connection.'''
        log.debug("Getting Unique Extranonce")
        return self.extranonce_counter.get_new_bin()
    
    def get_last_broadcast_args(self):
        '''Returns arguments for mining.notify
        from last known template.'''
        #log.debug("Getting Laat Template")
        return self.last_block.broadcast_args
        
    def add_template(self, block, block_height):
        '''Adds new template to the registry.
        It also clean up templates which should
        not be used anymore.'''
        
        prevhash = block.prevhash_hex

        if prevhash in self.prevhashes.keys():
            new_block = False
        else:
            new_block = True
            self.prevhashes[prevhash] = []
               
        # Blocks sorted by prevhash, so it's easy to drop
        # them on blockchain update
        self.prevhashes[prevhash].append(block)
        
        # Weak reference for fast lookup using job_id
        self.jobs[block.job_id] = block
        
        # Use this template for every new request
        self.last_block = block
        
        # Drop templates of obsolete blocks
        for ph in self.prevhashes.keys():
            if ph != prevhash:
                del self.prevhashes[ph]
                
        log.info("New template for %s" % prevhash)

        if new_block:
            # Tell the system about new block
            # It is mostly important for share manager
            self.on_block_callback(block_height)

        # Everything is ready, let's broadcast jobs!
        self.on_template_callback(new_block)
        

        #from twisted.internet import reactor
        #reactor.callLater(10, self.on_block_callback, new_block) 
              
    def update_block(self):
        '''Registry calls the getblocktemplate() RPC
        and build new block template.'''
        
        if self.update_in_progress:
            # Block has been already detected
            return
        
        self.update_in_progress = True
        self.last_update = Interfaces.timestamper.time()
        
        d = self.bitcoin_rpc.getblocktemplate()
        d.addCallback(self._update_block)
        d.addErrback(self._update_block_failed)
        
    def _update_block_failed(self, failure):
        log.error(str(failure))
        self.update_in_progress = False
        
    def _update_block(self, data):
        start = Interfaces.timestamper.time()
                
        template = self.block_template_class(Interfaces.timestamper, self.coinbaser, JobIdGenerator.get_new_id())
        template.fill_from_rpc(data)
        self.add_template(template,data['height'])

        log.info("Update finished, %.03f sec, %d txes" % \
                    (Interfaces.timestamper.time() - start, len(template.vtx)))
        
        self.update_in_progress = False        
        return data
    
    def get_job(self, job_id):
        '''For given job_id returns BlockTemplate instance or None'''
        try:
            j = self.jobs[job_id]
        except:
            log.info("Job id '%s' not found" % job_id)
            return None
        
        # Now we have to check if job is still valid.
        # Unfortunately weak references are not bulletproof and
        # old reference can be found until next run of garbage collector.
        if j.prevhash_hex not in self.prevhashes:
            log.info("Prevhash of job '%s' is unknown" % job_id)
            return None
        
        if j not in self.prevhashes[j.prevhash_hex]:
            log.info("Job %s is unknown" % job_id)
            return None
        
        return j
        
    def submit_share(self, job_id, worker_name, session, extranonce1_bin, data, difficulty):
        
        job = self.get_job(job_id)
        if job == None:
            raise SubmitException("Job '%s' not found" % job_id)

        ntime = util.flip(data[136:144])
        if not job.check_ntime(int(ntime, 16)):
            raise SubmitException("Ntime out of range")
        
        if not job.register_submit(data):
            log.info("Duplicate from %s, (%s %s)" % \
                    (worker_name, binascii.hexlify(extranonce1_bin), data))
            raise SubmitException("Duplicate share")
        
        hash_int = gapcoin_hash.getpowdiff(str(data))
        block_hash_bin = util.doublesha(binascii.unhexlify(data[0:168]))
        block_hash_hex = util.rev(binascii.hexlify(block_hash_bin))

        '''log.info("block_hash_hex %s" % block_hash_hex)
        log.info("shrint %s" % hash_int)
        log.info("jobint %s" % job.target)%f
        log.info("target %s" % difficulty)'''

        if hash_int < difficulty:
            raise SubmitException("Share less than target")

        share_diff = float(float(hash_int) / float(pow(2, 48)))
        
        if hash_int >= job.target:
            log.info("BLOCK CANDIDATE! %s" % block_hash_hex)

            extranonce2_bin = struct.pack('>L', 0)
            #self.last_block.vtx[0].set_extranonce(extranonce1_bin + extranonce2_bin) 
            #txs = binascii.hexlify(util.ser_vector(self.last_block.vtx))

            job.vtx[0].set_extranonce(extranonce1_bin + extranonce2_bin) 
            txs = binascii.hexlify(util.ser_vector(job.vtx))
            serialized = str(data) + str(txs)

            on_submit = self.bitcoin_rpc.submitblock(str(data), str(txs), block_hash_hex)
            if on_submit:
                self.update_block()

            return (block_hash_hex, share_diff, on_submit)
        
        return (block_hash_hex, share_diff, None)


