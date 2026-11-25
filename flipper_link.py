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
            try:
                d0 = self._read_for(port, 2.0)
                log("diag idle: %s" % d0.hex())
                w = port.write(b"help\r")
                d1 = self._read_for(port, 3.0)
                log("diag help1 ret=%r: %r" % (w, d1[:80]))
                port.write(b"\x03")
                d2 = self._read_for(port, 1.0)
                log("diag ctrlc: %r" % (d2[:40],))
                port.write(b"\r")
                d3 = self._read_for(port, 1.5)
                log("diag cr: %r" % (d3[:40],))
            except Exception as e:
                log("diag err: %r" % (e,))
            out = ""
            for cmd in (b"device_info", b"info device", b"help"):
                try:
                    n = 0
                    for ch in cmd + b"\r":
                        n += port.write(bytes([ch])) or 0
                        time.sleep(0.01)
                except Exception as e:
                    log("write err: %r" % (e,))
                    n = None
                log("sent %r ret=%r" % (cmd, n))
                raw = self._read_until_prompt(port, 3.0)
                log("reply: %r" % (raw[:120],))
                out = raw.decode(errors="replace")
                if ":" in out:
                    break
            try:
                for ch in b"start_rpc_session\r":
                    port.write(bytes([ch]))
                    time.sleep(0.01)
                r1 = self._read_for(port, 1.5)
                log("rpc start: %s" % r1.hex())
                port.write(bytes([0x04, 0x08, 0x01, 0x2a, 0x00]))
                r2 = self._read_for(port, 2.0)
                log("rpc ping: %s" % r2.hex())
            except Exception as e:
                log("rpc probe err: %r" % (e,))
            info = {}
            for line in out.splitlines():
                if ":" in line:
                    k, v = line.split(":", 1)
                    info[k.strip()] = v.strip()
            log("device_info: %d fields" % len(info))
            for k in list(info)[:6]:
                log("  %s = %s" % (k, info[k]))
            if not info:
                log("raw: %r" % (out[:200],))
            self.port, self.devname = port, name
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

