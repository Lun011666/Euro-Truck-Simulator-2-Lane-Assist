from ETS2LA.Module import *
import logging
import struct
import socket

class Module(ETS2LAModule):
    """Sends steering angles to a Moza wheel base over UDP."""
    def imports(self):
        global socket
        import socket

    def init(self):
        self.address = ("127.0.0.1", 60400)
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        except Exception as e:
            logging.error(f"Failed to create UDP socket for Moza: {e}")
            self.sock = None

    def send_angle(self, angle: float) -> None:
        if self.sock is None:
            return
        try:
            data = struct.pack("f", angle)
            self.sock.sendto(data, self.address)
        except Exception as e:
            logging.error(f"Failed to send angle to Moza wheel: {e}")

    def run(self, angle: float):
        self.send_angle(angle)
