<script setup lang="ts">
import {mm,money,areaM2,T,sourceLabel,type GlassPlan} from '../types'
import {download,csv,glassRows} from '../export'
const props=defineProps<{plan:GlassPlan;title:string;priced:boolean}>()
const printPlan=()=>window.print()
function exportCuts(){download(props.title+'-玻璃逐刀.csv',csv(glassRows(props.plan)),'text/csv;charset=utf-8')}
function largestRemnant(sheet:GlassPlan['sheets'][number]) {
  return sheet.remnants.reduce<(typeof sheet.remnants)[number] | undefined>((best, r) => !best || r.w*r.h > best.w*best.h ? r : best, undefined)
}
function exportPlan(){download(props.title+'-玻璃方案.json',JSON.stringify(props.plan,null,2))}
</script>
<template><section class="panel results-summary"><div class="panel-heading"><h2>玻璃采购与切割方案</h2><div class="action-row no-print"><el-button @click="exportCuts">逐刀 CSV</el-button><el-button @click="exportPlan">完整玻璃方案</el-button><el-button @click="printPlan">打印</el-button></div></div>
<el-alert :closable="false" :type="plan.primary_proven?'success':'warning'" :title="plan.primary_proven?'已达到扣除库存后的面积下界，采购张数已证明最少；余料布局仍为择优方案，不代表全局最优。':'当前为多策略搜索得到的可行方案，未证明全局最优。'"/>
<p class="muted">优先满足采购目标；同等采购方案下减少刀缝损耗，再优先保留完整的大块余料。下方浅色空白包含不同余料块，须以逐刀切割后的尺寸为准。</p>
<div class="plan-stats"><div><span>本次需采购</span><strong>{{plan.purchase_count}} <small>张</small></strong></div><div><span>采购金额</span><strong>{{(priced||plan.purchase_count===0)?'¥ '+money(plan.cost_cents):'未完整录价'}}</strong></div><div><span>面积利用率</span><strong>{{plan.total_stock_area?(100*plan.total_glass_area/plan.total_stock_area).toFixed(2):'0'}}%</strong></div><div><span>刀缝面积损耗</span><strong>{{areaM2(plan.loss_area)}} <small>m²</small></strong></div></div>
<p class="muted">共使用 {{plan.sheet_count}} 张玻璃，其中领用库存 {{plan.inventory_count}} 张，新采购 {{plan.purchase_count}} 张。</p>
<h3 v-if="plan.inventory_usage.length">已有库存使用计划（未扣减）</h3><el-table v-if="plan.inventory_usage.length" :data="plan.inventory_usage"><el-table-column prop="material" label="玻璃材料"/><el-table-column label="库存尺寸"><template #default="{row}">{{mm(row.width)}} × {{mm(row.height)}} mm</template></el-table-column><el-table-column prop="available" label="现有张数"/><el-table-column prop="count" label="本次使用"/><el-table-column prop="remaining" label="未领用张数"/></el-table>
<p v-if="!plan.purchase.length">本方案无需采购新玻璃。</p>
<div v-for="p in plan.purchase" :key="p.material+'/'+p.stock_id" class="glass-purchase">{{p.material}} {{p.stock_id}} · {{mm(p.width)}} × {{mm(p.height)}} mm <b>采购 {{p.count}} 张</b></div></section>
<section v-for="sheet in plan.sheets" :key="sheet.id" class="panel glass-sheet"><div class="panel-heading"><h3>{{sheet.id}} · {{sheet.supply==='inventory'?'已有库存':'需要采购'}} · {{sheet.stock_id}}</h3><span>{{mm(sheet.width)}} × {{mm(sheet.height)}} mm</span></div>
<svg class="glass-sheet-svg" :viewBox="`0 0 ${sheet.width/T} ${sheet.height/T}`" role="img" :aria-label="`${sheet.id} 玻璃切割排版`"><rect :width="sheet.width/T" :height="sheet.height/T" fill="#e9ede4"/><rect v-for="(c,i) in sheet.cuts" :key="'cut'+i" :x="c.kerf_rect.x/T" :y="c.kerf_rect.y/T" :width="c.kerf_rect.w/T" :height="c.kerf_rect.h/T" fill="#d8994c"/><g v-for="(p,i) in sheet.pieces" :key="p.instance"><rect :x="p.rect.x/T" :y="p.rect.y/T" :width="p.rect.w/T" :height="p.rect.h/T" fill="#b9dbe1" stroke="#4f838c" stroke-width="1" vector-effect="non-scaling-stroke"/><text :x="(p.rect.x+p.rect.w/2)/T" :y="(p.rect.y+p.rect.h/2)/T" text-anchor="middle" dominant-baseline="middle" :font-size="Math.min(sheet.width/T/40,p.rect.w/T/3,p.rect.h/T/3)" fill="#29545c">{{i+1}}</text></g></svg>
<div class="cut-sequence"><span v-for="(p,i) in sheet.pieces" :key="p.instance"><b>{{i+1}}</b>{{sourceLabel(p)}} · {{mm(p.width)}} × {{mm(p.height)}} mm{{p.rotated?' · 旋转90°':''}} · 左上 ({{mm(p.rect.x)}}, {{mm(p.rect.y)}})</span></div><p class="muted">玻璃 {{areaM2(sheet.glass_area)}} m² / 刀缝 {{areaM2(sheet.loss_area)}} m² / 余料 {{areaM2(sheet.remnant_area)}} m²</p>
<p v-if="largestRemnant(sheet)" class="muted">最大完整余料：<strong>{{mm(largestRemnant(sheet)!.w)}} × {{mm(largestRemnant(sheet)!.h)}} mm</strong>（{{areaM2(largestRemnant(sheet)!.w * largestRemnant(sheet)!.h)}} m²）</p>
<details><summary>逐刀顺序（原板左上角原点，坐标单位 mm）</summary><div class="glass-cut-table"><table class="plain-table"><thead><tr><th>刀序</th><th>当前余料：左上 / 宽×高</th><th>方向 / 原板坐标</th><th>刀缝</th></tr></thead><tbody><tr v-for="c in sheet.cuts" :key="c.index"><td>{{c.index}}<div class="source-label">{{sourceLabel(c)}}</div></td><td>({{mm(c.region.x)}}, {{mm(c.region.y)}}) / {{mm(c.region.w)}} × {{mm(c.region.h)}}</td><td>{{c.axis==='x'?'竖切 X':'横切 Y'}} = {{mm(c.at)}}</td><td>{{mm(c.axis==='x'?c.kerf_rect.w:c.kerf_rect.h)}}</td></tr></tbody></table></div></details>
</section></template>
