import {build} from 'esbuild'
import assert from 'node:assert/strict'
await build({entryPoints:['src/projectCutting.ts'],bundle:true,platform:'node',format:'esm',outfile:'output/check-project-cutting.mjs'})
const {requiredMaterials,missingConfiguration,cuttingPayload}=await import('../output/check-project-cutting.mjs')
const window={glass_material:'透明.5mm',project:{profiles:{window_frame:{stock_key:'框'},window_bead:{stock_key:'线'},sash_frame:{stock_key:'未使用'}},root:{kind:'glass',children:[]}}}
const house={customer_id:'c',name:'项目',address:'',layout:'',notes:'',stocks:[],settings:{kerf:0},glass_groups:{}}
assert.deepEqual(requiredMaterials([window]).keys,['框','线'])
assert.match(missingConfiguration(house,[window],'profiles'),/框、线/)
house.stocks=[{id:'a',stock_key:'框',available:null},{id:'b',stock_key:'线',available:0}]
assert.match(missingConfiguration(house,[window],'profiles'),/线/)
house.stocks[1].available=null
assert.equal(missingConfiguration(house,[window],'profiles'),'')
assert.match(missingConfiguration(house,[window],'glass'),/透明.5mm/)
house.glass_groups['透明.5mm']={stocks:[{id:'板',width:100,height:100,available:null}]}
assert.equal(missingConfiguration(house,[window],'glass'),'')
const stored=structuredClone(house),draft=structuredClone(house)
draft.stocks[0].id='';draft.glass_groups['透明.5mm'].stocks[0].width=200
const glass=cuttingPayload(draft,stored,'glass')
assert.equal(glass.stocks[0].id,'a');assert.equal(glass.glass_groups['透明.5mm'].stocks[0].width,200)
draft.glass_groups['透明.5mm'].stocks[0].width=null
const profiles=cuttingPayload(draft,stored,'profiles')
assert.equal(profiles.glass_groups['透明.5mm'].stocks[0].width,100)
assert.equal(draft.glass_groups['透明.5mm'].stocks[0].width,null)
assert.match(missingConfiguration(house,[],'profiles'),/暂无/)
console.log('通过：实际型号识别、缺料和零库存拦截、玻璃材料检查、分类型保存与本地草稿保留')

// 保存一种材料时，不能丢掉另一种材料已经保存的自定义标记。
stored.custom_profiles=true;stored.custom_glass=false
draft.custom_profiles=true;draft.custom_glass=true
assert.equal(cuttingPayload(draft,stored,'profiles').custom_glass,false)
assert.equal(cuttingPayload(draft,stored,'glass').custom_glass,true)
assert.equal(cuttingPayload(draft,stored,'glass').custom_profiles,true)
console.log('通过：项目自定义原料标记按型材/玻璃独立保存')
