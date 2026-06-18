"""Render the ACTUAL map graphics (decoded tiles+palettes) to PNG, so grass placement can be
judged against real green ground vs paved roads. Pure stdlib."""
import zlib, struct, binascii, os
import romlib, mapinfo

def lz77(data, off):
    assert data[off]==0x10, "not LZ77 @0x%X"%off
    size=data[off+1]|(data[off+2]<<8)|(data[off+3]<<16)
    out=bytearray(); pos=off+4
    while len(out)<size:
        flags=data[pos]; pos+=1
        for b in range(8):
            if len(out)>=size: break
            if flags&(0x80>>b):
                b1=data[pos]; b2=data[pos+1]; pos+=2
                length=(b1>>4)+3; disp=(((b1&0xF)<<8)|b2)+1
                s=len(out)-disp
                for i in range(length): out.append(out[s+i])
            else:
                out.append(data[pos]); pos+=1
    return bytes(out[:size])

def bgr555(c):
    return ((c&31)<<3, ((c>>5)&31)<<3, ((c>>10)&31)<<3)

def write_png(path,w,h,rgb):
    def chunk(t,d): return struct.pack(">I",len(d))+t+d+struct.pack(">I",binascii.crc32(t+d)&0xFFFFFFFF)
    raw=bytearray()
    for y in range(h):
        raw.append(0); raw+=rgb[y*w*3:(y+1)*w*3]
    png=b"\x89PNG\r\n\x1a\n"+chunk(b"IHDR",struct.pack(">IIBBBBB",w,h,8,2,0,0,0))
    png+=chunk(b"IDAT",zlib.compress(bytes(raw),9))+chunk(b"IEND",b"")
    open(path,"wb").write(png)

NUM_TILES_PRIMARY=640; NUM_PALS_PRIMARY=7

class Tileset:
    def __init__(self, rom, lay):
        self.rom=rom
        bd1,bd2=lay["bd1"],lay["bd2"]
        self.tiles_p=lz77(rom.data, rom.ptr(bd1+4))
        self.tiles_s=lz77(rom.data, rom.ptr(bd2+4))
        self.bs_p=rom.ptr(bd1+12); self.bs_s=rom.ptr(bd2+12)
        pp=rom.ptr(bd1+8); sp=rom.ptr(bd2+8)
        # 16 palettes x 16 colors; primary provides 0..6, secondary 7..15
        self.pal=[]
        for p in range(16):
            src = pp if p<NUM_PALS_PRIMARY else sp
            base = src + p*32
            self.pal.append([bgr555(rom.u16(base+i*2)) for i in range(16)])
        self._mt={}
    def _tilepix(self, tid, px, py):
        if tid < NUM_TILES_PRIMARY: data=self.tiles_p; t=tid
        else: data=self.tiles_s; t=tid-NUM_TILES_PRIMARY
        o=t*32+py*4+(px>>1)
        if o>=len(data): return 0
        byte=data[o]
        return (byte>>4) if (px&1) else (byte&0xF)
    def _entry(self, bs, mt, i):
        return self.rom.u16(bs+mt*16+i*2)
    def metatile(self, mt):
        if mt in self._mt: return self._mt[mt]
        img=[(0,0,0)]*256  # 16x16
        bs = self.bs_p if mt < 512 else self.bs_s
        midx = mt if mt<512 else mt-512
        for layer in range(2):
            for sub in range(4):
                e=self._entry(bs, midx, layer*4+sub)
                tid=e&0x3FF; hf=(e>>10)&1; vf=(e>>11)&1; pal=(e>>12)&0xF
                ox=(sub&1)*8; oy=(sub>>1)*8
                for yy in range(8):
                    for xx in range(8):
                        sx=7-xx if hf else xx; sy=7-yy if vf else yy
                        idx=self._tilepix(tid,sx,sy)
                        if layer==1 and idx==0: continue   # top layer 0 = transparent
                        img[(oy+yy)*16+(ox+xx)]=self.pal[pal][idx]
        self._mt[mt]=img; return img

class GreenGround:
    """Classifies metatiles as natural green grass-ground (vs paved gray paths / dirt) using the
    decoded tile colours, so town grass is only planted on lawn, never on roads."""
    def __init__(self, rom, lay):
        self.ts = Tileset(rom, lay); self.cache = {}
    def is_green(self, mt):
        if mt in self.cache: return self.cache[mt]
        img = self.ts.metatile(mt); n = len(img)
        r = sum(p[0] for p in img)//n; g = sum(p[1] for p in img)//n; b = sum(p[2] for p in img)//n
        v = (g - r >= 30 and g - b >= 20 and g >= 120)
        self.cache[mt] = v; return v

def render(rom, b, m, name, out_dir="maps_real", scale=12, mark=None):
    os.makedirs(out_dir,exist_ok=True)
    lay=mapinfo.layout(rom,b,m); W,H=lay["width"],lay["height"]
    ts=Tileset(rom,lay)
    bpp = 16  # metatile px
    img=bytearray(W*bpp*H*bpp*3)
    PW=W*bpp
    for by in range(H):
        for bx in range(W):
            v=rom.u16(lay["blockmap"]+(by*W+bx)*2); mt=v&0x3FF
            tile=ts.metatile(mt)
            for yy in range(16):
                for xx in range(16):
                    r,g,bl=tile[yy*16+xx]
                    o=((by*16+yy)*PW+(bx*16+xx))*3
                    img[o],img[o+1],img[o+2]=r,g,bl
    # optional marker overlay (list of (x,y) tiles) drawn as red outline
    if mark:
        for (mx,my) in mark:
            for yy in range(16):
                for xx in range(16):
                    if yy in (0,15) or xx in (0,15):
                        o=((my*16+yy)*PW+(mx*16+xx))*3
                        img[o],img[o+1],img[o+2]=255,0,0
    path=os.path.join(out_dir,name.replace(" ","_").replace(".","").replace("'","")+".png")
    write_png(path,PW,H*16,img)
    print("  rendered %-16s %dx%d -> %s"%(name,W,H,path))
    return path

if __name__=="__main__":
    rom=romlib.Rom()
    for nm,b,m in [("PEWTER CITY",3,2),("VIRIDIAN CITY",3,1),("CELADON CITY",3,6)]:
        render(rom,b,m,nm)
