"""Generate a Workflow script that adversarially audits the themed encounters."""
import json, romlib, themer, feature_wild as fw, mapinfo, gamedata

rom=romlib.Rom()
summary=json.load(open("encounters_summary.json"))
# intended theme per location
entries=fw.walk_wild(rom); loc_lo={}
for e in entries:
    nm=mapinfo.map_name(rom,e["bank"],e["map"])
    if not fw.is_preleague(nm): continue
    for cat,_ in fw.CATS:
        c=e["cats"][cat]
        if not c: continue
        for s in c: loc_lo[nm]=min(loc_lo.get(nm,99),s["lo"])
themes={nm:themer.location_theme(nm,loc_lo.get(nm,5)) for nm in summary}

data=json.dumps({"summary":summary,"themes":themes},separators=(",",":"))

js = '''export const meta = {
  name: 'audit-kanto-encounters',
  description: 'Adversarially audit themed wild-encounter tables for a Gen1-9 FireRed/Kanto romhack',
  phases: [{title:'Audit'},{title:'Synthesize'}],
}
const DATA = %s;
const SUMMARY = DATA.summary, THEMES = DATA.themes;
const AUDIT_SCHEMA = { type:'object', additionalProperties:false, required:['locations'], properties:{
  locations:{ type:'array', items:{ type:'object', additionalProperties:false,
    required:['name','coherence','issues'], properties:{
      name:{type:'string'}, coherence:{type:'integer'},
      issues:{ type:'array', items:{ type:'object', additionalProperties:false,
        required:['species','reason'], properties:{
          species:{type:'string'}, reason:{type:'string'} } } } } } } } };
const SYN_SCHEMA = { type:'object', additionalProperties:false, required:['top_issues','notes'], properties:{
  top_issues:{ type:'array', items:{ type:'object', additionalProperties:false,
    required:['location','problem','recommended_fix','priority'], properties:{
      location:{type:'string'}, problem:{type:'string'}, recommended_fix:{type:'string'},
      priority:{type:'string'} } } },
  notes:{type:'string'} } };

const names = Object.keys(SUMMARY);
const CH = 8, chunks = [];
for (let i=0;i<names.length;i+=CH) chunks.push(names.slice(i,i+CH));

phase('Audit');
const audits = await parallel(chunks.map((chunk,ci)=>()=>{
  const text = chunk.map(loc=>{
    const s=SUMMARY[loc];
    return `### ${loc}  (intended theme: ${(THEMES[loc]||[]).join(', ')})\\n  GRASS: ${(s.grass||[]).join(', ')||'(none)'}\\n  WATER: ${(s.water||[]).join(', ')||'(none)'}`;
  }).join('\\n\\n');
  return agent(
`You are auditing THEMED wild-Pokemon encounter tables for a Pokemon FireRed (Kanto) romhack that includes Gen 1-9 species.
Each location has an intended habitat theme. Judge whether the assigned species fit that location thematically (by typing, habitat, and Kanto flavour). Caves should be rock/ground/bat/fighting types; forests bug/grass; graveyard (Pokemon Tower) ghost/dark/poison; power plant electric/steel; volcano (Mansion/Cinnabar) fire; safari rare wild game; water bodies water types; cities a light mix of urban normal/psychic/etc.
For each location: give a coherence score 1-5 (5 = perfectly themed) and list any clearly OUT-OF-PLACE species with a one-line reason. Ignore minor quibbles; flag only genuinely jarring mismatches. Do not flag legendary/mythical (there are none).

LOCATIONS:
${text}`,
    {label:`audit ${ci}`, phase:'Audit', schema:AUDIT_SCHEMA});
}));

const flat=[];
for(const a of audits) if(a&&a.locations) for(const L of a.locations) flat.push(L);

phase('Synthesize');
const syn = await agent(
`Here are per-location audit results (JSON) for themed wild encounters in a Kanto romhack.
Consolidate into a PRIORITIZED list of the most impactful, systematic fixes (not one-off nitpicks).
Prefer fixes expressible as a habitat-rule change (e.g. "Fuchsia City should lean nature/poison not electric", "Type X should map to habitat Y").
JSON: ${JSON.stringify(flat)}`,
  {label:'synthesize', phase:'Synthesize', schema:SYN_SCHEMA});

const avg = flat.length ? (flat.reduce((s,l)=>s+(l.coherence||0),0)/flat.length) : 0;
return { average_coherence: Math.round(avg*100)/100, location_count: flat.length,
         low_scoring: flat.filter(l=>l.coherence<=2).map(l=>l.name),
         synthesis: syn };
''' % data

open("theme_audit_workflow.js","w",encoding="utf-8").write(js)
print("wrote theme_audit_workflow.js (%d bytes, %d locations)" % (len(js), len(summary)))
