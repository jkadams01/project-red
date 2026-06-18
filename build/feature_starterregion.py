"""Let the player choose which REGION's starters to pick from, at the first starter ball.

Oak's Lab = bank 4, map 3; the 3 balls = obj4/5/6 (gfx 0x5C). Each ball script does
`setvar VAR_0x4002,<species>` then gives it; we swap that to `copyvar VAR_0x4002,VAR_S_<pos>`
(same 5 bytes, in place). We repoint each ball object to a wrapper `call region_setup; goto <orig>`.

region_setup (run once, guarded by VAR_REGION): LOCK first (FRLG menus hang without it), then a region
menu, then fill VAR_S_LEFT/MID/RIGHT (grass/water/fire) with the chosen region's trio. FRLG menus cap at
6 options, so the 9 regions are PAGINATED: menu A = first 5 + "MORE", menu B = last 4.

The rival is unchanged (his starter is chosen by ball POSITION -> stays Kanto, as requested).
NOTE: edits the new-game/starter flow -> must be mGBA-playtested.
"""
import romlib, struct

# (name, grass=LEFT, water=MIDDLE, fire=RIGHT)
REGIONS = [
 ("KANTO","Bulbasaur","Squirtle","Charmander"),
 ("JOHTO","Chikorita","Totodile","Cyndaquil"),
 ("HOENN","Treecko","Mudkip","Torchic"),
 ("SINNOH","Turtwig","Piplup","Chimchar"),
 ("UNOVA","Snivy","Oshawott","Tepig"),
 ("KALOS","Chespin","Froakie","Fennekin"),
 ("ALOLA","Rowlet","Popplio","Litten"),
 ("GALAR","Grookey","Sobble","Scorbunny"),
 ("PALDEA","Sprigatito","Quaxly","Fuecoco"),
]
VAR_REGION=0x40E9; VAR_SL=0x40EA; VAR_SM=0x40ED; VAR_SR=0x40B8   # verified-unused saved vars
VAR_RESULT=0x800D; VAR_SPECIES=0x4002
MC_TABLE=0x3E04B0; SLOT_A=64; SLOT_B=63    # overwrite two unused Union-Room link menu slots
PAGE1=5                                     # first menu shows REGIONS[0:5] + "MORE"; menu B shows the rest
# (object index in Oak Lab, orig script addr, species-setvar addr, source var)
BALLS=[(4,0x169BAB,0x169BB2,VAR_SL),(5,0x169D78,0x169D7F,VAR_SM),(6,0x169DAE,0x169DB5,VAR_SR)]

def _v(var): return bytes([var&0xFF,var>>8])
def enc(s):  return bytes(romlib.RCHARMAP.get(c,0) for c in s)+b"\xFF"
def gba(off): return (off+0x08000000).to_bytes(4,"little")

def apply(rom, verbose=True):
    import feature_bosses as fb
    resolver=fb.build_resolver(rom)
    def sp(name):
        i=fb.resolve(resolver,name); assert i and i<0x4000, "bad species %s"%name; return i

    def write_list(slot, labels):
        opt=rom.alloc(len(labels)*8)
        for k,lab in enumerate(labels):
            ta=rom.alloc(len(enc(lab))); rom.data[ta:ta+len(enc(lab))]=enc(lab)
            rom.data[opt+k*8:opt+k*8+4]=gba(ta); rom.data[opt+k*8+4:opt+k*8+8]=b"\x00\x00\x00\x00"
        o=MC_TABLE+slot*8; rom.data[o:o+4]=gba(opt); rom.wu32(o+4,len(labels))
    # menu A = first 5 region names + "MORE"; menu B = remaining region names
    write_list(SLOT_A, [r[0] for r in REGIONS[:PAGE1]]+["MORE"])
    write_list(SLOT_B, [r[0] for r in REGIONS[PAGE1:]]+["BACK"])
    BACK_IDX = len(REGIONS)-PAGE1   # index of "BACK" in menu B (after the page-2 regions)

    # region setter scripts (one per region): setvar VAR_SL/SM/SR = grass/water/fire ; return
    setters=[]
    for (nm,g,w,f) in REGIONS:
        blob=(b"\x16"+_v(VAR_SL)+sp(g).to_bytes(2,"little")+b"\x16"+_v(VAR_SM)+sp(w).to_bytes(2,"little")
             +b"\x16"+_v(VAR_SR)+sp(f).to_bytes(2,"little")+b"\x03")
        a=rom.alloc(len(blob)); rom.data[a:a+len(blob)]=blob; setters.append(a)

    # region_setup: lock -> guard -> menuA -> (MORE? menuB/BACK) -> region# -> 9-way CALL setter -> release/return
    GRID=lambda slot: bytes([0x6F,1,0,slot,1])     # multichoice x=1 y=0 list, allowCancel=ForbidCancel
    body=bytearray(); P={}
    body+=b"\x6A"                                        # lock
    body+=b"\x21"+_v(VAR_REGION)+b"\x00\x00"             # compare VAR_REGION,0
    P["done@"]=len(body)+2; body+=b"\x06\x05"+b"\0\0\0\0"      # if1 != goto done
    P["menuA"]=len(body)                                 # loop target for "BACK"
    body+=GRID(SLOT_A)                                   # menu A
    body+=b"\x21"+_v(VAR_RESULT)+bytes([PAGE1,0])        # compare VAR_RESULT, PAGE1 (the "MORE" index)
    P["menuB@"]=len(body)+2; body+=b"\x06\x01"+b"\0\0\0\0"     # if1 == goto menuB
    body+=b"\x19"+_v(VAR_REGION)+_v(VAR_RESULT)          # copyvar region,result
    body+=b"\x17"+_v(VAR_REGION)+b"\x01\x00"             # addvar region,1  (regions 1..5)
    P["branch@"]=len(body)+1; body+=b"\x05"+b"\0\0\0\0"       # goto branch
    P["menuB"]=len(body); body+=GRID(SLOT_B)             # menuB: menu B
    body+=b"\x21"+_v(VAR_RESULT)+bytes([BACK_IDX,0])     # compare VAR_RESULT, BACK index
    P["menuA@"]=len(body)+2; body+=b"\x06\x01"+b"\0\0\0\0"     # if1 == goto menuA (BACK -> page 1)
    body+=b"\x19"+_v(VAR_REGION)+_v(VAR_RESULT)          # copyvar region,result
    body+=b"\x17"+_v(VAR_REGION)+bytes([PAGE1+1,0])      # addvar region, 6 (regions 6..9)
    P["branch"]=len(body)
    bpatch=[]
    for k in range(len(REGIONS)):
        body+=b"\x21"+_v(VAR_REGION)+bytes([k+1,0])      # compare region,k+1
        bpatch.append((len(body)+2,setters[k])); body+=b"\x07\x01"+b"\0\0\0\0"   # if2 == call setter
    P["done"]=len(body); body+=b"\x6C\x03"               # done: release; return
    setup=rom.alloc(len(body))
    body[P["done@"]:P["done@"]+4]=gba(setup+P["done"])
    body[P["menuB@"]:P["menuB@"]+4]=gba(setup+P["menuB"])
    body[P["menuA@"]:P["menuA@"]+4]=gba(setup+P["menuA"])
    body[P["branch@"]:P["branch@"]+4]=gba(setup+P["branch"])
    for pos,tgt in bpatch: body[pos:pos+4]=gba(tgt)
    rom.data[setup:setup+len(body)]=body

    # wrappers + repoint balls + species setvar->copyvar swap
    import mapinfo
    op=rom.ptr(rom.ptr(mapinfo.header(rom,4,3)+4)+4)
    for (objidx,orig,setvar_addr,srcvar) in BALLS:
        wrap=b"\x04"+gba(setup)+b"\x05"+gba(orig)
        wa=rom.alloc(len(wrap)); rom.data[wa:wa+len(wrap)]=wrap
        rom.wptr(op+objidx*0x18+0x10, wa)
        assert rom.u8(setvar_addr)==0x16 and rom.u16(setvar_addr+1)==VAR_SPECIES
        rom.wu8(setvar_addr,0x19); rom.data[setvar_addr+3:setvar_addr+5]=_v(srcvar)

    if verbose:
        print("[starterregion] %d regions (paged %d+%d), region_setup@0x%X, slots A=%d B=%d"
              % (len(REGIONS),PAGE1,len(REGIONS)-PAGE1,setup,SLOT_A,SLOT_B))
    return dict(regions=len(REGIONS), setup=setup)

if __name__=="__main__":
    apply(romlib.Rom())
