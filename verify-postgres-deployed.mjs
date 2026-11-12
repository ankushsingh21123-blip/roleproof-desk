// Run only against the actual returned HTTPS deployment URL, after plan/binding checks.
// Uses two anonymous browser workspaces and synthetic test records. No credentials needed.
import { chromium } from '@playwright/test';
import assert from 'node:assert/strict';
import {mkdir,writeFile} from 'node:fs/promises';
const origin=process.env.ROLEPROOF_DEPLOYED_URL;
assert(origin && new URL(origin).protocol==='https:', 'Set ROLEPROOF_DEPLOYED_URL to the actual HTTPS deployment origin.');
assert(new URL(origin).origin===origin.replace(/\/$/,''),'Provide an origin, not a path or signed URL.');
const base=new URL(origin).origin;
const out=process.env.ROLEPROOF_EVIDENCE_DIR||'deployed-evidence';
await mkdir(out,{recursive:true});
const browser=await chromium.launch({headless:true});
try {
 const a=await browser.newContext(),b=await browser.newContext();
 const p=await a.newPage(),q=await b.newPage();
 const errors=[];p.on('pageerror',e=>errors.push(e.message));
 const response=await a.request.get(base+'/api/health');assert.equal(response.status(),200);
 const health=await response.json();assert.equal(health.database,'Supabase PostgreSQL');assert.equal(health.mode,'hosted-isolated-demo');
 await p.goto(base);await p.getByRole('button',{name:/Unable to update workspace name/}).waitFor();
 const cookies=await a.cookies(base);const cookie=cookies.find(c=>c.name==='rp_session');
 assert(cookie?.httpOnly && cookie?.secure && cookie.sameSite==='Strict','HTTPS session cookie protections missing');
 const marker='Synthetic deployment check '+new Date().toISOString();
 await p.getByRole('button',{name:'+ New ticket'}).click();
 await p.getByLabel('Title',{exact:true}).fill(marker);
 await p.getByLabel('Description',{exact:true}).fill('Fictional acceptance-check record. No personal or customer information.');
 await p.getByRole('button',{name:'Create ticket',exact:true}).click();
 await p.getByRole('heading',{name:marker,exact:true}).waitFor();
 let all=await (await a.request.get(base+'/api/tickets')).json();
 const ticket=all.tickets.find(t=>t.title===marker);assert(ticket,'UI create was not returned by database API');
 assert(!('session_id' in ticket),'Internal workspace identifier leaked');
 await p.getByLabel('Update status').selectOption('Resolved');
 await p.getByText('Status saved to database.').waitFor({state:'attached'});
 await p.getByRole('button',{name:'Back to queue'}).click();
 await p.reload();await p.getByRole('button',{name:'Resolved',exact:true}).click();
 await p.getByLabel('Search requests').fill(marker);
 await p.getByRole('button',{name:new RegExp(marker.replace(/[.*+?^${}()|[\]\\]/g,'\\$&'))}).waitFor();
 all=await (await a.request.get(base+'/api/tickets')).json();
 const saved=all.tickets.find(t=>t.id===ticket.id);assert.equal(saved.status,'Resolved');assert.equal(saved.version,ticket.version+1);
 const stale=await a.request.patch(base+'/api/tickets/'+ticket.id,{headers:{Origin:base,'X-RoleProof-Client':'desk'},data:{status:'Open',version:ticket.version}});assert.equal(stale.status(),409);
 await q.goto(base);await q.getByRole('button',{name:/Unable to update workspace name/}).waitFor();
 const other=await (await b.request.get(base+'/api/tickets')).json();assert(!other.tickets.some(t=>t.id===ticket.id || t.title===marker));
 const denied=await b.request.patch(base+'/api/tickets/'+ticket.id,{headers:{Origin:base,'X-RoleProof-Client':'desk'},data:{status:'Open',version:saved.version}});assert.equal(denied.status(),404);
 for(const width of [320,390,1280]){
  await q.setViewportSize({width,height:900});
  assert(await q.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'Horizontal overflow at '+width);
  await q.screenshot({path:out+'/queue-'+width+'.png',fullPage:true});
 }
 assert.deepEqual(errors,[]);
 // Never serialize cookie values, browser storage state, raw response headers or credentials.
 const summary={checked_at:new Date().toISOString(),origin:base,health,checks:['bound PostgreSQL read','UI create/API read','update/reload persistence','Secure HttpOnly SameSite cookie','stale update 409','second-workspace isolation','foreign update 404','320/390/1280 overflow','no page errors'],limits:'Anonymous synthetic-data demo; not a production security audit. Workspace expires in seven days; lazy cleanup on a later new-session request.'};
 await writeFile(out+'/results.json',JSON.stringify(summary,null,2)+'\n');
 console.log(JSON.stringify(summary,null,2));
} finally {await browser.close();}
