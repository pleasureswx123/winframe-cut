import { build } from 'esbuild'
await build({entryPoints:['src/store.ts'],bundle:true,platform:'node',format:'esm',packages:'external',outfile:'output/review-store.mjs'})
import assert from 'node:assert/strict'
import axios from 'axios'
import { createPinia,setActivePinia } from 'pinia'

globalThis.localStorage={setItem(){},getItem(){return null}}
let saveResolve,glassResolve
axios.defaults.adapter=async config=>{
 const data=JSON.parse(config.data||'{}')
 const response=value=>({data:value,status:200,statusText:'OK',headers:{},config})
 if(config.url==='/calculate')return response({regions:[{id:'root',kind:'glass'}]})
 if(config.url==='/projects')return new Promise(resolve=>{saveResolve=()=>resolve(response({id:'old-save'}))})
 if(config.url==='/optimize-glass')return new Promise(resolve=>{glassResolve=()=>resolve(response({sheet_count:1}))})
 if(config.url==='/optimize')return response({bar_count:2})
 throw Error(config.url)
}
const { useWorkshop }=await import('../output/review-store.mjs')
setActivePinia(createPinia())
const s=useWorkshop(),p={name:'A',root:{id:'root',kind:'glass',children:[]},profiles:{}}
await s.commit(p)
const saving=s.save()
await s.commit({...p,name:'B'})
saveResolve();await saving
assert.equal(s.savedId,null)
s.savedId='B-id';await s.undo();assert.equal(s.savedId,null)
const glass=s.solveGlass();await s.solve();glassResolve();await glass
assert.equal(s.glassPlan.sheet_count,1);assert.equal(s.plan.bar_count,2)
console.log('通过：保存期间切换窗型不串档、撤销解除存档绑定、玻璃与型材并行计算保留两套结果')
