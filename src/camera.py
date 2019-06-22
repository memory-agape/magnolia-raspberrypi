import io
import picamera
import logging
import socketserver
from threading import Condition
from http import server
from socket import *
from struct import *
import argparse
import sys
import time

class StreamingOutput(object):
    def __init__(self):
        self.frame = None
        self.buffer = io.BytesIO()
        self.condition = Condition()

    def write(self, buf):
        if buf.startswith(b'\xff\xd8'):
            self.buffer.truncate()
            with self.condition:
                self.frame = self.buffer.getvalue()
                self.condition.notify_all()
            self.buffer.seek(0)
        return self.buffer.write(buf)

with picamera.PiCamera(resolution='640x480', framerate=24) as camera:
    parser = argparse.ArgumentParser()
    parser.add_argument("ip")
    parser.add_argument("port")
    args = parser.parse_args()
    if not args.ip:
        print("Must set --ip\n")
        sys.exit()
    if not args.port:
        print("Must set --port\n")
        sys.exit()

    output = StreamingOutput()
    camera.start_recording(output, format='mjpeg')

    while True:
        print("Starting camera.\n")
        try:
            address = (
                args.ip,
                int(args.port)
            )
            server = socket(
                AF_INET,
                SOCK_STREAM
            )
            server.connect(address)
            try:
                while True:
                    with output.condition:
                        output.condition.wait()
                        frame = output.frame
                    server.sendall(
                        pack("L", len(frame)) + frame
                    )
            except Exception as e:
                logging.warning(
                    'Disconnect client %s: %s',
                    address,
                    str(e)
                )
        finally:
            camera.stop_recording()
        print("Continue to start. Please wait 10 sec.\n")
        time.sleep(10)
