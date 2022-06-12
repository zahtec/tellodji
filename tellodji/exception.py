'''
Exception class decorator for calling methods and changing attributes when an error is raised within any class methods
Made by zahtec (https://www.github.com/zahtec)
'''

from inspect import getmembers
from typing import get_args, get_origin, get_type_hints
from .tello_error import TelloError

def exception(cls):
    def decor(func):
        def inner(self, *args, **kwargs):
            if not self._running: raise TelloError('The tello class has been exited. No more methods can be run afterwards')
            try:
                return func(self, *args, **kwargs)
            except Exception as e:
                # Code to run when an exception is raised with the exception bound to e
                if not 'Timed out.' in str(e) and self._sm and self._flying:
                    self._send_sync('land', 'basic')
                    if self._debug: print('[TELLO] Error raised. Landing drone')
                self._running = False
                raise e

        return inner

    for m in getmembers(cls, lambda t: True if callable(t) else False):
        if not '__' in m[0]: setattr(cls, m[0], decor(m[1]))

    return cls