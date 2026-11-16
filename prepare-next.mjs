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
