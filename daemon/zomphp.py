#!/usr/bin/env python
# -*- coding: utf-8 -*-

# TODO wkpo venv?

import socket
import os
import sys
import subprocess
import errno
import time
import datetime
import logging
import argparse

if os.path.exists('/etc/zomphp/settings.py'):
    sys.path.append('/etc/zomphp')

from threads import SoundSubmissiveDeamon, KillerDaddy
from utils import enum, set_logger
from settings import BACKEND_CLASS_NAME, BACKEND_KWARGS, ENABLE_FOR_CLI, ZOMPHP_DEAMON_OWNER
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

    # if a listener thread has received no meaningful data in that many seconds, it kills itself
    # sub-classes can override this to 0 to say a thread should never timeout
    MAX_IDLE_SPAN = 600 # 10 minutes

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
        self._last_significant_item = datetime.datetime.now()

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
                self._last_significant_item = datetime.datetime.now()
                self.process_item(new_item)

    def do_work(self):
        {
            self.STATUS.NOT_STARTED: lambda: self._connect_to_socket(),
            self.STATUS.LISTENING: lambda: self._accept_connection(),
            self.STATUS.RECEIVING: lambda: self._receive_data()
        }[self._status]()
        self._check_timeout()

    def _check_timeout():
        '''
        Checks this thread has been processing some significant data lately,
        otherwise terminates it
        '''
        if self.MAX_IDLE_SPAN <= 0:
            # means that class of thread should never time out
            return
        seconds_idle = (datetime.datetime.now() - self._last_significant_item).total_seconds()
        if seconds_idle >= self.MAX_IDLE_SPAN:
            logging.info('Listener %s has been idle for too long (%s seconds VS %d max allowed), shutting down' % (self.displayable_name, seconds_idle, self.MAX_IDLE_SPAN))
            self.work_done()

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

    # those listener threads should never time out
    MAX_IDLE_SPAN = 0

    IN_LISTENER_ID = 'in'
    IN_CLI_LISTENER_ID = 'in_cli'

    def process_item(self, item):
        new_thread = Worker(self._controller, int(item))
        self._controller.sumbit_new_thread(new_thread)


class OutgoingRequestsListener(ListenerThread):
    '''
    Listens to PHP processes signing out (basically, when the SAPI dies)
    '''

    # shouldn't time out either
    MAX_IDLE_SPAN = 0

    OUT_LISTENER_ID = 'out'

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
        self.sumbit_new_thread(OutgoingRequestsListener(self, OutgoingRequestsListener.OUT_LISTENER_ID))
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

    # the amount of time given to children before killing them -9 at shutdown time (in seconds)
    GRACE_PERIOD = 60

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
            logging.error('Caught exception %s (%s), cleaning up and shutting down' % (ex.__class__.__name__, ex))
            logging.exception(ex)
            # we ping all listeners to make sure they get the 'kill' order
            try:
                self._controller.kill_em_all()
                self._controller.ping_all_listeners()
                self._controller.cleanup()
            except BaseException as exc:
                # we're shutting down anyway, just log it and ignore it
                logging.error('Exception of type %s when trying to shut down (%s)!' % (exc.__class__.__name__, exc))
                logging.exception(ex)
            # force shut down in any case!
            # we still give children a reasonable amount of time to shut down gracefully
            time.sleep(self.GRACE_PERIOD)
            subprocess.call('kill -9 %d' % os.getpid(), shell=True)

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


def main():
    # argument processing
    parser = argparse.ArgumentParser(
        description='Detect your PHP dead code'
    )
    parser.add_argument('--get-owner', dest='get_owner', action='store_const',
                        const=True, default=False, help='Outputs the deamon\'s owner'
                        ' as set in the configuration, then exits')
    args = parser.parse_args()

    if args.get_owner:
        print ZOMPHP_DEAMON_OWNER if ZOMPHP_DEAMON_OWNER else 'root'
    else:
        # normal operation
        set_logger()
        app = ZomPHPApp()
        app.run()


if __name__ == '__main__':
    main()
