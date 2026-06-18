import romlib, gamedata
rom=romlib.Rom()
TR=rom.tables["data.trainers.stats"]["addr"]
MVN=rom.tables["data.pokemon.moves.names"]["addr"]
TCN=rom.tables["data.trainers.classes.names"]["addr"]
ELS={0:8,1:16,2:8,3:16}
def trclass(c): return rom.read_name(TCN+c*13,13).strip()
def mv(i): return rom.read_name(MVN+i*13,13).strip()
def show(tid,label):
    o=TR+tid*40; st=rom.u8(o); cnt=rom.u8(o+0x20); ptr=rom.ptr(o+0x24); esz=ELS[st]
    ai=rom.u8(o+0x1C)
    print("\n%s  (tr%d %s, %d mons, struct=%d, AI=0x%X)"%(label,tid,trclass(rom.u8(o+1)),cnt,st,ai))
    for m in range(cnt):
        mo=ptr+m*esz; lv=rom.u16(mo+2); sp=rom.u16(mo+4); it=rom.u16(mo+6)
        moves=[mv(rom.u16(mo+8+k*2)) for k in range(4)] if st in (1,3) else ["(default)"]
        st1=gamedata.stats(rom,sp)
        t1=gamedata.type_name(rom,st1["t1"]).strip(); t2=gamedata.type_name(rom,st1["t2"]).strip()
        ty=t1+("/"+t2 if t2!=t1 else "")
        print("   L%-2d %-11s [%-11s atk%d/spa%d] %s"%(lv,gamedata.spname(rom,sp),ty,st1["atk"],st1["spa"],moves))

# bosses
show(414,"BROCK (gym)"); show(420,"SABRINA (gym)"); show(413,"LANCE (E4)"); show(438,"CHAMPION")
# rival early + mid
show(332,"RIVAL early"); show(434,"RIVAL late")
# route trainers: find an early and a late one
def find_route(maxlv_lo,maxlv_hi):
    BOSS={348,349,350,410,411,412,413,414,415,416,417,418,419,420,438,439,440,735,736,737,738,739,740,741}
    for tid in range(89,300):
        if tid in BOSS: continue
        o=TR+tid*40; st=rom.u8(o); cnt=rom.u8(o+0x20); ptr=rom.ptr(o+0x24)
        if not ptr or cnt==0: continue
        esz=ELS[st]; lvs=[rom.u16(ptr+m*esz+2) for m in range(cnt)]
        if any(l<1 or l>100 for l in lvs): continue
        if maxlv_lo<=max(lvs)<=maxlv_hi: return tid
    return None
e=find_route(8,14); l=find_route(40,55)
if e: show(e,"ROUTE early")
if l: show(l,"ROUTE late")
