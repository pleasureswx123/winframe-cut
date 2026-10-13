import {mm,type Plan,type GlassPlan,type Source} from './types'
const origin=(s?:Source)=>(s?[s.window_id,s.window_name,s.floor,s.room,s.unit,s.part_id]:['','','','','',''])
export function profileRows(plan:Plan):(string|number)[][]{return [['原料根号','型号','规格mm','次序','构件实例','窗型编号','窗型名称','楼层','房间','第几樘','原构件编号','长边mm','短边mm','角度','毛坯起mm','毛坯止mm','前锯缝mm','后锯缝mm','原料来源','原料规格编号'],...plan.groups.flatMap(g=>g.bars.flatMap(b=>b.pieces.map((p,i)=>[b.id,b.stock_key,mm(b.length),i+1,p.instance,...origin(p.source),mm(p.length),mm(p.short_length),p.angle,mm(p.from_tick),mm(p.to_tick),mm(p.front_loss),mm(p.back_loss),b.supply==='inventory'?'已有库存':'需要采购',b.stock_id])))]}
export function glassRows(plan:GlassPlan):(string|number)[][]{
 const rows:(string|number)[][]=[['原板','材料','规格','刀序','构件实例','窗型编号','窗型名称','楼层','房间','第几樘','原构件编号','余料左Xmm','上Ymm','宽mm','高mm','方向','坐标mm','刀缝mm','说明','原料来源']]
 for(const b of plan.sheets){
  for(const c of b.cuts)rows.push([b.id,b.material??'',b.stock_id,c.index,c.instance,...origin(c.source),mm(c.region.x),mm(c.region.y),mm(c.region.w),mm(c.region.h),c.axis,mm(c.at),mm(c.axis==='x'?c.kerf_rect.w:c.kerf_rect.h),'切割',b.supply==='inventory'?'已有库存':'需要采购'])
  const cutInstances=new Set(b.cuts.map(c=>c.instance))
  for(const p of b.pieces??[])if(!cutInstances.has(p.instance))rows.push([b.id,b.material??'',b.stock_id,'',p.instance,...origin(p.source),mm(p.rect.x),mm(p.rect.y),mm(p.rect.w),mm(p.rect.h),'','','','整块使用（无需切割）',b.supply==='inventory'?'已有库存':'需要采购'])
 }
 return rows
}
export function download(name:string,content:string,type='application/json'){
  const url=URL.createObjectURL(new Blob([content],{type}));const a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)
}
export function csv(rows:(string|number)[][]){
  return '\ufeff'+rows.map(row=>row.map(v=>{let text=String(v);if(/^[=+@\t\r]/.test(text)||(/^\-/.test(text)&&!/^\-\d+(\.\d+)?$/.test(text)))text="'"+text;return '"'+text.replaceAll('"','""')+'"'}).join(',')).join('\r\n')
}
