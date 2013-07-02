# -*- coding: utf-8 -*-

'''
A few helper classes to handle thread pools
'''

import logging
import datetime
import time

from Queue import Queue, Empty
from threading import Thread


class KillException(BaseException):
    '''
    An exception raised in threads when ordered to die, can't be catched (at least not as an Exception)
    '''
    pass


class ExceptionBuffer(object):
    '''
    An object that will buffer exceptions, but not too many in too short a time
    '''

    # see __init__'s doc below
    _DEFAULT_MAX_EXCPTS = 3
    _DEFAULT_MAX_SPAN = 300 # 5 minutes # TODO wkpo mettre 300

    def __init__(self, max_excpts=_DEFAULT_MAX_EXCPTS, max_span=_DEFAULT_MAX_SPAN):
        '''
        Won't accept to buffer more than `max_excpts` in `max_span` seconds
        '''
        self._errors = {}
        self._max_excpts = max_excpts
        self._max_span = max_span

    def clean(self):
        '''
        Forgets about exceptions older than `self._max_span` minutes
        '''
        limit = datetime.datetime.now() - datetime.timedelta(seconds=self._max_span)
        self._errors = {k: v for k, v in self._errors.items() if k > limit}

    def buffer_exception(self, excp):
        '''
        Silently absobrs `excp` except if that's too many
        Retunrs False if it's too many
        '''
        self.clean()
        self._errors[datetime.datetime.now()] = excp
        if len(self._errors) > self._max_excpts:
            logging.error('Too many errors too quickly!')
            for e in self._errors.values():
                logging.exception(e)
            return False
        # let's give it some time, you never know
        time.sleep(1)
        return True


class SoundSubmissiveDeamon(Thread):
    '''
    An IDed deamon thread that notifies daddy (in the form of a controller class) if it dies unexpectedly too often
    It also gets killed if/when it calls stop_if_killed() after kill() has been called by the main thread
    '''

    def __init__(self, controller, thread_id):
        '''
        The controller is expected to be a KillerDaddy
        The ID can be anything, as long as it's hashable and well, unique.
        '''
        super(SoundSubmissiveDeamon, self).__init__(target=self.work, name=str(thread_id))
        self._id = thread_id
        self._controller = controller
        self._killed = False
        self._running = False
        self._exception_buffer = ExceptionBuffer()

    @property
    def id(self):
        return self._id

    @property
    def displayable_name(self):
        return 'Thread ID %s' % self._id

    def work(self):
        logging.debug('Starting %s' % self.displayable_name)
        self._running = True
        while self._running:
            try:
                self.do_work()
                self._stop_if_killed()
            except KillException:
                break
            except Exception as ex:
                if not self._exception_buffer.buffer_exception(ex):
                    self._controller.notify_failure(self, ex)
                    raise
        logging.debug('%s stopping and cleaning up!' % self.displayable_name)
        self._shutdown()

    def kill(self):
        self._killed = True

    def _shutdown(self):
        self.clean_up()
        self._controller.notify_completion(self)

    def _stop_if_killed(self):
        if self._killed:
            logging.error('%s was ordered to die, cleaning up and stopping' % self.displayable_name)
            self.clean_up(killed=True)
            raise KillException

    def do_work(self):
        '''
        Should be a short & quick elementary operation
        '''
        raise NotImplementedError

    def clean_up(self, killed=False):
        '''
        Child classes have a chance of doing some cleanup
        The flag says whether it's due to a kill order
        '''
        pass

    def work_done(self):
        '''
        Should be called by sub-classes when this thread can peacefully die
        '''
        self._running = False


class KillerDaddy(object):
    '''
    A controller class that owns a pool of children threads and kills 'em all
    when one of them dies unexpectedly
    '''

    def __init__(self):
        # a dict of thread ids => thread object
        self._threads = {}
        self._error_queue = Queue()
        self._done_queue = Queue()
        self._create_queue = Queue()

    def notify_failure(self, child, exception):
        '''
        Meant to be called from the children to notify when they fail
        '''
        self._error_queue.put((child, exception))

    def check_children_failures(self):
        '''
        Meant to be called from daddy
        Will kill the main thread and all its children if one the children is dead
        '''
        try:
            child, exception = self._error_queue.get_nowait()
            # sonny is dead, daddy cannot live on... long live to daddy
            logging.error('Main thread received an exception from child: %s, re-throwing and killing \'em all' % child.displayable_name)
            self.kill_em_all()
            raise KillException
        except Empty:
            # no error in the queue, daddy can live another day
            return
    
    @staticmethod
    def _do_kill_child(child):
        try:
            child.kill()
        except Exception:
            # will faill iff the child is already dead, which is no big deal
            pass

    def kill_em_all(self):
        '''
        Kills all children threads
        Meant to be called from daddy
        '''
        for child in self._threads.values():
            self._do_kill_child(child)

    @staticmethod
    def _get_child_id(child):
        '''
        Small utilitary function for methods that accept either child objects or ids
        '''
        if isinstance(child, SoundSubmissiveDeamon):
            return child.id
        return child

    def kill_child(self, child):
        '''
        Kill a child identified by its id
        Returns True if done, False otherwise
        '''
        child_id = self._get_child_id(child)
        if child_id in self._threads:
            self._do_kill_child(self._threads[child_id])
            return True
        return False

    def notify_completion(self, child):
        '''
        Meant to be called from the children to notify when they've exited gracefully
        Can pass an id directly, too
        '''
        self._done_queue.put(self._get_child_id(child))

    def sumbit_new_thread(self, thread):
        '''
        Can be called by anyone
        '''
        self._create_queue.put(thread)

    def _add_thread(self, thread):
        '''
        Can be called by anyone, but up to you to prevent race conditions!
        This should only be possibly called by one thread at any point in time
        (better to leave it to the main thread IMHO)
        Also starts the new thread
        '''
        self._threads[thread.id] = thread
        thread.start()

    def remove_done_thread(self):
        '''
        Meant to be called from daddy
        '''
        while True:
            try:
                child_id = self._done_queue.get_nowait()
                self._threads.pop(child_id, None)
            except Empty:
                # we're done
                break

    def add_new_threads(self):
        '''
        Meant to be called from daddy
        '''
        while True:
            try:
                new_thread = self._create_queue.get_nowait()
                self._add_thread(new_thread)
            except Empty:
                # we're done
                break

if __name__ == '__main__': # TODO wkpo
    pass

