'''
Class decorator for changing attributes when an error is raised within any class methods and enforced type checking.
May be reused, although it only goes 2 layers deep into typing specifically for TelloDji
Made by zahtec (https://www.github.com/zahtec)
'''

from typing import Callable, get_origin, get_args, Union
from inspect import getmembers, getfullargspec
from .tello_error import TelloError

def check_typing(func, args, kwargs):
    spec = getfullargspec(func)
    typing = {}

    i = 0
    for arg in spec.args:
        if arg == 'self': continue
        try: annotation = spec.annotations[arg]
        except: annotation = False

        if annotation: typing.update({ i: get_args(annotation) if get_origin(annotation) is Union else annotation })
        else: typing.update({ i: None })

        i += 1

    def check(arg, expected, iter):
        typ = Callable if isinstance(arg, Callable) else type(arg)

        if iter:
            if typ not in [get_origin(type) if get_origin(type) and type is not Callable else type for type in expected]: raise TypeError(f'Expected types {[t.__name__ if type(t) is not tuple else t for t in expected]}, instead got {typ.__name__}')
        else:
            if typ is not (get_origin(expected) if get_origin(expected) else expected): raise TypeError(f'Expected type {expected.__name__}, instead got {typ.__name__}')

        if typ in (tuple, list):
            if iter:
                for t in expected:
                    if get_origin(t) and t is not Callable:
                        t_args = get_args(t)
                        t_args_deep = get_args(*t_args)

                        if t_args_deep: new_expected_type = [a for a in t_args_deep]
                        else: new_expected_type = [a for a in t_args]
            else:
                expected_args = get_args(expected_type)
                if expected_args: new_expected_type = [a for a in expected_args]
                else: new_expected_type = [expected_type]

            for item in arg:
                arg_type = type(item)
                if arg_type not in [get_args(type) if get_args(type) else type for type in new_expected_type]: raise TypeError(f'Expected type(s) {[t.__name__ if type(t) is not tuple else t for t in new_expected_type]}, instead got {arg_type.__name__}')

    for index, arg in enumerate(args):
        typing_iterable = type(typing[index]) is tuple

        if typing_iterable: expected_type = [get_args(type) if get_origin(type) is Union else type for type in typing[index]]
        else: expected_type = typing[index]

        if expected_type: check(arg, expected_type, typing_iterable)

    if 'preferences' in spec.annotations:
        kw = spec.annotations['preferences']
        typing = get_args(kw) if get_origin(kw) else kw
        for kwarg in kwargs.values(): check(kwarg, typing, type(typing) is tuple)

def tello_decor(cls):

    def decor(func):
        def inner(self, *args, **kwargs):
            if not self._running: raise TelloError('The tello class has been exited. No more methods can be run afterwards')
            try:
                check_typing(func, args, kwargs)
                return func(self, *args, **kwargs)
            except Exception as e:
                if 'Timed out.' not in str(e) and self._sm and self._flying:
                    self._send_sync('land', 'basic')
                    if self._debug: print('[TELLO] Error raised. Landing drone')
                self._running = False
                raise e

        return inner

    for m in getmembers(cls, lambda t: True if callable(t) else False):
        if '__' not in m[0]: setattr(cls, m[0], decor(m[1]))

    return cls
