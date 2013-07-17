# -*- coding: utf-8 -*-

# if that setting is set to True, then your CLI scripts calling xdebug_start_code_coverage(XDEBUG_CC_ZOMPHP)
# will have to wait for up to a few hundred milliseconds before getting their socket
# any other SAPI than CLI will never wait, though
ENABLE_FOR_CLI = True

# your favorite backend class name and arguments to call the constructor
BACKEND_CLASS_NAME = 'MongoBackend'
BACKEND_KWARGS = {
    'db_name': 'jrouge_logs',
    'col_name': 'wk',
    'size': 45000,
    'host': 'dev-mongodb-01.local'
}

# logging options
LOG_FILE = '/tmp/zomphp.log' # set None to disable logging
LOG_LEVEL = 'DEBUG' # one of 'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL', otherwise defaults to 'WARNING'

# the user to run ZomPHP's daemon as
# leave to None if you want to run it as 'root' (not recommended)
ZOMPHP_DEAMON_OWNER = None
