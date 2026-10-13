import {houseInput,type House,type WindowRecord} from './business'
import {clone,type Node,type Category} from './types'
export type CuttingMode='profiles'|'glass'
// 只统计实际使用的构件型号，避免未使用的窗扇型号阻止计算。
export function requiredMaterials(windows:WindowRecord[]){
 const keys=new Set<string>(),materials=new Set<string>()
 for(const w of windows){
  keys.add(w.project.profiles.window_frame.stock_key)
  function visit(n:Node,context:'window'|'sash'){
   if(n.kind==='split')keys.add(w.project.profiles[`${context}_mullion` as Category].stock_key)
   if(n.kind==='glass'){keys.add(w.project.profiles[`${context}_bead` as Category].stock_key);materials.add(w.glass_material)}
   if(n.kind==='sash')keys.add(w.project.profiles.sash_frame.stock_key)
   n.children.forEach(c=>visit(c,n.kind==='sash'?'sash':context))
  }
  visit(w.project.root,'window')
 }
 return {keys:[...keys],materials:[...materials]}
}
export function missingConfiguration(h:House,windows:WindowRecord[],mode:CuttingMode){
 if(!windows.length)return '项目暂无已保存窗型，请先保存窗型。'
 const {keys,materials}=requiredMaterials(windows)
 if(mode==='profiles'){
  const missing=keys.filter(k=>!h.stocks.some(s=>s.stock_key===k&&s.available!==0))
  return missing.length?'以下型号缺少可用原料：'+missing.join('、')+'。请添加规格，或调整库存（留空表示可采购）。':''
 }
 if(!materials.length)return '项目没有需要排版的玻璃。'
 const missing=materials.filter(m=>!h.glass_groups[m]?.stocks.some(s=>s.available!==0))
 return missing.length?'以下玻璃材料缺少可用原板：'+missing.join('、')+'。请补充原板规格并核对库存。':''
}
// 保存当前页时保留另一页的服务器配置，未完成的本地输入仍留在页面内。
export function cuttingPayload(current:House,stored:ReturnType<typeof houseInput>,mode:CuttingMode){
 const payload=clone(stored)
 if(mode==='profiles'){payload.custom_profiles=current.custom_profiles??false;payload.stocks=clone(current.stocks);payload.settings=clone(current.settings)}
 else {payload.custom_glass=current.custom_glass??false;payload.glass_groups=clone(current.glass_groups)}
 return payload
}
