from http.server import BaseHTTPRequestHandler, HTTPServer
from webbrowser import open as openweb
from PIL.Image import open as openimg
from numpy import frombuffer, uint8
from .tello_error import TelloError
from typing import Callable, Union
from ipaddress import ip_address
from datetime import datetime
from threading import Thread
from os.path import abspath
from ffmpeg import input
from sys import stdout
import re

class _TelloWeb(BaseHTTPRequestHandler):
    '''
    Internal class for the live() and start_video() webserver. You normally wouldn't use this yourself
    '''

    def __init__(self, rec: bool) -> None:
        if rec:
            with open('record.html') as f:
                self._site = f.buffer
        else:
            with open('live.html') as f:
                self._site = f.buffer

    def do_GET(self) -> None:
        match self.path:
            case '/':
                self.send_response(200) 
                self.send_header('content-type', 'text/html')
                self.end_headers()

                self.wfile.write(self._site)

            case '/play.m3u8':
                self.send_response(200) 
                self.send_header('content-type', 'application/x-mpegURL')
                self.end_headers()

                with open('./video/play.m3u8') as f:
                    self.wfile.write(f.buffer)

            case _:
                self.send_response(301)
                self.send_header('location', '127.0.0.1')
                self.end_headers()

class TelloVideo:
    '''
    The main class for the Tello video stream. Used to construct a socket to receive data from the drones video stream and has
    methods for taking pictures and streaming/recording video. If an IP address or port was provided they will be used in construction of the socket.
    Includes a built-in webserver for streaming video. Can be automatically created and embedded within the Tello class by setting the video preference to True.
    Requires ffmpeg to be installed

    ### Parameters
    - ip?: The IP address you would like the Tello video socket to listen on (ipv4/ipv6, Defaults to 0.0.0.0)
    - ports?: The port you would like the Tello video socket to listen on (Defaults to 11111)

    ### Preferences
    - debug?: Enable/Disable the debug mode for verbose console messages based on what's happening (Defaults to false/disabled)
    - timeout?: The amount of time you would like to wait for a response from a drone before a timeout error is raised (Defaults to 7s, must be at least 1s)

    ### Constants
    - HD: Resolution value that represents the 1280 x 720 (720p) resolution for methods that have a resolution parameter
    - SD: Resolution value that represents the 852 x 480 (480p) for methods that have a resolution parameter
    '''

    HD = (1280, 720)
    SD = (852, 480)

    def __init__(self, ip: str = '192.168.10.1', port: int = 11111, **opt) -> None:
        if not type(ip) is str: raise ValueError('[TELLOVID] IP address provided was invalid. Please make sure it\'s a valid string and in proper ipv4/6 form')
        elif not type(port) is int: raise ValueError('[TELLOVID] Port provided was invalid. Please make sure it\'s a valid integer and in proper port form')
        elif 'debug' in opt and not type(opt['debug']) is bool: raise ValueError('[TELLOVID] Debug preference provided was invalid. Please make sure it\'s a valid boolean type')
        elif 'timeout' in opt and not type(opt['timeout']) is int: raise ValueError('[TELLOVID] Timeout provided was invalid. Please make sure it\'s a valid integer')
        elif 'sync' in opt and not type(opt['sync']) is bool: raise ValueError('[TELLOVID] Sync preference provided was invalid. Please make sure it\'s a valid boolean type')

        self._ip = ip
        self._port = port
        self._debug = opt['debug'] if 'debug' in opt else False
        self._to = '?timeout=\{{}\}'.format(opt['timeout'] * 1000000) if 'timeout' in opt else ''
        self._server = (input(f'udp://{ip}:{port}{self._to}').output('pipe:', format = 'rawvideo', pix_fmt = 'rgb24', loglevel = 'quiet').run_async(pipe_stdout = True, pipe_stderr = True))
        self._rec = False
        self._fra = False
        self._live = False
        self._resbytes = 1280 * 720 * 3

        if self._debug: print('[TELLOVID] Debug mode enabled')

    @property
    def ip(self) -> str:
        '''
        Returns the current IP address the Tello video socket is listening on
        '''

        return self._ip

    @ip.setter
    def ip(self, ip: str) -> None:
        '''
        Changes the Tello video socket's IP address to the one provided. Any currently running video capture will be stopped

        ### Parameters
        - ip: The IP that that you would like the socket to switch to (ipv4/ipv6)
        '''

        if not type(ip) is str: raise ValueError('[TELLOVID] IP address provided was invalid. Please make sure it\'s a valid string and in proper ipv4/6 form')

        ip = ip.strip()

        if ip == self._ip: raise ValueError('[TELLOVID] IP provided is the same as the currently set one')

        ip_address(ip)

        self._ip = ip

        self._server.terminate()
        self._server = (input(f'udp://{ip}:{self._port}{self._to}').output('pipe:', format = 'rawvideo', pix_fmt = 'rgb24', loglevel = 'quiet').run_async(pipe_stdout = True, pipe_stderr = True))

        if self._debug: print(f'[TELLOVID] Set video socket to -> {ip}:{self._port}')

    @property
    def port(self) -> int:
        '''
        Returns the current port the Tello video socket is listening on
        '''

        return self._port

    @port.setter
    def port(self, port: int) -> None:
        '''
        Changes the Tello video socket's port to the one provided. Any currently running video capture will be stopped

        ### Parameters
        - port: The port that that you would like the socket to switch to
        '''

        if not type(port) is int: raise ValueError('[TELLOVID] Port provided was invalid. Please make sure it\'s a valid integer and in proper port form')

        if port == self._port: raise ValueError('[TELLOVID] Port provided is the same as the currently set one')

        self._port = port

        self._server.terminate()
        self._server = (input(f'udp://{self._ip}:{port}{self._to}').output('pipe:', format = 'rawvideo', pix_fmt = 'rgb24', loglevel = 'quiet').run_async(pipe_stdout = True, pipe_stderr = True))

        if self._debug: print(f'[TELLOVID] Set video socket to -> {self._ip}:{port}')

    @property
    def timeout(self) -> int:
        '''
        Returns the current amount of time the Tello video socket waits before raising an error
        '''

        return self._to

    @timeout.setter
    def timeout(self, timeout: int) -> None:
        '''
        Changes the Tello video socket's timeout to the one provided

        ### Parameters
        - timeout: The amount of time you would like the video socket to wait for a response from a drone before a timeout error is raised (Must be at least 1 second)
        '''

        if not type(timeout) is int or timeout < 1: raise ValueError('[TELLOVID] Timeout provided was invalid. Please make sure it\'s a integer and at least 1 second')

        if timeout == re.findall(r'(?<=\{).+(?=\})', self._to)[0]: raise ValueError('[TELLOVID] Timeout provided was the same as the currently set one')

        self._to = '?timeout=\{{}\}'.format(timeout * 1000000)

        self._server.terminate()
        self._server = (input(f'udp://{self._ip}:{self._port}{self._to}').output('pipe:', format = 'rawvideo', pix_fmt = 'rgb24', loglevel = 'quiet').run_async(pipe_stdout = True, pipe_stderr = True))

        if self._debug: print(f'[TELLO] Set timeout to -> {timeout}')

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

        if not type(preference) is bool: raise ValueError('[TELLOVID] Preference value provided was invalid. Please make sure it\'s a valid boolean type')

        if self._debug and not preference: print('[TELLOVID] Debug mode disabled')
        elif not self._debug and preference: print('[TELLOVID] Debug mode enabled')

        self._debug = preference

    def photo(self, path: str = './photos', resolution: tuple[int] = (1280, 720), callback: Callable | bool | None = False, window: bool = False) -> Union['TelloVideo', str]:
        '''
        Takes a photo using the provided/default preferences.
        If no path is provided, it automatically creates a photos folder in the current directory with the photo having the current timestamp as the name and in png format @ 1280 x 720 (720p) resolution

        ### Parameters
        - path?: The path that can also include provided file name and format (Defaults to ./photos/TIMESTAMP.png)
        - resolution?: The resolution you would like the photo to be in. Goes up to 1280 x 720 (Defaults to HD/720p)
        - window?: Enable/Disable a preview window after the photo is taken (Defaults to false/disabled)
        - callback?: A function to be called once the image proccesing for the photo is complete with the absolute path of said photo as the first argument.
        If a none value is provided, this method will be non-blocking but will have no callback.
        If false is provided, this method will be blocking and return the response (Defaults to false/blocking)
        '''

        if not type(path) is str or not len(path) or not re.match(r'([:](?=[\/]+))|(^[\.](?=[\/]+))|(^[\~](?=[\/]+))|(^[\/](?=\w+))', path): raise TelloError('Provided path was invalid. Please make sure it\'s a valid string and in proper path format')
        elif not type(resolution) is tuple or not len(resolution) == 2: raise TelloError('Provided resolution was invalid. Please make sure it\'s a valid tuple with 2 integers providing the width and height of the resolution')
        elif not type(window) is bool: raise TelloError('Window preference provided was invalid. Please make sure it\'s a valid boolean type')

        for res in resolution:
            if not type(res) is int: raise TelloError('Provided resolution was invalid. Please make sure it\'s a valid tuple with 2 integers providing the width and height of the resolution')

        path = path.strip().rsplit('/', 1)
        file = path[1] if '.' in path[1] else datetime.now().strftime('%d/%m/%y__%H:%M:%S').join('.png')

        def thread():
            input(self._server.stdout.read(self._resbytes)).filter('scale', *resolution).filter('select', f'eq(n,1)').output(f'{path}/{file}', **{ 'frames:v': 1 }).overwrite_output()
            if window: openimg(f'{path}/{file}').show(f'Tello - {file}')
            if callback: callback(str(abspath(f'{path}/{file}')))
            return

        if callback is False:
            input(self._server.stdout.read(self._resbytes)).filter('scale', *resolution).filter('select', f'eq(n,1)').output(f'{path}/{file}', **{ 'frames:v': 1 }).overwrite_output()
            if window: openimg(f'{path}/{file}').show(f'Tello - {file}')
            return str(abspath(f'{path}/{file}'))
        else:
            Thread(target = thread).start()
            return self

    def photo_bytes(self, resolution: tuple[int] = (1280, 720), callback: Callable | bool = False) -> Union['TelloVideo', list[list[int]]]:
        '''
        Returns the bytes of the photo taken (A list of lists with 3 byte values, RGB for that pixel) in the provided/default resolution

        ### Parameters
        - resolution?: The resolution you would like the photo to be in. Goes up to 1280 x 720 (Defaults to HD/720p)
        - callback?: A function to be called once the image proccesing for the photo is complete with the bytes of said photo as the first argument.
        If false is provided, this method will be blocking and return the response (Defaults to false/blocking)
        '''

        if not type(resolution) is tuple or not len(resolution) == 2: raise TelloError('Provided resolution was invalid. Please make sure it\'s a valid tuple with 2 integers providing the width and height of the resolution')

        for res in resolution:
            if not type(res) is int: raise TelloError('Provided resolution was invalid. Please make sure it\'s a valid tuple with 2 integers providing the width and height of the resolution')

        def thread():
            callback(list(frombuffer(input(self._server.stdout.read(self._resbytes)).filter('scale', *resolution).filter('select', f'eq(n,1)'), uint8), uint8).reshape([-1, resolution[1], resolution[0], 3]))
            return

        if callback:
            Thread(target = thread).start()
            return self
        else:
            return list(frombuffer(input(self._server.stdout.read(self._resbytes)).filter('scale', *resolution).filter('select', f'eq(n,1)'), uint8), uint8).reshape([-1, resolution[1], resolution[0], 3])

    def start_video(self, path: str = './videos', resolution: tuple[int] = (1280, 720), framerate: int = 60, window: bool = False, callback: Callable | None = None) -> None:
        '''
        Takes a video using the provided/default parameters. If no path is provided, it automatically creates a videos folder in the current directory with the video having the current timestamp as the name and in mp4 format @ 1280 x 720 (720p) resolution
        and in 60fps. Will not stop recording until the stop_video() method is run

        ### Parameters
        - path?: The path that can also include provided file name and format (Defaults to ./videos/TIMESTAMP.mp4)
        - resolution?: The resolution you would like the video to be in. Goes up to 1280 x 720 (Defaults to HD/720p)
        - framerate?: The framerate you would like the video to be in. Goes up to 60fps (Defaults to 60fps)
        - window?: Enable/Disable a live preview window while the video is being taken (Defaults to false/disabled)
        - callback?: A function to be called once the stop_video() method is called with the absolute path to said video as the first argument (Defaults to none)
        '''

        if not type(path) is str or not len(path) or not re.match(r'([:](?=[\/]+))|(^[\.](?=[\/]+))|(^[\~](?=[\/]+))|(^[\/](?=\w+))', path): raise TelloError('Provided path was invalid. Please make sure it\'s a valid string and in proper path format')
        elif not type(resolution) is tuple or not len(resolution) == 2: raise TelloError('Provided resolution was invalid. Please make sure it\'s a valid tuple with 2 integers providing the width and height of the resolution')
        elif not type(framerate) is int or not 10 <= framerate <= 60: raise TelloError('Provided framerate was invalid. Please make sure it\'s a valid integer and inbetween 10 - 60')
        elif not type(window) == bool: raise TelloError('Window value provided was invalid. Please make sure it\'s a valid boolean type')

        for res in resolution:
            if not type(res) is int: raise TelloError('Provided resolution was invalid. Please make sure it\'s a valid tuple with 2 integers providing the width and height of the resolution')

        if window and self._web: raise TelloError('Webserver on live method already created. Please run the stop_live() method first')

        path = path.strip().rsplit('/', 1)
        file = path[1] if '.' in path[1] else datetime.now().strftime('%d/%m/%y__%H:%M:%S').join('.mp4')

        if window:
            rec = (input('pipe:', format='rawvideo', pix_fmt='rgb24').filter('scale', *resolution).output(f'{path}/{file}', pix_fmt='yuv420p', loglevel = 'quiet', r = framerate).overwrite_output().run_async())
            hls = (input('pipe:', format='rawvideo', pix_fmt='rgb24').filter('scale', *resolution).output(f'./video/play.m3u8', pix_fmt='yuv420p', loglevel = 'quiet', r = framerate, hls_playlist_type = 'vod').overwrite_output().run_async())
            self._rec = True

            def thread():
                while self._rec:
                    f = self._server.stdout.read(self._resbytes)
                    rec.stdin.write(f)
                    hls.stdin.write(f)
                else:
                    rec.terminate()
                    hls.terminate()
                    if self._web:
                        self._web.shutdown()
                        del self._web
                    if callback: callback(abspath(f'{path}/{file}'))
                    return

            self._web = HTTPServer(('127.0.0.1', 80), _TelloWeb(True))

            Thread(target = thread).start()
            Thread(target = self._web.serve_forever, daemon = True).start()

            openweb('127.0.0.1', new = 2)
        else:
            rec = (input('pipe:', format='rawvideo', pix_fmt='rgb24').filter('scale', *resolution).output(f'{path}/{file}', pix_fmt='yuv420p', loglevel = 'quiet', r = framerate).overwrite_output().run_async())
            self._rec = True

            def thread():
                while self._rec:
                    rec.stdin.write(self._server.stdout.read(self._resbytes))
                else:
                    rec.terminate()
                    if callback: callback(abspath(f'{path}/{file}'))
                    return

            Thread(target = thread).start()

    def video_frames(self, resolution: tuple[int] = (1280, 720), frames: int = 0) -> list[list[int]]:
        '''
        Generates the bytes of live video frames being taken in the provided/default resolution. Will not stop yielding bytes until the provided max frames is met or the stop_frames() method is run.
        This method is blocking

        ### Parameters
        - resolution?: The resolution you would like the video to be in. Goes up to 1280 x 720 (Defaults to HD/720p)
        - frames?: The max amount of frames you would like to be generated (Defaults to 0/unlimited)
        '''

        if not type(resolution) is tuple or not len(resolution) == 2: raise TelloError('Provided resolution was invalid. Please make sure it\'s a valid tuple with 2 integers providing the width and height of the resolution')
        elif not type(frames) is int: raise TelloError('Provided frame count was invalid. Please make sure it\'s a valid integer')

        for res in resolution:
            if not type(res) is int: raise TelloError('Provided resolution was invalid. Please make sure it\'s a valid tuple with 2 integers providing the width and height of the resolution')

        if frames:
            for _ in range(frames):
                yield list(frombuffer(input(self._server.stdout.read(self._resbytes)).filter('scale', *resolution).filter('select', f'eq(n,1)'), uint8), uint8).reshape([-1, resolution[1], resolution[0], 3])
        else:
            self._fra = True
            while self._fra:
                yield list(frombuffer(input(self._server.stdout.read(self._resbytes)).filter('scale', *resolution).filter('select', f'eq(n,1)'), uint8), uint8).reshape([-1, resolution[1], resolution[0], 3])

    def video_bytes(self) -> stdout:
        '''
        Returns a readable stdout object for receiving the live video feed in 1280 x 720 (720p)
        '''

        return self._server.stdout

    def live(self, resolution: tuple[int] = (1280, 720), framerate: int = 60) -> None:
        '''
        Displays a live feed of the drone video inside a browser window in the provided/default resolution and framerate. Will not shut down the webserver until the stop_live() method is run

        ### Parameters
        - resolution?: The resolution you would like the video to be in. Goes up to 1280 x 720 (Defaults to HD/720p)
        - framerate?: The framerate you would like the video to be in. Goes up to 60fps (Defaults to 60fps)
        '''

        if not type(resolution) is tuple or not len(resolution) == 2: raise TelloError('Provided resolution was invalid. Please make sure it\'s a valid tuple with 2 integers providing the width and height of the resolution')
        elif not type(framerate) is int or not 10 <= framerate <= 60: raise TelloError('Provided framerate was invalid. Please make sure it\'s a valid integer and inbetween 10 - 60')

        if self._web: raise TelloError('Webserver on video method already created. Please run the stop_video() method first')

        rec = (input('pipe:', format='rawvideo', pix_fmt='rgb24').filter('scale', *resolution).output(f'./video/play.m3u8', pix_fmt='yuv420p', loglevel = 'quiet', r = framerate, hls_playlist_type = 'vod').overwrite_output().run_async())

        def thread():
            while self._live:
                rec.stdin.write(self._server.stdout.read(self._resbytes))
            else:
                rec.terminate()
                return

        self._web = HTTPServer(('127.0.0.1', 80), _TelloWeb(False))

        Thread(target = thread).start()
        Thread(target = self._web.serve_forever, daemon = True).start()

        openweb('127.0.0.1', new = 2)

    def stop_video(self) -> None:
        '''
        Ends the start_video() method from recording data. The resulting video will be saved to disk and if the window preference was enabled the webserver will be shutdown
        '''

        self._rec = False

    def stop_frames(self) -> None:
        '''
        Ends the video_frames() method from generating frames
        '''

        self._fra = False

    def stop_live(self) -> None:
        '''
        Shuts down the live() method webserver
        '''

        if self._web:
            self._live = False
            self._web.shutdown()
            del self._web
        else: raise TelloError('No live server has been created. Please run the live() method first')
