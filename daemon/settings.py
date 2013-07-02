# -*- coding: utf-8 -*-

# the path to ZomPHP sockets (modulo a suffix)
# must have r+w+x access for both the user running ZomPHP and the users running the PHP processes (777 works great, if you can afford it)
SOCKET_PATH_PREFIX = '/tmp/zomphp_socket'

# if that setting is set to True, then your CLI scripts calling xdebug_start_code_coverage(XDEBUG_CC_ZOMPHP)
# will have to wait for up to a few hundred milliseconds before getting their socket
# any other SAPI than CLI will never wait, though
ENABLE_FOR_CLI = True # TODO wkpo
