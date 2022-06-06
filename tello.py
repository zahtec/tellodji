from socket import AF_INET6, socket, SOCK_DGRAM, AF_INET
from .tello_error import TelloError
from .tello_video import TelloVideo
from typing import Callable, Union
from ipaddress import ip_address
from threading import Thread
from getpass import getpass
import re

class Tello:
    '''
    The main class for the Tello library. Used to construct a socket that will send & receive data from any
    Tello Ryze drone. If an IP address or any ports were provided they will be used in the construction of the sockets.
    Made for the v2.0 of the Tello Ryze SDK, most features will work with v1.3 as well.

    ### Parameters
    - ips?: The IP addresses you would like the Tello sockets to bind & connect to. There must be at least 1 IP address with others inputted as None. 
    First one is for the command and state servers, second one is for the optional video server (ipv4/ipv6, Defaults to 192.168.10.1, 0.0.0.0)
    - ports?: The ports you would like the Tello sockets to bind & connect to. There must be at least 2 ports with others inputted as None.
    First one is for the command server, second one is for the state server, third one is for the optional video server (Defaults to 8889, 8890, 11111)

    ### Preferences
    - default_distance?: The default distance you would like the drone to move if none is provided during a movement function (Defaults to 50cm)
    - default_rotation?: The default degrees you would like the drone to rotate if none is provided during a movement function (Defaults to 90deg, must be between 1 - 360deg)
    - default_speed?: The default speed you would like the drone to move at (Defaults to 30cm/s, must be between 10 - 60cm/s)
    - timeout?: The amount of time you would like to wait for a response from a drone before a timeout error is raised. If 0 is provided it will have no timeout (Defaults to 7s)
    - safety?: Land the drone if an error is raised (Defaults to true/enabled)
    - sync?: Makes the library as synchronous by default. Meaning if no callback value is provided to certain methods, it will default to none instead of false (Defaults to true/enabled)
    - mission_pad?: Enable/Disable the detection of mission pads (Defaults to false/disabled)
    - debug?: Enable/Disable the debug mode for verbose console messages based on what's happening (Defaults to false/disabled)
    - video?: Enable/Disable the creation of an embedded TelloVideo class (accessible by Tello.video) for streaming video from the drone (Defaults to false/disabled)

    ### Constants
    - M1-8: Mission pad values used for methods that require a mission pad as a parameter
    '''

    M1 = 'm1'
    M2 = 'm2'
    M3 = 'm3'
    M4 = 'm4'
    M5 = 'm5'
    M6 = 'm6'
    M7 = 'm7'
    M8 = 'm8'

    def __init__(self, ips: tuple[int | None] = ('192.168.10.1', '0.0.0.0'), ports: tuple[int | None] = (8889, 8890, 11111), **opt) -> None:
        if not type(ips) is tuple or not len(ips) == 2: raise ValueError('[TELLO] IP addresses provided were invalid. Please make sure it\'s a valid tuple with at least 1 address with others inputted as None')
        elif not type(ports) is tuple or not len(ports) == 3: raise ValueError('[TELLO] Ports provided were invalid. Please make sure it\'s a valid tuple with at least 1 port with others inputted as None')
        elif 'default_distance' in opt and (not type(opt['default_distance']) is int or not 20 <= opt['default_distance']): raise ValueError('[TELLO] Default distance value provided was invalid. Please make sure it\'s a valid integer and at at least 20cm')
        elif 'default_rotation' in opt and (not type(opt['default_rotation']) is int or not 1 <= opt['default_rotation'] <= 360): raise ValueError('[TELLO] Default rotation value provided was invalid. Please make sure it\'s a valid integer and in between 1-360deg')
        elif 'default_speed' in opt and (not type(opt['default_speed']) is int or not 10 <= opt['default_speed'] <= 60): raise ValueError('[TELLO] Default speed value provided was invalid. Please make sure it\'s a valid integer and between 10-60cm/s')
        elif 'timeout' in opt and (not type(opt['timeout']) is int or not 0 <= opt['timeout']): raise ValueError('[TELLO] Timeout value provided was invalid. Please make sure it\'s a valid integer and at least 0')
        elif 'mission_pad' in opt and not type(opt['mission_pad']) is bool: raise ValueError('[TELLO] Mission pad preference provided was invalid. Please make sure it\'s a valid boolean type')
        elif 'safety' in opt and not type(opt['safety']) is bool: raise ValueError('[TELLO] Safety preference provided was invalid. Please make sure it\'s a valid boolean type')
        elif 'sync' in opt and not type(opt['sync']) is bool: raise ValueError('[TELLO] Sync preference provided was invalid. Please make sure it\'s a valid boolean type')
        elif 'debug' in opt and not type(opt['debug']) is bool: raise ValueError('[TELLO] Debug preference provided was invalid. Please make sure it\'s a valid boolean type')
        elif 'video' in opt and not type(opt['video']) is bool: raise ValueError('[TELLO] Video preference provided was invalid. Please make sure it\'s a valid boolean type')

        for ip in ips:
            if ip: ip_address(ip)

        for port in ports:
            if port and not type(port) is int: raise ValueError('[TELLO] One or more ports provided were invalid. Please make sure they are integers and in proper port form')

        self._ip = ips[0]
        self._ports = (ports[0], ports[1] if ports[1] else 8890)
        self._to = (opt['timeout'] if opt['timeout'] > 0 else None) if 'timeout' in opt else 7
        self._running = True
        self._flying = False
        self._cqueue, self._slist = [], {}

        self._dd = opt['default_distance'] if 'default_distance' in opt else 50
        self._dr = opt['default_rotation'] if 'default_rotation' in opt else 90
        self._spd = opt['default_speed'] if 'default_speed' in opt else 30
        self._sm = opt['safety'] if 'safety' in opt else True
        self._sync = opt['sync'] if 'sync' in opt else True
        self._mp = opt['mission_pad'] if 'mission_pad' in opt else False
        self._debug = opt['debug'] if 'debug' in opt else False
        if 'video' in opt: self.video = TelloVideo(ips[1] if ips[1] else '192.168.10.1', ports[2] if ports[2] else 11111, debug = self._debug, timeout = self._to)

        if self._debug: print('[TELLO] Debug mode enabled')

        try:
            if '.' in ips[0]:
                self._cserver, self._sserver = socket(AF_INET, SOCK_DGRAM), socket(AF_INET, SOCK_DGRAM)
                self._cserver.settimeout(self._to)
                self._sserver.settimeout(self._to)

                if self._debug: print(f'[TELLO] Set command socket to -> {ips[0]}:{ports[0]}\n[TELLO] Set state socket to -> {ips[0]}:{ports[1]}\n[TELLO] Timeout set to -> {self._to}')
            else:
                self._cserver, self._sserver = socket(AF_INET6, SOCK_DGRAM), socket(AF_INET6, SOCK_DGRAM)
                self._cserver.settimeout(self._to)
                self._sserver.settimeout(self._to)

                if self._debug: print(f'[TELLO] Set command socket to -> {ips[0]}:{ports[0]}\n[TELLO] Set state socket to -> {ips[0]}:{ports[1]}\n[TELLO] Timeout set to -> {self._to}')
        except OSError: raise TelloError('Unable to bind to provided IP/ports. Please make sure you are connected to your Tello drone')

        Thread(target=self._cthread).start()
        Thread(target=self._rthread).start()

        if self._debug: print('[TELLO] Created and started threads')

        self._sender('Command', 'basic', False)
        self._sender('speed', 'aval', False, self._spd)
        if self._mp: self._sender('mon', 'basic', False)
        if self._debug: print(f'[TELLO] Default movement distance is set to -> {self._dd}cm\n[TELLO] Default movement speed is set to -> {self._spd}cm/s')

    @property
    def ip(self) -> str:
        '''
        Returns the current IP address the Tello socket's are sending to/receiving from
        '''

        return self._ip

    @ip.setter
    def ip(self, ip: str) -> None:
        '''
        Changes the Tello socket's IP address to the one provided. Does not change the ip of the embedded video class if enabled or of any method ran beforehand

        ### Parameters
        - ip: The IP that that you want the sockets to switch to (ipv4/ipv6)
        '''

        if not type(ip) is str: raise ValueError('[TELLO] IP address provided was invalid. Please make sure it\'s a valid string and in proper ipv4/6 form')

        ip = ip.strip()

        if ip == self._ip: raise ValueError('[TELLO] IP provided is the same as the currently set one')

        ip_address(ip)

        self._ip = ip

        if self._debug: print(f'[TELLO] Set command socket to -> {ip}:{self._ports[0]}\n[TELLO] Set state socket to -> {ip}:{self._ports[1]}')

    @property
    def ports(self) -> tuple[int]:
        '''
        Returns the current ports the Tello socket's are sending to/receiving from
        '''

        return self._ports

    @ports.setter
    def ports(self, ports: tuple[int]) -> None:
        '''
        Changes the Tello socket's ports to the ones provided. Does not change the ports of the embedded video class if enabled or of any method ran beforehand

        ### Parameters
        - ports: The ports that that you want the sockets to switch to
        '''

        if not type(ports) is tuple or not len(ports) == 2: raise ValueError('[TELLO] Ports provided were invalid. Please make sure it\'s a valid tuple and there\'s exactly 2 ports')

        for port in ports:
            if not type(port) is int: raise ValueError('[TELLO] One or more ports provided were invalid. Please make sure they\'re valid integers and in proper port form')

        if ports == self._ports: raise ValueError('[TELLO] Ports provided are the same as the currently set ones')

        self._ports = ports

        if self._debug: print(f'[TELLO] Set command socket to -> {self._ip}:{ports[0]}\n[TELLO] Set state socket to -> {self._ip}:{ports[1]}')

    @property
    def timeout(self) -> int:
        '''
        Returns the current amount of time the Tello socket's wait before raising an error
        '''

        return self._to

    @timeout.setter
    def timeout(self, timeout: int) -> None:
        '''
        Changes the Tello socket's timeout to the one provided. Does not change the timeout of any method ran beforehand

        ### Parameters
        - timeout: The amount of time you would like the socket's to wait for a response from a drone before a timeout error is raised (Must be at least 1 second)
        '''

        if not type(timeout) is int or timeout < 1: raise ValueError('[TELLO] Timeout provided was invalid. Please make sure it\'s a integer and at least 1 second')

        if timeout == self._to: raise ValueError('[TELLO] Timeout provided was the same as the currently set one')

        self._to = timeout

        if self._debug: print(f'[TELLO] Set timeout to -> {timeout}')

    @property
    def default_distance(self) -> int:
        '''
        Returns the current set default distance you want the drone to go
        '''

        return self._dd

    @default_distance.setter
    def default_distance(self, distance: int) -> None:
        '''
        Changes the default distance the drone will move if none is provided during a movement function

        ### Parameters
        - distance: The distance you want the drone to move (20+ cm)
        '''

        if not type(distance) is int or not 20 <= distance: raise ValueError('[TELLO] Distance value provided was invalid. Please make sure it is a valid integer and at least 20cm')

        if distance == self._dd: raise ValueError('[TELLO] Default distance value provided is the same as the currently set value')

        self._dd = distance

        if self._debug: print(f'[TELLO] Set default distance to -> {distance}cm')

    @property
    def default_speed(self) -> int:
        '''
        Returns the current set default speed you want the drone to go
        '''

        return self._spd

    @default_speed.setter
    def default_speed(self, speed: int) -> None:
        '''
        Changes the default speed the drone will move if none is provided during a movement function that requires one or
        when doing a movement function that doesn't have a speed input. This setter is blocking

        ### Parameters
        - speed: The speed you want the drone to move at (10 - 60cm/s)
        '''

        if not speed is int or not 10 <= speed <= 100: raise ValueError('[TELLO] Speed value provided was invalid. Please make sure it is a valid integer and at least 10')

        if speed == self._spd: raise ValueError('[TELLO] Default speed value provided is the same as the currently set value')

        self._sender('speed', 'setspd', False, speed)
        if self._debug: print(f'[TELLO] Set default speed on drone to -> {speed}cm/s')

        self._spd = speed

        if self._debug: print(f'[TELLO] Set default speed in class to -> {speed}cm/s')

    @property
    def mission_pad(self) -> bool:
        '''
        Returns the state the mission pad preference is set to
        '''

        return self._mp

    @mission_pad.setter
    def mission_pad(self, preference: bool) -> None:
        '''
        Enables/Disables the use of the drones mission pad detection. When enabled forward and downward mission pad detection is enabled. This setter is blocking

        ### Parameters
        - preference: The state to set the mission pad preference to (True/False)
        '''

        if not type(preference) == bool: raise ValueError('[TELLO] Preference value provided was invalid. Please make sure it\'s a valid boolean type')

        if preference == self._mp: raise ValueError('[TELLO] Mission pad preference provided is the same as the currently set one')

        if preference: self._sender('mon', 'basic', False)
        else: self._sender('moff', 'basic', False)

        self._mp = preference

        if self._debug: print(f'[TELLO] Set mission pad preference to -> {preference}')

    @property
    def sync(self) -> bool:
        '''
        Returns the state the sync preference is set to
        '''

        return self._sync

    @sync.setter
    def sync(self, preference: bool) -> None:
        '''
        Enables/Disables the library as synchronous by default. Meaning if no callback value is provided to certain methods, it will default to none instead of false

        ### Parameters
        - preference: The state to set the sync preference to (True/False)
        '''

        if not type(preference) == bool: raise ValueError('[TELLO] Preference value provided was invalid. Please make sure it\'s a valid boolean type')

        if preference == self._sync: raise ValueError('[TELLO] Sync preference provided is the same as the currently set one')

        self._sync = preference

        if self._debug: print(f'[TELLO] Set sync preference to -> {preference}')

    @property
    def debug(self) -> bool:
        '''
        Returns the state the debug preference is set to
        '''

        return self._debug

    @debug.setter
    def debug(self, preference: bool) -> None:
        '''
        Enables/Disables the debug mode for verbose console messages based on what's happening

        ### Parameters
        - preference: The state to set the debug preference to (True/False)
        '''

        if not type(preference) == bool: raise ValueError('[TELLO] Preference value provided was invalid. Please make sure it\'s a valid boolean type')

        if preference == self._debug: raise ValueError('[TELLO] Debug preference provided is the same as the currently set one')

        if self._debug and not preference: print('[TELLO] Debug mode disabled')
        elif not self._debug and preference: print('[TELLO] Debug mode enabled')

        self._debug = preference

    def _cthread(self) -> None:
        '''
        Internal method for sending data to the drone within a seperate thread. You normally wouldn't use this yourself
        '''

        while self._running:
            for req, call in self._cqueue:
                self._cserver.sendto(req.encode(), (self._ip, self._ports[0]))

                try: res = self._cserver.recv(1024).decode().lower()
                except TimeoutError:
                    self._running = False
                    raise TelloError(f'Timed out. Did not receive response from drone within {self._to} seconds')
                except KeyboardInterrupt:
                    self._running = False
                    return

                if not 'ok' in res:
                    if self._sm:
                        self._send('land', 'basic')
                        if self._debug: print('[TELLO] Error raised. Landing drone')
                    raise TelloError(f'Drone responded with error: {res}')
                else:
                    if 'takeoff' in req: self._flying = True
                    elif 'land' in req: self._flying = False
                    elif 'emergency' in req: self._flying = False
                    if self._debug:
                        if 'wifi' in req: print(f'[TELLO] Set wifi successfully')
                        else: print(f'[TELLO] Sent command \'{req}\' successfully')

                if call: call(res)
                self._cqueue.remove((req, call))
        else:
            return

    def _rthread(self) -> None:
        '''
        Internal method for receiving state from the drone within a seperate thread. You normally wouldn't use this yourself
        '''

        while self._running:
            try: res = re.findall(r'[^;]+?(?=;)', self._sserver.recv(1024).decode().lower())
            except TimeoutError:
                self._running = False
                raise TelloError(f'Timed out. Did not receive response from drone within {self._to} seconds')
            except KeyboardInterrupt:
                self._running = False
                return

            for match in res:
                self._slist.update({ match[0]: int(match[1]) if match[1].isdigit() else match[1] })
        else:
            return

    def _send_sync(self, msg: str, type: str, val: int = None) -> str:
        '''
        Internal method for sending data synchronously to the drone. You normally wouldn't use this yourself
        '''

        def sender(msg: str):
            self._cserver.sendto(msg.encode(), (self._ip, self._ports[0]))

            try: res = self._cserver.recv(1024).decode().lower()
            except TimeoutError as e:
                self._running = False
                raise TelloError(f'Timed out. Did not receive response from drone within {self._to} seconds ({e})')
            except KeyboardInterrupt:
                self._running = False
                return

            if not 'ok' in res: raise TelloError(f'Drone responded with error: {res}')
            else:
                if 'takeoff' in msg: self._flying = True
                elif 'land' in msg: self._flying = False
                elif 'emergency' in msg: self._flying = False
                if self._debug:
                    if 'wifi' in msg: print(f'[TELLO] Set wifi successfully')
                    else: print(f'[TELLO] Sent command \'{msg}\' successfully')

            return res

        try:
            match type:
                case 'basic':
                    return sender(msg)

                case 'aval':
                    return sender(f'{msg} {val}')

                case 'dis':
                    if not val is int or not 20 <= val: raise ValueError('[TELLO] Distance value is incorrect. Please make sure it\'s a valid integer and at least 20cm')

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
                    if not val is int or not 1 <= val <= 360: raise ValueError('[TELLO] Rotational value is incorrect. Please make sure it\'s a valid integer and between 1 - 360deg')

                    return sender(f'{msg} {val}')

                case 'cord':
                    msg = f'{msg} '

                    for n in val:
                        isd = n is int

                        if val.index(n) == len(val)-1:
                            if not isd: raise ValueError('[TELLO] Speed value is incorrect. Please make sure it\'s a valid integer')
                            elif n[1] and not 10 <= n <= 60: raise ValueError('[TELLO] Speed value is incorrect. Please make sure it\'s between 10 - 60cm/s')
                            elif not n[1] and not 10 <= n <= 100: raise ValueError('[TELLO] Speed value is incorrect. Please make sure it\'s between 10 - 100cm/s')
                        elif not isd or not -500 <= n <= 500: raise ValueError('[TELLO] coordinate value is incorrect. Please make sure it\'s a valid integer and between -500 - 500cm')

                        msg += f'{val} '

                    return sender(msg.rstrip())

                case 'mid':
                    msg = f'{msg} '

                    for n in val:
                        ind = val.index(n)
                        leg = len(val)
                        isd = n is int

                        if ind == leg-2:
                            if not isd: raise ValueError('[TELLO] Speed value is incorrect. Please make sure it\'s a valid integer')
                            elif n[1] and not 10 <= n <= 60: raise ValueError('[TELLO] Speed value is incorrect. Please make sure it\'s between 10 - 60cm/s')
                            elif not n[1] and not 10 <= n <= 100: raise ValueError('[TELLO] Speed value is incorrect. Please make sure it\'s between 10 - 100cm/s')
                        elif ind == leg-1 and not type(val) == str or not re.match(r'^[m][1-8]$', val): raise ValueError('[TELLO] Mission Pad value is incorrect. Please make sure it\'s a valid string and is between m1 - m8')
                        elif not isd or not -500 <= n <= 500: raise ValueError('[TELLO] coordinate value is incorrect. Please make sure it\'s a valid integer and between -500 - 500cm')

                        msg += f'{val} '

                    return sender(msg.rstrip())

                case 'jump':
                    msg = f'{msg} '

                    for n in val:
                        ind = val.index(n)
                        leg = len(val)
                        isd = n is int

                        if ind == leg-4:
                            if not isd: raise ValueError('[TELLO] Speed value is incorrect. Please make sure it\'s a valid integer')
                            elif n[1] and not 10 <= n <= 60: raise ValueError('[TELLO] Speed value is incorrect. Please make sure it\'s between 10 - 60cm/s')
                            elif not n[1] and not 10 <= n <= 100: raise ValueError('[TELLO] Speed value is incorrect. Please make sure it\'s between 10 - 100cm/s')
                        elif ind == leg-3 and not 1 <= n <= 360: raise ValueError('[TELLO] Yaw value is incorrect. Please make sure it\'s a valid integer and between 1 - 360deg')
                        elif ind == leg-1 or ind == leg-2 and not type(val) == str or not re.match(r'^[m][1-8]$', val): raise ValueError('[TELLO] Mission Pad value is incorrect. Please make sure it\'s a valid string and is between m1 - m8')
                        elif not isd or not -500 <= n <= 500: raise ValueError('[TELLO] coordinate value is incorrect. Please make sure it\'s a valid integer and between -500 - 500cm')

                        msg += f'{val} '

                    return sender(msg.rstrip())

                case 'setspd':
                    if not val is int or not 10 <= val <= 60: raise ValueError('[TELLO] Speed value is incorrect. Please make sure it\'s a valid integer and between 10 - 60cm/s')

                    self._spd = val

                    return sender(f'{msg} {val}')

                case 'setrc':
                    msg = f'{msg} '

                    for n in val:
                        if not val is int or not -100 <= val <= 100: raise ValueError('[TELLO] Joystick distance value is incorrect. Please make sure it\'s a valid integer and between -100 - 100')
                        msg += f'{val} '

                    return sender(msg.rstrip())

                case 'setwifi':
                    if not val[0] and not val[1]:
                        try:
                            val[0] = input('Enter new WiFi SSID: ').strip()
                            val[1] = getpass(prompt='Enter new WiFi password: ').strip()
                        except: return

                    if not val[0] or not type(val[0]) == str or not len(val[0]): raise ValueError('[TELLO] WiFi SSID value is incorrect. Please make sure it\'s a valid string and at least 1 character')
                    elif not val[1] or not type([val[1]]) == str or not len(val[1]) >= 5: raise ValueError('[TELLO] WiFi password value is incorrect. Please make sure it\'s a valid string and at least 5 characters')
                    elif not re.match(r'(?=(?:[^a-z]*[a-z]){2})(?=(?:[^A-Z]*[A-Z]){2})(?=(?:[^0-9]*[0-9]){1})', val[1]): raise ValueError('[TELLO] WiFi password value is insecure. Please make sure it contains at least 2 lowercase and uppercase letters and 1 number')

                    return sender(f'{msg} {val[0]} {val[1]}')

                case 'connwifi':
                    if not val[0] and not val[1]:
                        try:
                            val[0] = input('Enter WiFi SSID: ').strip()
                            val[1] = getpass(prompt='Enter WiFi password: ').strip()
                        except: return

                    if not val[0] or not type(val[0]) == str or not len(val[0]): raise ValueError('[TELLO] WiFi SSID value is incorrect. Please make sure it\'s a valid string and at least 1 character')
                    elif not val[1] or not type([val[1]]) == str or not len(val[1]): raise ValueError('[TELLO] WiFi password value is incorrect. Please make sure it\'s a valid string and at least 1 character')

                    return sender(f'{msg} {val[0]} {val[1]}')

                case 'mpad':
                    if not self._mp: raise TelloError('Mission pad detection hasn\'t been enabled yet. Please run the mission_pad() method first')
                    elif not val is int or not 0 <= val <= 2: raise ValueError('[TELLO] Mission Pad Detection value is incorrect. Please make sure it\'s a valid integer and between 0 - 2')

                    return sender(f'{msg} {val}')

        except Exception as e:
            if self._sm:
                self._send('land', 'basic')
                if self._debug: print('[TELLO] Error raised. Landing drone')
            self._running = False
            raise e

    def _send(self, msg: str, typ: str, callback: Callable | None, val: int = None) -> 'Tello':
        '''
        Internal method for sending data asynchronously to the drone. You normally wouldn't use this yourself
        '''

        try:
            match typ:
                case 'basic':
                    self._cqueue.append((msg, callback))

                case 'aval':
                    self._cqueue.append((f'{msg} {val}', callback))

                case 'dis':
                    if not val is int or not 20 <= val: raise ValueError('[TELLO] Distance value is incorrect. Please make sure it\'s a valid integer and at least 20cm')

                    def disrun(val):
                        while val > 500:
                            val -= 500
                            yield 500
                        else: yield val

                    for dist in disrun(val): self._cqueue.append((f'{msg} {dist}', callback))

                case 'rot':
                    if not val is int or not 1 <= val <= 360: raise ValueError('[TELLO] Rotational value is incorrect. Please make sure it\'s a valid integer and between 1 - 360deg')

                    self._cqueue.append((f'{msg} {val}', callback))

                case 'cord':
                    msg = f'{msg} '

                    for n in val:
                        isd = n is int

                        if val.index(n) == len(val)-1:
                            if not isd: raise ValueError('[TELLO] Speed value is incorrect. Please make sure it\'s a valid integer')
                            elif n[1] and not 10 <= n <= 60: raise ValueError('[TELLO] Speed value is incorrect. Please make sure it\'s between 10 - 60cm/s')
                            elif not n[1] and not 10 <= n <= 100: raise ValueError('[TELLO] Speed value is incorrect. Please make sure it\'s between 10 - 100cm/s')
                        elif not isd or not -500 <= n <= 500: raise ValueError('[TELLO] coordinate value is incorrect. Please make sure it\'s a valid integer and between -500 - 500cm')

                        msg += f'{val} '

                    self._cqueue.append((msg.rstrip(), callback))

                case 'mid':
                    msg = f'{msg} '

                    for n in val:
                        ind = val.index(n)
                        leg = len(val)
                        isd = n is int

                        if ind == leg-2:
                            if not isd: raise ValueError('[TELLO] Speed value is incorrect. Please make sure it\'s a valid integer')
                            elif n[1] and not 10 <= n <= 60: raise ValueError('[TELLO] Speed value is incorrect. Please make sure it\'s between 10 - 60cm/s')
                            elif not n[1] and not 10 <= n <= 100: raise ValueError('[TELLO] Speed value is incorrect. Please make sure it\'s between 10 - 100cm/s')
                        elif ind == leg-1 and not type(val) == str or not re.match(r'^[m][1-8]$', val): raise ValueError('[TELLO] Mission Pad value is incorrect. Please make sure it\'s a valid string and is between m1 - m8')
                        elif not isd or not -500 <= n <= 500: raise ValueError('[TELLO] coordinate value is incorrect. Please make sure it\'s a valid integer and between -500 - 500cm')

                        msg += f'{val} '

                    self._cqueue.append((msg.rstrip(), callback))

                case 'jump':
                    msg = f'{msg} '

                    for n in val:
                        ind = val.index(n)
                        leg = len(val)
                        isd = n is int

                        if ind == leg-4:
                            if not isd: raise ValueError('[TELLO] Speed value is incorrect. Please make sure it\'s a valid integer')
                            elif n[1] and not 10 <= n <= 60: raise ValueError('[TELLO] Speed value is incorrect. Please make sure it\'s between 10 - 60cm/s')
                            elif not n[1] and not 10 <= n <= 100: raise ValueError('[TELLO] Speed value is incorrect. Please make sure it\'s between 10 - 100cm/s')
                        elif ind == leg-3 and not 1 <= n <= 360: raise ValueError('[TELLO] Yaw value is incorrect. Please make sure it\'s a valid integer and between 1 - 360deg')
                        elif ind == leg-1 or ind == leg-2 and not type(val) == str or not re.match(r'^[m][1-8]$', val): raise ValueError('[TELLO] Mission Pad value is incorrect. Please make sure it\'s a valid string and is between m1 - m8')
                        elif not isd or not -500 <= n <= 500: raise ValueError('[TELLO] coordinate value is incorrect. Please make sure it\'s a valid integer and between -500 - 500cm')

                        msg += f'{val} '

                    self._cqueue.append((msg.rstrip(), callback))

                case 'setspd':
                    if not val is int or not 10 <= val <= 60: raise ValueError('[TELLO] Speed value is incorrect. Please make sure it\'s a valid integer and between 10 - 60cm/s')

                    self._spd = val

                    self._cqueue.append((f'{msg} {val}', callback))

                case 'setrc':
                    msg = f'{msg} '

                    for n in val:
                        if not val is int or not -100 <= val <= 100: raise ValueError('[TELLO] Joystick distance value is incorrect. Please make sure it\'s a valid integer and between -100 - 100')
                        msg += f'{val} '

                    self._cqueue.append((msg.rstrip(), callback))

                case 'setwifi':
                    if not val[0] and not val[1]:
                        try:
                            val[0] = input('Enter new WiFi SSID: ').strip()
                            val[1] = getpass(prompt='Enter new WiFi password: ').strip()
                        except: return

                    if not val[0] or not type(val[0]) == str or not len(val[0]): raise ValueError('[TELLO] WiFi SSID value is incorrect. Please make sure it\'s a valid string and at least 1 character')
                    elif not val[1] or not type([val[1]]) == str or not len(val[1]) >= 5: raise ValueError('[TELLO] WiFi password value is incorrect. Please make sure it\'s a valid string and at least 5 characters')
                    elif not re.match(r'(?=(?:[^a-z]*[a-z]){2})(?=(?:[^A-Z]*[A-Z]){2})(?=(?:[^0-9]*[0-9]){1})', val[1]): raise ValueError('[TELLO] WiFi password value is insecure. Please make sure it contains at least 2 lowercase and uppercase letters and 1 number')

                    self._cqueue.append((f'{msg} {val[0]} {val[1]}', callback))

                case 'connwifi':
                    if not val[0] and not val[1]:
                        try:
                            val[0] = input('Enter WiFi SSID: ').strip()
                            val[1] = getpass(prompt='Enter WiFi password: ').strip()
                        except: return

                    if not val[0] or not type(val[0]) == str or not len(val[0]): raise ValueError('[TELLO] WiFi SSID value is incorrect. Please make sure it\'s a valid string and at least 1 character')
                    elif not val[1] or not type([val[1]]) == str or not len(val[1]): raise ValueError('[TELLO] WiFi password value is incorrect. Please make sure it\'s a valid string and at least 1 character')

                    self._cqueue.append((f'{msg} {val[0]} {val[1]}', callback))

                case 'mpad':
                    if not self._mp: raise TelloError('Mission pad detection hasn\'t been enabled yet. Please run the mission_pad() method first')
                    elif not val is int or not 0 <= val <= 2: raise ValueError('[TELLO] Mission Pad Detection value is incorrect. Please make sure it\'s a valid integer and between 0 - 2')

                    self._cqueue.append((f'{msg} {val}', callback))

            return self
        except Exception as e:
            if self._sm:
                self._send_sync('land', 'basic')
                if self._debug: print('[TELLO] Error raised. Landing drone')
            self._running = False
            raise e

    def _state(self, *msgs: str) -> tuple[int | str]:
        '''
        Internal method for receiving a state value from the state dict. You normally wouldn't use this yourself
        '''

        ret = []

        for key, val in self._slist.items():
            if key in msgs: ret.append(val)
            else: raise TelloError('The status requested is only available when mission pads are enabled. Please run the mission_pad() method first to use this method')

        return tuple(ret) if len(ret) > 1 else ret[0]

    def _sender(self, msg: str, type: str, callback: Callable | bool | None, *args) -> Union['Tello', str]:
        '''
        Internal method for deciding how to send data (sync or async). You normally wouldn't use this yourself
        '''

        if callback is False:
            if self._sync: return self._send_sync(msg, type, *args)
            else: return self._send(msg, type, None, *args)
        elif callback is None:
            return self._send(msg, type, None, *args)
        else:
            if not type(callback) is Callable: raise ValueError('[TELLO] Callback function is incorrect. Please make sure it\'s a callable')
            return self._send(msg, type, callback, *args)

    def _checkfly(self) -> None:
        '''
        Internal method to check whether the drone has taken off or not. You normally wouldn't use this yourself
        '''

        if not self._flying: raise TelloError(f'Can only run this method once the drone is flying. Please run the takeoff() method first')

    def takeoff(self, callback: Callable | bool | None = False) -> Union['Tello', str]:
        '''
        Makes the drone automatically takeoff to a height of 80cm

        ### Parameters
        - callback?: A function to be called once a response from the drone is received with said response as the first argument in string form.
        If a none value is provided, this method will be non-blocking but will have no callback.
        If false is provided, this method will be blocking and return the response (Defaults to false/blocking)
        '''

        return self._sender('takeoff', 'basic', callback)

    def land(self, callback: Callable | bool | None = False) -> Union['Tello', str]:
        '''
        Makes the drone automatically land at it's current position

        ### Parameters
        - callback?: A function to be called once a response from the drone is received with said response as the first argument in string form.
        If a none value is provided, this method will be non-blocking but will have no callback.
        If false is provided, this method will be blocking and return the response (Defaults to false/blocking)
        '''

        self._checkfly()
        return self._sender('land', 'basic', callback)

    def emergency(self, callback: Callable | bool | None = False) -> Union['Tello', str]:
        '''
        Stops all drone motors immediately in case of emergency

        ### Parameters
        - callback?: A function to be called once a response from the drone is received with said response as the first argument in string form.
        If a none value is provided, this method will be non-blocking but will have no callback.
        If false is provided, this method will be blocking and return the response (Defaults to false/blocking)
        '''

        return self._sender('emergency', 'basic', callback)

    def stop(self, callback: Callable | bool | None = False) -> Union['Tello', str]:
        '''
        Makes the drone hover in the air at it's current position

        ### Parameters
        - callback?: A function to be called once a response from the drone is received with said response as the first argument in string form.
        If a none value is provided, this method will be non-blocking but will have no callback.
        If false is provided, this method will be blocking and return the response (Defaults to false/blocking)
        '''

        self._checkfly()
        return self._sender('stop', 'basic', callback)

    def up(self, distance: int = None, callback: Callable | bool | None = False) -> Union['Tello', str]:
        '''
        Makes the drone move up the provided amount of centimeters. If distance isn't provided, the default amount of distance set will be used

        ### Parameters
        - distance: Distance you would like the drone to move (cm)
        - callback?: A function to be called once a response from the drone is received with said response as the first argument in string form.
        If a none value is provided, this method will be non-blocking but will have no callback.
        If false is provided, this method will be blocking and return the response (Defaults to false/blocking)
        '''

        self._checkfly()
        return self._sender('up', 'dist', callback, distance if distance else self._dd)

    def down(self, distance: int = None, callback: Callable | bool | None = False) -> Union['Tello', str]:
        '''
        Makes the drone move down the provided amount of centimeters. If distance isn't provided, the default amount of distance set will be used

        ### Parameters
        - distance?: Distance you would like the drone to move (cm)
        - callback?: A function to be called once a response from the drone is received with said response as the first argument in string form.
        If a none value is provided, this method will be non-blocking but will have no callback.
        If false is provided, this method will be blocking and return the response (Defaults to false/blocking)
        '''

        self._checkfly()
        return self._sender('down', 'dist', callback, distance if distance else self._dd)

    def left(self, distance: int = None, callback: Callable | bool | None = False) -> Union['Tello', str]:
        '''
        Makes the drone move left the provided amount of centimeters. If distance isn't provided, the default amount of distance set will be used

        ### Parameters
        - distance?: Distance you would like the drone to move (cm)
        - callback?: A function to be called once a response from the drone is received with said response as the first argument in string form.
        If a none value is provided, this method will be non-blocking but will have no callback.
        If false is provided, this method will be blocking and return the response (Defaults to false/blocking)
        '''

        self._checkfly()
        return self._sender('left', 'dist', callback, distance if distance else self._dd)

    def right(self, distance: int = None, callback: Callable | bool | None = False) -> Union['Tello', str]:
        '''
        Makes the drone move right the provided amount of centimeters. If distance isn't provided, the default amount of distance set will be used

        ### Parameters
        - distance?: Distance you would like the drone to move (cm)
        - callback?: A function to be called once a response from the drone is received with said response as the first argument in string form.
        If a none value is provided, this method will be non-blocking but will have no callback.
        If false is provided, this method will be blocking and return the response (Defaults to false/blocking)
        '''

        self._checkfly()
        return self._sender('right', 'dist', callback, distance if distance else self._dd)

    def forward(self, distance: int = None, callback: Callable | bool | None = False) -> Union['Tello', str]:
        '''
        Makes the drone move forward the provided amount of centimeters. If distance isn't provided, the default amount of distance set will be used

        ### Parameters
        - distance?: Distance you would like the drone to move (cm)
        - callback?: A function to be called once a response from the drone is received with said response as the first argument in string form.
        If a none value is provided, this method will be non-blocking but will have no callback.
        If false is provided, this method will be blocking and return the response (Defaults to false/blocking)
        '''

        self._checkfly()
        return self._sender('forward', 'dist', callback, distance if distance else self._dd)

    def backward(self, distance: int = None, callback: Callable | bool | None = False) -> Union['Tello', str]:
        '''
        Makes the drone move backward the provided amount of centimeters. If distance isn't provided, the default amount of distance set will be used

        ### Parameters
        - distance?: Distance you would like the drone to move (cm)
        - callback?: A function to be called once a response from the drone is received with said response as the first argument in string form.
        If a none value is provided, this method will be non-blocking but will have no callback.
        If false is provided, this method will be blocking and return the response (Defaults to false/blocking)
        '''

        self._checkfly()
        return self._sender('back', 'dist', callback, distance if distance else self._dd)

    def clockwise(self, degrees: int = None, callback: Callable | bool | None = False) -> Union['Tello', str]:
        '''
        Makes the drone rotate clockwise the provided amount of degrees. If degrees isn't provided, the default amount of rotation set will be used

        ### Parameters
        - degrees?: Degrees you would like the drone to turn
        - callback?: A function to be called once a response from the drone is received with said response as the first argument in string form.
        If a none value is provided, this method will be non-blocking but will have no callback.
        If false is provided, this method will be blocking and return the response (Defaults to false/blocking)
        '''

        self._checkfly()
        return self._sender('cw', 'rot', callback, degrees if degrees else self._dr)

    def counter_clockwise(self, degrees: int = None, callback: Callable | bool | None = False) -> Union['Tello', str]:
        '''
        Makes the drone rotate counterclockwise the provided amount of degrees.  If degrees isn't provided, the default amount of rotation set will be used

        ### Parameters
        - degrees?: Degrees you would like the drone to turn
        - callback?: A function to be called once a response from the drone is received with said response as the first argument in string form.
        If a none value is provided, this method will be non-blocking but will have no callback.
        If false is provided, this method will be blocking and return the response (Defaults to false/blocking)
        '''

        self._checkfly()
        return self._sender('ccw', 'rot', callback, degrees if degrees else self._dr)

    def flip_left(self, callback: Callable | bool | None = False) -> Union['Tello', str]:
        '''
        Makes the drone flip towards the left

        ### Parameters
        - callback?: A function to be called once a response from the drone is received with said response as the first argument in string form.
        If a none value is provided, this method will be non-blocking but will have no callback.
        If false is provided, this method will be blocking and return the response (Defaults to false/blocking)
        '''

        self._checkfly()
        return self._sender('flip', 'aval', callback, 'l')

    def flip_right(self, callback: Callable | bool | None = False) -> Union['Tello', str]:
        '''
        Makes the drone flip towards the right

        ### Parameters
        - callback?: A function to be called once a response from the drone is received with said response as the first argument in string form.
        If a none value is provided, this method will be non-blocking but will have no callback.
        If false is provided, this method will be blocking and return the response (Defaults to false/blocking)
        '''

        self._checkfly()
        return self._sender('flip', 'aval', callback, 'r')

    def flip_forward(self, callback: Callable | bool | None = False) -> Union['Tello', str]:
        '''
        Makes the drone flip forwards

        ### Parameters
        - callback?: A function to be called once a response from the drone is received with said response as the first argument in string form.
        If a none value is provided, this method will be non-blocking but will have no callback.
        If false is provided, this method will be blocking and return the response (Defaults to false/blocking)
        '''

        self._checkfly()
        return self._sender('flip', 'aval', callback, 'f')

    def flip_backward(self, callback: Callable | bool | None = False) -> Union['Tello', str]:
        '''
        Makes the drone flip backwards

        ### Parameters
        - callback?: A function to be called once a response from the drone is received with said response as the first argument in string form.
        If a none value is provided, this method will be non-blocking but will have no callback.
        If false is provided, this method will be blocking and return the response (Defaults to false/blocking)
        '''

        self._checkfly()
        return self._sender('flip', 'aval', callback, 'b')

    def go(self, x: int, y: int, z: int, speed: int = None, callback: Callable | bool | None = False) -> Union['Tello', str]:
        '''
        Makes the drone go to the provided coordinates based of it's current position (0, 0, 0). If speed isn't provided, the default amount of speed set will be used

        ### Parameters
        - x: The x coordinate you would like the drone to go to (-500 - 500)
        - y: The y coordinate you would like the drone to go to (-500 - 500)
        - z: The z coordinate you would like the drone to go to (-500 - 500)
        - speed?: The speed you would like the drone to fly (10 - 100cm/s)
        - callback?: A function to be called once a response from the drone is received with said response as the first argument in string form.
        If a none value is provided, this method will be non-blocking but will have no callback.
        If false is provided, this method will be blocking and return the response (Defaults to false/blocking)
        '''

        self._checkfly()
        return self._sender('go', 'cord', callback, (x, y, z, (speed if speed else self._spd, False)))

    def curve(self, x1: int, y1: int, z1: int, x2: int, y2: int, z2: int, speed, callback: Callable | bool | None = False) -> Union['Tello', str]:
        '''
        Makes the drone fly in a curve according to the two provided coordinates based off it's current position (0, 0, 0). If speed isn't provided, the default amount of speed set will be used

        ### Parameters
        - x1: The x coordinate you would like the drone to curve from (-500 - 500)
        - y1: The y coordinate you would like the drone to curve from (-500 - 500)
        - z1: The z coordinate you would like the drone to curve from (-500 - 500)
        - x2: The x coordinate you would like the drone to curve to (-500 - 500)
        - y2: The y coordinate you would like the drone to curve to (-500 - 500)
        - z2: The z coordinate you would like the drone to curve to (-500 - 500)
        - speed?: The speed you would like the drone to fly (10 - 60cm/s)
        - callback?: A function to be called once a response from the drone is received with said response as the first argument in string form.
        If a none value is provided, this method will be non-blocking but will have no callback.
        If false is provided, this method will be blocking and return the response (Defaults to false/blocking)
        '''

        self._checkfly()
        return self._sender('curve', 'cord', callback, (x1, y1, z1, x2, y2, z2, (speed if speed else self._spd, True)))

    def go_mid(self, x: int, y: int, z: int, mid: str, speed: int, callback: Callable | bool | None = False) -> Union['Tello', str]:
        '''
        Makes the drone go to the provided coordinates based off the provided mission pad. If speed isn't provided, the default amount of speed set will be used

        ### Parameters
        - x: The x coordinate you would like the drone to go to (-500 - 500)
        - y: The y coordinate you would like the drone to go to (-500 - 500)
        - z: The z coordinate you would like the drone to go to (-500 - 500)
        - mid: The mission pad ID you would like to base the coordinates off (m1 - m8)
        - speed?: The speed you would like the drone to fly (10 - 100cm/s)
        - callback?: A function to be called once a response from the drone is received with said response as the first argument in string form.
        If a none value is provided, this method will be non-blocking but will have no callback.
        If false is provided, this method will be blocking and return the response (Defaults to false/blocking)
        '''

        self._checkfly()
        return self._sender('go', 'cord', callback, (x, y, z, mid, (speed if speed else self._spd, False)))

    def curve_mid(self, x1: int, y1: int, z1: int, x2: int, y2: int, z2: int, mid: str, speed: int, callback: Callable | bool | None = False) -> Union['Tello', str]:
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
        - speed?: The speed you would like the drone to fly (10 - 60cm/s)
        - callback?: A function to be called once a response from the drone is received with said response as the first argument in string form.
        If a none value is provided, this method will be non-blocking but will have no callback.
        If false is provided, this method will be blocking and return the response (Defaults to false/blocking)
        '''

        self._checkfly()
        return self._sender('curve', 'cord', callback, (x1, y1, z1, x2, y2, z2, (speed if speed else self._spd, True), mid))

    def jump(self, x: int, y: int, z: int, mid1: str, mid2: str, yaw: int, speed: int, callback: Callable | bool | None = False) -> Union['Tello', str]:
        '''
        Makes the drone go to the provided coordinates based off the first provided mission pad then rotate to the yaw value based off the z coordinate of the second mission pad. If speed isn't provided, the default amount of speed set will be used

        ### Parameters
        - x: The x coordinate you would like the drone to go to (-500 - 500)
        - y: The y coordinate you would like the drone to go to (-500 - 500)
        - z: The z coordinate you would like the drone to go to (-500 - 500)
        - mid1: The mission pad ID you would like to base the coordinates off (m1 - m8)
        - mid2: The mission pad ID you would like the drone to base the z coordinate off (m1 - m8)
        - yaw: The yaw you would like the drone to rotate to (1 - 360deg)
        - speed?: The speed (in cm/s) you would like the drone to fly (10 - 100cm/s)
        '''

        self._checkfly()
        return self._sender('jump', 'cord', callback, (x, y, z, (speed if speed else self._spd, False), yaw, mid1, mid2))

    def speed(self, speed: int, callback: Callable | bool | None = False) -> Union['Tello', str]:
        '''
        Sets the speed (in cm/s) you would like the drone to go at by default

        ### Parameters
        - speed: The speed you would like the drone to move at (10 - 60cm/s)
        - callback?: A function to be called once a response from the drone is received with said response as the first argument in string form.
        If a none value is provided, this method will be non-blocking but will have no callback.
        If false is provided, this method will be blocking and return the response (Defaults to false/blocking)
        '''

        return self._sender('speed', 'setspd', callback, speed)

    def remote_controller(self, lr: int, fb: int, ud: int, y: int, callback: Callable | bool | None = False) -> Union['Tello', str]:
        '''
        Moves the drone based off of simulating a remote controller. Each value provided is how far it will move from it's current position in that direction

        ### Parameters
        - lr: The left/right position (in cm)
        - fb: the forward/backward position (in cm)
        - ud: The up/down position (in cm)
        - y: The yaw (in deg)
        - callback?: A function to be called once a response from the drone is received with said response as the first argument in string form.
        If a none value is provided, this method will be non-blocking but will have no callback.
        If false is provided, this method will be blocking and return the response (Defaults to false/blocking)
        '''

        self._checkfly()
        return self._sender('rc', 'setrc', callback, (lr, fb, ud, y))

    def set_wifi(self, ssid: str = None, pwd: str = None, callback: Callable | bool | None = False) -> Union['Tello', str]:
        '''
        Sets the drones wifi SSID and password. Has a basic security check requiring 2 lowercase and 2 uppercase letters with 1 number.
        If no values are provided a terminal prompt will be used to collect them instead

        ### Parameters
        - ssid?: The WiFi SSID you would like the drone to broadcast
        - pwd?: The password you would like the drone WiFi to be secure with
        - callback?: A function to be called once a response from the drone is received with said response as the first argument in string form.
        If a none value is provided, this method will be non-blocking but will have no callback.
        If false is provided, this method will be blocking and return the response (Defaults to false/blocking)
        '''

        return self._sender('setwifi', 'wifi', callback, (ssid, pwd))

    def mission_pad(self, on: bool = True, callback: Callable | bool | None = False) -> Union['Tello', str]:
        '''
        Enables/Disables the use of the drones mission pad detection. When enabled forward and downward mission pad detection is automatically enabled

        ### Parameters
        - on?: The state to set the mission pad preference to (True/False)
        - callback?: A function to be called once a response from the drone is received with said response as the first argument in string form.
        If a none value is provided, this method will be non-blocking but will have no callback.
        If false is provided, this method will be blocking and return the response (Defaults to false/blocking)
        '''

        if on:
            self._mp = True
            return self._sender('mon', 'aval', callback)
        else:
            self._mp =  False
            return self._sender('moff', 'aval', callback)

    def mission_pad_direction(self, dir: int, callback: Callable | bool | None = False) -> Union['Tello', str]:
        '''
        Sets the drones mission pad detection. Requires mission pad detection to be enabled

        ### Parameters
        - dir: The direction(s) you would like the drone to detect a mission pad with (0 = Downward only, 1 = Forward only, 2 = Downward and Forward)
        - callback?: A function to be called once a response from the drone is received with said response as the first argument in string form.
        If a none value is provided, this method will be non-blocking but will have no callback.
        If false is provided, this method will be blocking and return the response (Defaults to false/blocking)
        '''

        return self._sender('mdirection', 'mpad', callback, dir)

    def connect_wifi(self, ssid: str = None, pwd: str = None, callback: Callable | bool | None = False) -> Union['Tello', str]:
        '''
        Turns the drone into station mode and connects to a new access point with the provided SSID and password.
        If no values are provided a terminal prompt will be used to collect them instead

        ### Parameters
        - ssid?: The access point SSID you would like the drone to connect to
        - pwd?: The password for the access point you would like the drone to connect to
        - callback?: A function to be called once a response from the drone is received with said response as the first argument in string form.
        If a none value is provided, this method will be non-blocking but will have no callback.
        If false is provided, this method will be blocking and return the response (Defaults to false/blocking)
        '''

        return self._sender('ac', 'connwifi', callback, (ssid, pwd))

    def get_speed(self, callback: Callable | bool | None = False) -> Union['Tello', str]:
        '''
        Returns the current speed of the drone (in cm/s)

        ### Parameters
        - callback?: A function to be called once a response from the drone is received with said response as the first argument in string form.
        If a none value is provided, this method will be non-blocking but will have no callback.
        If false is provided, this method will be blocking and return the response (Defaults to false/blocking)
        '''

        return self._sender('speed?', 'basic', callback)

    def get_battery(self, callback: Callable | bool | None = False) -> Union['Tello', str]:
        '''
        Returns the current battery percentage of the drone. If run with a callback function provided, this method will be non blocking and will provide the result in a future to the callback function

        ### Parameters
        - callback?: A function to be called once a response from the drone is received with said response as the first argument in string form.
        If a none value is provided, this method will be non-blocking but will have no callback.
        If false is provided, this method will be blocking and return the response (Defaults to false/blocking)
        '''

        return self._sender('battery?', 'basic', callback)

    def get_time(self, callback: Callable | bool | None = False) -> Union['Tello', str]:
        '''
        Returns the current flight time of the drone. If run with a callback function provided, this method will be non blocking and will provide the result in a future to the callback function

        ### Parameters
        - callback?: A function to be called once a response from the drone is received with said response as the first argument in string form.
        If a none value is provided, this method will be non-blocking but will have no callback.
        If false is provided, this method will be blocking and return the response (Defaults to false/blocking)
        '''

        return self._sender('time?', 'basic', callback)

    def get_signal_noise(self, callback: Callable | bool | None = False) -> Union['Tello', str]:
        '''
        Returns the drones current WiFi SNR (signal:noise ratio). If run with a callback function provided, this method will be non blocking and will provide the result in a future to the callback function

        ### Parameters
        - callback?: A function to be called once a response from the drone is received with said response as the first argument in string form.
        If a none value is provided, this method will be non-blocking but will have no callback.
        If false is provided, this method will be blocking and return the response (Defaults to false/blocking)
        '''

        return self._sender('wifi?', 'basic', callback)

    def get_sdk(self, callback: Callable | bool | None = False) -> Union['Tello', str]:
        '''
        Returns the current Tello SDK version of the drone. If run with a callback function provided, this method will be non blocking and will provide the result in a future to the callback function

        ### Parameters
        - callback?: A function to be called once a response from the drone is received with said response as the first argument in string form.
        If a none value is provided, this method will be non-blocking but will have no callback.
        If false is provided, this method will be blocking and return the response (Defaults to false/blocking)
        '''

        return self._sender('sdk?', 'basic', callback)

    def get_serial(self, callback: Callable | bool | None = False) -> Union['Tello', str]:
        '''
        Returns the serial number of the drone. If run with a callback function provided, this method will be non blocking and will provide the result in a future to the callback function

        ### Parameters
        - callback?: A function to be called once a response from the drone is received with said response as the first argument in string form.
        If a none value is provided, this method will be non-blocking but will have no callback.
        If false is provided, this method will be blocking and return the response (Defaults to false/blocking)
        '''

        return self._sender('sn?', 'basic', callback)

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
        return (r for r in res) if not 0 in res else None

    def get_mpx(self) -> str | None:
        '''
        Returns the current x coordinate of the current detected mission pad or None if not detected
        '''

        res = self._state('x')
        return (r for r in res) if not 0 in res else None

    def get_mpy(self) -> str | None:
        '''
        Returns the current y coordinate of the current detected mission pad or None if not detected
        '''

        res = self._state('y')
        return (r for r in res) if not 0 in res else None

    def get_mpz(self) -> str | None:
        '''
        Returns the current z coordinate of the current detected mission pad or None if not detected
        '''

        res = self._state('z')
        return (r for r in res) if not 0 in res else None

    def get_pry(self) -> tuple[int]:
        '''
        Returns the current pitch, roll, and yaw of the drone (in degrees)
        '''

        return (r for r in self._state('pitch', 'roll', 'yaw'))

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

        return (r for r in self._state('vgx', 'vgy', 'vgz'))

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

        return (r for r in self._state('templ', 'temph'))

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

        return (r for r in self._state('agx', 'agy', 'agz'))

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
