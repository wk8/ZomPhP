# -*- coding: utf-8 -*-

# if that setting is set to True, then your CLI scripts calling xdebug_start_code_coverage(XDEBUG_CC_ZOMPHP)
# will have to wait for up to a few hundred milliseconds before getting their socket
# any other SAPI than CLI will never wait, though
ENABLE_FOR_CLI = True # TODO wkpo

# your favorite backend class name and arguments to call the constructor
BACKEND_CLASS_NAME = 'MongoBackend'
BACKEND_KWARGS = {
    'db_name': 'XXX',
    'col_name': 'XXX',
    'size': 104857600, # 100 MB
    'host': 'XXX'
}