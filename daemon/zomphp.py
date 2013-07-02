# -*- coding: utf-8 -*-

# 1 pinger that connects, 1 that listens to new, 1 that listens to killed/done, daddy kills, daddy gives, other workers

import socket
import os
import subprocess
import errno
import time

from threads import SoundSubmissiveDeamon, KillerDaddy
from utils import enum
from settings import BACKEND_CLASS_NAME, BACKEND_KWARGS
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

    def __init__(self, controller, thread_id, socket_suffix='', max_connections=socket.SOMAXCONN):
        '''
        `max_connections` is the max # of connections allowed on the socket
        '''
        super(ListenerThread, self).__init__(controller, thread_id)
        self._status = self.STATUS.NOT_STARTED
        self._socket_path = SOCKET_PATH_PREFIX + ('_' if socket_suffix else '') + socket_suffix
        self._max_connections = max_connections
        self._socket = None
        self._current_connection = None
        # the ongoing received data (might be distributed across several received)
        self._current_received_string = ''

    def process_item(self, item):
        '''
        Overriden by sub-classes to know what to do with the received data
        '''
        raise NotImplementedError

    def _connect_to_socket(self):
        '''
        Connects to the socket
        '''
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
    clean_up = _delete_socket_file


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

    def process_item(self, item):
        new_thread = Worker(self._controller, int(item), item)
        self._controller.sumbit_new_thread(new_thread)


class OutgoingRequestsListener(ListenerThread):
    '''
    Listens to PHP processes signing out (basically, when the SAPI dies)
    '''
    # TODO wkpo!!
    def process_item(self, item):
        self._controller.notify_completion(int(item))


class PingerThread(SoundSubmissiveDeamon):
    '''
    In charge of pinging all listener threads
    '''
    pass # TODO wkpo


class ZomPHPThreadController(KillerDaddy):
    '''
    The main thread controller class
    '''

    def __init__(self):
        super(ZomPHPThreadController, self).__init__() # TODO wkpo


class MainDeamon(object):

    def run(self):
        pass # TODO wkpo

if __name__ == '__main__': # TODO wkpo
    import logging
    logging.basicConfig(level=logging.DEBUG)
    class WkThread(ListenerThread):
        def process_item(self, item):
            print "dans %s on recoit : %s" % (self.displayable_name, item)
    c = ZomPHPThreadController()
    c.sumbit_new_thread(WkThread(c, 'in'))
    c.add_new_threads()

