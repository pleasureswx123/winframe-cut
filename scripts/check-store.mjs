import { build } from 'esbuild'
await build({entryPoints:['src/store.ts'],bundle:true,platform:'node',format:'esm',packages:'external',outfile:'output/review-store.mjs'})
import assert from 'node:assert/strict'
import axios from 'axios'
import { createPinia,setActivePinia } from 'pinia'

const drafts=new Map()
globalThis.localStorage={setItem(k,v){drafts.set(k,v)},getItem(k){return drafts.get(k)??null},removeItem(k){drafts.delete(k)}}
let saveResolve,saveReject,glassResolve,sampleResolve,failCalculate=false
axios.defaults.adapter=async config=>{
 const data=JSON.parse(config.data||'{}')
 const response=value=>({data:value,status:200,statusText:'OK',headers:{},config})
 if(config.url==='/calculate'&&failCalculate)throw Error('尺寸校验失败')
 if(config.url==='/calculate')return response({regions:[{id:'root',kind:'glass'}]})
 if(config.url==='/windows')return new Promise((resolve,reject)=>{saveResolve=()=>resolve(response({id:'old-save'}));saveReject=()=>reject(Error('旧请求失败'))})
 if(config.url==='/windows/saved-a')return response({id:'saved-a',house_id:'house-a',floor:'一楼',room:'客厅',glass_material:'透明',project:{name:'服务器版本',root:{id:'root',kind:'glass',children:[]},profiles:{}},stocks:[],settings:{kerf:0}})
 if(config.url==='/validate')return response(data)
 if(config.url==='/sample')return new Promise(resolve=>{sampleResolve=()=>resolve(response({name:'迟到示例',root:{id:'root',kind:'glass',children:[]},profiles:Object.fromEntries(['window_frame','window_mullion','window_bead','sash_frame','sash_mullion','sash_bead'].map(k=>[k,{width:100,stock_key:k}]))}))})
 if(config.url==='/optimize-glass')return new Promise(resolve=>{glassResolve=()=>resolve(response({sheet_count:1}))})
 if(config.url==='/optimize')return response({bar_count:2})
 throw Error(config.url)
}
const { useWorkshop }=await import('../output/review-store.mjs')
setActivePinia(createPinia())
const s=useWorkshop(),p={name:'A',root:{id:'root',kind:'glass',children:[]},profiles:{}}
s.setUser('owner-a');s.context.house_id='house-a'
await s.commit(p)
const saving=s.save()
await s.commit({...p,name:'B'})
saveResolve();await saving
assert.equal(s.savedId,'old-save');assert.equal(s.project.name,'B');assert.equal(s.dirty,true)
s.savedId='B-id';await s.undo();assert.equal(s.savedId,'B-id');await s.redo();assert.equal(s.savedId,'B-id')
const glass=s.solveGlass();await s.solve();glassResolve();await glass
assert.equal(s.glassPlan.sheet_count,1);assert.equal(s.plan.bar_count,2)
const pending=s.solveGlass()
await new Promise(resolve=>setImmediate(resolve))
s.resetSession();glassResolve();await pending
assert.equal(s.project,null);assert.equal(s.glassPlan,null);assert.deepEqual(s.history,[])
s.setUser('owner-b');s.context.house_id='house-b';await s.commit({...p,name:'另一用户'})
assert.ok([...drafts.keys()].some(k=>k.includes('owner-a')))
assert.ok([...drafts.keys()].some(k=>k.includes('owner-b')))
assert.ok([...drafts.entries()].filter(([k])=>k.includes('owner-b')).every(([,v])=>!v.includes('house-a')))
s.setUser('owner-a');await s.openWindow('saved-a');await s.commit({...s.project,name:'未保存的草稿'})
s.resetSession();s.setUser('owner-a');await s.openWindow('saved-a')
assert.equal(s.project.name,'未保存的草稿');assert.equal(s.savedId,'saved-a');assert.equal(s.dirty,true)
s.savedId=null;const oldSave=s.save();await new Promise(resolve=>setImmediate(resolve));s.resetSession();s.setUser('owner-b');saveReject();await oldSave
assert.equal(s.error,'');assert.equal(s.project,null)
const sample=s.loadSample();await new Promise(resolve=>setImmediate(resolve));await s.openWindow('saved-a');sampleResolve();await sample
assert.equal(s.project.name,'服务器版本');assert.equal(s.savedId,'saved-a')
s.savedId=null;const switchedSave=s.save();await new Promise(resolve=>setImmediate(resolve));s.resetSession();s.setUser('new-owner');saveResolve();await switchedSave
assert.equal(s.savedId,null);assert.equal(s.project,null)
console.log('通过：存档响应隔离、撤销绑定、双排料、退出后迟到响应隔离及账号草稿隔离')

// 连续新增必须保留归属且与原窗型记录、撤销历史隔离。
s.setUser('flow-user');s.context={house_id:'flow-house',floor:'二层',room:'主卧',glass_material:'透明 5mm'}
await s.commit({...p,quantity:3,profiles:Object.fromEntries(['window_frame','window_mullion','window_bead','sash_frame','sash_mullion','sash_bead'].map(k=>[k,{width:100,stock_key:k}]))})
s.savedId='previous-window'
failCalculate=true
assert.equal(await s.createNextWindow(),false)
assert.equal(s.savedId,'previous-window');assert.equal(s.context.room,'主卧')
failCalculate=false
assert.equal(await s.createNextWindow(),true)
assert.equal(s.savedId,null);assert.equal(s.project.quantity,1);assert.equal(s.context.house_id,'flow-house');assert.equal(s.context.floor,'二层');assert.equal(s.context.glass_material,'透明 5mm');assert.equal(s.context.room,'');assert.deepEqual(s.history,[])
s.parameterDraftDirty=true;assert.equal(await s.save(),false);s.parameterDraftDirty=false
const failed=s.save();await new Promise(resolve=>setImmediate(resolve));saveReject();assert.equal(await failed,false);assert.equal(s.savedId,null)
const successful=s.save();await new Promise(resolve=>setImmediate(resolve));saveResolve();assert.equal(await successful,true);assert.equal(s.dirty,false)
await s.commit({...s.project,name:'未保存修改'});s.discardLocalDraft();assert.equal(drafts.has('winframe-workspace-v2:flow-user:old-save'),false)
console.log('通过：连续新增隔离、失败保留原窗、保存成功与失败结果、未应用参数拦截及放弃草稿')
// 旧存档缺少回收门槛时应补默认值，已有自定义值不能被重置。
s.resetSession();s.setUser('owner-a');await s.openWindow('saved-a')
assert.equal(s.settings.reusable_min,1000000)
s.settings.reusable_min=1600000;s.persist()
s.resetSession();s.setUser('owner-a');await s.openWindow('saved-a')
assert.equal(s.settings.reusable_min,1600000)
console.log('通过：旧存档回收门槛默认值及自定义门槛草稿恢复')
