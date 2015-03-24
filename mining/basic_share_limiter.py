import lib.settings as settings

import lib.logger
log = lib.logger.get_logger('BasicShareLimiter')

import DBInterface
dbi = DBInterface.DBInterface()
#dbi.clear_worker_diff()

from twisted.internet import defer
from mining.interfaces import Interfaces
import time

''' This is just a customized ring buffer '''
class SpeedBuffer:
    def __init__(self, size_max):
        self.max = size_max
        self.data = []
        self.cur = 0
        
    def append(self, x):
        self.data.append(x)
        self.cur += 1
        if len(self.data) == self.max:
            self.cur = 0
            self.__class__ = SpeedBufferFull
            
    def avg(self):
        return sum(self.data) / self.cur
       
    def pos(self):
        return self.cur
           
    def clear(self):
        self.data = []
        self.cur = 0
            
    def size(self):
        return self.cur

class SpeedBufferFull:
    def __init__(self, n):
        raise "you should use SpeedBuffer"
           
    def append(self, x):                
        self.data[self.cur] = x
        self.cur = (self.cur + 1) % self.max
            
    def avg(self):
        return sum(self.data) / self.max
           
    def pos(self):
        return self.cur
           
    def clear(self):
        self.data = []
        self.cur = 0
        self.__class__ = SpeedBuffer
            
    def size(self):
        return self.max

class BasicShareLimiter(object):
    def __init__(self):
        self.worker_stats = {}
        self.target = settings.VDIFF_TARGET_TIME
        self.retarget = settings.VDIFF_RETARGET_TIME
        self.variance = self.target * (float(settings.VDIFF_VARIANCE_PERCENT) / float(100))
        self.tmin = self.target - self.variance
        self.tmax = self.target + self.variance
        self.buffersize = self.retarget / self.target * 4
        # TODO: trim the hash of inactive workers

    def submit(self, connection_ref, job_id, current_difficulty, timestamp, worker_name, extranonce1_bin):
        ts = int(timestamp)

        # Init the stats for this worker if it isn't set.        
        if extranonce1_bin not in self.worker_stats or self.worker_stats[extranonce1_bin]['last_ts'] < ts - settings.DB_USERCACHE_TIME :
            self.worker_stats[extranonce1_bin] = {'last_rtc': (ts - self.retarget / 2), 'last_ts': ts, 'buffer': SpeedBuffer(self.buffersize) }
            dbi.update_worker_diff(worker_name, settings.POOL_TARGET)
            return
        
        # Standard share update of data
        self.worker_stats[extranonce1_bin]['buffer'].append(ts - self.worker_stats[extranonce1_bin]['last_ts'])
        self.worker_stats[extranonce1_bin]['last_ts'] = ts

        # Do We retarget? If not, we're done.
        if ts - self.worker_stats[extranonce1_bin]['last_rtc'] < self.retarget and self.worker_stats[extranonce1_bin]['buffer'].size() > 0:
            return

        # Set up and log our check
        self.worker_stats[extranonce1_bin]['last_rtc'] = ts
        avg = self.worker_stats[extranonce1_bin]['buffer'].avg()
        log.info("Checking Retarget for %s diff:(%f) avg:(%i) target %i+-%i" % (worker_name, current_difficulty, avg,
                self.target, self.variance))
        
        if avg < 1:
            log.warning("Reseting avg = 1 since it's SOOO low")
            avg = 1

        ddiff = settings.POOL_TARGET

        if (avg > self.tmax and current_difficulty > settings.VDIFF_MIN_TARGET):
            # For fractional -0.1 ddiff's just drop by 2
            ddiff = current_difficulty - 0.693147181
            if ddiff < settings.VDIFF_MIN_TARGET:
               ddiff = settings.VDIFF_MIN_TARGET
        elif avg < self.tmin:
            # For fractional 0.1 ddiff's just up by 2 e.g. 0.693147181
            ddiff = current_difficulty + 0.693147181
            if ddiff > settings.VDIFF_MAX_TARGET:
               ddiff = settings.VDIFF_MAX_TARGET
        else:  # If we are here, then we should not be retargeting.
            return

        # At this point we are retargeting this worker
        new_diff = int(settings.BASE_POOL_TARGET * ddiff)
        log.info("Retarget for %s old: %f new: %f raw: %i" % (worker_name, current_difficulty, ddiff, new_diff))

        self.worker_stats[extranonce1_bin]['buffer'].clear()
        session = connection_ref().get_session()
        session['difficulty'] = new_diff
        session['basediff'] = ddiff
        dbi.update_worker_diff(worker_name, ddiff)

