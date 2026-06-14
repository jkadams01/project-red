# Toolkit for headless byte-editing of the UCDEP (CFRU/DPE) FireRed ROM.
# Uses table addresses from HexManiacAdvance's .toml metadata.
import struct, re, os

ROM_PATH = os.path.join(os.path.dirname(__file__), "project-red.gba")
TOML_PATH = os.path.join(os.path.dirname(__file__), "project-red.toml")

# ---- PCS (Pokemon Character Set) for FRLG names ----
def _build_charmap():
    m = {}
    for i, c in enumerate("0123456789"):       m[0xA1 + i] = c
    for i, c in enumerate("ABCDEFGHIJKLMNOPQRSTUVWXYZ"): m[0xBB + i] = c
    for i, c in enumerate("abcdefghijklmnopqrstuvwxyz"): m[0xD5 + i] = c
    m[0x00] = " "
    m[0xAB] = "!"; m[0xAC] = "?"; m[0xAD] = "."; m[0xAE] = "-"
    m[0xB4] = "'"; m[0xBA] = ""  # extras
    m[0x2D] = "&"
    return m
CHARMAP = _build_charmap()
RCHARMAP = {v: k for k, v in CHARMAP.items() if v}

class Rom:
    FREE_BASE = 0x0071AE00   # inside the verified 6 MB 0xFF region at 0x71AD9C

    def __init__(self, path=ROM_PATH):
        self.path = path
        with open(path, "rb") as f:
            self.data = bytearray(f.read())
        self.tables = parse_toml_anchors(TOML_PATH)
        self._free = self.FREE_BASE

    def alloc(self, length, align=4):
        """Bump-allocate `length` bytes from the big free region. Verifies the target is free."""
        p = (self._free + align - 1) & ~(align - 1)
        if any(b != 0xFF for b in self.data[p:p+length]):
            raise RuntimeError("alloc target 0x%X not free (%d bytes)" % (p, length))
        self._free = p + length
        return p

    def save(self, path=None):
        with open(path or self.path, "wb") as f:
            f.write(self.data)

    # ---- primitive reads/writes ----
    def u8(self, a):  return self.data[a]
    def u16(self, a): return self.data[a] | (self.data[a+1] << 8)
    def u32(self, a): return struct.unpack_from("<I", self.data, a)[0]
    def wu8(self, a, v):  self.data[a] = v & 0xFF
    def wu16(self, a, v):
        self.data[a] = v & 0xFF; self.data[a+1] = (v >> 8) & 0xFF
    def wu32(self, a, v): struct.pack_into("<I", self.data, a, v & 0xFFFFFFFF)

    def ptr(self, a):
        """Read a GBA pointer at address a -> ROM offset (or None if null/invalid)."""
        v = self.u32(a)
        if v == 0: return None
        if v < 0x08000000 or v >= 0x0A000000: return None
        return v - 0x08000000
    def wptr(self, a, off):
        self.wu32(a, (off + 0x08000000) if off is not None else 0)
    def to_gba(self, off): return off + 0x08000000

    # ---- names ----
    def read_name(self, addr, maxlen=20):
        out = []
        for i in range(maxlen):
            b = self.data[addr + i]
            if b == 0xFF: break
            out.append(CHARMAP.get(b, "?"))
        return "".join(out)
    def write_name(self, addr, text, field_len):
        b = bytearray([0xFF]) * field_len
        for i, ch in enumerate(text):
            if i >= field_len: break
            b[i] = RCHARMAP.get(ch, 0x00)
        if len(text) < field_len:
            b[len(text)] = 0xFF
        self.data[addr:addr+field_len] = b

    # ---- free space ----
    def find_free(self, length, align=4, start=0x00200000):
        """Find a run of 0xFF bytes of given length. Returns ROM offset."""
        d = self.data
        n = len(d)
        need = length
        a = start
        a = (a + align - 1) & ~(align - 1)
        while a + need <= n:
            # quick check: scan for a 0xFF run
            if d[a] != 0xFF:
                a += align
                continue
            ok = True
            for j in range(need):
                if d[a + j] != 0xFF:
                    ok = False
                    break
            if ok:
                return a
            # skip past the non-FF byte we found
            a = (a + j + align) & ~(align - 1)
        raise RuntimeError("no free space for %d bytes" % length)


def parse_toml_anchors(path):
    """Return {name: {'addr': int, 'format': str}} from HMA toml NamedAnchors."""
    with open(path, "r", encoding="utf-8") as f:
        txt = f.read()
    tables = {}
    # blocks separated by [[NamedAnchors]]
    for block in txt.split("[[NamedAnchors]]")[1:]:
        nm = re.search(r"Name\s*=\s*'''(.*?)'''", block, re.S)
        ad = re.search(r"Address\s*=\s*0x([0-9A-Fa-f]+)", block)
        fmt = re.search(r"Format\s*=\s*'''(.*?)'''", block, re.S)
        if nm and ad:
            tables[nm.group(1)] = {
                "addr": int(ad.group(1), 16),
                "format": fmt.group(1) if fmt else "",
            }
    return tables


if __name__ == "__main__":
    rom = Rom()
    print("ROM size:", len(rom.data))
    print("tables parsed:", len(rom.tables))
    for key in ["data.pokemon.names", "data.pokemon.stats", "data.pokemon.evolutions",
                "data.pokemon.wild", "data.trainers.stats", "data.trainers.classes.names"]:
        t = rom.tables.get(key)
        print("  %-32s addr=0x%X" % (key, t["addr"]) if t else "  MISSING "+key)
