# -*- coding: utf-8 -*-

# 1 pinger that connects, 1 that listens to new, 1 that listens to killed/done, daddy kills, daddy gives, other workers

import socket
import os
import subprocess
import errno
import time
import datetime
import logging

from threads import SoundSubmissiveDeamon, KillerDaddy
from utils import enum
from settings import BACKEND_CLASS_NAME, BACKEND_KWARGS, ENABLE_FOR_CLI, LOG_FILE, LOG_LEVEL
from constants import SOCKET_PATH_PREFIX
import backend


class ListenerThread(SoundSubmissiveDeamon):
    '''
    A generic class for listener threads
    '''

    STATUS = enum('NOT_STARTED', 'LISTENING', 'RECEIVING')

    # sub-classes can change that, but no reason too IMHO
    # and from the doc : "For best match with hardware and network realities, the value of bufsize should be a relatively small power of 2"
    RCV_CHUNK_SIZE = 1024

    # the separator between two items
    ITEM_SEPARATOR = '\n'

    def __init__(self, controller, thread_id, max_connections=socket.SOMAXCONN):
        '''
        `max_connections` is the max # of connections allowed on the socket
        '''
        super(ListenerThread, self).__init__(controller, thread_id)
        self._status = self.STATUS.NOT_STARTED
        self._socket_path = self.get_socket_path_from_id(thread_id)
        self._max_connections = max_connections
        self._socket = None
        self._current_connection = None
        # the ongoing received data (might be distributed across several received)
        self._current_received_string = ''

    @staticmethod
    def get_socket_path_from_id(thread_id):
        socket_suffix = str(thread_id)
        return SOCKET_PATH_PREFIX + ('_' if socket_suffix else '') + socket_suffix

    def process_item(self, item):
        '''
        Overriden by sub-classes to know what to do with the received data
        '''
        raise NotImplementedError

    def _connect_to_socket(self):
        '''
        Connects to the socket
        '''
        logging.debug('Listener %s opening its socket' % self.displayable_name)
        self._socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        # remove the old file, if any
        self._delete_socket_file()
        # then connect
        self._socket.bind(self._socket_path)
        # then allow everyone to connect to it
        subprocess.call("chmod 777 %s" % self._socket_path, shell=True)
        # and listen!
        self._socket.listen(self._max_connections)
        self._status = self.STATUS.LISTENING
        logging.debug('Listener %s successfully opened its socket' % self.displayable_name)

    def _accept_connection(self):
        '''
        Accepts an incoming connection
        '''
        self._current_connection, _ = self._socket.accept()
        self._status = self.STATUS.RECEIVING

    def _receive_data(self):
        '''
        Receives data from the current connection
        '''
        data = self._current_connection.recv(self.RCV_CHUNK_SIZE)
        if data:
            # process whatever we've received
            self._process_received_data(data)
        else:
            # let's get ready for the next connection
            self._current_connection = None
            self._status = self.STATUS.LISTENING

    def _process_received_data(self, data):
        '''
        Unpacks the received data to re-build the individual messages
        '''
        self._current_received_string += data
        new_items_raw, _, self._current_received_string = self._current_received_string.rpartition(self.ITEM_SEPARATOR)
        for new_item in new_items_raw.split(self.ITEM_SEPARATOR):
            if new_item:
                logging.debug('Listener %s processing new data: %s' % (self.displayable_name, new_item))
                self.process_item(new_item)

    def do_work(self):
        {
            self.STATUS.NOT_STARTED: lambda: self._connect_to_socket(),
            self.STATUS.LISTENING: lambda: self._accept_connection(),
            self.STATUS.RECEIVING: lambda: self._receive_data()
        }[self._status]()

    def _delete_socket_file(self):
        '''
        Deletes the socket file
        '''
        try:
            os.remove(self._socket_path)
        except OSError as ex:
            if ex.errno != errno.ENOENT:
                # otherwise just means there's nothing to remove
                # but any other error is not normal
                raise

    # we just remove the socket when we're done
    def clean_up(self, killed=False):
        self._delete_socket_file()


class Worker(ListenerThread):
    '''
    The main type of thread: in charge of getting the data from PHP processes and pushing it to the backend
    '''

    def __init__(self, *args, **kwargs):
        super(Worker, self).__init__(*args, **kwargs)
        # build the backend
        self._backend = getattr(backend, BACKEND_CLASS_NAME)(**BACKEND_KWARGS)

    def process_item(self, item):
        # just push to the backend
        self._backend.record(item)


class IncomingRequestsListener(ListenerThread):
    '''
    A thread that listens for requests for sockets from PHP processes
    and creates the relevant listener threads
    '''

    IN_LISTENER_ID = 'in'
    IN_CLI_LISTENER_ID = 'in_cli'
    OUT_LISTENER_ID = 'out'

    def process_item(self, item):
        new_thread = Worker(self._controller, int(item))
        self._controller.sumbit_new_thread(new_thread)


class OutgoingRequestsListener(ListenerThread):
    '''
    Listens to PHP processes signing out (basically, when the SAPI dies)
    '''

    def process_item(self, item):
        self._controller.notify_completion(int(item))


class PingerThread(SoundSubmissiveDeamon):
    '''
    In charge of pinging all listener threads
    '''

    PINGER_THREAD_ID = 'pinger'

    def __init__(self, controller):
        '''
        There's only one such thread!
        '''
        logging.debug('Pinger thread alive')
        super(PingerThread, self).__init__(controller, self.PINGER_THREAD_ID)
        self._thread_ids = []

    def do_work(self):
        try:
            child_id = self._thread_ids.pop()
            if isinstance(child_id, int):
                # otherwise it's one of the 4 control threads, no need to ping it
                ZomPHPThreadController.ping_listener(child_id)
        except IndexError:
            # the list is empty, we need to grab a new fresh one from daddy!
            self._thread_ids = self._controller.get_current_children_ids()
            # we don't want to be looping too fast on that, nothing critical here
            time.sleep(1)


class ZomPHPThreadController(KillerDaddy):
    '''
    The main thread controller class
    '''

    def __init__(self):
        super(ZomPHPThreadController, self).__init__()
        self.cleanup()
        # add the listener threads according the configuration
        self.sumbit_new_thread(IncomingRequestsListener(self, IncomingRequestsListener.IN_LISTENER_ID))
        self.sumbit_new_thread(OutgoingRequestsListener(self, IncomingRequestsListener.OUT_LISTENER_ID))
        if ENABLE_FOR_CLI:
            self.sumbit_new_thread(IncomingRequestsListener(self, IncomingRequestsListener.IN_CLI_LISTENER_ID))
        # and the pinger thread
        self.sumbit_new_thread(PingerThread(self))
        logging.debug('Controller successfully loaded!')

    @staticmethod
    def cleanup():
        '''
        Deletes all the old sockets
        '''
        logging.info('Deleting all old sockets')
        subprocess.call(r'rm -f %s*' % SOCKET_PATH_PREFIX, shell=True)

    @staticmethod
    def ping_listener(child_id):
        '''
        Tries to ping a child socket, but will ignore any error
        '''
        socket_path = ListenerThread.get_socket_path_from_id(child_id)
        try:
            sckt = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            sckt.connect(socket_path)
            sckt.send(ListenerThread.ITEM_SEPARATOR)
            sckt.close()
        except socket.error as ex:
            logging.debug('Got a socket error when pinging %s : %s' % (socket_path, ex))

    def ping_all_listeners(self):
        '''
        Pings all listeners, including control threads
        Meant to be called exclusively from daddy
        '''
        for child_id in self._threads.keys():
            if child_id != PingerThread.PINGER_THREAD_ID:
                self.ping_listener(child_id)


class ZomPHPApp(object):

    # the minimum time spent in one cycle, in SECONDS (can, and obviously should, be a float)
    MIN_TIME_ONE_CYCLE = 0.05

    def __init__(self):
        self._controller = ZomPHPThreadController()
        self._last_run_date = datetime.datetime.now()

    def run(self):
        try:
            while True:
                self._last_run_date = datetime.datetime.now()
                self._do_one_cycle()
                self._sleep()
        except BaseException as ex:
            logging.error('Caught exception %s, cleaning up and shutting down' % ex.__class__.__name__)
            self._controller.kill_em_all()
            # we ping all listeners to make sure they get the 'kill' order
            self._controller.ping_all_listeners()
            self._controller.cleanup()
            raise

    def _do_one_cycle(self):
        # take care of all your children, daddy
        self._controller.check_children_failures()
        self._controller.remove_done_threads()
        self._controller.add_new_threads()

    def _sleep(self):
        '''
        If the cycle has taken less time than MIN_TIME_ONE_CYCLE s, we sleep to complete
        '''
        diff = self.MIN_TIME_ONE_CYCLE - (datetime.datetime.now() - self._last_run_date).total_seconds()
        if diff >= 0:
            time.sleep(diff)
        else:
            logging.debug('Didn\'t have to sleep! (took %s s more)' % -diff)


if __name__ == '__main__':
    if LOG_FILE:
        # set the right logging if set to
        # TODO wkpo rights?
        log_level = getattr(logging, LOG_LEVEL, logging.WARNING)
        logging.basicConfig(level=log_level)
        handler = logging.FileHandler(LOG_FILE)
        logger = logging.getLogger('zomphp')
        logger.addHandler(handler)
        logger.setLevel(log_level)
    app = ZomPHPApp()
    app.run()
