"""Generate a Workflow that adversarially audits the Mega Evolution feature implementation."""
import romlib, gamedata, json
import feature_bosses as fb, feature_megastones as fm

rom=romlib.Rom()
TR=rom.tables["data.trainers.stats"]["addr"]; IST=rom.tables["data.items.stats"]["addr"]
def itn(i): return rom.read_name(IST+i*44,14)
ELS={2:8,3:16}

# boss mega data (read back from built ROM)
bosses=[]
for d in fb.boss_defs()+fb.champion_defs():
    if not d.get("mega"): continue
    tid=d["ids"][0]; o=TR+tid*40; st=rom.u8(o); cnt=rom.u8(o+0x20); ptr=rom.ptr(o+0x24); esz=ELS.get(st,16)
    team=[]
    for k in range(cnt):
        mo=ptr+k*esz; team.append(dict(sp=gamedata.spname(rom,rom.u16(mo+4)),lv=rom.u16(mo+2),
                                       item=itn(rom.u16(mo+6)) if rom.u16(mo+6) else ""))
    ace=team[-1]
    bosses.append(dict(boss=d["name"],tid=tid,ace=ace["sp"],ace_dex=rom.u16(ptr+(cnt-1)*esz+4),
                       team=[(t["sp"],t["lv"],t["item"]) for t in team]))

# the give-item script bytes for a sample stone + the ring
def script_for(item):
    return " ".join("%02X"%b for b in [0x1A,0x00,0x80,item&0xFF,item>>8,0x1A,0x01,0x80,0x01,0x00,0x09,0x01,0x02])

data=dict(
  bosses=bosses,
  ring_delivery="Mega Ring (item 353, a KEY ITEM) appended to scripts.newgame.pc.item (gNewGamePCItems) "
                "so it sits in the player's bedroom PC item-storage at new game; player withdraws it.",
  itemball_script_example=script_for(533),
  itemball_script_decode="setorcopyvar VAR_0x8000, <item>; setorcopyvar VAR_0x8001, 1; callstd 1; end "
                "(repointed from the original ball; original pickup FLAG is kept so the ball vanishes once taken)",
  scatter=fm.STONES[:26],
  notes="ROM base = UCDEP (CFRU + DPE expansion) FireRed. All Gen1-9 megas + stones (items 533-579) present. "
        "No traineraibits 'mega' flag exists; bosses currently have aiFlags=0x07 (CheckBadMove/TryToKO/CheckViability).",
)
blob=json.dumps(data,separators=(",",":"))

js='''export const meta = {
  name: 'audit-mega-evolution',
  description: 'Adversarially audit the Mega Evolution feature (boss stones, scatter, player Mega Ring) of a CFRU/DPE FireRed romhack',
  phases: [{title:'Review'},{title:'Synthesize'}],
}
const D = %s;
const FINDING = { type:'object', additionalProperties:false, required:['dimension','findings'], properties:{
  dimension:{type:'string'},
  findings:{ type:'array', items:{ type:'object', additionalProperties:false,
    required:['severity','issue','recommendation'], properties:{
      severity:{type:'string', description:'blocker|major|minor|ok'},
      issue:{type:'string'}, recommendation:{type:'string'} } } } } };

const dims = [
 {key:'cfru-trainer-mega', prompt:
`Dimension: will the AI bosses actually Mega Evolve in battle?
In CFRU/DPE FireRed, does an opponent trainer's Pokemon Mega Evolve automatically when it merely HOLDS the
correct Mega Stone as its held item, with NO special AI flag set? (Bosses have aiFlags=0x07.) Is anything else
required (a battle flag, the mon's ability, a 'mega ring' for the AI side)? Identify any blocker that would
stop these held-stone bosses from mega-evolving. Boss data: ${JSON.stringify(D.bosses)}`},
 {key:'player-mega-ring', prompt:
`Dimension: can the PLAYER mega-evolve? CFRU requires the player to own a key item (Mega Ring, item 353).
Delivery used: ${D.ring_delivery}
Does delivering a KEY ITEM through gNewGamePCItems (the bedroom PC item storage) work in FRLG/CFRU — i.e. can a
key item be placed there and successfully WITHDRAWN into the Key Items pocket? Or will it get stuck / not show?
If risky, recommend a more reliable guaranteed delivery (e.g. an item-ball on the forced early path, or a script).`},
 {key:'itemball-bytecode', prompt:
`Dimension: is the give-item script correct? Each scattered ball was repointed to this XSE bytecode:
${D.itemball_script_example}  =>  ${D.itemball_script_decode}
Is 'callstd 1' the correct standard script for a Poke-ball field item (the "found ITEM!" that removes the ball)
in FRLG? Will it also correctly give a KEY ITEM and a regular Mega Stone? Any off-by-one / wrong std index / missing
fanfare / flag handling issue? The original object FLAG (FLAG_ITEM_*) is reused unchanged.`},
 {key:'boss-pairings', prompt:
`Dimension: correctness of boss mega assignments. For each boss verify: exactly one teammate holds a stone, the
stone matches that species' real Mega Evolution, and the ACE (listed last) is a Gen-1 species (National Dex <=151).
Flag any wrong stone/species pairing or non-Gen1 ace. Data: ${JSON.stringify(D.bosses)}`},
 {key:'scatter-design', prompt:
`Dimension: scattered stones for the player. ${D.scatter.length} stones placed early->late by repointing existing
low-value item balls (potions/X-items/repels), preserving each ball's flag, never touching TMs/Rare Candy/key items.
List (location order): ${JSON.stringify(D.scatter)}. Judge: good geographic/difficulty spread? any stone for a Pokemon
the player cannot obtain? any concern with replacing those item balls? ${D.notes}`},
];

phase('Review');
const results = await parallel(dims.map(d=>()=>
  agent(`You are a Pokemon CFRU/DPE FireRed romhacking expert doing an ADVERSARIAL correctness review.
${d.prompt}
Be concrete and skeptical; cite CFRU/FRLG behavior. Only flag real problems. Use severity ok when fine.`,
    {label:d.key, phase:'Review', schema:FINDING})));

phase('Synthesize');
const syn = await agent(
`Consolidate these mega-evolution audit findings into a prioritized action list (blockers first). For each, give the
single most reliable fix. Findings JSON: ${JSON.stringify(results.filter(Boolean))}`,
  {label:'synthesize', phase:'Synthesize', schema:{type:'object',additionalProperties:false,
    required:['blockers','actions','verdict'],properties:{
      blockers:{type:'array',items:{type:'string'}},
      actions:{type:'array',items:{type:'object',additionalProperties:false,required:['priority','action'],
        properties:{priority:{type:'string'},action:{type:'string'}}}},
      verdict:{type:'string'}}}});
return { reviews: results.filter(Boolean), synthesis: syn };
''' % blob

open("mega_audit_workflow.js","w",encoding="utf-8").write(js)
print("wrote mega_audit_workflow.js (%d bytes); %d bosses, %d stones"%(len(js),len(bosses),len(fm.STONES[:26])))
