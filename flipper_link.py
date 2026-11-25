import threading
import time

from kivy.clock import Clock
from kivy.utils import platform

FLIPPER_VID = 0x0483

def log(msg):
    print(msg)


class FlipperLink:
    """USB link to a Flipper Zero (Android USB host via usb4a + usbserial4a)."""

    def __init__(self, on_state, ext_log=None):
        if ext_log:
            globals()["log"] = ext_log
        self.on_state = on_state
        self.port = None
        self.rpc = None
        self.on_frame = None
        self.devname = None
        self.busy = False
        self.failed = None
        self.asked = set()
        self.seen = None
        self.usb = self.serial4a = None
        if platform == "android":
            try:
                from usb4a import usb
                from usbserial4a import serial4a
                self.usb, self.serial4a = usb, serial4a
                log("USB libraries loaded")
            except Exception as e:
                log("USB libraries missing: %r" % (e,))
        else:
            log("Not on Android: USB disabled")

    def poll(self, dt):
        try:
            self._poll()
        except Exception as e:
            log("poll error: %r" % (e,))

    def _poll(self):
        if not self.usb or self.busy:
            return
        devices = list(self.usb.get_usb_device_list())
        names = [d.getDeviceName() for d in devices]
        if tuple(names) != self.seen:
            self.seen = tuple(names)
            log("USB devices: %d" % len(devices))
            for d in devices:
                log("  %s %04x:%04x" % (d.getDeviceName(), d.getVendorId(),
                                       d.getProductId()))
        if self.port is not None:
            if self.devname not in names:
                self._lost()
            return
        flipper = next((d for d in devices if d.getVendorId() == FLIPPER_VID), None)
        if flipper is None:
            self.asked.clear()
            self.failed = None
            self.on_state("waiting", {})
            return
        name = flipper.getDeviceName()
        if name == self.failed:
            return
        if not self.usb.has_usb_permission(flipper):
            self.on_state("permission", {})
            if name not in self.asked:
                self.asked.add(name)
                log("requesting USB permission")
                self.usb.request_usb_permission(flipper)
            return
        self.busy = True
        threading.Thread(target=self._open, args=(name,), daemon=True).start()

    def _lost(self):
        log("Flipper disconnected")
        try:
            self.port.close()
        except Exception:
            pass
        self.port = self.devname = None
        self.on_state("waiting", {})

    @staticmethod
    def _read_until_prompt(port, timeout):
        buf = b""
        end = time.time() + timeout
        try:
            port.timeout = 0.1
        except Exception:
            pass
        while time.time() < end:
            try:
                chunk = port.read(256)
            except Exception as e:
                log("read err: %r" % (e,))
                break
            if chunk:
                buf += chunk
                if buf.rstrip(b" \r\n").endswith(b">:"):
                    break
            else:
                time.sleep(0.02)
        log("rx %d bytes" % len(buf))
        return buf

    @staticmethod
    def _read_for(port, secs):
        buf = b""
        end = time.time() + secs
        while time.time() < end:
            try:
                chunk = port.read(256)
            except Exception as e:
                log("read err: %r" % (e,))
                break
            if chunk:
                buf += chunk
            else:
                time.sleep(0.02)
        return buf

    def _stream(self, port, rpc):
        n = 0
        idle = 0
        try:
            rpc.start_stream()
            log("stream started")
            while self.port is port:
                data = rpc.screen(0.5)
                if not data:
                    idle += 1
                    if idle % 10 == 0:
                        log("no frame x%d" % idle)
                    continue
                n += 1
                if n == 1 or n % 10 == 0 or len(data) != 1024:
                    log("frame #%d len=%d" % (n, len(data)))
                if len(data) == 1024 and self.on_frame:
                    Clock.schedule_once(lambda dt, d=data: self.on_frame(d))
        except Exception as e:
            log("stream err: %r" % (e,))

    def _open(self, name):
        port = None
        try:
            port = self.serial4a.get_serial_port(name, 115200, 8, "N", 1)
            if not port or not port.is_open:
                raise RuntimeError("serial port did not open")
            try:
                port.dtr = True
                port.rts = True
            except Exception as e:
                log("dtr: %r" % (e,))
            log("port open, asking device_info")
            time.sleep(0.3)
            port.write(b"\r\n")
            g = self._read_until_prompt(port, 2.0)
            log("greet: %r" % (g,))
            info = {}
            try:
                from flipper_rpc import Rpc
                for ch in b"start_rpc_session\r":
                    port.write(bytes([ch]))
                    time.sleep(0.01)
                r1 = self._read_for(port, 1.0)
                log("rpc start: %s" % r1.hex())
                self.rpc = Rpc(port, log)
                info = self.rpc.device_info()
            except Exception as e:
                log("rpc err: %r" % (e,))
            log("device_info: %d fields" % len(info))
            for k in list(info)[:6]:
                log("  %s = %s" % (k, info[k]))
            self.port, self.devname = port, name
            if self.rpc:
                threading.Thread(target=self._stream, args=(port, self.rpc),
                                 daemon=True).start()
            Clock.schedule_once(lambda dt: self.on_state("connected", info))
        except Exception as e:
            log("open failed: %r" % (e,))
            self.failed = name
            try:
                if port:
                    port.close()
            except Exception:
                pass
            msg = repr(e)
            Clock.schedule_once(lambda dt: self.on_state("error", {"msg": msg}))
        finally:
            self.busy = False

