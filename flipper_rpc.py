import time


def _vi(n):
    out = bytearray()
    while True:
        b = n & 0x7F
        n >>= 7
        if n:
            out.append(b | 0x80)
        else:
            out.append(b)
            return bytes(out)


def _rd_vi(buf, i):
    v = shift = 0
    while True:
        if i >= len(buf):
            return None, i
        b = buf[i]
        i += 1
        v |= (b & 0x7F) << shift
        if not b & 0x80:
            return v, i
        shift += 7


def _fields(buf):
    i, out = 0, {}
    while i < len(buf):
        tag, i = _rd_vi(buf, i)
        if tag is None:
            break
        f, wt = tag >> 3, tag & 7
        if wt == 0:
            v, i = _rd_vi(buf, i)
        elif wt == 2:
            n, i = _rd_vi(buf, i)
            v = bytes(buf[i:i + n])
            i += n
        else:
            break
        out[f] = v
    return out


class Rpc:
    KEYS = {"up": 0, "down": 1, "right": 2, "left": 3, "ok": 4, "back": 5}

    def __init__(self, port, log=print):
        self.port, self.log, self.cid, self.buf = port, log, 0, bytearray()

    def send(self, field, payload=b"", cid=None):
        if cid is None:
            self.cid += 1
            cid = self.cid
        body = b"\x08" + _vi(cid) + _vi(field << 3 | 2) + _vi(len(payload)) + payload
        self.port.write(_vi(len(body)) + body)
        return cid

    def frame(self, timeout=2.0):
        end = time.time() + timeout
        while time.time() < end:
            n, i = _rd_vi(self.buf, 0)
            if n is not None and len(self.buf) >= i + n:
                body = bytes(self.buf[i:i + n])
                del self.buf[:i + n]
                f = _fields(body)
                return {"id": f.get(1), "status": f.get(2, 0),
                        "next": bool(f.get(3, 0)), "f": f}
            chunk = self.port.read(256)
            if chunk:
                self.buf += chunk
            else:
                time.sleep(0.01)
        return None

    def device_info(self):
        self.send(32)
        info = {}
        while True:
            fr = self.frame(3.0)
            if not fr:
                break
            if fr["status"]:
                self.log("rpc status %r" % fr["status"])
                break
            m = fr["f"].get(33)
            if m is not None:
                kv = _fields(m)
                k = kv.get(1, b"").decode(errors="replace")
                info[k] = kv.get(2, b"").decode(errors="replace")
            if not fr["next"]:
                break
        return info

    def start_stream(self):
        self.send(20)

    def stop_stream(self):
        self.send(21)

    def screen(self, timeout=1.0):
        fr = self.frame(timeout)
        if fr and 22 in fr["f"]:
            return _fields(fr["f"][22]).get(1)
        return None

    def key(self, name):
        k = self.KEYS[name]
        for t in (0, 2, 1):
            self.send(23, b"\x08" + _vi(k) + b"\x10" + _vi(t))
