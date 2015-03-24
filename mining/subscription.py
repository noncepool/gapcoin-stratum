from stratum.pubsub import Pubsub, Subscription
from mining.interfaces import Interfaces
import struct
import binascii
import lib.util as util
import lib.settings as settings
import lib.logger
log = lib.logger.get_logger('subscription')

class MiningSubscription(Subscription):
    #def __init__(self):
    '''This subscription object implements
    logic for broadcasting new jobs to the clients.'''
    
    event = 'mining.notify'
    
    @classmethod
    def on_template(cls, is_new_block):
        '''This is called when TemplateRegistry registers
           new block which we have to broadcast clients.'''
        
        start = Interfaces.timestamper.time()
        clean_jobs = is_new_block
        
        (job_id, prevhash, version, nbits, ntime, _) = Interfaces.template_registry.get_last_broadcast_args()     

        # Push new job to subscribed clients
        for subscription in Pubsub.iterate_subscribers(cls.event):
            try:
                if subscription != None:
                    session = subscription.connection_ref().get_session()
                    session.setdefault('authorized', {})
                    if session['authorized'].keys():
                        worker_name = session['authorized'].keys()[0]
                        extranonce1 = session.get('extranonce1', None)
                        extranonce2 = struct.pack('>L', 0)        
                        coinbase_bin = Interfaces.template_registry.last_block.serialize_coinbase(extranonce1, extranonce2)
                        coinbase_hash = util.doublesha(coinbase_bin)
                        merkle_root_bin = Interfaces.template_registry.last_block.merkletree.withFirst(coinbase_hash)
                        merkle_root = binascii.hexlify(merkle_root_bin)
                        job = {}
                        job['data'] = version + prevhash + merkle_root + ntime + nbits
                        job['difficulty'] = session['difficulty']
                        work_id = Interfaces.worker_manager.register_work(extranonce1, merkle_root, session['difficulty'], job_id, session['basediff']) 
                        subscription.emit_single(job)            
                    else:
                        continue
                  
            except Exception as e:
                log.exception("Error broadcasting work to client %s" % str(e))
                pass
        
        cnt = Pubsub.get_subscription_count(cls.event)
        log.info("BROADCASTED to %d connections in %.03f sec" % (cnt, (Interfaces.timestamper.time() - start)))
        
    def _finish_after_subscribe(self, result):
        return result
                
    def after_subscribe(self, *args):
        '''This will send new job to the client *after* he receive subscription details.
        on_finish callback solve the issue that job is broadcasted *during*
        the subscription request and client receive messages in wrong order.'''
        self.connection_ref().on_finish.addCallback(self._finish_after_subscribe)

