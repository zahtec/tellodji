'''
Library for interacting with Tello drones using the v2.0 and v1.3 versions of the Tello Ryze SDK.
Made by zahtec (https://www.github.com/zahtec/tellodji)
'''

from socket import AF_INET6, socket, SOCK_DGRAM, AF_INET
from .tello_web import _TelloWebLive, _TelloWebRec
from webbrowser import open as openweb
from PIL.Image import open as openimg
from .tello_decor import tello_decor
from threading import Thread, Event
from typing import Callable, Union
from subprocess import Popen, PIPE
from.tello_error import TelloError
from http.server import HTTPServer
from shutil import rmtree, which
from ipaddress import ip_address
from datetime import datetime
from re import findall, match
from os.path import abspath
from getpass import getpass
from queue import Queue
from time import sleep
from os import mkdir

@tello_decor
class Tello:
    '''
    The main class for the Tello library. Used to construct a socket that will send & receive data from any
    Tello Ryze drone. If an IP address or any ports were provided they will be used in the construction of the sockets.
    Made for the v2.0 and v1.3 of the Tello Ryze SDK. For anything video related, ffmpeg must be installed.
    Kwargs are nicknamed preferences for semantic reasons

    ### Parameters
    - ips?: The IP addresses you would like the Tello sockets to bind & connect to. There must be at least 1 IP address with others inputted as None.
    First one is for the command and state servers, second one is for the video server (ipv4/ipv6, Defaults to 192.168.10.1, 0.0.0.0)
    - ports?: The ports you would like the Tello sockets to bind & connect to. There must be at least 2 ports with others inputted as None.
    First one is for the command server, second one is for the state server, third one is for the video server (Defaults to 8889, 8890, 11111)

    ### Preferences
    - debug?: Enable/Disable the debug mode for verbose console logging (Defaults to False/Disabled)
    - default_distance?: The default distance you would like the drone to move if none is provided during a movement function (Defaults to 50cm)
    - default_rotation?: The default degrees you would like the drone to rotate if none is provided during a movement function (Defaults to 90deg, must be between 1 - 360deg)
    - default_speed?: The default speed you would like the drone to move at (Defaults to 30cm/s, must be between 10 - 60cm/s)
    - mission_pad?: Enable/Disable the detection of mission pads (Defaults to False/Disabled)
    - safety?: Enable/Disable automatically landing the drone if an error is raised within the class while it's flying (Defaults to True/Enabled)
    - sync?: Make library as synchronous by default. Meaning if no callback value is provided to certain methods, it will default to None instead of False. If a function is provided for this preference, it will be set to the default callback for every method. Does not include video methods (Defaults to True/Enabled)
    - syncfix?: Enable/Disable preventing commands going out of sync, if an asynchronous method hasn't completed when a synchronous method is called it will wait for the asynchronous task to complete (Defaults to True/Enabled)
    - timeout?: The amount of time you would like to wait for a response from a drone before a timeout error is raised. If 0 is provided it will have no timeout (Defaults to 7s)
    - takeoff?: Enable/Disable automatically making the drone takeoff on class construction. Unchangeable after construction (Defaults to False/Disabled)
    - video?: Enable/Disable video on by default. Will send the streamon command to the drone. Unchangeable after construction (Defaults to False/Disabled)

    ### Constants
    - M1-8: Mission pad values used for methods that require a mission pad as a parameter
    - HD: Resolution value that represents the 1280 x 720 (720p) for methods that have a resolution parameter
    - SD: Resolution value that represents the 852 x 480 (480p) for methods that have a resolution parameter
    '''

    M1 = 'm1'
    M2 = 'm2'
    M3 = 'm3'
    M4 = 'm4'
    M5 = 'm5'
    M6 = 'm6'
    M7 = 'm7'
    M8 = 'm8'
    HD = (960, 720)
    SD = (640, 480)

    def __init__(self, ips: tuple[int | None] = ('192.168.10.1', '0.0.0.0'), ports: tuple[int | None] = (8889, 8890, 11111), **preferences: Union[int, bool]) -> None:
        if len(ips) != 2 or (ips[0] and ips[1] == None): raise ValueError('IP addresses provided were invalid. Please make sure it\'s a valid tuple with at least 1 address with others inputted as None')
        elif len(ports) != 3 or (ports[0] and ports[1] and ports[2] == None): raise ValueError('Ports provided were invalid. Please make sure it\'s a valid tuple with at least 1 port with others inputted as None')
        elif 'default_distance' in preferences and (type(preferences['default_distance']) is not int or not 20 <= preferences['default_distance']): raise ValueError('Default distance value provided was invalid. Please make sure it\'s a valid integer and at at least 20cm')
        elif 'default_rotation' in preferences and (type(preferences['default_rotation']) is not int or not 1 <= preferences['default_rotation'] <= 360): raise ValueError('Default rotation value provided was invalid. Please make sure it\'s a valid integer and in between 1 - 360deg')
        elif 'default_speed' in preferences and (type(preferences['default_speed']) is not int or not 10 <= preferences['default_speed'] <= 60): raise ValueError('Default speed value provided was invalid. Please make sure it\'s a valid integer and between 10 - 60cm/s')
        elif 'timeout' in preferences and (type(preferences['timeout']) is not int or not 0 <= preferences['timeout']): raise ValueError('Timeout value provided was invalid. Please make sure it\'s a valid integer and at least 0')
        elif 'mission_pad' in preferences and type(preferences['mission_pad']) is not bool: raise TypeError('Mission pad preference provided was invalid. Please make sure it\'s a valid boolean type')
        elif 'safety' in preferences and type(preferences['safety']) is not bool: raise TypeError('Safety preference provided was invalid. Please make sure it\'s a valid boolean type')
        elif 'sync' in preferences and not (type(preferences['sync']) is bool or callable(preferences['sync'])): raise TypeError('Sync preference provided was invalid. Please make sure it\'s a valid boolean type or a callable')
        elif 'takeoff' in preferences and type(preferences['takeoff']) is not bool: raise TypeError('Takeoff preference provided was invalid. Please make sure it\'s a valid boolean type')
        elif 'syncfix' in preferences and type(preferences['syncfix']) is not bool: raise TypeError('Syncfix preference provided was invalid. Please make sure it\'s a valid boolean type')
        elif 'debug' in preferences and type(preferences['debug']) is not bool: raise TypeError('Debug preference provided was invalid. Please make sure it\'s a valid boolean type')
        elif 'video' in preferences and type(preferences['video']) is not bool: raise TypeError('Video preference provided was invalid. Please make sure it\'s a valid boolean type')

        for ip in ips:
            if ip: ip_address(ip)

        self._ips = (ips[0] if ips[0] else '192.168.10.1', ips[1] if ips[1] else '0.0.0.0')
        self._ports = (ports[0] if ports[0] else 8889, ports[1] if ports[1] else 8890, ports[2] if ports[2] else 11111)
        self._to = (preferences['timeout'] if preferences['timeout'] > 0 else None) if 'timeout' in preferences else 7
        self._running = True
        self._flying = False
        self._rec = False
        self._web = None
        self._frames = False
        self._live = False
        self._streaming = True
        self._cqueue = Queue()
        self._slist = {}
        self._sevent = Event()
        self._sevent.set()

        self._dd = preferences['default_distance'] if 'default_distance' in preferences else 50
        self._dr = preferences['default_rotation'] if 'default_rotation' in preferences else 90
        self._spd = preferences['default_speed'] if 'default_speed' in preferences else 30
        self._sm = preferences['safety'] if 'safety' in preferences else True
        self._sync = preferences['sync'] if 'sync' in preferences else True
        self._oos = preferences['syncfix'] if 'syncfix' in preferences else True
        self._mp = preferences['mission_pad'] if 'mission_pad' in preferences else False
        self._debug = preferences['debug'] if 'debug' in preferences else False

        if self._debug: print('[TELLO] Debug mode enabled')

        try:
            if '.' in ips[0]:
                self._cserver, self._sserver = socket(AF_INET, SOCK_DGRAM), socket(AF_INET, SOCK_DGRAM)
                self._cserver.settimeout(self._to)
                self._sserver.bind((ips[0], self._ports[1]))
                self._sserver.settimeout(self._to)

                if self._debug: print(f'[TELLO] Set command socket to -> {ips[0]}:{ports[0]}\n[TELLO] Set state socket to -> {ips[0]}:{self._ports[1]}\n[TELLO] Timeout set to -> {self._to}')
            else:
                self._cserver, self._sserver = socket(AF_INET6, SOCK_DGRAM), socket(AF_INET6, SOCK_DGRAM)
                self._cserver.settimeout(self._to)
                self._sserver.bind((ips[0], self._ports[1]))
                self._sserver.settimeout(self._to)

                if self._debug: print(f'[TELLO] Set command socket to -> {ips[0]}:{ports[0]}\n[TELLO] Set state socket to -> {ips[0]}:{self._ports[1]}\n[TELLO] Timeout set to -> {self._to}')
        except OSError: raise TelloError('Unable to bind to provided IP/ports. Please make sure you are connected to your Tello drone')

        Thread(target=self._cthread).start()
        Thread(target=self._rthread).start()

        if self._debug: print('[TELLO] Created and started threads')

        self._send('Command', 'basic')
        self._send('speed', 'aval', False, self._spd)
        if self._mp: self._send('mon', 'basic')
        if 'video' in preferences and preferences['video']: self._send('streamon', 'basic')
        if 'takeoff' in preferences and preferences['takeoff']:
            self._flying = True
            self._send('takeoff', 'basic')
        if self._debug: print(f'[TELLO] Default movement distance is set to -> {self._dd}cm\n[TELLO] Default movement speed is set to -> {self._spd}cm\n[TELLO] Default rotation is set to -> {self._dr}')

    def ips(self) -> tuple[str]:
        '''
        Returns the current IP addresses the Tello socket's are sending to/receiving from
        '''

        return self._ips

    def set_ips(self, ips: tuple[Union[str, None]]) -> None:
        '''
        Changes the Tello socket's IP addresses to the ones provided. Does not change the ip of any method ran beforehand

        ### Parameters
        - ip: The IP's that that you want the sockets to switch to (ipv4/ipv6)
        '''

        if len(ips) != 2 or (ips[0] and ips[1] == None): raise ValueError('IP addresses provided were invalid. Please make sure it\'s a valid tuple with at least 1 address with others inputted as None')

        for ip in ips:
            if ip: ip_address(ip)

        ips = (ips[0] if ips[0] else self._ips[0], ips[1] if ips[1] else self._ips[1])

        if ips == self._ips: raise ValueError('IPs provided are the same as the currently set ones')

        self._ips = ips

        self._sevent.clear()

        self._sserver.shutdown()
        self._sserver = socket(AF_INET, SOCK_DGRAM), socket(AF_INET, SOCK_DGRAM)
        self._sserver.bind((ips[0], self._ports[1]))
        self._sserver.settimeout(self._to)

        self._sevent.set()

        if self._debug: print(f'[TELLO] Set command socket to -> {ips[0]}:{self._ports[0]}\n[TELLO] Set state socket to -> {ips[0]}:{self._ports[1]}')

    def ports(self) -> tuple[int]:
        '''
        Returns the current ports the Tello socket's are sending to/receiving from
        '''

        return self._ports

    def set_ports(self, ports: tuple[Union[int, None]]) -> None:
        '''
        Changes the Tello socket's ports to the ones provided. Does not change the ports of any method ran beforehand

        ### Parameters
        - ports: The ports that that you want the sockets to switch to
        '''

        if len(ports) != 3 or (ports[0] and ports[1] and ports[2] == None): raise ValueError('Ports provided were invalid. Please make sure it\'s a valid tuple with at least 1 port with others inputted as None')

        ports = (ports[0] if ports[0] else self._ports[0], ports[1] if ports[1] else self._ports[1], ports[2] if ports[2] else self._ports[2])

        if ports == self._ports: raise ValueError('Ports provided are the same as the currently set ones')

        self._ports = ports
        self._sevent.clear()

        self._sserver.shutdown()
        self._sserver = socket(AF_INET, SOCK_DGRAM), socket(AF_INET, SOCK_DGRAM)
        self._sserver.bind((self._ips[0], ports[1]))
        self._sserver.settimeout(self._to)

        self._sevent.set()

        if self._debug: print(f'[TELLO] Set command socket to -> {self._ips[0]}:{ports[0]}\n[TELLO] Set state socket to -> {self._ips[0]}:{ports[1]}')

    def debug(self) -> bool:
        '''
        Returns the state the debug preference is set to
        '''

        return self._debug

    def set_debug(self, preference: bool) -> None:
        '''
        Enables/Disables the debug mode for verbose console logging

        ### Parameters
        - preference: The state to set the debug preference to (True/False)
        '''

        if preference == self._debug: raise ValueError('Debug preference provided is the same as the currently set one')

        if self._debug and not preference: print('[TELLO] Debug mode disabled')
        elif not self._debug and preference: print('[TELLO] Debug mode enabled')

        self._debug = preference

    def default_distance(self) -> int:
        '''
        Returns the current set default distance you want the drone to go
        '''

        return self._dd

    def set_default_distance(self, distance: int) -> None:
        '''
        Changes the default distance the drone will move if none is provided during a movement function

        ### Parameters
        - distance: The distance you want the drone to move (20+ cm)
        '''

        if not 20 <= distance: raise ValueError('Distance value provided was invalid. Please make sure it is a valid integer and at least 20cm')

        if distance == self._dd: raise ValueError('Distance value provided is the same as the currently set value')

        self._dd = distance

        if self._debug: print(f'[TELLO] Set default distance to -> {distance}cm')

    def default_rotation(self) -> int:
        '''
        Returns the current set default rotation you want the drone to rotate
        '''

        return self._dr

    def set_default_rotation(self, rotation: int) -> None:
        '''
        Changes the default degrees the drone will rotate if none is provided during a movement function

        ### Parameters
        - rotation: The distance you want the drone to turn (1 - 360deg)
        '''

        if not 10 <= rotation <= 360: raise ValueError('Rotation value provided was invalid. Please make sure it\'s a valid integer and in between 1 - 360deg')

        if rotation == self._dr: raise ValueError('Rotation value provided is the same as the currently set value')

        self._dr = rotation

        if self._debug: print(f'[TELLO] Set default rotation to -> {rotation}deg')

    def default_speed(self) -> int:
        '''
        Returns the current set default speed you want the drone to go
        '''

        return self._spd

    def set_default_speed(self, speed: int) -> None:
        '''
        Changes the default speed the drone will move if none is provided during a movement function that requires one or
        when doing a movement function that doesn't have a speed input. This setter is blocking

        ### Parameters
        - speed: The speed you want the drone to move at (10 - 60cm/s)
        '''

        if not 10 <= speed <= 60: raise ValueError('Speed value provided was invalid. Please make sure it\'s a valid integer and between 10 - 60cm/s')

        if speed == self._spd: raise ValueError('Speed value provided is the same as the currently set value')

        self._send('speed', 'setspd', speed)
        if self._debug: print(f'[TELLO] Set default speed on drone to -> {speed}cm/s')

        self._spd = speed

        if self._debug: print(f'[TELLO] Set default speed in class to -> {speed}cm/s')

    def mission_pad(self) -> bool:
        '''
        Returns the state the mission pad preference is set to
        '''

        return self._mp

    def set_mission_pad(self, preference: bool) -> None:
        '''
        Enables/Disables the use of the drones mission pad detection. When enabled forward and downward mission pad detection is enabled. This setter is blocking

        ### Parameters
        - preference: The state to set the mission pad preference to (True/False)
        '''

        if preference == self._mp: raise ValueError('Mission pad preference provided is the same as the currently set one')

        if preference: self._send('mon', 'basic')
        else: self._send('moff', 'basic')

        self._mp = preference

        if self._debug: print(f'[TELLO] Set mission pad preference to -> {preference}')

    def safety(self) -> bool:
        '''
        Returns the state the safety preference is set to
        '''

        return self._sm

    def set_safety(self, preference: bool) -> None:
        '''
        Enables/Disables landing the drone if an error is raised within the class and the drone is flying

        ### Parameters
        - preference: The state to set the safety preference to (True/False)
        '''

        if preference == self._sm: raise ValueError('Safety preference provided is the same as the currently set one')

        self._sync = preference

        if self._debug: print(f'[TELLO] Set safety preference to -> {preference}')

    def sync(self) -> bool:
        '''
        Returns the state the sync preference is set to
        '''

        return self._sync

    def set_sync(self, preference: Union[bool, Callable]) -> None:
        '''
        Enables/Disables the library as synchronous by default. Meaning if no callback value is provided to certain methods, it will default to None instead of False.
        If a function is provided for this preference, it will be set to the default callback for every method. Does not include video methods

        ### Parameters
        - preference: The state to set the sync preference to (True/False)
        '''
        if preference == self._sync: raise ValueError('Sync preference provided is the same as the currently set one')

        self._sync = preference

        if self._debug: print('[TELLO] Set sync preference to -> {}'.format(preference if not callable(preference) else f'function \'{preference.__name__}\''))

    def syncfix(self) -> bool:
        '''
        Returns the state the syncfix preference is set to
        '''

        return self._sync

    def set_syncfix(self, preference: bool) -> None:
        '''
        Enables/Disables preventing commands going out of sync, if an asynchronous method hasnt completed when a synchronous method is called it will wait for the asynchronous task to complete

        ### Parameters
        - preference: The state to set the syncfix preference to (True/False)
        '''

        if preference == self._oos: raise ValueError('Syncfix preference provided is the same as the currently set one')

        self._oos = preference

        if self._debug: print(f'[TELLO] Set syncfix preference to -> {preference}')

    def timeout(self) -> int:
        '''
        Returns the current amount of time the Tello socket's wait before raising an error
        '''

        return self._to

    def set_timeout(self, timeout: int) -> None:
        '''
        Changes the Tello socket's timeout to the one provided. Does not change the timeout of any method ran beforehand

        ### Parameters
        - timeout: The amount of time you would like the socket's to wait for a response from a drone before a timeout error is raised (Must be at least 1 second)
        '''

        if timeout < 1: raise ValueError('Timeout provided was invalid. Please make sure it\'s a integer and at least 1 second')

        if timeout == self._to: raise ValueError('Timeout provided was the same as the currently set one')

        self._to = timeout

        if self._debug: print(f'[TELLO] Set timeout to -> {timeout}')

    def _cthread(self) -> None:
        '''
        Internal method for sending data to the drone within a seperate thread. You normally wouldn't use this yourself
        '''

        while self._running:
            if self._cqueue.qsize():
                req, call = self._cqueue.get()

                self._cserver.sendto(req.encode(), (self._ips[0], self._ports[0]))

                try: res = self._cserver.recv(1024).decode().lower()
                except TimeoutError: raise TelloError(f'Timed out. Did not receive response from drone within {self._to} second(s)')
                except KeyboardInterrupt: return

                if 'ok' not in res: raise TelloError(f'Drone responded with error: {res}')
                else:
                    if 'streamon' in req: self._streaming = True
                    elif 'streamoff' in req: self._streaming = False
                    if self._debug:
                        if 'wifi' in req or req.startswith('ac'): print(f'[TELLO] Set wifi successfully')
                        else: print(f'[TELLO] Sent command \'{req}\' successfully')

                if call: call(res)
                self._cqueue.task_done()
        else: return

    def _rthread(self) -> None:
        '''
        Internal method for receiving state from the drone within a seperate thread. You normally wouldn't use this yourself
        '''

        while self._running:
            self._sevent.wait()

            try: res = [m.split(':') for m in findall(r'[^;]+?(?=%)', self._sserver.recv(1024).decode().lower())]
            except TimeoutError: raise TelloError(f'Timed out. Did not receive response from drone within {self._to} second(s)')
            except KeyboardInterrupt: return

            for match in res:
                self._slist.update({ match[0]: int(match[1]) if match[1].isdigit() else match[1] })
        else: return

    def _send(self, msg: str, typ: str, callback: Union[Callable, bool, None] = False, val: Union[int, tuple[Union[int, str]], None] = None) -> str:
        '''
        Internal method for sending data synchronously to the drone. You normally wouldn't use this yourself
        '''

        if self._sync == False: callback = None
        elif callable(self._sync): callback = self._sync

        def sender(msg: str):
            if self._oos: self._cqueue.join()

            self._cserver.sendto(msg.encode(), (self._ips[0], self._ports[0]))

            try: res = self._cserver.recv(1024).decode().lower()
            except TimeoutError: raise TelloError(f'Timed out. Did not receive response from drone within {self._to} second(s)')
            except KeyboardInterrupt: return

            if 'ok' not in res: raise TelloError(f'Drone responded with error: {res}')
            else:
                if 'streamon' in msg: self._streaming = True
                elif 'streamoff' in msg: self._streaming = False
                if self._debug:
                    if 'wifi' in msg or msg.startswith('ac'): print(f'[TELLO] Set wifi successfully')
                    else: print(f'[TELLO] Sent command \'{msg}\' successfully')

            return res

        match typ:
            case 'basic':
                if callback == False: return sender(msg)
                else: self._cqueue.put((msg, callback))

            case 'aval':
                if callback == False: return sender(f'{msg} {val}')
                else: self._cqueue.put((f'{msg} {val}', callback))

            case 'dist':
                if not 20 <= val: raise ValueError('Distance value is incorrect. Please make sure it\'s a valid integer and at least 20cm')

                def disrun(val):
                    while val > 500:
                        val -= 500
                        yield 500
                    else: yield val

                ret = []

                if callback == False:
                    for dist in disrun(val): ret.append(sender(f'{msg} {dist}'))
                    return ret if len(ret) > 1 else ret[0]
                else:
                    for dist in disrun(val): self._cqueue.put((f'{msg} {dist}', callback))

            case 'rot':
                if not 1 <= val <= 360: raise ValueError('Rotational value is incorrect. Please make sure it\'s a valid integer and between 1 - 360deg')

                if callback == False: return sender(f'{msg} {val}')
                else: self._cqueue.put((f'{msg} {val}', callback))

            case 'cord':
                msg = f'{msg} '

                for n in val:
                    if val.index(n) == len(val)-1:
                        if n[1] and not 10 <= n <= 60: raise ValueError('Speed value is incorrect. Please make sure it\'s between 10 - 60cm/s')
                        elif not n[1] and not 10 <= n <= 100: raise ValueError('Speed value is incorrect. Please make sure it\'s between 10 - 100cm/s')
                    elif not -500 <= n <= 500: raise ValueError('coordinate value is incorrect. Please make sure it\'s a valid integer and between -500 - 500cm')

                    msg += f'{n} '

                if callback == False: return sender(msg.rstrip())
                else: self._cqueue.put((msg.rstrip(), callback))

            case 'mid':
                msg = f'{msg} '

                for n in val:
                    ind = val.index(n)
                    leg = len(val)

                    if ind == leg-2:
                        if n[1] and not 10 <= n <= 60: raise ValueError('Speed value is incorrect. Please make sure it\'s between 10 - 60cm/s')
                        elif not n[1] and not 10 <= n <= 100: raise ValueError('Speed value is incorrect. Please make sure it\'s between 10 - 100cm/s')
                    elif ind == leg-1 and type(n) is not str or not match(r'^[m][1-8]$', n): raise ValueError('Mission Pad value is incorrect. Please make sure it\'s a valid string and is between m1 - m8')
                    elif not -500 <= n <= 500: raise ValueError('coordinate value is incorrect. Please make sure it\'s a valid integer and between -500 - 500cm')

                    msg += f'{n} '

                if callback == False: return sender(msg.rstrip())
                else: self._cqueue.put((msg.rstrip(), callback))

            case 'jump':
                msg = f'{msg} '

                for n in val:
                    ind = val.index(n)
                    leg = len(val)

                    if ind == leg-4:
                        if n[1] and not 10 <= n <= 60: raise ValueError('Speed value is incorrect. Please make sure it\'s between 10 - 60cm/s')
                        elif not n[1] and not 10 <= n <= 100: raise ValueError('Speed value is incorrect. Please make sure it\'s between 10 - 100cm/s')
                    elif ind == leg-3 and not 1 <= n <= 360: raise ValueError('Yaw value is incorrect. Please make sure it\'s a valid integer and between 1 - 360deg')
                    elif ind == leg-1 or ind == leg-2 and type(n) is not str or not match(r'^[m][1-8]$', n): raise ValueError('Mission Pad value is incorrect. Please make sure it\'s a valid string and is between m1 - m8')
                    elif not -500 <= n <= 500: raise ValueError('coordinate value is incorrect. Please make sure it\'s a valid integer and between -500 - 500cm')

                    msg += f'{n} '

                if callback == False: return sender(msg.rstrip())
                else: self._cqueue.put((msg.rstrip(), callback))

            case 'setspd':
                if not 10 <= val <= 60: raise ValueError('Speed value is incorrect. Please make sure it\'s a valid integer and between 10 - 60cm/s')

                self._spd = val

                if callback == False: return sender(f'{msg} {val}')
                else: self._cqueue.put((f'{msg} {val}', callback))

            case 'setrc':
                msg = f'{msg} '

                for n in val:
                    if not -100 <= n <= 100: raise ValueError('Joystick distance value is incorrect. Please make sure it\'s a valid integer and between -100 - 100')
                    msg += f'{n} '

                if callback == False: return sender(msg.rstrip())
                else: self._cqueue.put((msg.rstrip(), callback))

            case 'setwifi':
                val = list(val)

                if not val[0] and not val[1]:
                    try:
                        val[0] = input('Enter new WiFi SSID: ').strip()
                        val[1] = getpass('Enter new WiFi password: ').strip()
                    except: return
                if len(val[0]) or not val[0].isascii(): raise ValueError('WiFi SSID value is incorrect. Please make sure it\'s a valid string in ascii and at least 1 character')
                elif not len(val[1]) >= 5 or not val[1].isascii(): raise ValueError('WiFi password value is incorrect. Please make sure it\'s a valid string in ascii and at least 5 characters')
                elif not match(r'(?=(?:[^a-z]*[a-z]){2})(?=(?:[^A-Z]*[A-Z]){2})(?=(?:[^0-9]*[0-9]){1})', val[1]): raise ValueError('WiFi password value is insecure. Please make sure it contains at least 2 lowercase and uppercase letters and 1 number')

                if callback == False: return sender(f'{msg} {val[0]} {val[1]}')
                else: self._cqueue.put((f'{msg} {val[0]} {val[1]}', callback))

            case 'connwifi':
                val = list(val)

                if not val[0] and not val[1]:
                    try:
                        val[0] = input('Enter WiFi SSID: ').strip()
                        val[1] = getpass('Enter WiFi password: ').strip()
                    except: return

                if not len(val[0]): raise ValueError('WiFi SSID value is incorrect. Please make sure it\'s a valid string and at least 1 character')
                elif not len(val[1]): raise ValueError('WiFi password value is incorrect. Please make sure it\'s a valid string and at least 1 character')

                if callback == False: return sender(f'{msg} {val[0]} {val[1]}')
                else: self._cqueue.put((f'{msg} {val[0]} {val[1]}', callback))

            case 'mpad':
                if not self._mp: raise ValueError('Mission pad detection hasn\'t been enabled yet. Please run the Tello.set_mission_pad() method first')
                elif not 0 <= val <= 2: raise ValueError('Mission Pad Detection value is incorrect. Please make sure it\'s a valid integer and between 0 - 2')

                if callback == False: return sender(f'{msg} {val}')
                else: self._cqueue.put((f'{msg} {val}', callback))

        if callback: return self

    def _state(self, *msgs: str) -> tuple[Union[int, str]]:
        '''
        Internal method for receiving a state value from the state dict. You normally wouldn't use this yourself
        '''

        ret = []

        for key, val in self._slist.items():
            if key in msgs: ret.append(val)
            else: raise TelloError('The status requested is only available when mission pads are enabled. Please run the Tello.set_mission_pad() method first to use this method')

        return tuple(ret) if len(ret) > 1 else ret[0]

    def _checkstream(self) -> None:
        '''
        Internal method to check whether the drone is streaming video or not. You normally wouldn't use this yourself
        '''

        if which('ffmpeg') == None: raise TelloError(f'Can not stream video as ffmpeg is not installed')

        if not self._streaming: raise TelloError(f'Can only run this method once the drone video stream is enabled. Please run the Tello.stream() method first')

    def _checkfly(self) -> None:
        '''
        Internal method to check whether the drone has taken off or not. You normally wouldn't use this yourself
        '''

        if not self._flying: raise TelloError(f'Can only run this method once the drone is flying. Please run the Tello.takeoff() method first')

    def takeoff(self, **preferences: Union[Callable, bool, None]) -> Union['Tello', str]:
        '''
        Makes the drone automatically takeoff to a height of 80cm

        ### Preferences
        - callback?: A function to be called once a response from the drone is received with said response as the first argument in string form.
        If a None value is provided, this method will be non-blocking but will have no callback.
        If False is provided, this method will be blocking and return the response (Defaults to False/blocking)
        '''

        if self._flying: raise TelloError('Already flying. Can\'t takeoff')
        self._flying = True
        return self._send('takeoff', 'basic', preferences['callback'] if 'callback' in preferences else False)

    def land(self, **preferences:  Union[Callable, bool, None]) -> Union['Tello', str]:
        '''
        Makes the drone automatically land at it's current position

        ### Preferences
        - callback?: A function to be called once a response from the drone is received with said response as the first argument in string form.
        If a None value is provided, this method will be non-blocking but will have no callback.
        If False is provided, this method will be blocking and return the response (Defaults to False/blocking)
        '''

        self._checkfly()
        self._flying = False
        return self._send('land', 'basic', preferences['callback'] if 'callback' in preferences else False)

    def emergency(self, **preferences:  Union[Callable, bool, None]) -> Union['Tello', str]:
        '''
        Stops all drone motors immediately in case of emergency

        ### Preferences
        - callback?: A function to be called once a response from the drone is received with said response as the first argument in string form.
        If a None value is provided, this method will be non-blocking but will have no callback.
        If False is provided, this method will be blocking and return the response (Defaults to False/blocking)
        '''

        self._flying = False
        return self._send('emergency', 'basic', preferences['callback'] if 'callback' in preferences else False)

    def stop(self, **preferences:  Union[Callable, bool, None]) -> Union['Tello', str]:
        '''
        Makes the drone hover in the air at it's current position

        ### Preferences
        - callback?: A function to be called once a response from the drone is received with said response as the first argument in string form.
        If a None value is provided, this method will be non-blocking but will have no callback.
        If False is provided, this method will be blocking and return the response (Defaults to False/blocking)
        '''

        self._checkfly()
        return self._send('stop', 'basic', preferences['callback'] if 'callback' in preferences else False)

    def up(self, distance: Union[int, None] = None, **preferences:  Union[Callable, bool, None]) -> Union['Tello', str]:
        '''
        Makes the drone move up the provided amount of centimeters. If distance isn't provided, the default amount of distance set will be used

        ### Parameters
        - distance?: Distance in centimeters you would like the drone to move (Defaults to None/default distance)

        ### Preferences
        - callback?: A function to be called once a response from the drone is received with said response as the first argument in string form.
        If a None value is provided, this method will be non-blocking but will have no callback.
        If False is provided, this method will be blocking and return the response (Defaults to False/blocking)
        '''

        self._checkfly()
        return self._send('up', 'dist', preferences['callback'] if 'callback' in preferences else False, distance if distance else self._dd)

    def down(self, distance: Union[int, None] = None, **preferences:  Union[Callable, bool, None]) -> Union['Tello', str]:
        '''
        Makes the drone move down the provided amount of centimeters. If distance isn't provided, the default amount of distance set will be used

        ### Parameters
        - distance?: Distance in centimeters you would like the drone to move (Defaults to None/default distance)

        ### Preferences
        - callback?: A function to be called once a response from the drone is received with said response as the first argument in string form.
        If a None value is provided, this method will be non-blocking but will have no callback.
        If False is provided, this method will be blocking and return the response (Defaults to False/blocking)
        '''

        self._checkfly()
        return self._send('down', 'dist', preferences['callback'] if 'callback' in preferences else False, distance if distance else self._dd)

    def left(self, distance: Union[int, None] = None, **preferences:  Union[Callable, bool, None]) -> Union['Tello', str]:
        '''
        Makes the drone move left the provided amount of centimeters. If distance isn't provided, the default amount of distance set will be used

        ### Parameters
        - distance?: Distance in centimeters you would like the drone to move (Defaults to None/default distance)

        ### Preferences
        - callback?: A function to be called once a response from the drone is received with said response as the first argument in string form.
        If a None value is provided, this method will be non-blocking but will have no callback.
        If False is provided, this method will be blocking and return the response (Defaults to False/blocking)
        '''

        self._checkfly()
        return self._send('left', 'dist', preferences['callback'] if 'callback' in preferences else False, distance if distance else self._dd)

    def right(self, distance: Union[int, None] = None, **preferences:  Union[Callable, bool, None]) -> Union['Tello', str]:
        '''
        Makes the drone move right the provided amount of centimeters. If distance isn't provided, the default amount of distance set will be used

        ### Parameters
        - distance?: Distance in centimeters you would like the drone to move (Defaults to None/default distance)

        ### Preferences
        - callback?: A function to be called once a response from the drone is received with said response as the first argument in string form.
        If a None value is provided, this method will be non-blocking but will have no callback.
        If False is provided, this method will be blocking and return the response (Defaults to false/blocking)
        '''

        self._checkfly()
        return self._send('right', 'dist', preferences['callback'] if 'callback' in preferences else False, distance if distance else self._dd)

    def forward(self, distance: Union[int, None] = None, **preferences:  Union[Callable, bool, None]) -> Union['Tello', str]:
        '''
        Makes the drone move forward the provided amount of centimeters. If distance isn't provided, the default amount of distance set will be used

        ### Parameters
        - distance?: Distance in centimeters you would like the drone to move (Defaults to None/default distance)

        ### Preferences
        - callback?: A function to be called once a response from the drone is received with said response as the first argument in string form.
        If a None value is provided, this method will be non-blocking but will have no callback.
        If False is provided, this method will be blocking and return the response (Defaults to False/blocking)
        '''

        self._checkfly()
        return self._send('forward', 'dist', preferences['callback'] if 'callback' in preferences else False, distance if distance else self._dd)

    def backward(self, distance: Union[int, None] = None, **preferences:  Union[Callable, bool, None]) -> Union['Tello', str]:
        '''
        Makes the drone move backward the provided amount of centimeters. If distance isn't provided, the default amount of distance set will be used

        ### Parameters
        - distance?: Distance in centimeters you would like the drone to move (Defaults to None/default distance)

        ### Preferences
        - callback?: A function to be called once a response from the drone is received with said response as the first argument in string form.
        If a None value is provided, this method will be non-blocking but will have no callback.
        If False is provided, this method will be blocking and return the response (Defaults to false/blocking)
        '''

        self._checkfly()
        return self._send('back', 'dist', preferences['callback'] if 'callback' in preferences else False, distance if distance else self._dd)

    def clockwise(self, degrees: Union[int, None] = None, **preferences:  Union[Callable, bool, None]) -> Union['Tello', str]:
        '''
        Makes the drone rotate clockwise the provided amount of degrees. If degrees isn't provided, the default amount of rotation set will be used

        ### Parameters
        - degrees?: Degrees you would like the drone to turn (Defaults to None/default rotation)

        ### Preferences
        - callback?: A function to be called once a response from the drone is received with said response as the first argument in string form.
        If a None value is provided, this method will be non-blocking but will have no callback.
        If False is provided, this method will be blocking and return the response (Defaults to False/blocking)
        '''

        self._checkfly()
        return self._send('cw', 'rot', preferences['callback'] if 'callback' in preferences else False, degrees if degrees else self._dr)

    def counter_clockwise(self, degrees: Union[int, None] = None, **preferences: Union[Callable, bool, None]) -> Union['Tello', str]:
        '''
        Makes the drone rotate counter-clockwise the provided amount of degrees.  If degrees isn't provided, the default amount of rotation set will be used

        ### Parameters
        - degrees?: Degrees you would like the drone to turn (Defaults to None/default rotation)

        ### Preferences
        - callback?: A function to be called once a response from the drone is received with said response as the first argument in string form.
        If a None value is provided, this method will be non-blocking but will have no callback.
        If False is provided, this method will be blocking and return the response (Defaults to False/blocking)
        '''

        self._checkfly()
        return self._send('ccw', 'rot', preferences['callback'] if 'callback' in preferences else False, degrees if degrees else self._dr)

    def flip_left(self, **preferences: Union[Callable, bool, None]) -> Union['Tello', str]:
        '''
        Makes the drone flip towards the left

        ### Preferences
        - callback?: A function to be called once a response from the drone is received with said response as the first argument in string form.
        If a None value is provided, this method will be non-blocking but will have no callback.
        If False is provided, this method will be blocking and return the response (Defaults to False/blocking)
        '''

        self._checkfly()
        return self._send('flip', 'aval', preferences['callback'] if 'callback' in preferences else False, 'l')

    def flip_right(self, **preferences: Union[Callable, bool, None]) -> Union['Tello', str]:
        '''
        Makes the drone flip towards the right

        ### Preferences
        - callback?: A function to be called once a response from the drone is received with said response as the first argument in string form.
        If a None value is provided, this method will be non-blocking but will have no callback.
        If False is provided, this method will be blocking and return the response (Defaults to False/blocking)
        '''

        self._checkfly()
        return self._send('flip', 'aval', preferences['callback'] if 'callback' in preferences else False, 'r')

    def flip_forward(self, **preferences: Union[Callable, bool, None]) -> Union['Tello', str]:
        '''
        Makes the drone flip forwards

        ### Parameters
        - callback?: A function to be called once a response from the drone is received with said response as the first argument in string form.
        If a None value is provided, this method will be non-blocking but will have no callback.
        If False is provided, this method will be blocking and return the response (Defaults to False/blocking)
        '''

        self._checkfly()
        return self._send('flip', 'aval', preferences, 'f')

    def flip_backward(self, **preferences: Union[Callable, bool, None]) -> Union['Tello', str]:
        '''
        Makes the drone flip backwards

        ### Preferences
        - callback?: A function to be called once a response from the drone is received with said response as the first argument in string form.
        If a None value is provided, this method will be non-blocking but will have no callback.
        If False is provided, this method will be blocking and return the response (Defaults to False/blocking)
        '''

        self._checkfly()
        return self._send('flip', 'aval', preferences['callback'] if 'callback' in preferences else False, 'b')

    def go(self, x: int, y: int, z: int, speed: Union[int, None] = None, **preferences: Union[Callable, bool, None]) -> Union['Tello', str]:
        '''
        Makes the drone go to the provided coordinates based of it's current position (0, 0, 0). If speed isn't provided, the default amount of speed set will be used

        ### Parameters
        - x: The x coordinate you would like the drone to go to (-500 - 500)
        - y: The y coordinate you would like the drone to go to (-500 - 500)
        - z: The z coordinate you would like the drone to go to (-500 - 500)
        - speed?: The speed you would like the drone to fly inbetween 10 - 100cm/s (Defaults to None/default speed)

        ### Preferences
        - callback?: A function to be called once a response from the drone is received with said response as the first argument in string form.
        If a None value is provided, this method will be non-blocking but will have no callback.
        If False is provided, this method will be blocking and return the response (Defaults to False/blocking)
        '''

        self._checkfly()
        return self._send('go', 'cord', preferences['callback'] if 'callback' in preferences else False, (x, y, z, (speed if speed else self._spd, False)))

    def curve(self, x1: int, y1: int, z1: int, x2: int, y2: int, z2: int, speed: Union[int, None] = None, **preferences: Union[Callable, bool, None]) -> Union['Tello', str]:
        '''
        Makes the drone fly in a curve according to the two provided coordinates based off it's current position (0, 0, 0). If speed isn't provided, the default amount of speed set will be used

        ### Parameters
        - x1: The x coordinate you would like the drone to curve from (-500 - 500)
        - y1: The y coordinate you would like the drone to curve from (-500 - 500)
        - z1: The z coordinate you would like the drone to curve from (-500 - 500)
        - x2: The x coordinate you would like the drone to curve to (-500 - 500)
        - y2: The y coordinate you would like the drone to curve to (-500 - 500)
        - z2: The z coordinate you would like the drone to curve to (-500 - 500)
        - speed?: The speed you would like the drone to fly inbetween 10 - 60cm/s (Defaults to None/default speed)

        ### Preferences
        - callback?: A function to be called once a response from the drone is received with said response as the first argument in string form.
        If a None value is provided, this method will be non-blocking but will have no callback.
        If False is provided, this method will be blocking and return the response (Defaults to False/blocking)
        '''

        self._checkfly()
        return self._send('curve', 'cord', preferences['callback'] if 'callback' in preferences else False, (x1, y1, z1, x2, y2, z2, (speed if speed else self._spd, True)))

    def go_mid(self, x: int, y: int, z: int, mid: str, speed: Union[int, None] = None, **preferences: Union[Callable, bool, None]) -> Union['Tello', str]:
        '''
        Makes the drone go to the provided coordinates based off the provided mission pad. If speed isn't provided, the default amount of speed set will be used

        ### Parameters
        - x: The x coordinate you would like the drone to go to (-500 - 500)
        - y: The y coordinate you would like the drone to go to (-500 - 500)
        - z: The z coordinate you would like the drone to go to (-500 - 500)
        - mid: The mission pad ID you would like to base the coordinates off (m1 - m8)
        - speed?: The speed you would like the drone to fly inbetween 10 - 100cm/s (Defaults to None/default speed)

        ### Preferences
        - callback?: A function to be called once a response from the drone is received with said response as the first argument in string form.
        If a None value is provided, this method will be non-blocking but will have no callback.
        If False is provided, this method will be blocking and return the response (Defaults to False/blocking)
        '''

        self._checkfly()
        return self._send('go', 'cord', preferences['callback'] if 'callback' in preferences else False, (x, y, z, mid, (speed if speed else self._spd, False)))

    def curve_mid(self, x1: int, y1: int, z1: int, x2: int, y2: int, z2: int, mid: str, speed: Union[int, None] = None, **preferences: Union[Callable, bool, None]) -> Union['Tello', str]:
        '''
        Makes the drone fly in a curve according to the two provided coordinates based off the provided mission pad. If speed isn't provided, the default amount of speed set will be used

        ### Parameters
        - x1: The x coordinate you would like the drone to curve from (-500 - 500)
        - y1: The y coordinate you would like the drone to curve from (-500 - 500)
        - z1: The z coordinate you would like the drone to curve from (-500 - 500)
        - x2: The x coordinate you would like the drone to curve to (-500 - 500)
        - y2: The y coordinate you would like the drone to curve to (-500 - 500)
        - z2: The z coordinate you would like the drone to curve to (-500 - 500)
        - mid: The mission pad ID you would like to base the coordinates off (m1 - m8)
        - speed?: The speed you would like the drone to fly inbetween 10 - 60cm/s (Defaults to None/default speed)

        ### Preferences
        - callback?: A function to be called once a response from the drone is received with said response as the first argument in string form.
        If a None value is provided, this method will be non-blocking but will have no callback.
        If False is provided, this method will be blocking and return the response (Defaults to False/blocking)
        '''

        self._checkfly()
        return self._send('curve', 'cord', preferences['callback'] if 'callback' in preferences else False, (x1, y1, z1, x2, y2, z2, (speed if speed else self._spd, True), mid))

    def jump(self, x: int, y: int, z: int, mid1: str, mid2: str, yaw: int, speed: Union[int, None] = None, **preferences: Union[Callable, bool, None]) -> Union['Tello', str]:
        '''
        Makes the drone go to the provided coordinates based off the first provided mission pad then rotate to the yaw value based off the z coordinate of the second mission pad. If speed isn't provided, the default amount of speed set will be used

        ### Parameters
        - x: The x coordinate you would like the drone to go to (-500 - 500)
        - y: The y coordinate you would like the drone to go to (-500 - 500)
        - z: The z coordinate you would like the drone to go to (-500 - 500)
        - mid1: The mission pad ID you would like to base the coordinates off (m1 - m8)
        - mid2: The mission pad ID you would like the drone to base the z coordinate off (m1 - m8)
        - yaw: The yaw you would like the drone to rotate to (1 - 360deg)
        - speed?: The speed you would like the drone to fly inbetween 10 - 100cm/s (Defaults to None/default speed)

        ### Preferences
        - callback?: A function to be called once a response from the drone is received with said response as the first argument in string form.
        If a None value is provided, this method will be non-blocking but will have no callback.
        If False is provided, this method will be blocking and return the response (Defaults to False/blocking)
        '''

        self._checkfly()
        return self._send('jump', 'cord', preferences['callback'] if 'callback' in preferences else False, (x, y, z, (speed if speed else self._spd, False), yaw, mid1, mid2))

    def remote_controller(self, lr: int, fb: int, ud: int, y: int, **preferences: Union[Callable, bool, None]) -> Union['Tello', str]:
        '''
        Moves the drone based off of simulating a remote controller. Each value provided is how far it will move from it's current position in that direction

        ### Parameters
        - lr: The left/right position (in cm)
        - fb: the forward/backward position (in cm)
        - ud: The up/down position (in cm)
        - y: The yaw (in deg)

        ### Preferences
        - callback?: A function to be called once a response from the drone is received with said response as the first argument in string form.
        If a None value is provided, this method will be non-blocking but will have no callback.
        If False is provided, this method will be blocking and return the response (Defaults to False/blocking)
        '''

        self._checkfly()
        return self._send('rc', 'setrc', preferences['callback'] if 'callback' in preferences else False, (lr, fb, ud, y))

    def set_wifi(self, ssid: Union[str, None] = None, pwd: Union[str, None] = None, **preferences: Union[Callable, bool, None]) -> Union['Tello', str]:
        '''
        Sets the drones wifi SSID and password. Has a basic security check requiring 2 lowercase and 2 uppercase letters with 1 number.
        If no values are provided a terminal prompt will be used to collect them instead

        ### Parameters
        - ssid?: The WiFi SSID you would like the drone to broadcast
        - pwd?: The password you would like the drone WiFi to be secure with

        ### Preferences
        - callback?: A function to be called once a response from the drone is received with said response as the first argument in string form.
        If a None value is provided, this method will be non-blocking but will have no callback.
        If False is provided, this method will be blocking and return the response (Defaults to False/blocking)
        '''

        return self._send('wifi', 'setwifi', preferences['callback'] if 'callback' in preferences else False, (ssid, pwd))

    def mission_pad_direction(self, dir: int, **preferences: Union[Callable, bool, None]) -> Union['Tello', str]:
        '''
        Sets the drones mission pad detection. Requires mission pad detection to be enabled

        ### Parameters
        - dir: The direction(s) you would like the drone to detect a mission pad with (0 = Downward only, 1 = Forward only, 2 = Downward and Forward)

        ### Preferences
        - callback?: A function to be called once a response from the drone is received with said response as the first argument in string form.
        If a None value is provided, this method will be non-blocking but will have no callback.
        If False is provided, this method will be blocking and return the response (Defaults to False/blocking)
        '''

        return self._send('mdirection', 'mpad', preferences['callback'] if 'callback' in preferences else False, dir)

    def connect_wifi(self, ssid: Union[str, None] = None, pwd: Union[str, None] = None, **preferences: Union[Callable, bool, None]) -> Union['Tello', str]:
        '''
        Turns the drone into station mode and connects to a new access point with the provided SSID and password.
        If no values are provided a terminal prompt will be used to collect them instead

        ### Parameters
        - ssid?: The access point SSID you would like the drone to connect to
        - pwd?: The password for the access point you would like the drone to connect to

        ### Preferences
        - callback?: A function to be called once a response from the drone is received with said response as the first argument in string form.
        If a None value is provided, this method will be non-blocking but will have no callback.
        If False is provided, this method will be blocking and return the response (Defaults to False/blocking)
        '''

        return self._send('ac', 'connwifi', preferences['callback'] if 'callback' in preferences else False, (ssid, pwd))

    def get_speed(self, **preferences: Union[Callable, bool]) -> Union['Tello', str]:
        '''
        Returns the current speed of the drone (in cm/s)

        ### Preferences
        - callback?: A function to be called once a response from the drone is received with said response as the first argument in string form.
        If False is provided, this method will be blocking and return the response. Does not accept None since the return value of this function is needed (Defaults to False/blocking)
        '''

        if 'callback' in preferences and preferences['callback'] != False and not callable(preferences['callback']): raise TypeError('Callback function is incorrect. Please make sure it\'s a callable')

        return self._send('speed?', 'basic', preferences['callback'] if 'callback' in preferences else False)

    def get_battery(self, **preferences: Union[Callable, bool]) -> Union['Tello', str]:
        '''
        Returns the current battery percentage of the drone

        ### Preferences
        - callback?: A function to be called once a response from the drone is received with said response as the first argument in string form.
        If False is provided, this method will be blocking and return the response. Does not accept None since the return value of this function is needed (Defaults to False/blocking)
        '''

        return self._send('battery?', 'basic', preferences['callback'] if 'callback' in preferences else False)

    def get_time(self, **preferences: Union[Callable, bool]) -> Union['Tello', str]:
        '''
        Returns the current flight time of the drone

        ### Preferences
        - callback?: A function to be called once a response from the drone is received with said response as the first argument in string form.
        If False is provided, this method will be blocking and return the response. Does not accept None since the return value of this function is needed (Defaults to False/blocking)
        '''

        return self._send('time?', 'basic', preferences['callback'] if 'callback' in preferences else False)

    def get_signal_noise(self, **preferences: Union[Callable, bool]) -> Union['Tello', str]:
        '''
        Returns the drones current WiFi SNR (signal:noise ratio)

        ### Preferences
        - callback?: A function to be called once a response from the drone is received with said response as the first argument in string form.
        If False is provided, this method will be blocking and return the response. Does not accept None since the return value of this function is needed (Defaults to False/blocking)
        '''

        return self._send('wifi?', 'basic', preferences['callback'] if 'callback' in preferences else False)

    def get_sdk(self, **preferences: Union[Callable, bool]) -> Union['Tello', str]:
        '''
        Returns the current Tello SDK version of the drone

        ### Preferences
        - callback?: A function to be called once a response from the drone is received with said response as the first argument in string form.
        If False is provided, this method will be blocking and return the response. Does not accept None since the return value of this function is needed (Defaults to False/blocking)
        '''

        return self._send('sdk?', 'basic', preferences['callback'] if 'callback' in preferences else False)

    def get_serial(self, **preferences: Union[Callable, bool]) -> Union['Tello', str]:
        '''
        Returns the serial number of the drone

        ### Preferences
        - callback?: A function to be called once a response from the drone is received with said response as the first argument in string form.
        If False is provided, this method will be blocking and return the response. Does not accept None since the return value of this function is needed (Defaults to False/blocking)
        '''

        return self._send('sn?', 'basic', preferences['callback'] if 'callback' in preferences else False)

    def stream(self, on: bool = True, **preferences: Union[Callable, bool, None]) -> Union['Tello', str]:
        '''
        Enables/Disables the drones video stream

        ### Parameters
        - on?: The state to set the video stream to (Defaults to true/enabled)

        ### Preferences
        - callback?: A function to be called once a response from the drone is received with said response as the first argument in string form.
        If a None value is provided, this method will be non-blocking but will have no callback.
        If False is provided, this method will be blocking and return the response (Defaults to False/blocking)
        '''

        callback = preferences['callback'] if 'callback' in preferences else False

        if on:
            return self._send('streamon', 'basic', callback)
        else:
            return self._send('streamoff', 'basic', callback)

    def get_mission_pad(self) -> Union[str, None]:
        '''
        Returns the current mission pad ID of the one detected or None if not detected
        '''

        res = self._state('mid')
        return res if not res == -1 else None
    
    def get_mpxyz(self) -> Union[tuple[str], None]:
        '''
        Returns the current x, y, and z coordinates of the current detected mission pad or None if not detected
        '''

        res = self._state('x', 'y', 'z')
        return res if not 0 in res else None

    def get_mpx(self) -> Union[str, None]:
        '''
        Returns the current x coordinate of the current detected mission pad or None if not detected
        '''

        res = self._state('x')
        return res if not 0 in res else None

    def get_mpy(self) -> Union[str, None]:
        '''
        Returns the current y coordinate of the current detected mission pad or None if not detected
        '''

        res = self._state('y')
        return res if not 0 in res else None

    def get_mpz(self) -> Union[str, None]:
        '''
        Returns the current z coordinate of the current detected mission pad or None if not detected
        '''

        res = self._state('z')
        return res if not 0 in res else None

    def get_pry(self) -> tuple[str]:
        '''
        Returns the current pitch, roll, and yaw of the drone (in degrees)
        '''

        return self._state('pitch', 'roll', 'yaw')

    def get_pitch(self) -> str:
        '''
        Returns the current pitch of the drone (in degrees)
        '''

        return self._state('pitch')

    def get_roll(self) -> str:
        '''
        Returns the current roll of the drone (in degrees)
        '''

        return self._state('roll')

    def get_yaw(self) -> str:
        '''
        Returns the current yaw of the drone (in degrees)
        '''

        return self._state('yaw')

    def get_xyzspd(self) -> tuple[str]:
        '''
        Returns the current speed on the x, y, and z axis of the drone (in cm/s)
        '''

        return self._state('vgx', 'vgy', 'vgz')

    def get_xspd(self) -> str:
        '''
        Returns the current speed on the x axis of the drone (in cm/s)
        '''

        return self._state('vgx')

    def get_yspd(self) -> str:
        '''
        Returns the current speed on the y axis of the drone (in cm/s)
        '''

        return self._state('vgy')

    def get_zspd(self) -> str:
        '''
        Returns the current speed on the z axis of the drone (in cm/s)
        '''

        return self._state('vgz')

    def get_temps(self) -> tuple[str]:
        '''
        Returns the highest and lowest temperature the drone has experienced (in celsius)
        '''

        return self._state('templ', 'temph')

    def lowest_temp(self) -> str:
        '''
        Returns the lowest temprature the drone has experienced (in celsius)
        '''

        return self._state('templ')

    def highest_temp(self) -> str:
        '''
        Returns the highest temprature the drone has experienced (in celsius)
        '''

        return self._state('temph')

    def flight_length(self) -> str:
        '''
        Returns the distance the drone has flown in total (in cm)
        '''

        return self._state('tof')

    def get_height(self) -> str:
        '''
        Returns the current height of the drone (in cm)
        '''

        return self._state('h')

    def get_pressure(self) -> str:
        '''
        Returns the current air pressure of the drone (in cm)
        '''

        return self._state('baro')

    def get_time(self) -> str:
        '''
        Returns the total amount of time the drone motors have been used for
        '''

        return self._state('time')

    def get_axyz(self) -> tuple[str]:
        '''
        Returns the current acceleration on the x, y, and z axis of the drone (in cm/s)
        '''

        return self._state('agx', 'agy', 'agz')

    def get_ax(self) -> str:
        '''
        Returns the current acceleration on the x axis of the drone (in cm/s)
        '''

        return self._state('agx')

    def get_ay(self) -> str:
        '''
        Returns the current acceleration on the y axis of the drone (in cm/s)
        '''

        return self._state('agy')

    def get_az(self) -> str:
        '''
        Returns the current acceleration on the z axis of the drone (in cm/s)
        '''

        return self._state('agz')

    def photo(self, **preferences: Union[str, tuple[int], bool, Callable, None]) -> Union['Tello', str]:
        '''
        Takes a photo using the provided/default preferences.
        If no path is provided, it automatically creates a photos folder in the current directory with the photo having the current timestamp as the name and in png format @ 960 x 720 (720p, 4:3) resolution

        ## Preferences
        - path?: A string path that can also include provided file name and format. For pure directories, it must have a trailing forward slash (Defaults to ./photos/TIMESTAMP.png)
        - resolution?: A tuple of the resolution you would like the photo to be in. Goes up to 960 x 720 (Defaults to HD/720p)
        - window?: Enable/Disable a preview window after the photo is taken (Defaults to False/disabled)
        - callback?: A function to be called once the image proccesing for the photo is complete with the absolute path of said photo as the first argument.
        If a None value is provided, this method will be non-blocking but will have no callback.
        If False is provided, this method will be blocking and return the response (Defaults to False/blocking)
        '''

        self._checkstream()

        path = preferences['path'] if 'path' in preferences else './photos/'
        resolution = preferences['resolution'] if 'resolution' in preferences else (960, 720)
        callback = preferences['callback'] if 'callback' in preferences else False
        window = preferences['window'] if 'window' in preferences else False

        if type(window) is not bool: raise TypeError('Window preference provided was invalid. Please make sure it\'s a valid boolean type')
        elif type(path) is not str or not len(path) or not match(r'([:](?=[\/]+))|(^[\.](?=[\/]+))|(^[\~](?=[\/]+))|(^[\/](?=\w+))', path): raise ValueError('Provided path was invalid. Please make sure it\'s a valid string and in proper path format')
        elif type(resolution) is not tuple or len(resolution) != 2: raise ValueError('Provided resolution was invalid. Please make sure it\'s a valid tuple with 2 integers providing the width and height of the resolution')
        elif not (callback == False or None) and not callable(callback): raise TypeError('Callback function is incorrect. Please make sure it\'s a callable')

        for res in resolution:
            if type(res) is not int: raise TypeError('Provided resolution was invalid. Please make sure it\'s a valid tuple with 2 integers providing the width and height of the resolution')

        path = path.rsplit('/', 1)
        file = path[1] if '.' in path[1] else '{}.png'.format(datetime.now().strftime('%d_%m_%y_%H_%M_%S'))
        p = str(abspath(path[0]))
        path = f'{p}/{file}'

        if callback == False:
            try: mkdir(p)
            except FileExistsError: pass

            err = Popen([
                'ffmpeg',
                '-loglevel', 'quiet',
                '-y',
                '-f', 'h264',
                '-i', 'udp://{}:{}{}'.format(self._ips[1], self._ports[2], '?timeout={}'.format((self._to/3.2) * 1000000) if self._to else ''),
                '-pix_fmt', 'rgb24',
                '-frames:v', '1',
                '-vf', f'scale={resolution[0]}x{resolution[1]}',
                path
            ]).wait()

            if err: raise TelloError(f'Video server timed out. Did not receive stream from drone within {self._to} second(s)')

            if self._debug: print('[TELLO] Took a photo')
            if window: openimg(path).show(f'Tello - {file}')

            return path
        else:
            def thread():
                try: mkdir(p)
                except FileExistsError: pass

                err = Popen([
                        'ffmpeg',
                        '-loglevel', 'quiet',
                        '-y',
                        '-f', 'h264',
                        '-i', 'udp://{}:{}{}'.format(self._ips[1], self._ports[2], '?timeout={}'.format(self._to * 1000000) if self._to else ''),
                        '-pix_fmt', 'rgb24',
                        '-frames:v', '1',
                        '-vf', f'scale={resolution[0]}x{resolution[1]}',
                        path
                    ]).wait()

                if err: raise TelloError(f'Video server timed out. Did not receive stream from drone within {self._to} second(s)')

                if self._debug: print('[TELLO] Took a photo')
                if window: openimg(path).show(f'Tello - {file}')
                if callback: callback(path)

                return

            Thread(target = thread).start()
            return self

    def photo_bytes(self, **preferences: Union[tuple[int], Callable, bool]) -> Union['Tello', bytes]:
        '''
        Returns the bytes of the photo taken in the provided/default resolution

        ### Preferences
        - resolution?: A tuple of the resolution you would like the photo to be in. Goes up to 1280 x 720 (Defaults to HD/720p)
        - callback?: A function to be called once the image proccesing for the photo is complete with the bytes of said photo as the first argument.
        If False is provided, this method will be blocking and return the response. Does not accept None since the return value of this function is needed
        (Defaults to False/blocking)
        '''

        self._checkstream()

        resolution = preferences['resolution'] if 'resolution' in preferences else (960, 720)
        callback = preferences['callback'] if 'callback' in preferences else False

        if type(resolution) is not tuple or len(resolution) != 2: raise ValueError('Provided resolution was invalid. Please make sure it\'s a valid tuple with 2 integers providing the width and height of the resolution')
        elif callback != False and not callable(callback): raise TypeError('Callback function is incorrect. Please make sure it\'s a callable')

        for res in resolution:
            if type(res) is not int: raise TypeError('Provided resolution was invalid. Please make sure it\'s a valid tuple with 2 integers providing the width and height of the resolution')

        if callback:
            def thread():
                proc = Popen([
                    'ffmpeg',
                    '-loglevel', 'quiet',
                    '-y',
                    '-f', 'h264',
                    '-i', 'udp://{}:{}{}'.format(self._ips[1], self._ports[2], '?timeout={}'.format((self._to/3.2) * 1000000) if self._to else ''),
                    '-f', 'image2',
                    '-frames:v', '1',
                    '-vf', f'scale={resolution[0]}x{resolution[1]}',
                    '-'
                ], stdout = PIPE, bufsize = 10**8)

                if proc.wait(): raise TelloError(f'Video server timed out. Did not receive stream from drone within {self._to} second(s)')

                callback(proc.communicate()[0])
                return

            Thread(target = thread).start()
            return self
        else:
            proc = Popen([
                'ffmpeg',
                '-loglevel', 'quiet',
                '-y',
                '-f', 'h264',
                '-i', 'udp://{}:{}{}'.format(self._ips[1], self._ports[2], '?timeout={}'.format((self._to/3.2) * 1000000) if self._to else ''),
                '-f', 'image2',
                '-frames:v', '1',
                '-vf', f'scale={resolution[0]}x{resolution[1]}',
                '-'
            ], stdout = PIPE, bufsize = 10**8)

            if proc.wait(): raise TelloError(f'Video server timed out. Did not receive stream from drone within {self._to} second(s)')

            return proc.communicate()[0]

    def start_video(self, **preferences: Union[str, tuple[int], int, bool, Callable, None]) -> None:
        '''
        Takes a video using the provided/default parameters. If no path is provided, it automatically creates a videos folder in the current directory with the video having the current timestamp as the name and in mp4 format @ 960 x 720 (720p, 4:3) resolution
        and in 60fps. Will not stop recording until the Tello.stop_video() method is run

        ### Preferences
        - path?: A string path that can also include provided file name and format. For pure directories, it must have a trailing forward slash (Defaults to ./videos/TIMESTAMP.mp4)
        - resolution?: A tuple of the resolution you would like the video to be in. Goes up to 1280 x 720 (Defaults to HD/720p)
        - framerate?: An integer of the framerate you would like the video to be in. Goes up to 60fps (Defaults to 60fps)
        - window?: Enable/Disable a live preview window while the video is being taken. If enabled a web folder will be created for the livestream and will be deleted at the end (Defaults to False/disabled)
        - callback?: A function to be called once the Tello.stop_video() method is called with the absolute path to said video as the first argument.
        Does not accept False since the video recorder always runs in a seperate thread (Defaults to None)
        '''

        self._checkstream()

        path = preferences['path'] if 'path' in preferences else './videos/'
        resolution = preferences['resolution'] if 'resolution' in preferences else (960, 720)
        framerate = preferences['framerate'] if 'framerate' in preferences else 60
        callback = preferences['callback'] if 'callback' in preferences else None
        window = preferences['window'] if 'window' in preferences else False
        rb = resolution[0] * resolution[1] * 3

        if not type(path) is str or not len(path) or not match(r'([:](?=[\/]+))|(^[\.](?=[\/]+))|(^[\~](?=[\/]+))|(^[\/](?=\w+))', path): raise ValueError('Provided path was invalid. Please make sure it\'s a valid string and in proper path format')
        elif not type(resolution) is tuple or not len(resolution) == 2: raise ValueError('Provided resolution was invalid. Please make sure it\'s a valid tuple with 2 integers providing the width and height of the resolution')
        elif not type(framerate) is int or not 10 <= framerate <= 60: raise ValueError('Provided framerate was invalid. Please make sure it\'s a valid integer and inbetween 10 - 60')
        elif not type(window) is bool: raise TypeError('Window value provided was invalid. Please make sure it\'s a valid boolean type')
        elif callback != None and not callable(callback): raise TypeError('Callback function is incorrect. Please make sure it\'s a callable')

        for res in resolution:
            if type(res) is not int: raise TypeError('Provided resolution was invalid. Please make sure it\'s a valid tuple with 2 integers providing the width and height of the resolution')

        if window and self._web: raise TelloError('Webserver on live method already created. Please run the Tello.stop_live() method first')

        path = path.rsplit('/', 1)
        file = path[1] if '.' in path[1] else '{}.mp4'.format(datetime.now().strftime('%d_%m_%y_%H_%M_%S'))
        p = str(abspath(path[0]))
        path = f'{p}/{file}'

        self._rec = True

        try: mkdir(p)
        except FileExistsError: pass

        proc = Popen([
            'ffmpeg',
            '-loglevel', 'quiet',
            '-y',
            '-f', 'h264',
            '-i', 'udp://{}:{}{}'.format(self._ips[1], self._ports[2], '?timeout={}'.format((self._to/3.2) * 1000000) if self._to else ''),
            '-f', 'rawvideo',
            '-pix_fmt', 'rgb24',
            '-vf', f'scale={resolution[0]}x{resolution[1]}, fps={str(framerate)}',
            '-'
        ], stdout = PIPE, bufsize = 10**8)

        sleep(self._to)
        if proc.poll(): raise TelloError(f'Video server timed out. Did not receive stream from drone within {self._to} second(s)')

        rec = Popen([
            'ffmpeg',
            '-loglevel', 'quiet',
            '-y',
            '-pix_fmt', 'rgb24',
            '-s', f'{resolution[0]}x{resolution[1]}',
            '-f', 'rawvideo',
            '-i', '-',
            '-pix_fmt', 'yuv420p',
            path
        ], stdin = PIPE)

        if window:
            try: mkdir('./web')
            except: pass

            open('./web/play.m3u8', 'w').close()

            hls = Popen([
                'ffmpeg',
                '-y',
                '-loglevel', 'quiet',
                '-pix_fmt', 'rgb24',
                '-s', f'{resolution[0]}x{resolution[1]}',
                '-f', 'rawvideo',
                '-i', '-',
                '-pix_fmt', 'yuv420p',
                '-hls_time', '0',
                '-hls_flags', 'delete_segments',
                '-hls_list_size', '1',
                './web/play.m3u8'
            ], stdin = PIPE)

            def thread():
                f = proc.stdout.read(rb)
                rec.stdin.write(f)
                hls.stdin.write(f)
                if self._debug: print('[TELLO] Starting recording')

                openweb('http://127.0.0.1', new = 2)

                while self._rec and self._running:
                    f = proc.stdout.read(rb)
                    rec.stdin.write(f)
                    hls.stdin.write(f)
                else:
                    rec.communicate()
                    hls.communicate()
                    proc.send_signal(2)
                    self._web.shutdown()
                    self._web = None

                    rmtree('./web')

                    if self._debug: print('[TELLO] Recording finished')
                    if callback: callback(path)
                    return

            self._web = HTTPServer(('', 80), _TelloWebRec)

            Thread(target = thread).start()
            Thread(target = self._web.serve_forever, daemon = True).start()
        else:
            def thread():
                rec.stdin.write(proc.stdout.read(rb))

                if self._debug: print('[TELLO] Starting recording')
                while self._rec and self._running:
                    rec.stdin.write(proc.stdout.read(rb))
                else:
                    rec.communicate()
                    proc.send_signal(2)

                    if self._debug: print('[TELLO] Recording finished')
                    if callback: callback(path)
                    return

            Thread(target = thread).start()

    def video_bytes(self, **preferences: Union[tuple[int], int, bool, Callable]) -> Union['Tello', list[bytes]]:
        '''
        Returns a list of each video frame with the bytes of said frame being taken in the provided/default resolution. Will not stop appending frames until the provided max frames is met or the Tello.stop_frames() method is run

        ### Preferences
        - resolution?: A tuple of the resolution you would like the video to be in. Goes up to 1280 x 720 (Defaults to HD/720p)
        - frames?: The max amount of frames you would like to be generated (Defaults to 0/unlimited)
        - callback?: A function to be called once the max amount of frames is reached or the Tello.stop_frames() method is run with the bytes of said video frames as the first argument.
        If False is provided, this method will be blocking and return the response. Does not accept None since the return value of this function is needed (Defaults to False/blocking)
        '''

        self._checkstream()

        frames = preferences['frames'] if 'frames' in preferences else 0
        resolution = preferences['resolution'] if 'resolution' in preferences else (960, 720)
        callback = preferences['callback'] if 'callback' in preferences else False
        rb = resolution[0] * resolution[1] * 3

        if type(resolution) is not tuple or len(resolution) != 2: raise ValueError('Provided resolution was invalid. Please make sure it\'s a valid tuple with 2 integers providing the width and height of the resolution')
        elif type(frames) is not int: raise TypeError('Provided frame count was invalid. Please make sure it\'s a valid integer')
        elif callback != False and not callable(callback): raise TypeError('Callback function is incorrect. Please make sure it\'s a callable')

        for res in resolution:
            if type(res) is not int: raise TypeError('Provided resolution was invalid. Please make sure it\'s a valid tuple with 2 integers providing the width and height of the resolution')

        ret = []

        if callback:
            def thread():
                proc = Popen([
                    'ffmpeg',
                    '-loglevel', 'quiet',
                    '-y',
                    '-f', 'h264',
                    '-i', 'udp://{}:{}{}'.format(self._ips[1], self._ports[2], '?timeout={}'.format((self._to/3.2) * 1000000) if self._to else ''),
                    '-f', 'rawvideo',
                    '-pix_fmt', 'rgb24',
                    '-vf', f'scale={resolution[0]}x{resolution[1]}'
                    '-'
                ], stdout = PIPE, bufsize = 10**8)

                sleep(self._to)
                if proc.poll(): raise TelloError(f'Video server timed out. Did not receive stream from drone within {self._to} second(s)')

                if frames:
                    for _ in range(frames):
                        ret.append(proc.stdout.read(rb))
                    else:
                        proc.send_signal(2)
                else:
                    self._frames = True
                    while self._frames and self._running:
                        ret.append(proc.stdout.read(rb))
                    else:
                        proc.send_signal(2)

                callback(ret)
                return

            Thread(target = thread).start()
            return self
        else:
            proc = Popen([
                'ffmpeg',
                '-loglevel', 'quiet',
                '-y',
                '-f', 'h264',
                '-i', 'udp://{}:{}{}'.format(self._ips[1], self._ports[2], '?timeout={}'.format((self._to/3.2) * 1000000) if self._to else ''),
                '-f', 'rawvideo',
                '-pix_fmt', 'rgb24',
                '-vf', f'scale={resolution[0]}x{resolution[1]}',
                '-'
            ], stdout = PIPE, bufsize = 10**8)

            sleep(self._to)  
            if proc.poll(): raise TelloError(f'Video server timed out. Did not receive stream from drone within {self._to} second(s)')

            if frames:
                for _ in range(frames):
                    ret.append(proc.stdout.read(rb))
                else:
                    proc.send_signal(2)
            else:
                self._frames = True
                while self._frames and self._running:
                    ret.append(proc.stdout.read(rb))
                else:
                    proc.send_signal(2)

            return ret

    def live(self, **preferences: Union[tuple[int], int]) -> None:
        '''
        Displays a live feed of the drone video inside a browser window in the provided/default resolution and framerate. Will not shut down the webserver until the Tello.stop_live() method is run

        ### Parameters
        - resolution?: A tuple of the resolution you would like the video to be in. Goes up to 1280 x 720 (Defaults to HD/720p)
        - framerate?: An integer of the framerate you would like the video to be in. Goes up to 60fps (Defaults to 60fps)
        '''

        self._checkstream()

        resolution = preferences['resolution'] if 'resolution' in preferences else (960, 720)
        framerate = preferences['framerate'] if 'framerate' in preferences else 60
        rb = resolution[0] * resolution[1] * 3

        if type(resolution) is not tuple or len(resolution) != 2: raise ValueError('Provided resolution was invalid. Please make sure it\'s a valid tuple with 2 integers providing the width and height of the resolution')
        elif type(framerate) is not int or not 10 <= framerate <= 60: raise ValueError('Provided framerate was invalid. Please make sure it\'s a valid integer and inbetween 10 - 60')

        if self._web: raise TelloError('Webserver on video method already created. Please run the Tello.stop_video() method first')

        self._live = True

        proc = Popen([
            'ffmpeg',
            '-loglevel', 'quiet',
            '-y',
            '-f', 'h264',
            '-i', 'udp://{}:{}{}'.format(self._ips[1], self._ports[2], '?timeout={}'.format((self._to/3.2) * 1000000) if self._to else ''),
            '-f', 'rawvideo',
            '-pix_fmt', 'rgb24',
            '-vf', f'scale={resolution[0]}x{resolution[1]}, fps={str(framerate)}'
            '-'
        ], stdout = PIPE, bufsize = 10**8)

        if proc.poll(): raise TelloError(f'Video server timed out. Did not receive stream from drone within {self._to} second(s)')

        try: mkdir('./web')
        except: pass

        open('./web/play.m3u8', 'w').close()

        hls = Popen([
            'ffmpeg',
            '-y',
            '-loglevel', 'quiet',
            '-pix_fmt', 'rgb24',
            '-s', f'{resolution[0]}x{resolution[1]}',
            '-f', 'rawvideo',
            '-i', '-',
            '-pix_fmt', 'yuv420p',
            '-hls_time', '0',
            '-hls_flags', 'delete_segments',
            '-hls_list_size', '1',
            './web/play.m3u8'
        ], stdin = PIPE)

        def thread():
            hls.stdin.write(proc.stdout.read(rb))
            if self._debug: print('[TELLO] Starting live session')

            openweb('http://127.0.0.1', new = 2)

            while self._live and self._running:
                hls.stdin.write(proc.stdout.read(rb))
            else:
                hls.communicate()
                proc.send_signal(2)
                self._web.shutdown()
                self._web = None

                rmtree('./web')

                if self._debug: print('[TELLO] Live session ended')
                return

        self._web = HTTPServer(('', 80), _TelloWebLive)

        Thread(target = thread).start()
        Thread(target = self._web.serve_forever, daemon = True).start()

    def stop_video(self) -> None:
        '''
        Ends the Tello.start_video() method from recording data. The resulting video will be saved to disk and if the window preference was enabled the webserver will be shutdown
        '''

        self._rec = False

    def stop_frames(self) -> None:
        '''
        Stops the Tello.video_bytes() method from collecting frames
        '''

        self._frames = False

    def stop_live(self) -> None:
        '''
        Shuts down the Tello.live() method webserver
        '''

        self._live = False

    def exit(self, wait: bool = True) -> None:
        '''
        Exits the class and closes all threads. If the drone is still flying, it will be landed if the safety preference is enabled

        ### Parameters
        - wait?: Enable/Disable waiting for the asynchronous queue to finish (Defaults to True/Enabled)
        '''

        if self._sm and self._flying: self._send('land', 'basic')

        if wait: self._cqueue.join()

        self._running = False
