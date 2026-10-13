<script setup lang="ts">
import GlassResults from "./GlassResults.vue"
import { ref, computed, watch, onUnmounted } from 'vue'
import { type FormInstance } from 'element-plus'
import { useWorkshop } from '../store'
import { clone, mm, T, money, areaM2 } from '../types'
import { csv, download } from '../export'
import { newId } from '../id'
import LengthInput from './LengthInput.vue'
const s=useWorkshop(),draft=ref(clone(s.project!.glass)),form=ref<FormInstance>()
watch(()=>s.project,p=>{if(p)draft.value=clone(p.glass)})
const dirty=computed(()=>JSON.stringify(draft.value)!==JSON.stringify(s.project!.glass))
watch(dirty,v=>{s.glassDraftDirty=v;if(v)s.invalidate()})
onUnmounted(()=>{s.glassDraftDirty=false})
const dimensionRule={validator:(_:unknown,v:number,done:(e?:Error)=>void)=>done(Number.isSafeInteger(v)&&v>0?undefined:new Error('请输入大于零的有效尺寸')),trigger:'blur'}
async function apply(){if(!await form.value?.validate().catch(()=>false)){document.querySelector('.glass-planner .is-error')?.scrollIntoView({block:'center',behavior:'smooth'});return false;}const p=clone(s.project!);p.glass=clone(draft.value);return s.commit(p)}
async function solve(){if(s.busy||s.glassSolving)return;if(dirty.value&&!await apply())return;await s.solveGlass()}
function exportPlan(){if(s.glassPlan&&!dirty.value)download(`${s.project!.name}-玻璃排版.json`,JSON.stringify({project:s.project,result:s.glassPlan},null,2))}
function exportCuts(){if(!s.glassPlan||dirty.value)return;download(`${s.project!.name}-玻璃逐刀.csv`,csv([['原板','规格','刀序','当前余料左Xmm','上Ymm','宽mm','高mm','方向','原板绝对坐标mm','刀缝mm','对应玻璃'],...s.glassPlan.sheets.flatMap(b=>b.cuts.map(c=>[b.id,b.stock_id,c.index,mm(c.region.x),mm(c.region.y),mm(c.region.w),mm(c.region.h),c.axis==='x'?'竖切':'横切',mm(c.at),mm(s.project!.glass.kerf),c.instance]))]),'text/csv;charset=utf-8')}
const printPlan=()=>window.print()
defineExpose({apply})
</script>
<template><div class="glass-planner">
<section class="panel no-print"><div class="panel-heading"><div><span class="eyebrow">GLASS CUTTING</span><h2>玻璃原板与二维切割</h2></div><el-tag>刀缝默认 0 mm</el-tag></div><p class="muted">同一玻璃材质、厚度的原板一起排版。默认规格仅为示例，请改为厂家的实际可切净尺寸；不同材质或厚度在项目中使用不同玻璃材料标识。</p>
<el-form ref="form" :model="draft" :disabled="s.busy" label-position="top"><div class="cut-settings"><el-form-item label="玻璃切割刀缝" prop="kerf" :rules="[{validator:(_:unknown,v:number,done:(e?:Error)=>void)=>done(Number.isSafeInteger(v)&&v>=0&&v<=20*T?undefined:new Error('刀缝需在 0～20 mm 之间'))}]"><LengthInput v-model="draft.kerf" label="玻璃切割刀缝"/></el-form-item><el-form-item label="玻璃优化目标"><el-select v-model="draft.objective"><el-option value="sheets" label="最少张数，其次最少采购面积"/><el-option value="cost" label="最低金额，其次最少张数"/></el-select></el-form-item><el-form-item label="允许玻璃旋转 90°"><el-switch v-model="draft.allow_rotate" active-text="允许" inactive-text="禁止"/></el-form-item></div>
<div class="glass-stock-grid"><article v-for="(row,index) in draft.stocks" :key="index" class="mobile-card"><div class="card-title"><b>玻璃原板 {{index+1}}</b><el-button text type="danger" @click="draft.stocks.splice(index,1)">删除原板</el-button></div><el-form-item label="规格编号" :prop="`stocks.${index}.id`" :rules="[{required:true,message:'请输入规格编号'}]"><el-input v-model="row.id" maxlength="80"/></el-form-item><div class="two-cols"><el-form-item label="原板宽度" :prop="`stocks.${index}.width`" :rules="[dimensionRule]"><LengthInput v-model="row.width" label="玻璃原板宽度"/></el-form-item><el-form-item label="原板高度" :prop="`stocks.${index}.height`" :rules="[dimensionRule]"><LengthInput v-model="row.height" label="玻璃原板高度"/></el-form-item><el-form-item label="单价 / 元"><el-input-number :model-value="row.price_cents/100" :min="0" :max="100000" :precision="2" :controls="false" @update:model-value="(v:number|undefined)=>row.price_cents=Math.round((v??0)*100)"/></el-form-item><el-form-item label="可用张数（空为不限）"><el-input-number v-model="row.available" :min="0" :max="500" :precision="0" :controls="false" @update:model-value="(v:number|undefined)=>row.available=v??null"/></el-form-item></div></article></div>
<el-button class="full-button" @click="draft.stocks.push({id:'玻璃-'+newId(),width:2440*T,height:1830*T,price_cents:0,available:null})">添加玻璃原板规格</el-button>

<div class="solve-action"><span v-if="s.glassSolving" role="status">正在计算玻璃方案，请稍候…</span><el-button :disabled="!dirty||s.busy" @click="apply">应用玻璃排料参数</el-button><el-button type="primary" :loading="s.glassSolving" :disabled="s.busy" @click="solve">计算玻璃采购与切割</el-button></div><el-alert v-if="dirty" title="玻璃排料参数尚未应用，旧方案已失效。请应用后保存或导出项目。" type="warning" :closable="false" class="full-button"/></el-form>
<p class="muted">贯通直切：每刀切穿当前余料，按图下方刀序加工。刀缝计入面积损耗；原板边缘不额外切割。多策略搜索可行方案，未达到下界时不宣称全局最优。</p></section>
<GlassResults v-if="s.glassPlan&&!dirty" :plan="s.glassPlan" :title="s.project!.name" :priced="s.project!.glass.stocks.filter(x=>x.available!==0).every(x=>x.supply==='inventory'||x.price_cents>0)"/></div></template>
