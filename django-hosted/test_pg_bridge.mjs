// Local verification fixture: actual PostgreSQL WASM, not deployed or a model mock.
import {PGlite} from '@electric-sql/pglite';
import {createServer} from 'node:http';
import fs from 'node:fs/promises';
const db=new PGlite();
await db.exec('CREATE ROLE anon; CREATE ROLE authenticated;');
await db.exec(await fs.readFile(new URL('./schema.postgres.sql',import.meta.url),'utf8'));
const server=createServer(async(req,res)=>{
 try {
 let body='';for await(const c of req)body+=c;
 const {action,token_hash,payload}=JSON.parse(body);
 const r=(await db.query('SELECT public.roleproof_rpc($1,$2,$3) r',[action,token_hash,JSON.stringify(payload)])).rows[0].r;
 res.setHeader('Content-Type','application/json');res.end(JSON.stringify(r));
 }catch(e){res.writeHead(500);res.end('{}');}
});
server.listen(8795,'127.0.0.1',()=>console.log('READY'));
process.on('SIGTERM',()=>server.close(async()=>{await db.close();process.exit(0)}));
