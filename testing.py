'''
Testing script for the TelloDji library
Made by zahtec (https://www.github.com/zahtec/tellodji)
'''

from socket import AF_INET, SOCK_DGRAM, socket
from threading import Thread
from subprocess import Popen
from tellodji import Tello

s = socket(AF_INET, SOCK_DGRAM)
s.bind(('127.0.0.1', 8889))
r = True


def thr1():
    while r:
        p = s.recvfrom(1024)
        s.sendto('ok'.encode(), p[1])
        print(p[0], p[1], sep=' -- ')
    else:
        return


def thr2():
    while r:
        s.sendto('agx:55%.2f;agy:55%.2f;agz:55%.2f;'.encode(),
                 ('127.0.0.1', 8890))
    else:
        return


p = Popen([
    'ffmpeg',
    '-loglevel', 'quiet',
    '-f', 'avfoundation',
    '-framerate', '30',
    '-pix_fmt', 'yuyv422',
    '-i', '0',
    '-f', 'h264',
    'udp://0.0.0.0:11111'
])

Thread(target=thr1).start()
Thread(target=thr2).start()

print('Command and state servers active\nffmpeg active')


def caller(m):
    print(f'CALLBACK - {m}')


t = Tello(('127.0.0.1', '0.0.0.0'), debug=True,
          takeoff=True, video=True, safety=False)

t.up(50, callback=caller)

t.down()

t.left()

t.right()

t.forward(callback=caller).backward(callback=caller)

t.set_sync(caller)

t.land()

t.exit()

r = False
p.send_signal(2)
