# -*- coding: utf-8 -*-

import logging # TODO wkpo

import pymongo


class BaseBackend(object):
    '''
    A base class that any backend must extend, and override its methods
    '''

    def record(self, function):
        '''
        `function` is a string formatted in the ZomPHP usual form, i.e. path/to/file.php:funcName:lineNo
        Report to whatever backend lies here
        '''
        raise NotImplementedError

class MongoBackend(BaseBackend):
    '''
    Just records everything in mongo
    '''

    # the key for mongo_record (make it short!)
    _KEY_NAME = 'l'
    # the name for our index
    _INDEX_NAME = 'zomphp_index'

    def __init__(self, db_name, col_name, size, *mongo_client_args, **mongo_client_kwargs):
        '''
        The size is the size of the Mongo capped collection (in bytes)
        The last 2 args are passed as is to pymongo's MongoClient's constuctor
        (see http://api.mongodb.org/python/current/api/pymongo/mongo_client.html#pymongo.mongo_client.MongoClient)
        '''
        client = pymongo.MongoClient(*mongo_client_args, **mongo_client_kwargs)
        self._create_mongo_col(client, db_name, col_name, size)
        self._mongo_col = client[db_name][col_name]
        self._ensure_index()

    @staticmethod
    def _create_mongo_col(client, db_name, col_name, size):
        '''
        Creates the right Mongo collection, if not present
        If it is present, it checks that it's got the right settings, otherwise it deletes it
        and re-creates it
        '''
        db_object = client[db_name]
        try:
            return db_object.create_collection(col_name, capped=True, size=size, autoIndexId=False)
        except pymongo.errors.CollectionInvalid:
            # the collection already exists, we check it has the right settings
            # otherwise delete it, and re-create it!
            logging.info('Checking %s.%s\'s settings' % (db_name, col_name))
            if not MongoBackend._check_coll_setings(client, db_object[col_name], size):
                logging.info('Wrong settings, dropping and re-creating collection')
                db_object.drop_collection(col_name)
                return MongoBackend._create_mongo_col(client, db_name, col_name, size)

    @staticmethod
    def _check_coll_setings(client, col_object, size):
        '''
        Returns true iff the settings are OK
        '''
        # first no autoIndexId
        for idx in col_object.index_information().values():
            # TODO wkpo ensure pymongo's right version, esp >= 1.7
            if idx['key'] == [(u'_id', 1)]:
                logging.debug('Found an index on _id')
                return False
        # then that it's capped, with the right size
        options = col_object.options()
        if not options.get('capped', False):
            logging.debug('Collection not capped')
            return False
        if options.get('size', -1) != size:
            logging.debug('Capped collection does not have the right size (expected %d VS actual %d)' % (size, options.get('size', -1)))
            return False
        # all good!
        return True

    def _ensure_index(self):
        '''
        Ensures we have the right index on the coll
        '''
        self._mongo_col.ensure_index(self._KEY_NAME, name=self._INDEX_NAME, unique=True, dropDups=True)

    def record(self, function):
        doc = {self._KEY_NAME: function}
        self._mongo_col.update(doc, doc, upsert=True, manipulate=False, w=0, check_keys=False)


if __name__ == '__main__': # TODO wkpo
    logging.basicConfig(level=logging.DEBUG)
    b = MongoBackend('jrouge_logs', 'wk', 10000, host='dev-mongodb-01.local')
    b.record('coucou')
    b.record('wkpo')
    b.record('coucou')

