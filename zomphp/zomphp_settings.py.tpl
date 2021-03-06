# -*- coding: utf-8 -*-

# your favorite backend class name and arguments to call the constructor
BACKEND_CLASS_NAME = 'DummyBackend'
BACKEND_KWARGS = {}

# Example for a Mongo backend
# BACKEND_CLASS_NAME = 'MongoBackend'
# BACKEND_KWARGS = {
#     'db_name': 'XXX',
#     'col_name': 'XXX',
#     'size': 104857600, # 100 MB
#     'host': 'XXX'
# }


# logging options
LOG_FILE = '/var/log/zomphp.log' # the daemon's owner must obviously have the right to write in there
LOG_LEVEL = 'DEBUG' # one of 'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL', otherwise defaults to 'INFO'


# the user to run ZomPHP's daemon as
# leave to None if you want to run it as 'root' (not recommended)
ZOMPHP_DEAMON_OWNER = None
