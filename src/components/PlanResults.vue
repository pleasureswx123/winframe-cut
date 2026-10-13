<script setup lang="ts">
import {mm,money,sourceLabel,type Plan} from '../types'
import {download,csv,profileRows} from '../export'
import {Download,Printer} from 'lucide-vue-next'
const props=defineProps<{plan:Plan;title:string;priced:boolean}>()
function proofText(){
 const target=props.plan.settings.objective==='cost'?'采购金额':'采购根数'
 if(props.plan.status==='OPTIMAL')return target+'及后续购料、余料目标均已证明最优（当前工艺与库存约束下）。'
 if(props.plan.primary_proven)return target+'已证明最少；后续购料或余料目标尚未全部证明最优。'
 return '当前为搜索得到的完整可行方案，尚未证明最优；可延长求解时限再次比较。'
}
const printPlan=()=>window.print()
function exportCuts(){download(props.title+'-型材切割.csv',csv(profileRows(props.plan)),'text/csv;charset=utf-8')}
function exportPlan(){download(props.title+'-型材方案.json',JSON.stringify(props.plan,null,2))}
</script>
<template>
<section id="profile-result" class="panel results-summary"><div class="panel-heading"><div><span class="eyebrow">CUTTING PLAN</span><h2>采购与切割方案</h2></div><div class="no-print action-row"><el-button @click="exportCuts"><Download :size="15"/>切割 CSV</el-button><el-button @click="exportPlan">完整方案</el-button><el-button @click="printPlan"><Printer :size="15"/>打印</el-button></div></div>
<el-alert :type="plan.primary_proven?'success':'warning'" :closable="false" :title="proofText()"/>
<div class="plan-stats"><div><span>本次需采购</span><strong>{{plan.purchase_count}} <small>根</small></strong></div><div><span>采购金额</span><strong>{{(priced||plan.purchase_count===0)?'¥ '+money(plan.cost_cents):'价格未完整录入'}}</strong></div><div><span>长度利用率</span><strong>{{(plan.total_parts/plan.total_stock*100).toFixed(2)}}<small>%</small></strong></div><div><span>剩余料长</span><strong>{{mm(plan.total_remnant)}} <small>mm</small></strong></div></div>
<div class="plan-stats"><div><span>可回收余料</span><strong>{{mm(plan.reusable_remnant)}} <small>mm</small></strong></div><div><span>短废料</span><strong>{{mm(plan.scrap_remnant)}} <small>mm</small></strong></div><div><span>最长余料</span><strong>{{mm(plan.largest_remnant)}} <small>mm</small></strong></div><div><span>回收长度门槛</span><strong>{{mm(plan.settings.reusable_min)}} <small>mm</small></strong></div></div>
<p class="muted">余料达到门槛可回收，不自动加入库存；短废料不含锯缝与端部修整损耗。</p>
<p class="muted">共使用 {{plan.bar_count}} 根原料，其中领用库存 {{plan.inventory_count}} 根，新采购 {{plan.purchase_count}} 根。</p>
<h3 v-if="plan.inventory_usage.length">已有库存使用计划（未扣减）</h3><el-table v-if="plan.inventory_usage.length" :data="plan.inventory_usage"><el-table-column prop="stock_key" label="型号"/><el-table-column label="库存料长"><template #default="{row}">{{mm(row.length)}} mm</template></el-table-column><el-table-column prop="available" label="现有根数"/><el-table-column prop="count" label="本次使用"/><el-table-column prop="remaining" label="未领用根数"/></el-table>
<h3>新料采购清单</h3><el-table :data="plan.purchase" empty-text="本方案无需采购新料" class="purchase-table"><el-table-column prop="stock_key" label="原料型号" min-width="120"/><el-table-column prop="stock_id" label="规格编号" min-width="120"/><el-table-column label="整料长度 / mm" min-width="130"><template #default="{row}">{{mm(row.length)}}</template></el-table-column><el-table-column prop="count" label="采购根数"/><el-table-column label="小计 / 元"><template #default="{row}">{{row.price_cents?money(row.cost_cents):'未录价'}}</template></el-table-column></el-table>
</section>
<section v-for="g in plan.groups" :key="g.stock_key" class="panel cut-group"><div class="panel-heading"><h3>{{g.stock_key}} <small>{{g.bars.length}} 根整料</small></h3><el-tag :type="g.primary_proven?'success':'warning'">{{g.status==='OPTIMAL'?'各阶段最优':g.primary_proven?'主目标最优':'可行方案'}}</el-tag></div>
<article v-for="(b,i) in g.bars" :key="b.id" class="bar-card"><div class="bar-caption"><strong>{{String(i+1).padStart(2,'0')}} <span>{{b.supply==='inventory'?'库存':'采购'}} · {{b.stock_id}} · {{mm(b.length)}} mm</span></strong><span>{{b.pieces.length}} 件 · 工艺损耗 {{mm(b.loss)}} · {{b.remnant===0?'无余料':b.reusable_remnant>0?'可回收余料':'短废料'}} {{mm(b.remnant)}} mm</span></div>
<div class="cut-bar-scroll"><svg class="cut-bar" viewBox="0 0 1000 42" preserveAspectRatio="none" role="img" :aria-label="`${b.id} 切割示意图`"><rect width="1000" height="42" fill="#e9e9e0"/><rect v-if="b.trim_start" :width="b.trim_start/b.length*1000" height="42" fill="#c68b47"/><g v-for="(p,j) in b.pieces" :key="p.instance"><rect :x="p.from_tick/b.length*1000" :width="(p.to_tick-p.from_tick)/b.length*1000" height="42" fill="#c68b47"/><rect :x="p.cut_start/b.length*1000" :width="p.length/b.length*1000" height="42" :fill="j%2?'#54796b':'#31594e'" stroke="white" stroke-width="1"/><text v-if="p.length/b.length>.035" :x="(p.cut_start+p.length/2)/b.length*1000" y="26" text-anchor="middle" fill="white" font-size="12">{{mm(p.length)}}</text></g><rect v-if="b.trim_end" :x="1000-b.trim_end/b.length*1000" :width="b.trim_end/b.length*1000" height="42" fill="#c68b47"/></svg></div>
<div class="cut-sequence"><span v-for="(p,j) in b.pieces" :key="p.instance"><b>{{j+1}}</b> {{sourceLabel(p)}} · {{mm(p.length)}} mm · {{p.angle}}°</span></div>
<details><summary>查看精确切割区间与锯缝</summary><table class="plain-table"><thead><tr><th>构件实例</th><th>长边／短边</th><th>轴向占用区间</th><th>前／后锯缝</th></tr></thead><tbody><tr v-for="p in b.pieces" :key="p.instance"><td>{{sourceLabel(p)}}</td><td>{{mm(p.length)}} / {{mm(p.short_length)}}</td><td>{{mm(p.from_tick)}}～{{mm(p.to_tick)}}</td><td>{{mm(p.front_loss)}} / {{mm(p.back_loss)}}</td></tr></tbody></table></details>
</article><p class="muted">绿色：构件长边包络；金色：锯缝及修整；浅灰色：余料。45° 构件按独立毛坯展示，区间不代表锯机靠尺设置。</p></section>
</template>
