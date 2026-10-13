import {build} from 'esbuild'
import assert from 'node:assert/strict'
await build({entryPoints:['src/export.ts'],bundle:true,platform:'node',format:'esm',outfile:'output/project-export.mjs'})
const {profileRows,glassRows,csv}=await import('../output/project-export.mjs')
const source={window_id:'window-a',window_name:'客厅窗',floor:'二楼',room:'客厅',unit:2,part_id:'frame-1'}
const rows=profileRows({groups:[{bars:[{id:'raw-1',stock_id:'stock',stock_key:'白色型材',length:12000000,pieces:[{instance:'unique',source,length:2000000,short_length:1800000,angle:45,from_tick:0,to_tick:2020000,front_loss:10000,back_loss:10000}]}]}]})
for(const value of ['客厅窗','二楼','客厅','window-a','白色型材'])assert.ok(csv(rows).includes(value))
const glass=glassRows({sheets:[{id:'g1',stock_id:'board',material:'磨砂',cuts:[{index:1,instance:'glass-a',source,axis:'x',at:2000,region:{x:0,y:0,w:4000,h:4000},kerf_rect:{w:20,h:4000}}]}]})
for(const value of ['客厅窗','磨砂','二楼','window-a'])assert.ok(csv(glass).includes(value))
const full=glassRows({sheets:[{id:'full-board',stock_id:'board',material:'透明',cuts:[],pieces:[{instance:'full-a',source,width:4000,height:4000,rect:{x:0,y:0,w:4000,h:4000}}]}]})
assert.ok(csv(full).includes('window-a'));assert.ok(csv(full).includes('无需切割'))
console.log('通过：型材和玻璃 CSV 保留材料、窗型编号、名称、楼层房间及实例来源')
