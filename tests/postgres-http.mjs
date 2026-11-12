import {PGlite} from '@electric-sql/pglite';
import {createServer} from 'node:http';
import fs from 'node:fs/promises';
import assert from 'node:assert/strict';
import {createHandler} from '../api/desk.mjs';
process.env.ROLEPROOF_LOCAL_TEST='1';
const db=new PGlite();await db.exec('CREATE ROLE anon; CREATE ROLE authenticated;');await db.exec(await fs.readFile(new URL('../schema.postgres.sql',import.meta.url),'utf8'));
const handler=createHandler({rpcUrl:'https://localtest.supabase.co',publicKey:'public-test-key',fetchImpl:async(url,init)=>{
 const {action,token_hash,payload}=JSON.parse(init.body);
 const r=(await db.query('SELECT public.roleproof_rpc($1,$2,$3) r',[action,token_hash,JSON.stringify(payload)])).rows[0].r;
 return new Response(JSON.stringify(r));
}});
const server=createServer(async(req,res)=>{
 if(req.url.startsWith('/api/'))return handler(req,res);
 let p=req.url==='/'?'index.html':req.url.slice(1);if(!/^(index.html|assets\/[a-zA-Z0-9_.-]+)$/.test(p)){res.writeHead(404);return res.end();}
 try{res.setHeader('Content-Type',p.endsWith('.js')?'application/javascript':p.endsWith('.css')?'text/css':'text/html');res.end(await fs.readFile(new URL('../dist/'+p,import.meta.url)));}catch{res.writeHead(404);res.end();}
});
server.listen(8791,'127.0.0.1',async()=>{
 if(process.argv.includes('--serve'))return console.log('Postgres HTTP demo test server ready8791');
 const origin='http://127.0.0.1:8791';let jar='';
 async function api(path,method='GET',body,extra={}){const r=await fetch(origin+path,{method,headers:{Origin:origin,'Content-Type':'application/json','X-RoleProof-Client':'desk',Cookie:jar,...extra},body:body===undefined?undefined:JSON.stringify(body)});if(r.headers.has('set-cookie'))jar=r.headers.get('set-cookie').split(';')[0];return {status:r.status,body:await r.json(),headers:r.headers};}
 try{
 assert.equal((await api('/api/health')).body.database,'Supabase PostgreSQL');
 assert.equal((await api('/api/tickets')).status,401);
 assert.equal((await api('/api/session','POST',{})).status,201);
 assert.equal((await api('/api/tickets')).body.tickets.length,5);
 assert.equal((await api('/api/session','POST',{}, {Origin:'https://evil.invalid'})).status,403);
 assert.equal((await api('/api/tickets','POST',{title:'no'})).status,400);
 const r=await api('/api/tickets','POST',{title:'Browser test case',description:'Only synthetic data here',category:'Product',priority:'High'});assert.equal(r.status,201);
 const id=r.body.ticket.id;
 assert.equal((await api('/api/tickets/'+id,'PATCH',{version:1,status:'Resolved'})).status,200);
 assert.equal((await api('/api/tickets/'+id,'PATCH',{version:1,status:'Open'})).status,409);
 const first=jar;jar='';await api('/api/session','POST',{});
 assert.equal((await api('/api/tickets/'+id,'PATCH',{version:2,status:'Open'})).status,404);
 jar=first;assert.equal((await api('/api/tickets')).body.tickets.find(x=>x.id===id).status,'Resolved');
 assert.equal((await api('/api/desk?route=health')).status,200);
 assert.equal((await api('/api/tickets','POST',{}, {'X-RoleProof-Client':''})).status,400);
 console.log('PASS: HTTP + PostgreSQL integration,12checks covering sessions, cookies, create/update/reload persistence, stale409, second-workspace404, CSRF403, input400 and Vercel rewritten route.');
 }finally{server.close();await db.close();}
});
