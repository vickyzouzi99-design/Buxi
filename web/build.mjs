import {build} from 'esbuild';
import {mkdir,copyFile,readFile,stat} from 'node:fs/promises';
import path from 'node:path';
const root=process.cwd();
// Explicit project-local resolution avoids scanning protected parent folders.
// This resolver only supports this project's JS/TS/CSS and installed npm files.
const localResolver={
 name:'project-local',
 setup(build){
  build.onResolve({filter:/.*/},async args=>{
   let file;
   if(args.path.startsWith('.')||path.isAbsolute(args.path)){
    file=path.resolve(args.resolveDir||root,args.path);
   }else{
    const parts=args.path.split('/');
    const name=args.path.startsWith('@')?parts.splice(0,2).join('/'):parts.shift();
    const dir=path.join(root,'node_modules',name);
    if(parts.length) file=path.join(dir,...parts);
    else {const pkg=JSON.parse(await readFile(path.join(dir,'package.json'),'utf8'));file=path.join(dir,pkg.main||'index.js');}
   }
   for(const candidate of [file,file+'.js',file+'.tsx',path.join(file,'index.js')]){
    try{if((await stat(candidate)).isFile())return {path:candidate,namespace:'local'};}catch{}
   }
   return {errors:[{text:'Cannot resolve '+args.path}]};
  });
  build.onLoad({filter:/.*/,namespace:'local'},async args=>({
   contents:await readFile(args.path,'utf8'),
   loader:args.path.endsWith('.css')?'css':args.path.endsWith('.tsx')?'tsx':'js',
   resolveDir:path.dirname(args.path)
  }));
 }
};
await mkdir('dist',{recursive:true});
await build({entryPoints:{main:'./src/main.tsx'},bundle:true,outdir:'dist',minify:true,jsx:'automatic',sourcemap:false,plugins:[localResolver],define:{'process.env.NODE_ENV':'"production"'}});
await copyFile('index.html','dist/index.html');
console.log('Buxi web built: dist/');

