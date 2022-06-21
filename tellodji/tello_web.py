'''
Module for holding the Tello webserver classes
Made by zahtec (https://www.github.com/zahtec/tellodji)
'''

from http.server import BaseHTTPRequestHandler
from os.path import dirname

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