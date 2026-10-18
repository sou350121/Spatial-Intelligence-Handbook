// Compile complete page sources. Never strip metadata or mistake partial success for a healthy site.
import {createRequire} from 'node:module';
import {pathToFileURL} from 'node:url';
import {readdir,readFile} from 'node:fs/promises';
import path from 'node:path';
const prefix=process.env.PULSAR_MDX_PREFIX;
if(!prefix)throw new Error('PULSAR_MDX_PREFIX must point to the pinned validation dependencies');
const require=createRequire(path.resolve(prefix,'__resolve.cjs'));
const {compile}=await import(pathToFileURL(require.resolve('@mdx-js/mdx')).href);
const {default:math}=await import(pathToFileURL(require.resolve('remark-math')).href);
const {default:gfm}=await import(pathToFileURL(require.resolve('remark-gfm')).href);
function strictMathFences(){return tree=>{function visit(n){if(n.type==='math'&&n.meta?.trim())throw new Error('Display math delimiters must be on their own lines');for(const c of n.children||[])visit(c);}visit(tree);};}
const root=path.resolve(process.argv[2]||'.');
const zones=new Set(['benchmarks','bridge-to-vla','cheat-sheet','companies','crossing','deployment','embodiments','foundations','reports']);
const pages=new Set();
async function walk(dir){for(const e of await readdir(dir,{withFileTypes:true})){const p=path.join(dir,e.name);if(e.isDirectory())await walk(p);else if(e.name.endsWith('.md')&&e.name!=='README.md')pages.add(p);}}
for(const zone of zones)await walk(path.join(root,zone));
function nav(x){if(Array.isArray(x))for(const y of x)nav(y);else if(x&&typeof x==='object')for(const [key,value]of Object.entries(x)){if(key==='pages'&&Array.isArray(value))for(const p of value){if(typeof p==='string')pages.add(path.resolve(root,/\.mdx?$/.test(p)?p:p+'.md'));else nav(p);}else nav(value);}}
try{nav(JSON.parse(await readFile(path.join(root,'docs.json'),'utf8')).navigation);}catch(e){if(e.code!=='ENOENT')throw e;}
const errors=[];
for(const p of [...pages].sort()){
 if(!p.startsWith(root+path.sep))throw new Error('Navigation path escapes repository');
 try{
  let source;
  try{source=await readFile(p,'utf8');}
  catch(e){if(e.code==='ENOENT'&&p.endsWith('.md'))source=await readFile(p+'x','utf8');else throw e;}
  await compile(source,{remarkPlugins:[math,gfm,strictMathFences]});
 }
 catch(e){errors.push({path:path.relative(root,p).replaceAll('\\','/'),error:String(e.message)});}
}
console.log(JSON.stringify({ok:errors.length===0,pages:pages.size,errors},null,2));
if(errors.length)process.exitCode=1;
