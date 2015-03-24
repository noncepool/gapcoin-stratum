'''
This is example configuration for Stratum server.
Please rename it to config.py and fill correct values.

This is already setup with sane values for solomining.
You NEED to set the parameters in BASIC SETTINGS
'''

# ******************** BASIC SETTINGS ***************
# These are the MUST BE SET parameters!

ADMIN_PASSWORD_SHA256 = ''

CENTRAL_WALLET = ''

DAEMON_TRUSTED_HOST = 'localhost'
DAEMON_TRUSTED_PORT = 31397
DAEMON_TRUSTED_USER = 'user'
DAEMON_TRUSTED_PASSWORD = 'pass'

# ******************** GENERAL SETTINGS ***************
# Set process name of twistd, much more comfortable if you run multiple processes on one machine
STRATUM_MINING_PROCESS_NAME= 'gapcoin_stratum'

# Enable some verbose debug (logging requests and responses).
DEBUG = False

# Destination for application logs, files rotated once per day.
LOGDIR = 'log/'

# Main application log file.
LOGFILE = 'stratum.log'      # eg. 'stratum.log'
LOGLEVEL = 'INFO'
# Logging Rotation can be enabled with the following settings
# It if not enabled here, you can set up logrotate to rotate the files. 
# For built in log rotation set LOG_ROTATION = True and configure the variables
LOG_ROTATION = True
LOG_SIZE = 10485760 # Rotate every 10M
LOG_RETENTION = 10 # Keep 10 Logs

# How many threads use for synchronous methods (services).
# 30 is enough for small installation, for real usage
# it should be slightly more, say 100-300.
THREAD_POOL_SIZE = 300

# ******************** TRANSPORTS *********************
# Hostname or external IP to expose
HOSTNAME = 'localhost'

# Disable the example service
ENABLE_EXAMPLE_SERVICE = False

# Port used for Socket transport. Use 'None' for disabling the transport.
LISTEN_SOCKET_TRANSPORT = 3333
# Port used for HTTP Poll transport. Use 'None' for disabling the transport
LISTEN_HTTP_TRANSPORT = None
# Port used for HTTPS Poll transport
LISTEN_HTTPS_TRANSPORT = None
# Port used for WebSocket transport, 'None' for disabling WS
LISTEN_WS_TRANSPORT = None
# Port used for secure WebSocket, 'None' for disabling WSS
LISTEN_WSS_TRANSPORT = None

# Salt used for Block Notify Password
PASSWORD_SALT = 'some_crazy_string'

# ******************** Database  *********************
# MySQL
DB_MYSQL_HOST = 'localhost'
DB_MYSQL_DBNAME = 'db'
DB_MYSQL_USER = 'user'
DB_MYSQL_PASS = 'pass'
DB_MYSQL_PORT = 3306            # Default port for MySQL

# ******************** Adv. DB Settings *********************
#  Don't change these unless you know what you are doing

DB_LOADER_CHECKTIME = 15        # How often we check to see if we should run the loader
DB_LOADER_REC_MIN = 1          # Min Records before the bulk loader fires
DB_LOADER_REC_MAX = 75          # Max Records the bulk loader will commit at a time
DB_LOADER_FORCE_TIME = 300      # How often the cache should be flushed into the DB regardless of size.
DB_STATS_AVG_TIME = 300         # When using the DATABASE_EXTEND option, average speed over X sec
                                # Note: this is also how often it updates
DB_USERCACHE_TIME = 600         # How long the usercache is good for before we refresh

# ******************** Pool Settings *********************

# User Auth Options
USERS_AUTOADD = False           # Automatically add users to database when they connect.
                                # This basically disables User Auth for the pool.
USERS_CHECK_PASSWORD = False    # Check the workers password? (Many pools don't)

# Transaction Settings
COINBASE_EXTRAS = '/nonce-pool/'  # Extra Descriptive String to incorporate in solved blocks

# Coin Daemon communication polling settings (In Seconds)
PREVHASH_REFRESH_INTERVAL = 5   # How often to check for new Blocks
                                #   If using the blocknotify script (recommended) set = to MERKLE_REFRESH_INTERVAL
                                #   (No reason to poll if we're getting pushed notifications)
MERKLE_REFRESH_INTERVAL = 60    # How often check memorypool
                                #   This effectively resets the template and incorporates new transactions.
                                #   This should be "slow"

INSTANCE_ID = 31                # Used for extranonce and needs to be 0-31

# How long before work expires
WORK_EXPIRE = 180

# ******************** Pool Difficulty Settings *********************
# 13=1 13.693147181=2 14.386294362=4  15.079441543=8 15.772588724=16 16.465735905=32 17.158883086=64 17.852030267=128
# 18.545177448=256 19.238324629=512 19.93147181=1024 20.624618991=2048
BASE_POOL_TARGET = 281474976710656 # pow(2, 48)
POOL_SHARE = 16                    # getwork proxy share value

POOL_TARGET = 15.772588724         # Initial pool target whole integer + any multiple of 0.693147181

VARIABLE_DIFF = True               # Master variable difficulty enable

# Variable diff tuning variables
#VARDIFF will start at the POOL_TARGET. It can go as low as the VDIFF_MIN and as high as min(VDIFF_MAX or DAEMONs difficulty)
VDIFF_MIN_TARGET = 15.079441543    # Minimum target difficulty same as POOL_TARGET
VDIFF_MAX_TARGET = 20.624618991    # Maximum target difficulty 
VDIFF_TARGET_TIME = 30             # Target time per share (i.e. try to get 1 share per this many seconds)
VDIFF_RETARGET_TIME = 90           # Check to see if we should retarget this often
VDIFF_VARIANCE_PERCENT = 30        # Allow average time to very this % from target without retarget

# Allow external setting of worker difficulty, checks pool_worker table datarow[6] position for target difficulty
# if present or else defaults to pool target, over rides all other difficulty settings, no checks are made
# for min or max limits this should be done by your front end software
ALLOW_EXTERNAL_DIFFICULTY = False 

# ******************** Worker Ban Options *********************
ENABLE_WORKER_STATS = False     # Master stats control disable to reduce server load
ENABLE_WORKER_BANNING = True    # Enable/disable temporary worker banning 
WORKER_CACHE_TIME = 600         # How long the worker stats cache is good before we check and refresh
WORKER_BAN_TIME = 300           # How long we temporarily ban worker
INVALID_SHARES_PERCENT = 500     # Allow average invalid shares vary this % before we ban
INVALID_SHARES_SPAM = 100     # Ban if we have this many invalids total before check time



