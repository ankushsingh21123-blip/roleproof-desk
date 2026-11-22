// Local actual-PostgreSQL migration and capacity regression, not a hosted load test.
import {PGlite} from '@electric-sql/pglite';
import fs from 'node:fs/promises';
import assert from 'node:assert/strict';
const db = new PGlite();
try {
 await db.exec('CREATE ROLE anon; CREATE ROLE authenticated;');
 const schema=await fs.readFile(new URL('./schema.postgres.sql',import.meta.url),'utf8');
 assert.equal(schema.split('(SELECT count(*) FROM roleproof_private.sessions)>=500').length,2);
 await db.exec(schema.replace('(SELECT count(*) FROM roleproof_private.sessions)>=500','(SELECT count(*) FROM roleproof_private.sessions)>=100'));
 await db.exec(`INSERT INTO roleproof_private.sessions(id,expires_at) SELECT lpad(to_hex(n),64,'0'),floor(extract(epoch FROM now()))::bigint+604800 FROM generate_series(1,99)n`);
 const token=n=>n.toString(16).padStart(64,'0');
 const rpc=async n=>(await db.query("SELECT public.roleproof_rpc('session',$1,'{}'::jsonb) r",[token(n)])).rows[0].r;
 assert.equal((await rpc(100)).status,201);
 assert.equal((await rpc(101)).status,503);
 const before=(await db.query('SELECT row_to_json(s) r FROM roleproof_private.sessions s ORDER BY id')).rows;
 const tickets=(await db.query('SELECT row_to_json(t) r FROM roleproof_private.tickets t ORDER BY id')).rows;
 const migration=await fs.readFile(new URL('./capacity-recovery.sql',import.meta.url),'utf8');
 await db.exec(migration);
 assert.deepEqual((await db.query('SELECT row_to_json(s) r FROM roleproof_private.sessions s ORDER BY id')).rows,before);
 assert.deepEqual((await db.query('SELECT row_to_json(t) r FROM roleproof_private.tickets t ORDER BY id')).rows,tickets);
 assert.equal((await rpc(100)).status,200);
 assert.equal((await rpc(101)).status,201);
 await db.exec(`INSERT INTO roleproof_private.sessions(id,expires_at) SELECT lpad(to_hex(n),64,'0'),floor(extract(epoch FROM now()))::bigint+604800 FROM generate_series(102,500)n`);
 assert.equal((await rpc(100)).status,200);
 assert.equal((await rpc(501)).status,503);
 assert.equal((await db.query('SELECT count(*)::int n FROM roleproof_private.sessions')).rows[0].n,500);
 let refused=false;try{await db.exec(migration)}catch{refused=true;await db.exec('ROLLBACK')}
 assert.equal(refused,true);
 assert.equal((await rpc(100)).status,200);
 console.log('PASS: old cap reproduced, 100 existing records and tickets preserved exactly, fresh workspace recovered, cap500 enforced, replay safely rejected, existing workspace retained.');
} finally {await db.close()}
