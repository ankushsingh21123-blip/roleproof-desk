// AI-assisted fixed-entry production build for the legacy React demo.
// No glob expansion, development server, or user-controlled build inputs.
import { build } from 'esbuild';
import { readFile, writeFile, mkdir, rm } from 'node:fs/promises';
const entry = '<script type="module" src="/main.tsx"></script>';
const html = await readFile('index.html', 'utf8');
if (html.split(entry).length !== 2) throw new Error('Expected exactly one reviewed legacy entrypoint.');
await rm('dist', { recursive: true, force: true });
await mkdir('dist/assets', { recursive: true });
await build({
  entryPoints: ['main.tsx'], outfile: 'dist/assets/desk.js', bundle: true,
  minify: true, sourcemap: false, format: 'esm', target: ['es2022'],
  jsx: 'automatic', define: { 'process.env.NODE_ENV': '"production"' },
  legalComments: 'linked', metafile: false,
});
await writeFile('dist/index.html', html.replace(entry,
  '<link rel="stylesheet" href="/assets/desk.css"/><script type="module" src="/assets/desk.js"></script>'));
for (const path of ['dist/index.html', 'dist/assets/desk.js', 'dist/assets/desk.css']) {
  if (!(await readFile(path)).length) throw new Error('Missing production asset: ' + path);
}
console.log('Built fixed-entry React demo with CSS and linked dependency licences.');
