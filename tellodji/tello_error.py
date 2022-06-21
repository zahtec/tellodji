'''
Module for holding the shared TelloError class for the TelloDji library
Made by zahtec (https://www.github.com/zahtec/tellodji)
'''

class TelloError(Exception):
    '''
    Internal class for raising errors with Tello as the descriptor. You normally wouldn't use this yourself
    '''

    def __init__(self, m: str) -> None:
        super().__init__(m)
