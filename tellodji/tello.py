'''
Library for interacting with Tello drones using the v2.0 and v1.3 versions of the Tello Ryze SDK.
Made by zahtec (https://www.github.com/zahtec/tellodji)
'''

from http.server import BaseHTTPRequestHandler, HTTPServer
from socket import AF_INET6, socket, SOCK_DGRAM, AF_INET
from webbrowser import open as openweb
from PIL.Image import open as openimg
from os.path import abspath, dirname
from threading import Thread, Event
from typing import Callable, Union
from subprocess import Popen, PIPE
from.tello_error import TelloError
from shutil import rmtree, which
from ipaddress import ip_address
from .exception import exception
from datetime import datetime
from re import findall, match
from getpass import getpass
from queue import Queue
from time import sleep
from os import mkdir

class _TelloWebRec(BaseHTTPRequestHandler):
    '''
    Internal class for the start_video() webserver. You normally wouldn't use this yourself
    '''

    def do_GET(self) -> None:
        if self.path == '/':
            self.send_response(200) 
            self.send_header('content-type', 'text/html')
            self.end_headers()

            with open(f'{dirname(__file__)}/record.html') as f:
                self.wfile.writelines(f.buffer)

        elif self.path == '/play.m3u8':
            self.send_response(200) 
            self.send_header('content-type', 'application/x-mpegURL')
            self.end_headers()

            with open('./web/play.m3u8') as f:
                self.wfile.writelines(f.buffer)

        elif self.path.endswith('.ts'):
            try:
                self.send_response(200) 
                self.send_header('content-type', 'application/x-mpegURL')
                self.end_headers()
                with open(f'./web{self.path}') as f:
                    self.wfile.writelines(f.buffer)
            except:
                self.send_response(404)
                self.end_headers()

        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, *_) -> None:
        pass

class _TelloWebLive(BaseHTTPRequestHandler):
    '''
    Internal class for the live() webserver. You normally wouldn't use this yourself
    '''

    def do_GET(self) -> None:
        if self.path == '/':
            self.send_response(200) 
            self.send_header('content-type', 'text/html')
            self.end_headers()

            with open(f'{dirname(__file__)}/live.html') as f:
                self.wfile.writelines(f.buffer)

        elif self.path == '/play.m3u8':
            self.send_response(200) 
            self.send_header('content-type', 'application/x-mpegURL')
            self.end_headers()

            with open('./web/play.m3u8') as f:
                self.wfile.writelines(f.buffer)

        elif self.path.endswith('.ts'):
            try:
                self.send_response(200) 
                self.send_header('content-type', 'application/x-mpegURL')
                self.end_headers()
                with open(f'./web{self.path}') as f:
                    self.wfile.writelines(f.buffer)
            except:
                self.send_response(404)
                self.end_headers()

        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, *_) -> None:
        pass

@exception
class Tello:
    '''
    The main class for the Tello library. Used to construct a socket that will send & receive data from any
    Tello Ryze drone. If an IP address or any ports were provided they will be used in the construction of the sockets.
    Made for the v2.0 and v1.3 of the Tello Ryze SDK. For anything video related, ffmpeg must be installed.
    Kwargs are nicknamed preferences for semantic reasons

    ### Parameters
    - ips?: The IP addresses you would like the Tello sockets to bind & connect to. There must be at least 1 IP address with others inputted as None
    First one is for the command and state servers, second one is for the optional video server (ipv4/ipv6, Defaults to 192.168.10.1, 0.0.0.0)
    - ports?: The ports you would like the Tello sockets to bind & connect to. There must be at least 2 ports with others inputted as None
    First one is for the command server, second one is for the state server, third one is for the optional video server (Defaults to 8889, 8890, 11111)

    ### Preferences
    - default_distance?: The default distance you would like the drone to move if none is provided during a movement function (Defaults to 50cm)
    - default_rotation?: The default degrees you would like the drone to rotate if none is provided during a movement function (Defaults to 90deg, must be between 1 - 360deg)
    - default_speed?: The default speed you would like the drone to move at (Defaults to 30cm/s, must be between 10 - 60cm/s)
    - timeout?: The amount of time you would like to wait for a response from a drone before a timeout error is raised. If 0 is provided it will have no timeout (Defaults to 7s)
    - sync?: Make library as synchronous by default. Meaning if no callback value is provided to certain methods, it will default to none instead of false. If a function is provided for this preference, it will be set to the default callback for each method. Does not include video methods (Defaults to true/enabled)
    - safety?: Enable/Disable landing the drone if an error is raised (Defaults to true/enabled)
    - takeoff?: Enable/Disable automatically making the drone takeoff on class contrusction (Defaults to false/disabled))
    - syncfix?: Enable/Disable preventing commands going out of sync, if an asynchronous method hasnt completed when a synchronous method is called it will wait for the asynchronous task to complete (Defaults to true/enabled)
    - mission_pad?: Enable/Disable the detection of mission pads (Defaults to false/disabled)
    - video?: Enable/Disable video on by default. Will send the streamon command to the drone (Defaults to false/disabled)
    - debug?: Enable/Disable the debug mode for verbose console logging (Defaults to false/disabled)

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
    HD = (1280, 720)
    SD = (852, 480)

    def __init__(self, ips: tuple[int | None] = ('192.168.10.1', '0.0.0.0'), ports: tuple[int | None] = (8889, 8890, 11111), **opt) -> None:
        if not type(ips) is tuple or not len(ips) == 2: raise TelloError('IP addresses provided were invalid. Please make sure it\'s a valid tuple with at least 1 address with others inputted as None')
        elif not type(ports) is tuple or not len(ports) == 3: raise TelloError('Ports provided were invalid. Please make sure it\'s a valid tuple with at least 1 port with others inputted as None')
        elif 'default_distance' in opt and (not type(opt['default_distance']) is int or not 20 <= opt['default_distance']): raise TelloError('Default distance value provided was invalid. Please make sure it\'s a valid integer and at at least 20cm')
        elif 'default_rotation' in opt and (not type(opt['default_rotation']) is int or not 1 <= opt['default_rotation'] <= 360): raise TelloError('Default rotation value provided was invalid. Please make sure it\'s a valid integer and in between 1-360deg')
        elif 'default_speed' in opt and (not type(opt['default_speed']) is int or not 10 <= opt['default_speed'] <= 60): raise TelloError('Default speed value provided was invalid. Please make sure it\'s a valid integer and between 10-60cm/s')
        elif 'timeout' in opt and (not type(opt['timeout']) is int or not 0 <= opt['timeout']): raise TelloError('Timeout value provided was invalid. Please make sure it\'s a valid integer and at least 0')
        elif 'mission_pad' in opt and not type(opt['mission_pad']) is bool: raise TelloError('Mission pad preference provided was invalid. Please make sure it\'s a valid boolean type')
        elif 'safety' in opt and not type(opt['safety']) is bool: raise TelloError('Safety preference provided was invalid. Please make sure it\'s a valid boolean type')
        elif 'sync' in opt and not (type(opt['sync']) is bool or callable(opt['sync'])): raise TelloError('Sync preference provided was invalid. Please make sure it\'s a valid boolean type or a callable')
        elif 'takeoff' in opt and not type(opt['takeoff']) is bool: raise TelloError('Takeoff preference provided was invalid. Please make sure it\'s a valid boolean type')
        elif 'syncfix' in opt and not type(opt['syncfix']) is bool: raise TelloError('Syncfix preference provided was invalid. Please make sure it\'s a valid boolean type')
        elif 'debug' in opt and not type(opt['debug']) is bool: raise TelloError('Debug preference provided was invalid. Please make sure it\'s a valid boolean type')
        elif 'video' in opt and not type(opt['video']) is bool: raise TelloError('Video preference provided was invalid. Please make sure it\'s a valid boolean type')

        for ip in ips:
            if ip: ip_address(ip)

        for port in ports:
            if port and not type(port) is int: raise TelloError('One or more ports provided were invalid. Please make sure they are integers and in proper port form')

        self._ips = (ips[0], ips[1] if ips[1] else '0.0.0.0')
        self._ports = (ports[0], ports[1] if ports[1] else 8890, ports[2] if ports[2] else 11111)
        self._to = (opt['timeout'] if opt['timeout'] > 0 else None) if 'timeout' in opt else 7
        self._running = True
        self._flying = False
        self._rec = False
        self._web = None
        self._frames = False
        self._live = False
        self._streaming = True
        self._cqueue, self._slist = Queue(), {}
        self._sevent = Event()
        self._sevent.set()

        self._dd = opt['default_distance'] if 'default_distance' in opt else 50
        self._dr = opt['default_rotation'] if 'default_rotation' in opt else 90
        self._spd = opt['default_speed'] if 'default_speed' in opt else 30
        self._sm = opt['safety'] if 'safety' in opt else True
        self._sync = opt['sync'] if 'sync' in opt else True
        self._oos = opt['syncfix'] if 'syncfix' in opt else True
        self._mp = opt['mission_pad'] if 'mission_pad' in opt else False
        self._debug = opt['debug'] if 'debug' in opt else False

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

        self._send_sync('Command', 'basic')
        self._send_sync('speed', 'aval', self._spd)
        if self._mp: self._send_sync('mon', 'basic')
        if 'video' in opt and opt['video']: self._send_sync('streamon', 'basic')
        if 'takeoff' in opt and opt['takeoff']:
            self._flying = True
            self._send_sync('takeoff', 'basic')
        if self._debug: print(f'[TELLO] Default movement distance is set to -> {self._dd}cm\n[TELLO] Default movement speed is set to -> {self._spd}cm/s')

    def ips(self) -> str:
        '''
        Returns the current IP addresses the Tello socket's are sending to/receiving from
        '''

        return self._ips

    def set_ips(self, ips: tuple[str]) -> None:
        '''
        Changes the Tello socket's IP address to the one provided. Does not change the ip of any method ran beforehand

        ### Parameters
        - ip: The IP that that you want the sockets to switch to (ipv4/ipv6)
        '''

        if not type(ips) is tuple or not len(ips) == 2: raise TelloError('IP addresses provided were invalid. Please make sure it\'s a valid tuple with at least 1 address with others inputted as None')

        for ip in ips:
            if not type(ip) is int or (ips.index(ip) == 1 and type(ip) is None): raise TelloError('IP addresses provided were invalid. Please make sure it\'s a valid tuple with at least 1 address with others inputted as None')
            ip_address(ip)

        ips = (ips[0], ips[1] if ips[1] else self._ips[1])

        if ips == self._ips: raise TelloError('IPs provided are the same as the currently set ones')

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

        if not type(ports) is tuple or not len(ports) == 2: raise TelloError('Ports provided were invalid. Please make sure it\'s a valid tuple with at least 1 port with others inputted as None')

        for port in ports:
            if not type(port) is int or None: raise TelloError('One or more ports provided were invalid. Please make sure they\'re valid integers and in proper port form')

        ports = (ports[0], ports[1] if ports[1] else self._ports[1])

        if ports == self._ports: raise TelloError('Ports provided are the same as the currently set ones')

        self._ports = ports
        self._sevent.clear()

        self._sserver.shutdown()
        self._sserver = socket(AF_INET, SOCK_DGRAM), socket(AF_INET, SOCK_DGRAM)
        self._sserver.bind((self._ips[0], ports[1]))
        self._sserver.settimeout(self._to)

        self._sevent.set()

        if self._debug: print(f'[TELLO] Set command socket to -> {self._ips[0]}:{ports[0]}\n[TELLO] Set state socket to -> {self._ips[0]}:{ports[1]}')

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

        if not type(timeout) is int or timeout < 1: raise TelloError('Timeout provided was invalid. Please make sure it\'s a integer and at least 1 second')

        if timeout == self._to: raise TelloError('Timeout provided was the same as the currently set one')

        self._to = timeout

        if self._debug: print(f'[TELLO] Set timeout to -> {timeout}')

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

        if not type(distance) is int or not 20 <= distance: raise TelloError('Distance value provided was invalid. Please make sure it is a valid integer and at least 20cm')

        if distance == self._dd: raise TelloError('Default distance value provided is the same as the currently set value')

        self._dd = distance

        if self._debug: print(f'[TELLO] Set default distance to -> {distance}cm')

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

        if not speed is int or not 10 <= speed <= 100: raise TelloError('Speed value provided was invalid. Please make sure it is a valid integer and at least 10')

        if speed == self._spd: raise TelloError('Default speed value provided is the same as the currently set value')

        self._send_sync('speed', 'setspd', speed)
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

        if not type(preference) is bool: raise TelloError('Preference value provided was invalid. Please make sure it\'s a valid boolean type')

        if preference == self._mp: raise TelloError('Mission pad preference provided is the same as the currently set one')

        if preference: self._send_sync('mon', 'basic')
        else: self._send_sync('moff', 'basic')

        self._mp = preference

        if self._debug: print(f'[TELLO] Set mission pad preference to -> {preference}')

    def sync(self) -> bool:
        '''
        Returns the state the sync preference is set to
        '''

        return self._sync

    def set_sync(self, preference: bool | Callable) -> None:
        '''
        Enables/Disables the library as synchronous by default. Meaning if no callback value is provided to certain methods, it will default to none instead of false

        ### Parameters
        - preference: The state to set the sync preference to (True/False)
        '''

        c = callable(preference)

        if not (type(preference) is bool or c): raise TelloError('Preference value provided was invalid. Please make sure it\'s a valid boolean type or a callable')

        if preference == self._sync: raise TelloError('Sync preference provided is the same as the currently set one')

        self._sync = preference

        if self._debug: print('[TELLO] Set sync preference to -> {}'.format(preference if not c else f'function {preference.__name__}'))

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

        if not type(preference) is bool: raise TelloError('Preference value provided was invalid. Please make sure it\'s a valid boolean type')

        if preference == self._oos: raise TelloError('Syncfix preference provided is the same as the currently set one')

        self._oos = preference

        if self._debug: print(f'[TELLO] Set syncfix preference to -> {preference}')

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

        if not type(preference) is bool: raise TelloError('Preference value provided was invalid. Please make sure it\'s a valid boolean type')

        if preference == self._debug: raise TelloError('Debug preference provided is the same as the currently set one')

        if self._debug and not preference: print('[TELLO] Debug mode disabled')
        elif not self._debug and preference: print('[TELLO] Debug mode enabled')

        self._debug = preference

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

                if not 'ok' in res: raise TelloError(f'Drone responded with error: {res}')
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

    def _send_sync(self, msg: str, typ: str, val: int | tuple[Union[int, str]] = None) -> str:
        '''
        Internal method for sending data synchronously to the drone. You normally wouldn't use this yourself
        '''

        def sender(msg: str):
            if self._oos: self._cqueue.join()

            self._cserver.sendto(msg.encode(), (self._ips[0], self._ports[0]))

            try: res = self._cserver.recv(1024).decode().lower()
            except TimeoutError: raise TelloError(f'Timed out. Did not receive response from drone within {self._to} second(s)')
            except KeyboardInterrupt: return

            if not 'ok' in res: raise TelloError(f'Drone responded with error: {res}')
            else:
                if 'streamon' in msg: self._streaming = True
                elif 'streamoff' in msg: self._streaming = False
                if self._debug:
                    if 'wifi' in msg or msg.startswith('ac'): print(f'[TELLO] Set wifi successfully')
                    else: print(f'[TELLO] Sent command \'{msg}\' successfully')

            return res

        match typ:
            case 'basic':
                return sender(msg)

            case 'aval':
                return sender(f'{msg} {val}')

            case 'dist':
                if not type(val) is int or not 20 <= val: raise TelloError('Distance value is incorrect. Please make sure it\'s a valid integer and at least 20cm')

                def disrun(val):
                    while val > 500:
                        val -= 500
                        yield 500
                    else: yield val

                ret = []

                for dist in disrun(val):
                    ret.append(sender(f'{msg} {dist}'))

                return ret if len(ret) > 1 else ret[0]

            case 'rot':
                if not type(val) is int or not 1 <= val <= 360: raise TelloError('Rotational value is incorrect. Please make sure it\'s a valid integer and between 1 - 360deg')

                return sender(f'{msg} {val}')

            case 'cord':
                msg = f'{msg} '

                for n in val:
                    isd = type(n) is int

                    if val.index(n) == len(val)-1:
                        if not isd: raise TelloError('Speed value is incorrect. Please make sure it\'s a valid integer')
                        elif n[1] and not 10 <= n <= 60: raise TelloError('Speed value is incorrect. Please make sure it\'s between 10 - 60cm/s')
                        elif not n[1] and not 10 <= n <= 100: raise TelloError('Speed value is incorrect. Please make sure it\'s between 10 - 100cm/s')
                    elif not isd or not -500 <= n <= 500: raise TelloError('coordinate value is incorrect. Please make sure it\'s a valid integer and between -500 - 500cm')

                    msg += f'{n} '

                return sender(msg.rstrip())

            case 'mid':
                msg = f'{msg} '

                for n in val:
                    ind = val.index(n)
                    leg = len(val)
                    isd = type(n) is int

                    if ind == leg-2:
                        if not isd: raise TelloError('Speed value is incorrect. Please make sure it\'s a valid integer')
                        elif n[1] and not 10 <= n <= 60: raise TelloError('Speed value is incorrect. Please make sure it\'s between 10 - 60cm/s')
                        elif not n[1] and not 10 <= n <= 100: raise TelloError('Speed value is incorrect. Please make sure it\'s between 10 - 100cm/s')
                    elif ind == leg-1 and not type(n) == str or not match(r'^[m][1-8]$', n): raise TelloError('Mission Pad value is incorrect. Please make sure it\'s a valid string and is between m1 - m8')
                    elif not isd or not -500 <= n <= 500: raise TelloError('coordinate value is incorrect. Please make sure it\'s a valid integer and between -500 - 500cm')

                    msg += f'{n} '

                return sender(msg.rstrip())

            case 'jump':
                msg = f'{msg} '

                for n in val:
                    ind = val.index(n)
                    leg = len(val)
                    isd = type(n) is int

                    if ind == leg-4:
                        if not isd: raise TelloError('Speed value is incorrect. Please make sure it\'s a valid integer')
                        elif n[1] and not 10 <= n <= 60: raise TelloError('Speed value is incorrect. Please make sure it\'s between 10 - 60cm/s')
                        elif not n[1] and not 10 <= n <= 100: raise TelloError('Speed value is incorrect. Please make sure it\'s between 10 - 100cm/s')
                    elif ind == leg-3 and not 1 <= n <= 360: raise TelloError('Yaw value is incorrect. Please make sure it\'s a valid integer and between 1 - 360deg')
                    elif ind == leg-1 or ind == leg-2 and not type(n) == str or not match(r'^[m][1-8]$', n): raise TelloError('Mission Pad value is incorrect. Please make sure it\'s a valid string and is between m1 - m8')
                    elif not isd or not -500 <= n <= 500: raise TelloError('coordinate value is incorrect. Please make sure it\'s a valid integer and between -500 - 500cm')

                    msg += f'{n} '

                return sender(msg.rstrip())

            case 'setspd':
                if not type(val) is int or not 10 <= val <= 60: raise TelloError('Speed value is incorrect. Please make sure it\'s a valid integer and between 10 - 60cm/s')

                self._spd = val

                return sender(f'{msg} {val}')

            case 'setrc':
                msg = f'{msg} '

                for n in val:
                    if not type(n) is int or not -100 <= n <= 100: raise TelloError('Joystick distance value is incorrect. Please make sure it\'s a valid integer and between -100 - 100')
                    msg += f'{n} '

                return sender(msg.rstrip())

            case 'setwifi':
                val = [*val]

                if not val[0] and not val[1]:
                    try:
                        val[0] = input('Enter new WiFi SSID: ').strip()
                        val[1] = getpass('Enter new WiFi password: ').strip()
                    except: return
                if not type(val[0]) is str or not len(val[0]): raise TelloError('WiFi SSID value is incorrect. Please make sure it\'s a valid string and at least 1 character')
                elif not type(val[1]) is str or not len(val[1]) >= 5: raise TelloError('WiFi password value is incorrect. Please make sure it\'s a valid string and at least 5 characters')
                elif not match(r'(?=(?:[^a-z]*[a-z]){2})(?=(?:[^A-Z]*[A-Z]){2})(?=(?:[^0-9]*[0-9]){1})', val[1]): raise TelloError('WiFi password value is insecure. Please make sure it contains at least 2 lowercase and uppercase letters and 1 number')

                return sender(f'{msg} {val[0]} {val[1]}')

            case 'connwifi':
                val = [*val]

                if not val[0] and not val[1]:
                    try:
                        val[0] = input('Enter WiFi SSID: ').strip()
                        val[1] = getpass('Enter WiFi password: ').strip()
                    except: return

                if not type(val[0]) is str or not len(val[0]): raise TelloError('WiFi SSID value is incorrect. Please make sure it\'s a valid string and at least 1 character')
                elif not type(val[1]) is str or not len(val[1]): raise TelloError('WiFi password value is incorrect. Please make sure it\'s a valid string and at least 1 character')

                return sender(f'{msg} {val[0]} {val[1]}')

            case 'mpad':
                if not self._mp: raise TelloError('Mission pad detection hasn\'t been enabled yet. Please run the mission_pad() method first')
                elif not val is int or not 0 <= val <= 2: raise TelloError('Mission Pad Detection value is incorrect. Please make sure it\'s a valid integer and between 0 - 2')

                return sender(f'{msg} {val}')

    def _send(self, msg: str, typ: str, callback: Callable | None, val: int = None) -> 'Tello':
        '''
        Internal method for sending data asynchronously to the drone. You normally wouldn't use this yourself
        '''

        match typ:
            case 'basic':
                self._cqueue.put((msg, callback))

            case 'aval':
                self._cqueue.put((f'{msg} {val}', callback))

            case 'dist':
                if not type(val) is int or not 20 <= val: raise TelloError('Distance value is incorrect. Please make sure it\'s a valid integer and at least 20cm')

                def disrun(val):
                    while val > 500:
                        val -= 500
                        yield 500
                    else: yield val

                for dist in disrun(val): self._cqueue.put((f'{msg} {dist}', callback))

            case 'rot':
                if not type(val) is int or not 1 <= val <= 360: raise TelloError('Rotational value is incorrect. Please make sure it\'s a valid integer and between 1 - 360deg')

                self._cqueue.put((f'{msg} {val}', callback))

            case 'cord':
                msg = f'{msg} '

                for n in val:
                    isd = n is int

                    if val.index(n) == len(val)-1:
                        if not isd: raise TelloError('Speed value is incorrect. Please make sure it\'s a valid integer')
                        elif n[1] and not 10 <= n <= 60: raise TelloError('Speed value is incorrect. Please make sure it\'s between 10 - 60cm/s')
                        elif not n[1] and not 10 <= n <= 100: raise TelloError('Speed value is incorrect. Please make sure it\'s between 10 - 100cm/s')
                    elif not isd or not -500 <= n <= 500: raise TelloError('coordinate value is incorrect. Please make sure it\'s a valid integer and between -500 - 500cm')

                    msg += f'{n} '

                self._cqueue.put((msg.rstrip(), callback))

            case 'mid':
                msg = f'{msg} '

                for n in val:
                    ind = val.index(n)
                    leg = len(val)
                    isd = n is int

                    if ind == leg-2:
                        if not isd: raise TelloError('Speed value is incorrect. Please make sure it\'s a valid integer')
                        elif n[1] and not 10 <= n <= 60: raise TelloError('Speed value is incorrect. Please make sure it\'s between 10 - 60cm/s')
                        elif not n[1] and not 10 <= n <= 100: raise TelloError('Speed value is incorrect. Please make sure it\'s between 10 - 100cm/s')
                    elif ind == leg-1 and not type(n) is str or not match(r'^[m][1-8]$', val): raise TelloError('Mission Pad value is incorrect. Please make sure it\'s a valid string and is between m1 - m8')
                    elif not isd or not -500 <= n <= 500: raise TelloError('coordinate value is incorrect. Please make sure it\'s a valid integer and between -500 - 500cm')

                    msg += f'{n} '

                self._cqueue.put((msg.rstrip(), callback))

            case 'jump':
                msg = f'{msg} '

                for n in val:
                    ind = val.index(n)
                    leg = len(val)
                    isd = n is int

                    if ind == leg-4:
                        if not isd: raise TelloError('Speed value is incorrect. Please make sure it\'s a valid integer')
                        elif n[1] and not 10 <= n <= 60: raise TelloError('Speed value is incorrect. Please make sure it\'s between 10 - 60cm/s')
                        elif not n[1] and not 10 <= n <= 100: raise TelloError('Speed value is incorrect. Please make sure it\'s between 10 - 100cm/s')
                    elif ind == leg-3 and not 1 <= n <= 360: raise TelloError('Yaw value is incorrect. Please make sure it\'s a valid integer and between 1 - 360deg')
                    elif ind == leg-1 or ind == leg-2 and not type(n) is str or not match(r'^[m][1-8]$', val): raise TelloError('Mission Pad value is incorrect. Please make sure it\'s a valid string and is between m1 - m8')
                    elif not isd or not -500 <= n <= 500: raise TelloError('coordinate value is incorrect. Please make sure it\'s a valid integer and between -500 - 500cm')

                    msg += f'{n} '

                self._cqueue.put((msg.rstrip(), callback))

            case 'setspd':
                if not type(val) is int or not 10 <= val <= 60: raise TelloError('Speed value is incorrect. Please make sure it\'s a valid integer and between 10 - 60cm/s')

                self._spd = val

                self._cqueue.put((f'{msg} {val}', callback))

            case 'setrc':
                msg = f'{msg} '

                for n in val:
                    if not type(n) is int or not -100 <= val <= 100: raise TelloError('Joystick distance value is incorrect. Please make sure it\'s a valid integer and between -100 - 100')
                    msg += f'{n} '

                self._cqueue.put((msg.rstrip(), callback))

            case 'setwifi':
                val = [*val]

                if not val[0] and not val[1]:
                    try:
                        val[0] = input('Enter new WiFi SSID: ').strip()
                        val[1] = getpass('Enter new WiFi password: ').strip()
                    except: return
                if not type(val[0]) is str or not len(val[0]): raise TelloError('WiFi SSID value is incorrect. Please make sure it\'s a valid string and at least 1 character')
                elif not type(val[1]) is str or not len(val[1]) >= 5: raise TelloError('WiFi password value is incorrect. Please make sure it\'s a valid string and at least 5 characters')
                elif not match(r'(?=(?:[^a-z]*[a-z]){2})(?=(?:[^A-Z]*[A-Z]){2})(?=(?:[^0-9]*[0-9]){1})', val[1]): raise TelloError('WiFi password value is insecure. Please make sure it contains at least 2 lowercase and uppercase letters and 1 number')

                self._cqueue.put((f'{msg} {val[0]} {val[1]}', callback))

            case 'connwifi':
                val = [*val]

                if not val[0] and not val[1]:
                    try:
                        val[0] = input('Enter WiFi SSID: ').strip()
                        val[1] = getpass('Enter WiFi password: ').strip()
                    except: return

                if not type(val[0]) is str or not len(val[0]): raise TelloError('WiFi SSID value is incorrect. Please make sure it\'s a valid string and at least 1 character')
                elif not type(val[1]) is str or not len(val[1]): raise TelloError('WiFi password value is incorrect. Please make sure it\'s a valid string and at least 1 character')

                self._cqueue.put((f'{msg} {val[0]} {val[1]}', callback))

            case 'mpad':
                if not self._mp: raise TelloError('Mission pad detection hasn\'t been enabled yet. Please run the mission_pad() method first')
                elif not type(val) is int or not 0 <= val <= 2: raise TelloError('Mission Pad Detection value is incorrect. Please make sure it\'s a valid integer and between 0 - 2')

                self._cqueue.put((f'{msg} {val}', callback))

        return self

    def _state(self, *msgs: str) -> tuple[int | str]:
        '''
        Internal method for receiving a state value from the state dict. You normally wouldn't use this yourself
        '''

        ret = []

        for key, val in self._slist.items():
            if key in msgs: ret.append(val)
            else: raise TelloError('The status requested is only available when mission pads are enabled. Please run the mission_pad() method first to use this method')

        return tuple(ret) if len(ret) > 1 else ret[0]

    def _sender(self, msg: str, typ: str, callback: Callable | bool | None, *args) -> Union['Tello', str]:
        '''
        Internal method for deciding how to send data (sync or async). You normally wouldn't use this yourself
        '''

        if callback is False:
            if callable(self._sync): return self._send(msg, typ, self._sync, *args)
            elif self._sync: return self._send_sync(msg, typ, *args)
            else: return self._send(msg, typ, None, *args)
        elif callback is None:
            return self._send(msg, typ, None, *args)
        else:
            if not callable(callback): raise ValueError('Callback function is incorrect. Please make sure it\'s a callable')
            return self._send(msg, typ, callback, *args)

    def _checkstream(self) -> None:
        '''
        Internal method to check whether the drone is streaming video or not. You normally wouldn't use this yourself
        '''

        if which('ffmpeg') == None: raise TelloError(f'Can not stream video as ffmpeg is not installed')

        if not self._streaming: raise TelloError(f'Can only run this method once the drone video stream is enabled. Please run the stream() method first')

    def _checkfly(self) -> None:
        '''
        Internal method to check whether the drone has taken off or not. You normally wouldn't use this yourself
        '''

        if not self._flying: raise TelloError(f'Can only run this method once the drone is flying. Please run the takeoff() method first')

    def takeoff(self, **preferences) -> Union['Tello', str]:
        '''
        Makes the drone automatically takeoff to a height of 80cm

        ### Preferences
        - callback?: A function to be called once a response from the drone is received with said response as the first argument in string form.
        If a none value is provided, this method will be non-blocking but will have no callback.
        If false is provided, this method will be blocking and return the response (Defaults to false/blocking)
        '''

        if self._flying: raise TelloError('Already flying. Can\'t takeoff')
        self._flying = True
        return self._sender('takeoff', 'basic', preferences['callback'] if 'callback' in preferences else False)

    def land(self, **preferences) -> Union['Tello', str]:
        '''
        Makes the drone automatically land at it's current position

        ### Preferences
        - callback?: A function to be called once a response from the drone is received with said response as the first argument in string form.
        If a none value is provided, this method will be non-blocking but will have no callback.
        If false is provided, this method will be blocking and return the response (Defaults to false/blocking)
        '''

        self._checkfly()
        self._flying = False
        return self._sender('land', 'basic', preferences['callback'] if 'callback' in preferences else False)

    def emergency(self, **preferences) -> Union['Tello', str]:
        '''
        Stops all drone motors immediately in case of emergency

        ### Preferences
        - callback?: A function to be called once a response from the drone is received with said response as the first argument in string form.
        If a none value is provided, this method will be non-blocking but will have no callback.
        If false is provided, this method will be blocking and return the response (Defaults to false/blocking)
        '''

        self._flying = False
        return self._sender('emergency', 'basic', preferences['callback'] if 'callback' in preferences else False)

    def stop(self, **preferences) -> Union['Tello', str]:
        '''
        Makes the drone hover in the air at it's current position

        ### Preferences
        - callback?: A function to be called once a response from the drone is received with said response as the first argument in string form.
        If a none value is provided, this method will be non-blocking but will have no callback.
        If false is provided, this method will be blocking and return the response (Defaults to false/blocking)
        '''

        self._checkfly()
        return self._sender('stop', 'basic', preferences['callback'] if 'callback' in preferences else False)

    def up(self, distance: int = None, **preferences) -> Union['Tello', str]:
        '''
        Makes the drone move up the provided amount of centimeters. If distance isn't provided, the default amount of distance set will be used

        ### Parameters
        - distance?: Distance in centimeters you would like the drone to move (Defaults to none/default distance)

        ### Preferences
        - callback?: A function to be called once a response from the drone is received with said response as the first argument in string form.
        If a none value is provided, this method will be non-blocking but will have no callback.
        If false is provided, this method will be blocking and return the response (Defaults to false/blocking)
        '''

        self._checkfly()
        return self._sender('up', 'dist', preferences['callback'] if 'callback' in preferences else False, distance if distance else self._dd)

    def down(self, distance: int = None, **preferences) -> Union['Tello', str]:
        '''
        Makes the drone move down the provided amount of centimeters. If distance isn't provided, the default amount of distance set will be used

        ### Parameters
        - distance?: Distance in centimeters you would like the drone to move (Defaults to none/default distance)

        ### Preferences
        - callback?: A function to be called once a response from the drone is received with said response as the first argument in string form.
        If a none value is provided, this method will be non-blocking but will have no callback.
        If false is provided, this method will be blocking and return the response (Defaults to false/blocking)
        '''

        self._checkfly()
        return self._sender('down', 'dist', preferences['callback'] if 'callback' in preferences else False, distance if distance else self._dd)

    def left(self, distance: int = None, **preferences) -> Union['Tello', str]:
        '''
        Makes the drone move left the provided amount of centimeters. If distance isn't provided, the default amount of distance set will be used

        ### Parameters
        - distance?: Distance in centimeters you would like the drone to move (Defaults to none/default distance)

        ### Preferences
        - callback?: A function to be called once a response from the drone is received with said response as the first argument in string form.
        If a none value is provided, this method will be non-blocking but will have no callback.
        If false is provided, this method will be blocking and return the response (Defaults to false/blocking)
        '''

        self._checkfly()
        return self._sender('left', 'dist', preferences['callback'] if 'callback' in preferences else False, distance if distance else self._dd)

    def right(self, distance: int = None, **preferences) -> Union['Tello', str]:
        '''
        Makes the drone move right the provided amount of centimeters. If distance isn't provided, the default amount of distance set will be used

        ### Parameters
        - distance?: Distance in centimeters you would like the drone to move (Defaults to none/default distance)

        ### Preferences
        - callback?: A function to be called once a response from the drone is received with said response as the first argument in string form.
        If a none value is provided, this method will be non-blocking but will have no callback.
        If false is provided, this method will be blocking and return the response (Defaults to false/blocking)
        '''

        self._checkfly()
        return self._sender('right', 'dist', preferences['callback'] if 'callback' in preferences else False, distance if distance else self._dd)

    def forward(self, distance: int = None, **preferences) -> Union['Tello', str]:
        '''
        Makes the drone move forward the provided amount of centimeters. If distance isn't provided, the default amount of distance set will be used

        ### Parameters
        - distance?: Distance in centimeters you would like the drone to move (Defaults to none/default distance)

        ### Preferences
        - callback?: A function to be called once a response from the drone is received with said response as the first argument in string form.
        If a none value is provided, this method will be non-blocking but will have no callback.
        If false is provided, this method will be blocking and return the response (Defaults to false/blocking)
        '''

        self._checkfly()
        return self._sender('forward', 'dist', preferences['callback'] if 'callback' in preferences else False, distance if distance else self._dd)

    def backward(self, distance: int = None, **preferences) -> Union['Tello', str]:
        '''
        Makes the drone move backward the provided amount of centimeters. If distance isn't provided, the default amount of distance set will be used

        ### Parameters
        - distance?: Distance in centimeters you would like the drone to move (Defaults to none/default distance)

        ### Preferences
        - callback?: A function to be called once a response from the drone is received with said response as the first argument in string form.
        If a none value is provided, this method will be non-blocking but will have no callback.
        If false is provided, this method will be blocking and return the response (Defaults to false/blocking)
        '''

        self._checkfly()
        return self._sender('back', 'dist', preferences['callback'] if 'callback' in preferences else False, distance if distance else self._dd)

    def clockwise(self, degrees: int = None, **preferences) -> Union['Tello', str]:
        '''
        Makes the drone rotate clockwise the provided amount of degrees. If degrees isn't provided, the default amount of rotation set will be used

        ### Parameters
        - degrees?: Degrees you would like the drone to turn (Defaults to none/default rotation)

        ### Preferences
        - callback?: A function to be called once a response from the drone is received with said response as the first argument in string form.
        If a none value is provided, this method will be non-blocking but will have no callback.
        If false is provided, this method will be blocking and return the response (Defaults to false/blocking)
        '''

        self._checkfly()
        return self._sender('cw', 'rot', preferences['callback'] if 'callback' in preferences else False, degrees if degrees else self._dr)

    def counter_clockwise(self, degrees: int = None, **preferences) -> Union['Tello', str]:
        '''
        Makes the drone rotate counterclockwise the provided amount of degrees.  If degrees isn't provided, the default amount of rotation set will be used

        ### Preferences
        - degrees?: Degrees you would like the drone to turn (Defaults to none/default rotation)
        - callback?: A function to be called once a response from the drone is received with said response as the first argument in string form.
        If a none value is provided, this method will be non-blocking but will have no callback.
        If false is provided, this method will be blocking and return the response (Defaults to false/blocking)
        '''

        self._checkfly()
        return self._sender('ccw', 'rot', preferences['callback'] if 'callback' in preferences else False, degrees if degrees else self._dr)

    def flip_left(self, **preferences) -> Union['Tello', str]:
        '''
        Makes the drone flip towards the left

        ### Preferences
        - callback?: A function to be called once a response from the drone is received with said response as the first argument in string form.
        If a none value is provided, this method will be non-blocking but will have no callback.
        If false is provided, this method will be blocking and return the response (Defaults to false/blocking)
        '''

        self._checkfly()
        return self._sender('flip', 'aval', preferences['callback'] if 'callback' in preferences else False, 'l')

    def flip_right(self, **preferences) -> Union['Tello', str]:
        '''
        Makes the drone flip towards the right

        ### Preferences
        - callback?: A function to be called once a response from the drone is received with said response as the first argument in string form.
        If a none value is provided, this method will be non-blocking but will have no callback.
        If false is provided, this method will be blocking and return the response (Defaults to false/blocking)
        '''

        self._checkfly()
        return self._sender('flip', 'aval', preferences['callback'] if 'callback' in preferences else False, 'r')

    def flip_forward(self, **preferences) -> Union['Tello', str]:
        '''
        Makes the drone flip forwards

        ### Parameters
        - callback?: A function to be called once a response from the drone is received with said response as the first argument in string form.
        If a none value is provided, this method will be non-blocking but will have no callback.
        If false is provided, this method will be blocking and return the response (Defaults to false/blocking)
        '''

        self._checkfly()
        return self._sender('flip', 'aval', preferences, 'f')

    def flip_backward(self, **preferences) -> Union['Tello', str]:
        '''
        Makes the drone flip backwards

        ### Preferences
        - callback?: A function to be called once a response from the drone is received with said response as the first argument in string form.
        If a none value is provided, this method will be non-blocking but will have no callback.
        If false is provided, this method will be blocking and return the response (Defaults to false/blocking)
        '''

        self._checkfly()
        return self._sender('flip', 'aval', preferences['callback'] if 'callback' in preferences else False, 'b')

    def go(self, x: int, y: int, z: int, speed: int = None, **preferences) -> Union['Tello', str]:
        '''
        Makes the drone go to the provided coordinates based of it's current position (0, 0, 0). If speed isn't provided, the default amount of speed set will be used

        ### Parameters
        - x: The x coordinate you would like the drone to go to (-500 - 500)
        - y: The y coordinate you would like the drone to go to (-500 - 500)
        - z: The z coordinate you would like the drone to go to (-500 - 500)
        - speed?: The speed you would like the drone to fly (10 - 100cm/s)

        ### Preferences
        - callback?: A function to be called once a response from the drone is received with said response as the first argument in string form.
        If a none value is provided, this method will be non-blocking but will have no callback.
        If false is provided, this method will be blocking and return the response (Defaults to false/blocking)
        '''

        self._checkfly()
        return self._sender('go', 'cord', preferences['callback'] if 'callback' in preferences else False, (x, y, z, (speed if speed else self._spd, False)))

    def curve(self, x1: int, y1: int, z1: int, x2: int, y2: int, z2: int, speed: int = None, **preferences) -> Union['Tello', str]:
        '''
        Makes the drone fly in a curve according to the two provided coordinates based off it's current position (0, 0, 0). If speed isn't provided, the default amount of speed set will be used

        ### Parameters
        - x1: The x coordinate you would like the drone to curve from (-500 - 500)
        - y1: The y coordinate you would like the drone to curve from (-500 - 500)
        - z1: The z coordinate you would like the drone to curve from (-500 - 500)
        - x2: The x coordinate you would like the drone to curve to (-500 - 500)
        - y2: The y coordinate you would like the drone to curve to (-500 - 500)
        - z2: The z coordinate you would like the drone to curve to (-500 - 500)
        - speed?: The speed you would like the drone to fly inbetween 10 - 60cm/s (Defaults to none/default speed)

        ### Preferences
        - callback?: A function to be called once a response from the drone is received with said response as the first argument in string form.
        If a none value is provided, this method will be non-blocking but will have no callback.
        If false is provided, this method will be blocking and return the response (Defaults to false/blocking)
        '''

        self._checkfly()
        return self._sender('curve', 'cord', preferences['callback'] if 'callback' in preferences else False, (x1, y1, z1, x2, y2, z2, (speed if speed else self._spd, True)))

    def go_mid(self, x: int, y: int, z: int, mid: str, speed: int = None, **preferences) -> Union['Tello', str]:
        '''
        Makes the drone go to the provided coordinates based off the provided mission pad. If speed isn't provided, the default amount of speed set will be used

        ### Parameters
        - x: The x coordinate you would like the drone to go to (-500 - 500)
        - y: The y coordinate you would like the drone to go to (-500 - 500)
        - z: The z coordinate you would like the drone to go to (-500 - 500)
        - mid: The mission pad ID you would like to base the coordinates off (m1 - m8)
        - speed?: The speed you would like the drone to fly inbetween 10 - 100cm/s (Defaults to none/default speed)

        ### Preferences
        - callback?: A function to be called once a response from the drone is received with said response as the first argument in string form.
        If a none value is provided, this method will be non-blocking but will have no callback.
        If false is provided, this method will be blocking and return the response (Defaults to false/blocking)
        '''

        self._checkfly()
        return self._sender('go', 'cord', preferences['callback'] if 'callback' in preferences else False, (x, y, z, mid, (speed if speed else self._spd, False)))

    def curve_mid(self, x1: int, y1: int, z1: int, x2: int, y2: int, z2: int, mid: str, speed: int = None, **preferences) -> Union['Tello', str]:
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
        - speed?: The speed you would like the drone to fly inbetween 10 - 60cm/s (Defaults to none/default speed)

        ### Preferences
        - callback?: A function to be called once a response from the drone is received with said response as the first argument in string form.
        If a none value is provided, this method will be non-blocking but will have no callback.
        If false is provided, this method will be blocking and return the response (Defaults to false/blocking)
        '''

        self._checkfly()
        return self._sender('curve', 'cord', preferences['callback'] if 'callback' in preferences else False, (x1, y1, z1, x2, y2, z2, (speed if speed else self._spd, True), mid))

    def jump(self, x: int, y: int, z: int, mid1: str, mid2: str, yaw: int, speed: int = None, **preferences) -> Union['Tello', str]:
        '''
        Makes the drone go to the provided coordinates based off the first provided mission pad then rotate to the yaw value based off the z coordinate of the second mission pad. If speed isn't provided, the default amount of speed set will be used

        ### Parameters
        - x: The x coordinate you would like the drone to go to (-500 - 500)
        - y: The y coordinate you would like the drone to go to (-500 - 500)
        - z: The z coordinate you would like the drone to go to (-500 - 500)
        - mid1: The mission pad ID you would like to base the coordinates off (m1 - m8)
        - mid2: The mission pad ID you would like the drone to base the z coordinate off (m1 - m8)
        - yaw: The yaw you would like the drone to rotate to (1 - 360deg)
        - speed?: The speed you would like the drone to fly inbetween 10 - 100cm/s (Defaults to none/default speed)

        ### Preferences
        - callback?: A function to be called once a response from the drone is received with said response as the first argument in string form.
        If a none value is provided, this method will be non-blocking but will have no callback.
        If false is provided, this method will be blocking and return the response (Defaults to false/blocking)
        '''

        self._checkfly()
        return self._sender('jump', 'cord', preferences['callback'] if 'callback' in preferences else False, (x, y, z, (speed if speed else self._spd, False), yaw, mid1, mid2))

    def speed(self, speed: int, **preferences) -> Union['Tello', str]:
        '''
        Sets the speed (in cm/s) you would like the drone to go at by default

        ### Parameters
        - speed: The speed you would like the drone to move at (10 - 60cm/s)

        ### Preferences
        - callback?: A function to be called once a response from the drone is received with said response as the first argument in string form.
        If a none value is provided, this method will be non-blocking but will have no callback.
        If false is provided, this method will be blocking and return the response (Defaults to false/blocking)
        '''

        return self._sender('speed', 'setspd', preferences['callback'] if 'callback' in preferences else False, speed)

    def remote_controller(self, lr: int, fb: int, ud: int, y: int, **preferences) -> Union['Tello', str]:
        '''
        Moves the drone based off of simulating a remote controller. Each value provided is how far it will move from it's current position in that direction

        ### Parameters
        - lr: The left/right position (in cm)
        - fb: the forward/backward position (in cm)
        - ud: The up/down position (in cm)
        - y: The yaw (in deg)

        ### Preferences
        - callback?: A function to be called once a response from the drone is received with said response as the first argument in string form.
        If a none value is provided, this method will be non-blocking but will have no callback.
        If false is provided, this method will be blocking and return the response (Defaults to false/blocking)
        '''

        self._checkfly()
        return self._sender('rc', 'setrc', preferences['callback'] if 'callback' in preferences else False, (lr, fb, ud, y))

    def set_wifi(self, ssid: str = None, pwd: str = None, **preferences) -> Union['Tello', str]:
        '''
        Sets the drones wifi SSID and password. Has a basic security check requiring 2 lowercase and 2 uppercase letters with 1 number.
        If no values are provided a terminal prompt will be used to collect them instead

        ### Parameters
        - ssid?: The WiFi SSID you would like the drone to broadcast
        - pwd?: The password you would like the drone WiFi to be secure with

        ### Preferences
        - callback?: A function to be called once a response from the drone is received with said response as the first argument in string form.
        If a none value is provided, this method will be non-blocking but will have no callback.
        If false is provided, this method will be blocking and return the response (Defaults to false/blocking)
        '''

        return self._sender('wifi', 'setwifi', preferences['callback'] if 'callback' in preferences else False, (ssid, pwd))

    def mission_pad(self, on: bool = True, **preferences) -> Union['Tello', str]:
        '''
        Enables/Disables the use of the drones mission pad detection. When enabled forward and downward mission pad detection is automatically enabled

        ### Parameters
        - on?: The state to set the mission pad preference to (Defaults to true/enabled)

        ### Preferences
        - callback?: A function to be called once a response from the drone is received with said response as the first argument in string form.
        If a none value is provided, this method will be non-blocking but will have no callback.
        If false is provided, this method will be blocking and return the response (Defaults to false/blocking)
        '''

        callback = preferences['callback'] if 'callback' in preferences else False

        if on:
            self._mp = True
            return self._sender('mon', 'basic', callback)
        else:
            self._mp =  False
            return self._sender('moff', 'basic', callback)

    def mission_pad_direction(self, dir: int, **preferences) -> Union['Tello', str]:
        '''
        Sets the drones mission pad detection. Requires mission pad detection to be enabled

        ### Parameters
        - dir: The direction(s) you would like the drone to detect a mission pad with (0 = Downward only, 1 = Forward only, 2 = Downward and Forward)

        ### Preferences
        - callback?: A function to be called once a response from the drone is received with said response as the first argument in string form.
        If a none value is provided, this method will be non-blocking but will have no callback.
        If false is provided, this method will be blocking and return the response (Defaults to false/blocking)
        '''

        return self._sender('mdirection', 'mpad', preferences['callback'] if 'callback' in preferences else False, dir)

    def connect_wifi(self, ssid: str = None, pwd: str = None, **preferences) -> Union['Tello', str]:
        '''
        Turns the drone into station mode and connects to a new access point with the provided SSID and password.
        If no values are provided a terminal prompt will be used to collect them instead

        ### Parameters
        - ssid?: The access point SSID you would like the drone to connect to
        - pwd?: The password for the access point you would like the drone to connect to

        ### Preferences
        - callback?: A function to be called once a response from the drone is received with said response as the first argument in string form.
        If a none value is provided, this method will be non-blocking but will have no callback.
        If false is provided, this method will be blocking and return the response (Defaults to false/blocking)
        '''

        return self._sender('ac', 'connwifi', preferences['callback'] if 'callback' in preferences else False, (ssid, pwd))

    def get_speed(self, **preferences) -> Union['Tello', str]:
        '''
        Returns the current speed of the drone (in cm/s)

        ### Preferences
        - callback?: A function to be called once a response from the drone is received with said response as the first argument in string form.
        If a none value is provided, this method will be non-blocking but will have no callback.
        If false is provided, this method will be blocking and return the response (Defaults to false/blocking)
        '''

        return self._sender('speed?', 'basic', preferences['callback'] if 'callback' in preferences else False)

    def get_battery(self, **preferences) -> Union['Tello', str]:
        '''
        Returns the current battery percentage of the drone. If run with a callback function provided, this method will be non blocking and will provide the result in a future to the callback function

        ### Preferences
        - callback?: A function to be called once a response from the drone is received with said response as the first argument in string form.
        If a none value is provided, this method will be non-blocking but will have no callback.
        If false is provided, this method will be blocking and return the response (Defaults to false/blocking)
        '''

        return self._sender('battery?', 'basic', preferences['callback'] if 'callback' in preferences else False)

    def get_time(self, **preferences) -> Union['Tello', str]:
        '''
        Returns the current flight time of the drone. If run with a callback function provided, this method will be non blocking and will provide the result in a future to the callback function

        ### Preferences
        - callback?: A function to be called once a response from the drone is received with said response as the first argument in string form.
        If a none value is provided, this method will be non-blocking but will have no callback.
        If false is provided, this method will be blocking and return the response (Defaults to false/blocking)
        '''

        return self._sender('time?', 'basic', preferences['callback'] if 'callback' in preferences else False)

    def get_signal_noise(self, **preferences) -> Union['Tello', str]:
        '''
        Returns the drones current WiFi SNR (signal:noise ratio). If run with a callback function provided, this method will be non blocking and will provide the result in a future to the callback function

        ### Preferences
        - callback?: A function to be called once a response from the drone is received with said response as the first argument in string form.
        If a none value is provided, this method will be non-blocking but will have no callback.
        If false is provided, this method will be blocking and return the response (Defaults to false/blocking)
        '''

        return self._sender('wifi?', 'basic', preferences['callback'] if 'callback' in preferences else False)

    def get_sdk(self, **preferences) -> Union['Tello', str]:
        '''
        Returns the current Tello SDK version of the drone. If run with a callback function provided, this method will be non blocking and will provide the result in a future to the callback function

        ### Preferences
        - callback?: A function to be called once a response from the drone is received with said response as the first argument in string form.
        If a none value is provided, this method will be non-blocking but will have no callback.
        If false is provided, this method will be blocking and return the response (Defaults to false/blocking)
        '''

        return self._sender('sdk?', 'basic', preferences['callback'] if 'callback' in preferences else False)

    def get_serial(self, **preferences) -> Union['Tello', str]:
        '''
        Returns the serial number of the drone. If run with a callback function provided, this method will be non blocking and will provide the result in a future to the callback function

        ### Preferences
        - callback?: A function to be called once a response from the drone is received with said response as the first argument in string form.
        If a none value is provided, this method will be non-blocking but will have no callback.
        If false is provided, this method will be blocking and return the response (Defaults to false/blocking)
        '''

        return self._sender('sn?', 'basic', preferences['callback'] if 'callback' in preferences else False)

    def stream(self, on: bool = True, **preferences) -> Union['Tello', str]:
        '''
        Enables/Disables the drones video stream

        ### Parameters
        - on?: The state to set the video stream to (Defaults to true/enabled)

        ### Preferences
        - callback?: A function to be called once a response from the drone is received with said response as the first argument in string form.
        If a none value is provided, this method will be non-blocking but will have no callback.
        If false is provided, this method will be blocking and return the response (Defaults to false/blocking)
        '''

        callback = preferences['callback'] if 'callback' in preferences else False

        if on:
            return self._sender('streamon', 'basic', callback)
        else:
            return self._sender('streamoff', 'basic', callback)

    def get_mission_pad(self) -> str | None:
        '''
        Returns the current mission pad ID of the one detected or None if not detected
        '''

        res = self._state('mid')
        return res if not res == -1 else None
    
    def get_mpxyz(self) -> tuple[int] | None:
        '''
        Returns the current x, y, and z coordinates of the current detected mission pad or None if not detected
        '''

        res = self._state('x', 'y', 'z')
        return res if not 0 in res else None

    def get_mpx(self) -> str | None:
        '''
        Returns the current x coordinate of the current detected mission pad or None if not detected
        '''

        res = self._state('x')
        return res if not 0 in res else None

    def get_mpy(self) -> str | None:
        '''
        Returns the current y coordinate of the current detected mission pad or None if not detected
        '''

        res = self._state('y')
        return res if not 0 in res else None

    def get_mpz(self) -> str | None:
        '''
        Returns the current z coordinate of the current detected mission pad or None if not detected
        '''

        res = self._state('z')
        return res if not 0 in res else None

    def get_pry(self) -> tuple[int]:
        '''
        Returns the current pitch, roll, and yaw of the drone (in degrees)
        '''

        return self._state('pitch', 'roll', 'yaw')

    def get_pitch(self) -> int:
        '''
        Returns the current pitch of the drone (in degrees)
        '''

        return self._state('pitch')

    def get_roll(self) -> int:
        '''
        Returns the current roll of the drone (in degrees)
        '''

        return self._state('roll')

    def get_yaw(self) -> int:
        '''
        Returns the current yaw of the drone (in degrees)
        '''

        return self._state('yaw')

    def get_xyzspd(self) -> tuple[int]:
        '''
        Returns the current speed on the x, y, and z axis of the drone (in cm/s)
        '''

        return self._state('vgx', 'vgy', 'vgz')

    def get_xspd(self) -> int:
        '''
        Returns the current speed on the x axis of the drone (in cm/s)
        '''

        return self._state('vgx')

    def get_yspd(self) -> int:
        '''
        Returns the current speed on the y axis of the drone (in cm/s)
        '''

        return self._state('vgy')

    def get_zspd(self) -> int:
        '''
        Returns the current speed on the z axis of the drone (in cm/s)
        '''

        return self._state('vgz')

    def get_temps(self) -> tuple[int]:
        '''
        Returns the highest and lowest temperature the drone has experienced (in celsius)
        '''

        return self._state('templ', 'temph')

    def lowest_temp(self) -> int:
        '''
        Returns the lowest temprature the drone has experienced (in celsius)
        '''

        return self._state('templ')

    def highest_temp(self) -> int:
        '''
        Returns the highest temprature the drone has experienced (in celsius)
        '''

        return self._state('temph')

    def flight_length(self) -> int:
        '''
        Returns the distance the drone has flown in total (in cm)
        '''

        return self._state('tof')

    def get_height(self) -> int:
        '''
        Returns the current height of the drone (in cm)
        '''

        return self._state('h')

    def get_pressure(self) -> int:
        '''
        Returns the current air pressure of the drone (in cm)
        '''

        return self._state('baro')

    def get_time(self) -> int:
        '''
        Returns the total amount of time the drone motors have been used for
        '''

        return self._state('time')

    def get_axyz(self) -> tuple[int]:
        '''
        Returns the current acceleration on the x, y, and z axis of the drone (in cm/s)
        '''

        return self._state('agx', 'agy', 'agz')

    def get_ax(self) -> int:
        '''
        Returns the current acceleration on the x axis of the drone (in cm/s)
        '''

        return self._state('agx')

    def get_ay(self) -> int:
        '''
        Returns the current acceleration on the y axis of the drone (in cm/s)
        '''

        return self._state('agy')

    def get_az(self) -> int:
        '''
        Returns the current acceleration on the z axis of the drone (in cm/s)
        '''

        return self._state('agz')

    def photo(self, **preferences) -> Union['Tello', str]:
        '''
        Takes a photo using the provided/default preferences.
        If no path is provided, it automatically creates a photos folder in the current directory with the photo having the current timestamp as the name and in png format @ 1280 x 720 (720p) resolution

        ## Preferences
        - path?: A string path that can also include provided file name and format. For pure directories, it must have a trailing forward slash (Defaults to ./photos/TIMESTAMP.png)
        - resolution?: A tuple of the resolution you would like the photo to be in. Goes up to 960 x 720 (Defaults to HD/720p)
        - callback?: A function to be called once the image proccesing for the photo is complete with the absolute path of said photo as the first argument.
        If a none value is provided, this method will be non-blocking but will have no callback.
        If false is provided, this method will be blocking and return the response (Defaults to false/blocking)
        - window?: Enable/Disable a preview window after the photo is taken (Defaults to false/disabled)
        '''

        self._checkstream()

        path = preferences['path'] if 'path' in preferences else './photos/'
        resolution = preferences['resolution'] if 'resolution' in preferences else (960, 720)
        callback = preferences['callback'] if 'callback' in preferences else False
        window = preferences['window'] if 'window' in preferences else False

        if not type(window) is bool: raise TelloError('Window preference provided was invalid. Please make sure it\'s a valid boolean type')
        elif not type(path) is str or not len(path) or not match(r'([:](?=[\/]+))|(^[\.](?=[\/]+))|(^[\~](?=[\/]+))|(^[\/](?=\w+))', path): raise TelloError('Provided path was invalid. Please make sure it\'s a valid string and in proper path format')
        elif not type(resolution) == None and (not type(resolution) is tuple or not len(resolution) == 2): raise TelloError('Provided resolution was invalid. Please make sure it\'s a valid tuple with 2 integers providing the width and height of the resolution')
        elif not callback == False and not callable(callback): raise TelloError('Callback function is incorrect. Please make sure it\'s a callable')

        for res in resolution:
            if not type(res) is int: raise TelloError('Provided resolution was invalid. Please make sure it\'s a valid tuple with 2 integers providing the width and height of the resolution')

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

    def photo_bytes(self, **preferences) -> Union['Tello', bytes]:
        '''
        Returns the bytes of the photo taken in the provided/default resolution

        ### Preferences
        - resolution?: A tuple of the resolution you would like the photo to be in. Goes up to 1280 x 720 (Defaults to HD/720p)
        - callback?: A function to be called once the image proccesing for the photo is complete with the bytes of said photo as the first argument.
        If false is provided, this method will be blocking and return the response (Defaults to false/blocking)
        '''

        self._checkstream()

        resolution = preferences['resolution'] if 'resolution' in preferences else (960, 720)
        callback = preferences['callback'] if 'callback' in preferences else False

        if not type(resolution) is tuple or not len(resolution) == 2: raise TelloError('Provided resolution was invalid. Please make sure it\'s a valid tuple with 2 integers providing the width and height of the resolution')
        elif callback and not callable(callback): raise TelloError('Callback function is incorrect. Please make sure it\'s a callable')

        for res in resolution:
            if not type(res) is int: raise TelloError('Provided resolution was invalid. Please make sure it\'s a valid tuple with 2 integers providing the width and height of the resolution')

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

    def start_video(self, **preferences) -> None:
        '''
        Takes a video using the provided/default parameters. If no path is provided, it automatically creates a videos folder in the current directory with the video having the current timestamp as the name and in mp4 format @ 1280 x 720 (720p) resolution
        and in 60fps. Will not stop recording until the stop_video() method is run

        ### Preferences
        - path?: A string path that can also include provided file name and format. For pure directories, it must have a trailing forward slash (Defaults to ./videos/TIMESTAMP.mp4)
        - resolution?: A tuple of the resolution you would like the video to be in. Goes up to 1280 x 720 (Defaults to HD/720p)
        - framerate?: An integer of the framerate you would like the video to be in. Goes up to 60fps (Defaults to 60fps)
        - window?: Enable/Disable a live preview window while the video is being taken. If enabled a web folder will be created for the livestream and will be deleted at the end (Defaults to false/disabled)
        - callback?: A function to be called once the stop_video() method is called with the absolute path to said video as the first argument (Defaults to none)
        '''

        self._checkstream()

        path = preferences['path'] if 'path' in preferences else './videos/'
        resolution = preferences['resolution'] if 'resolution' in preferences else (960, 720)
        framerate = preferences['framerate'] if 'framerate' in preferences else 60
        callback = preferences['callback'] if 'callback' in preferences else None
        window = preferences['window'] if 'window' in preferences else False
        rb = resolution[0] * resolution[1] * 3

        if not type(path) is str or not len(path) or not match(r'([:](?=[\/]+))|(^[\.](?=[\/]+))|(^[\~](?=[\/]+))|(^[\/](?=\w+))', path): raise TelloError('Provided path was invalid. Please make sure it\'s a valid string and in proper path format')
        elif not type(resolution) is tuple or not len(resolution) == 2: raise TelloError('Provided resolution was invalid. Please make sure it\'s a valid tuple with 2 integers providing the width and height of the resolution')
        elif not type(framerate) is int or not 10 <= framerate <= 60: raise TelloError('Provided framerate was invalid. Please make sure it\'s a valid integer and inbetween 10 - 60')
        elif not type(window) is bool: raise TelloError('Window value provided was invalid. Please make sure it\'s a valid boolean type')
        elif not callback == None and not callable(callback): raise TelloError('Callback function is incorrect. Please make sure it\'s a callable')

        for res in resolution:
            if not type(res) is int: raise TelloError('Provided resolution was invalid. Please make sure it\'s a valid tuple with 2 integers providing the width and height of the resolution')

        if window and self._web: raise TelloError('Webserver on live method already created. Please run the stop_live() method first')

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
            '-vf', f'scale={resolution[0]}x{resolution[1]}',
            '-pix_fmt', 'rgb24',
            '-'
        ], stdout = PIPE, bufsize = 10**8)

        sleep(self._to)
        if proc.poll(): raise TelloError(f'Video server timed out. Did not receive stream from drone within {self._to} second(s)')

        rec = Popen([
            'ffmpeg',
            '-loglevel', 'quiet',
            '-y',
            '-pix_fmt', 'rgb24',
            '-s', '960x720',
            '-f', 'rawvideo',
            '-r', str(framerate),
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
                '-s', '960x720',
                '-f', 'rawvideo',
                '-r', str(framerate),
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

    def video_bytes(self, **preferences) -> Union['Tello', list[bytes]]:
        '''
        Returns a list of each video frame with the bytes of said frame being taken in the provided/default resolution. Will not stop appending frames until the provided max frames is met or the stop_frames() method is run

        ### Preferences
        - resolution?: A tuple of the resolution you would like the video to be in. Goes up to 1280 x 720 (Defaults to HD/720p)
        - frames?: The max amount of frames you would like to be generated (Defaults to 0/unlimited)
        - callback?: A function to be called once the max amount of frames is reached or the stop_frames method is run with the bytes of said video frames as the first argument.
        If false is provided, this method will be blocking and return the response (Defaults to false/blocking)
        '''

        self._checkstream()

        frames = preferences['frames'] if 'frames' in preferences else 0
        resolution = preferences['resolution'] if 'resolution' in preferences else (960, 720)
        callback = preferences['callback'] if 'callback' in preferences else False
        rb = resolution[0] * resolution[1] * 3

        if not type(resolution) is tuple or not len(resolution) == 2: raise TelloError('Provided resolution was invalid. Please make sure it\'s a valid tuple with 2 integers providing the width and height of the resolution')
        elif not type(frames) is int: raise TelloError('Provided frame count was invalid. Please make sure it\'s a valid integer')
        elif callback and not callable(callback): raise TelloError('Callback function is incorrect. Please make sure it\'s a callable')

        for res in resolution:
            if not type(res) is int: raise TelloError('Provided resolution was invalid. Please make sure it\'s a valid tuple with 2 integers providing the width and height of the resolution')

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
                    '-vf', f'scale={resolution[0]}x{resolution[1]}',
                    '-pix_fmt', 'rgb24',
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
                '-vf', f'scale={resolution[0]}x{resolution[1]}',
                '-pix_fmt', 'rgb24',
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

    def live(self, **preferences) -> None:
        '''
        Displays a live feed of the drone video inside a browser window in the provided/default resolution and framerate. Will not shut down the webserver until the stop_live() method is run

        ### Parameters
        - resolution?: A tuple of the resolution you would like the video to be in. Goes up to 1280 x 720 (Defaults to HD/720p)
        - framerate?: An integer of the framerate you would like the video to be in. Goes up to 60fps (Defaults to 60fps)
        '''

        self._checkstream()

        resolution = preferences['resolution'] if 'resolution' in preferences else (960, 720)
        framerate = preferences['framerate'] if 'framerate' in preferences else 60
        rb = resolution[0] * resolution[1] * 3

        if not type(resolution) is tuple or not len(resolution) == 2: raise TelloError('Provided resolution was invalid. Please make sure it\'s a valid tuple with 2 integers providing the width and height of the resolution')
        elif not type(framerate) is int or not 10 <= framerate <= 60: raise TelloError('Provided framerate was invalid. Please make sure it\'s a valid integer and inbetween 10 - 60')

        if self._web: raise TelloError('Webserver on video method already created. Please run the stop_video() method first')

        self._live = True

        proc = Popen([
            'ffmpeg',
            '-loglevel', 'quiet',
            '-y',
            '-f', 'h264',
            '-i', 'udp://{}:{}{}'.format(self._ips[1], self._ports[2], '?timeout={}'.format((self._to/3.2) * 1000000) if self._to else ''),
            '-f', 'rawvideo',
            '-vf', f'scale={resolution[0]}x{resolution[1]}',
            '-pix_fmt', 'rgb24',
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
            '-s', '960x720',
            '-f', 'rawvideo',
            '-r', str(framerate),
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
        Ends the start_video() method from recording data. The resulting video will be saved to disk and if the window preference was enabled the webserver will be shutdown
        '''

        self._rec = False

    def stop_frames(self) -> None:
        '''
        Ends the video_frames() method from generating frames
        '''

        self._frames = False

    def stop_live(self) -> None:
        '''
        Shuts down the live() method webserver
        '''

        self._live = False

    def exit(self, wait: bool = True) -> None:
        '''
        Exits the class and closes all threads. If the drone is still flying, it will be landed if the safety preference is enabled

        ### Parameters
        - wait?: Enable/Disable waiting for the asynchronous queue to finish and immediatly stops actions (Defaults to enabled/true)
        '''

        if wait: self._cqueue.join()

        if self._sm and self._flying: self._send_sync('land', 'basic')
        self._running = False
