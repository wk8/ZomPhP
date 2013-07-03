# -*- coding: utf-8 -*-


def enum(*enums):
    '''
    Implements enums (only exists in versions >= 3.4)
    '''
    return type('Enum', (), {e: e for e in enums})
