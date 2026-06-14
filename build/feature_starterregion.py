"""Let the player choose which REGION's starters to pick from, at the first starter ball.

How it works (Oak's Lab = bank 4, map 3; balls = obj4/5/6, gfx 0x5C):
  * Each ball script sets VAR_0x4002 = <species literal> then gives it. We swap that `setvar` to
    `copyvar VAR_0x4002, VAR_S_<pos>` (same 5 bytes, in place) so the species comes from a variable.
  * We repoint each ball's object-script to a tiny wrapper: `call region_setup; goto <orig ball script>`.
  * region_setup (run once, guarded by VAR_REGION): shows a 3x3 region multichoice grid, then a 9-way
    branch fills VAR_S_LEFT/MID/RIGHT (grass/water/fire) with the chosen region's trio.
The rival is unchanged (his starter is still chosen by ball POSITION -> stays Kanto, as requested).

NOTE: this edits the new-game/starter flow, which can't be exercised headless — needs an mGBA playtest.
"""
import romlib, gamedata, struct

# (name shown in menu, grass=LEFT, water=MIDDLE, fire=RIGHT) — order matches the ball positions.
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
MC_TABLE=0x3E04B0; MC_SLOT=64                                    # overwrite a Union-Room link menu slot
MC_GRID_PERROW=3
# (object index in Oak Lab, orig script addr, species-setvar addr, source var)
BALLS=[(4,0x169BAB,0x169BB2,VAR_SL),(5,0x169D78,0x169D7F,VAR_SM),(6,0x169DAE,0x169DB5,VAR_SR)]

def _v(var): return bytes([var&0xFF,var>>8])
def enc(s):  return bytes(romlib.RCHARMAP.get(c,0) for c in s)+b"\xFF"
def gba(off): return (off+0x08000000).to_bytes(4,"little")

def apply(rom, verbose=True):
    res={}
    import feature_bosses as fb
    resolver=fb.build_resolver(rom)
    def sp(name):
        i=fb.resolve(resolver,name)
        assert i and i<0x4000, "bad species %s -> %s"%(name,i)
        return i

    # 1) region-name strings + options array (9 x {text_ptr, unused}) -> multichoice slot 64
    opt_entries=[]
    for (nm,g,w,f) in REGIONS:
        taddr=rom.alloc(len(enc(nm))); rom.data[taddr:taddr+len(enc(nm))]=enc(nm)
        opt_entries.append(taddr)
    opts=rom.alloc(len(REGIONS)*8)
    for k,taddr in enumerate(opt_entries):
        rom.data[opts+k*8:opts+k*8+4]=gba(taddr)
        rom.data[opts+k*8+4:opts+k*8+8]=b"\x00\x00\x00\x00"
    # slot 64 = {options_ptr, count}
    so=MC_TABLE+MC_SLOT*8
    rom.data[so:so+4]=gba(opts); rom.wu32(so+4, len(REGIONS))

    # 2) region setter scripts (one per region): setvar VAR_SL/SM/SR = grass/water/fire ; return
    setters=[]
    for (nm,g,w,f) in REGIONS:
        blob=(b"\x16"+_v(VAR_SL)+sp(g).to_bytes(2,"little")
             +b"\x16"+_v(VAR_SM)+sp(w).to_bytes(2,"little")
             +b"\x16"+_v(VAR_SR)+sp(f).to_bytes(2,"little")
             +b"\x03")
        a=rom.alloc(len(blob)); rom.data[a:a+len(blob)]=blob; setters.append(a)

    # 3) region_setup script (guard -> menu -> compute -> 9-way branch -> done)
    body=bytearray()
    body+=b"\x21"+_v(VAR_REGION)+b"\x00\x00"          # compare VAR_REGION, 0
    guard_goto_pos=len(body); body+=b"\x06\x05"+b"\x00\x00\x00\x00"   # if1 != goto done (patch)
    body+=bytes([0x71,1,1,MC_SLOT,MC_GRID_PERROW,0])  # multichoicegrid x1 y1 list per_row noCancel
    body+=b"\x19"+_v(VAR_REGION)+_v(VAR_RESULT)        # copyvar VAR_REGION, VAR_RESULT
    body+=b"\x17"+_v(VAR_REGION)+b"\x01\x00"           # addvar VAR_REGION, 1
    branch_patches=[]
    for k in range(len(REGIONS)):
        body+=b"\x21"+_v(VAR_REGION)+bytes([k+1,0])    # compare VAR_REGION, k+1
        branch_patches.append((len(body), setters[k])) # if1 == goto setter (patch ptr)
        body+=b"\x06\x01"+b"\x00\x00\x00\x00"
    done_off=len(body); body+=b"\x03"                  # done: return
    setup=rom.alloc(len(body))
    # patch gotos with absolute addresses
    body[guard_goto_pos+2:guard_goto_pos+6]=gba(setup+done_off)
    for pos,target in branch_patches:
        body[pos+2:pos+6]=gba(target)
    rom.data[setup:setup+len(body)]=body

    # 4) wrappers (call region_setup ; goto orig ball script) + repoint object scripts + swap species
    import mapinfo
    h=mapinfo.header(rom,4,3); op=rom.ptr(rom.ptr(h+4)+4)
    for (objidx,orig,setvar_addr,srcvar) in BALLS:
        wrap=b"\x04"+gba(setup)+b"\x05"+gba(orig)       # call setup ; goto orig
        wa=rom.alloc(len(wrap)); rom.data[wa:wa+len(wrap)]=wrap
        rom.wptr(op+objidx*0x18+0x10, wa)               # object script -> wrapper
        # swap `setvar VAR_4002, species` (16 02 40 LL HH) -> `copyvar VAR_4002, srcvar` (19 02 40 vv vv)
        assert rom.u8(setvar_addr)==0x16 and rom.u16(setvar_addr+1)==VAR_SPECIES
        rom.wu8(setvar_addr,0x19); rom.data[setvar_addr+3:setvar_addr+5]=_v(srcvar)

    if verbose:
        print("[starterregion] %d regions; menu slot=%d, region_setup@0x%X, vars region=0x%X L/M/R=0x%X/0x%X/0x%X"
              % (len(REGIONS),MC_SLOT,setup,VAR_REGION,VAR_SL,VAR_SM,VAR_SR))
        print("[starterregion] repointed balls obj4/5/6 + swapped species setvars; rival unchanged (Kanto)")
    res.update(regions=len(REGIONS), setup=setup)
    return res

if __name__=="__main__":
    apply(romlib.Rom())
