// AI-assisted Next.js adaptation of the existing public portfolio source.
// Generated entrypoints stay small; main.tsx remains the readable UI source.
import {mkdir,readFile,writeFile} from 'node:fs/promises';
await mkdir('pages/api',{recursive:true});
let source=await readFile('main.tsx','utf8');
source=source.replace('import { createRoot } from "react-dom/client";\n','').replace('import "./style.css";\n','').replace('function App() {','export default function App() {');
const marker=source.indexOf('createRoot(document.getElementById');
if(marker<0)throw new Error('Expected original React root marker. Review the adapter before building.');
await writeFile('pages/index.tsx',source.slice(0,marker));
await writeFile('pages/_app.tsx','import type { AppProps } from "next/app";\nimport "../style.css";\nexport default function Application({ Component, pageProps }: AppProps) { return <Component {...pageProps} />; }\n');
await writeFile('pages/api/[...path].js','import handler from "../../api/desk.mjs";\nexport const config = { api: { bodyParser: { sizeLimit: "8kb" } } };\nexport default handler;\n');
await writeFile('next.config.mjs','const config = { poweredByHeader: false, reactStrictMode: true };\nexport default config;\n');
await writeFile('tsconfig.json',JSON.stringify({compilerOptions:{target:'ES2022',lib:['dom','dom.iterable','esnext'],allowJs:true,skipLibCheck:true,strict:true,noEmit:true,esModuleInterop:true,module:'esnext',moduleResolution:'bundler',resolveJsonModule:true,isolatedModules:true,jsx:'react-jsx',incremental:true,plugins:[{name:'next'}]},include:['next-env.d.ts','pages/**/*.ts','pages/**/*.tsx','.next/types/**/*.ts'],exclude:['node_modules']},null,2)+'\n');

// Reproducible local Next + PostgreSQL fixture checks. Not used by hosted requests.
await writeFile("tests/next-preload.mjs","// Local verification fixture only. Never configure this preload in a deployment.\nimport {PGlite} from '@electric-sql/pglite';\nimport fs from 'node:fs/promises';\nconst db=new PGlite();\nawait db.exec('CREATE ROLE anon; CREATE ROLE authenticated;');\nawait db.exec(await fs.readFile(new URL('../schema.postgres.sql',import.meta.url),'utf8'));\nconst original=globalThis.fetch;\nglobalThis.fetch=async(url,init)=>{\n if(String(url)==='https://localtest.supabase.co/rest/v1/rpc/roleproof_rpc'){\n  const {action,token_hash,payload}=JSON.parse(init.body);\n  const r=(await db.query('SELECT public.roleproof_rpc($1,$2,$3) r',[action,token_hash,JSON.stringify(payload)])).rows[0].r;\n  return new Response(JSON.stringify(r));\n }\n return original(url,init);\n};\n");
await writeFile("playwright.next.config.ts","import {defineConfig} from '@playwright/test';\nexport default defineConfig({testDir:'.',testMatch:'desk.spec.ts',workers:1,use:{baseURL:'http://127.0.0.1:8792',headless:true},webServer:{command:'ROLEPROOF_LOCAL_TEST=1 SUPABASE_URL=https://localtest.supabase.co SUPABASE_PUBLISHABLE_KEY=public-test-key node --import ./tests/next-preload.mjs node_modules/next/dist/bin/next start --hostname 127.0.0.1 --port 8792',url:'http://127.0.0.1:8792/api/health',reuseExistingServer:false,gracefulShutdown:{signal:'SIGTERM',timeout:5000}},reporter:[['list']]});\n");
