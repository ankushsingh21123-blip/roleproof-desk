// Synthetic portfolio demo. The only backend credential is a public Supabase
// publishable/anon key. Narrow RPCs enforce scope, validation and database caps.
import {createHash, randomBytes} from 'node:crypto';
const headers={
 'X-Content-Type-Options':'nosniff','Referrer-Policy':'no-referrer',
 'X-Frame-Options':'DENY','Cache-Control':'no-store',
 'Content-Security-Policy':"default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'",
 'Permissions-Policy':'camera=(), microphone=(), geolocation=()'
};
const cookie='rp_session';
function send(res,status,body,extra={}){res.writeHead(status,{...headers,'Content-Type':'application/json; charset=utf-8',...extra});res.end(JSON.stringify(body));}
async function readBody(req){
 if(req.headers['x-roleproof-client']!=='desk'||req.headers['content-type']?.split(';')[0]!=='application/json')throw Object.assign(new Error('JSON and client header required.'),{status:400});
 if(req.body!==undefined){const v=typeof req.body==='string'?JSON.parse(req.body):req.body;if(Buffer.byteLength(JSON.stringify(v))>8192||!v||typeof v!=='object'||Array.isArray(v))throw Object.assign(new Error('Invalid JSON object or body too large.'),{status:400});return v;}
 let size=0;const chunks=[];
 for await(const c of req){size+=Buffer.byteLength(c);if(size>8192)throw Object.assign(new Error('Request is too large.'),{status:400});chunks.push(Buffer.from(c));}
 let value;try{value=JSON.parse(Buffer.concat(chunks).toString('utf8'));}catch{throw Object.assign(new Error('Invalid JSON.'),{status:400});}
 if(!value||typeof value!=='object'||Array.isArray(value))throw Object.assign(new Error('JSON object required.'),{status:400});
 return value;
}
export function createHandler({rpcUrl=process.env.SUPABASE_URL,publicKey=process.env.SUPABASE_PUBLISHABLE_KEY,fetchImpl=fetch}={}){
 return async function handler(req,res){
  try{
   // Vercel serves HTTPS. Never use an untrusted forwarded Host for CSRF checks.
   const origin=req.headers.origin;
   const host=req.headers.host;
   const u=new URL(req.url,'https://localhost');
   const path=u.pathname==='/api/desk'&&u.searchParams.has('route')?'/api/'+u.searchParams.get('route'):u.pathname;
   if(!['GET','POST','PATCH'].includes(req.method))return send(res,405,{error:'Method not allowed.'});
   if(req.method!=='GET'&&origin!==`https://${host}`&&!(process.env.ROLEPROOF_LOCAL_TEST==='1'&&origin===`http://${host}`))return send(res,403,{error:'Same-origin requests only.'});
   let action,payload={};
   if(path==='/api/health'&&req.method==='GET')action='health';
   else if(path==='/api/session'&&req.method==='POST'){await readBody(req);action='session';}
   else if(path==='/api/tickets'&&req.method==='GET')action='list';
   else if(path==='/api/tickets'&&req.method==='POST'){payload=await readBody(req);action='create';}
   else if(/^\/api\/tickets\/[1-9][0-9]{0,14}$/.test(path)&&req.method==='PATCH'){
    payload=await readBody(req);if(Object.keys(payload).sort().join(',')!=='status,version')return send(res,400,{error:'Expected status and version.'});
    payload.id=Number(path.split('/').pop());action='update';
   }else return send(res,404,{error:'Route not found.'});
   let token=(req.headers.cookie||'').split(';').map(x=>x.trim()).find(x=>x.startsWith(cookie+'='))?.slice(cookie.length+1);
   const hadToken=!!token&&/^[a-f0-9]{64}$/.test(token);
   if(!hadToken&&action!=='session'&&action!=='health')return send(res,401,{error:'Demo session expired. Reload to start a fresh synthetic workspace.'});
   if(!hadToken)token=randomBytes(32).toString('hex');
   if(!rpcUrl||!/^https:\/\/[a-z0-9]+\.supabase\.co$/.test(rpcUrl)||!publicKey)return send(res,503,{error:'Demo storage is not configured.'});
   const response=await fetchImpl(rpcUrl+'/rest/v1/rpc/roleproof_rpc',{
    method:'POST',headers:{apikey:publicKey,'Content-Type':'application/json'},
    body:JSON.stringify({action,token_hash:createHash('sha256').update(token).digest('hex'),payload}),signal:AbortSignal.timeout(12000)
   });
   if(!response.ok)throw new Error('Storage unavailable');
   const result=await response.json();
   if(![200,201,400,401,404,409,429,503].includes(result.status)||!result.body)throw new Error('Invalid storage response');
   const extra={};
   if(action==='session'&&[200,201].includes(result.status)){
    const ttl=Math.max(0,Math.min(604800,result.body.expires_at-Math.floor(Date.now()/1000)));
    extra['Set-Cookie']=`${cookie}=${token}; Path=/; HttpOnly; SameSite=Strict; Max-Age=${ttl}${process.env.ROLEPROOF_LOCAL_TEST==='1'?'':'; Secure'}`;
   }
   return send(res,result.status,result.body,extra);
  }catch(e){return send(res,e.status===400?400:503,{error:e.status===400?e.message:'Demo storage is unavailable. Please try again later.'});}
 };
}
export default createHandler();
