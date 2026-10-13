<script setup lang="ts">
import {ref,onMounted,computed,watch} from 'vue'
import {useRoute,onBeforeRouteLeave} from 'vue-router'
import {ElMessage,ElMessageBox,type FormInstance} from 'element-plus'
import {api,errorText} from '../api'
import {defaultSettings,houseInput,type House,type WindowRecord,type Page} from '../business'
import {clone,mm,money,type Stock,type GlassSettings,type Plan,type GlassPlan} from '../types'
import {requiredMaterials,missingConfiguration,cuttingPayload,type CuttingMode} from '../projectCutting'
import {Scissors,PanelsTopLeft,ChevronDown} from 'lucide-vue-next'

import ProjectStockEditor from '../components/ProjectStockEditor.vue'
import LengthInput from '../components/LengthInput.vue'
import PlanResults from '../components/PlanResults.vue'
import GlassResults from '../components/GlassResults.vue'
const route=useRoute(),house=ref<House|null>(null),windows=ref<WindowRecord[]>([]),error=ref(''),busy=ref(false),tab=ref<CuttingMode>('profiles'),plan=ref<Plan|null>(null),glassPlan=ref<GlassPlan|null>(null),form=ref<FormInstance>(),saved=ref('')
const sourceStocks=computed({get:()=>house.value?.stocks??[],set:(v:Stock[])=>{if(house.value)house.value.stocks=v}})
const sourceGlass=computed({get:()=>house.value?.glass_groups??{},set:(v:Record<string,GlassSettings>)=>{if(house.value)house.value.glass_groups=v}})
const sourceErrors=ref({profiles:'',glass:''})
const profileKeys=computed(()=>[...new Set([...requiredMaterials(windows.value).keys,...sourceStocks.value.map(s=>s.stock_key)])])
const materialError=computed(()=>house.value?.[tab.value==='profiles'?'custom_profiles':'custom_glass']?'':sourceErrors.value[tab.value])
function changed(){if(house.value)house.value[tab.value==='profiles'?'custom_profiles':'custom_glass']=true}
const loading=ref(true)
const blocker=computed(()=>loading.value?'正在加载项目窗型…':materialError.value||(house.value?missingConfiguration({...house.value,stocks:sourceStocks.value,glass_groups:sourceGlass.value},windows.value,tab.value):'项目未加载'))

const dirty=computed(()=>!!house.value&&JSON.stringify(houseInput(house.value))!==saved.value)
watch(house,()=>{plan.value=null;glassPlan.value=null},{deep:true,flush:'sync'})


async function loadSources(){
 loading.value=true;error.value='';plan.value=null;glassPlan.value=null
 try{
  const {data}=await api.get<{windows:WindowRecord[];profiles:{data:Stock[];error:string};glass:{data:Record<string,GlassSettings>;error:string}}>('/houses/'+route.params.id+'/cutting-sources')
  windows.value=data.windows;if(!house.value!.custom_profiles)sourceStocks.value=clone(data.profiles.data);if(!house.value!.custom_glass)sourceGlass.value=clone(data.glass.data);else for(const [m,cfg] of Object.entries(data.glass.data))if(!sourceGlass.value[m])sourceGlass.value[m]=clone(cfg);sourceErrors.value={profiles:data.profiles.error,glass:data.glass.error}
 }catch(e){error.value=errorText(e);sourceErrors.value={profiles:'窗型原料读取失败，请刷新重试',glass:'窗型原料读取失败，请刷新重试'}}finally{loading.value=false}
}
onMounted(async()=>{try{house.value=(await api.get('/houses/'+route.params.id)).data;house.value!.settings={...defaultSettings(),...house.value!.settings};await loadSources();saved.value=JSON.stringify(houseInput(house.value!))}catch(e){error.value=errorText(e);loading.value=false}})
onBeforeRouteLeave(async()=>{if(!dirty.value)return true;try{await ElMessageBox.confirm('项目原料配置尚未保存，确认离开？','未保存配置');return true}catch{return false}})
async function save(){
 if(!house.value||!await form.value?.validate().catch(()=>false)){ElMessage.warning('请检查当前页标出的原料参数');return false}
 const payload=cuttingPayload(house.value,JSON.parse(saved.value),tab.value)
 await api.put('/houses/'+house.value.id,payload);saved.value=JSON.stringify(payload);return true
}
async function saveOnly(){if(busy.value||loading.value)return;busy.value=true;error.value='';try{if(await save())ElMessage.success('项目原料配置已保存')}catch(e){error.value=errorText(e)}finally{busy.value=false}}
async function solve(){if(!house.value||busy.value)return;if(blocker.value){ElMessage.warning(blocker.value);return}busy.value=true;error.value='';const mode=tab.value;if(mode==='profiles')plan.value=null;else glassPlan.value=null;try{if(!await save())return;const {data}=await api.post(`/houses/${house.value.id}/${mode==='profiles'?'optimize':'optimize-glass'}`);if(mode==='profiles')plan.value=data;else glassPlan.value=data}catch(e){error.value=errorText(e)}finally{busy.value=false}}
</script>
<template><main class="platform-page"><el-alert v-if="error" :title="error" type="error" :closable="false"/><template v-if="house"><div class="page-heading no-print"><div><router-link :to="'/houses/'+house.id">← 项目窗型</router-link><h1>{{house.name}} · 统一排料</h1><p class="muted">将全部已保存窗型乘以制作数量后统一安排材料。浏览器内未保存的修改不参与本次计算。</p></div><el-button :disabled="busy" :loading="loading" @click="loadSources">刷新窗型数据</el-button></div><details class="panel project-window-roster no-print"><summary><span class="roster-heading"><span class="roster-icon"><PanelsTopLeft :size="20"/></span><span><strong>参与排料窗型</strong><small>全部已保存窗型参与本次计算</small></span></span><span class="roster-totals"><span><b>{{windows.length}}</b> 种窗型</span><span>共 <b>{{windows.reduce((n,w)=>n+w.project.quantity,0)}}</b> 樘</span></span><span class="roster-toggle"><span class="roster-expand">查看明细</span><span class="roster-collapse">收起明细</span><ChevronDown :size="16"/></span></summary><div class="roster-content"><p v-if="loading" class="roster-empty">正在加载窗型…</p><p v-else-if="!windows.length" class="roster-empty">暂无已保存窗型，请先在项目中添加并保存。</p><template v-else><div class="roster-columns" aria-hidden="true"><span>窗型名称</span><span>楼层 / 安装位置</span><span>整窗尺寸（mm）</span><span>制作数量</span><span>玻璃材料</span></div><ul class="roster-list"><li v-for="w in windows" :key="w.id"><strong class="roster-name">{{w.name}}</strong><span data-label="安装位置">{{w.floor||'未标楼层'}} / {{w.room||'未标位置'}}</span><span data-label="尺寸（mm）" class="roster-size">{{mm(w.project.width)}} × {{mm(w.project.height)}}<small class="roster-mobile-unit"> mm</small></span><span data-label="制作数量"><b class="roster-quantity">{{w.project.quantity}} 樘</b></span><span data-label="玻璃材料">{{w.glass_material}}</span></li></ul></template></div></details><div class="project-mode-bar no-print"><el-tabs v-model="tab" class="project-mode-tabs" aria-label="项目排料类型"><el-tab-pane label="型材排料" name="profiles" :disabled="busy"><template #label><Scissors :size="17" aria-hidden="true"/><span>型材排料</span></template></el-tab-pane><el-tab-pane label="玻璃排版" name="glass" :disabled="busy"><template #label><PanelsTopLeft :size="17" aria-hidden="true"/><span>玻璃排版</span></template></el-tab-pane></el-tabs><span class="project-mode-description">{{tab==='profiles'?'按型号合并构件，统一安排整料切割':'按玻璃材料分组，统一安排原板排版'}}</span></div><el-alert v-if="blocker" :title="blocker" type="warning" show-icon :closable="false" class="project-readiness"/><el-form :key="tab" ref="form" :model="house" :disabled="busy" label-position="top" class="no-print">
<section v-if="tab==='profiles'" class="panel"><div class="panel-heading"><h2>项目型材原料</h2><el-tag effect="plain">共享库存 · 不重复累加</el-tag></div><p class="muted">首次从窗型汇总；在这里添加或编辑后保存为项目配置。已有库存需填写实际数量，不计本次采购费用；试算不会扣减库存。</p><ProjectStockEditor v-model="sourceStocks" mode="profiles" :keys="profileKeys" @change="changed"/><h3 class="source-settings-title">项目切割规则</h3><div class="cut-settings"><el-form-item label="刀片厚度 mm"><LengthInput v-model="house.settings.kerf" label="刀片厚度"/></el-form-item><el-form-item label="头部修整 mm"><LengthInput v-model="house.settings.trim_start" label="头部修整"/></el-form-item><el-form-item label="尾部修整 mm"><LengthInput v-model="house.settings.trim_end" label="尾部修整"/></el-form-item><el-form-item label="优化目标"><el-select v-model="house.settings.objective"><el-option value="bars" label="最少根数，其次最少购料长度"/><el-option value="cost" label="最低采购金额，其次最少根数"/></el-select></el-form-item><el-form-item label="可回收余料最短长度"><LengthInput v-model="house.settings.reusable_min" label="可回收余料最短长度"/></el-form-item><el-form-item label="每种型号时限"><el-select v-model="house.settings.time_limit"><el-option v-for="n in [3,10,30]" :key="n" :value="n" :label="n+' 秒'"/></el-select></el-form-item></div></section>
<section v-if="tab==='glass'" class="panel"><h2>项目玻璃原料</h2><p class="muted">首次按材料汇总窗型原板，可添加相同规格、厚度和颜色的库存余料。填写无破损的可用矩形尺寸；项目内共享数量，试算不扣库存。</p><article v-for="(cfg,material) in sourceGlass" :key="material" class="project-stock-card"><h3>{{material}}</h3><p class="muted">刀缝 {{mm(cfg.kerf)}} mm · {{cfg.allow_rotate?'允许旋转 90°':'不允许旋转'}} · {{cfg.objective==='sheets'?'最少张数':'最低金额'}}</p><ProjectStockEditor v-model="cfg.stocks" mode="glass" :material="String(material)" @change="changed"/></article></section><div class="solve-action"><el-button :loading="busy" @click="saveOnly">保存原料配置</el-button><el-button type="primary" :loading="busy" :disabled="busy||!!blocker" @click="solve">{{tab==='profiles'?'保存并计算全部型材':'保存并计算全部玻璃'}}</el-button></div></el-form><PlanResults v-if="tab==='profiles'&&plan" :plan="plan" :title="house.name" :priced="sourceStocks.every(s=>s.supply==='inventory'||s.price_cents>0)"/><GlassResults v-if="tab==='glass'&&glassPlan" :plan="glassPlan" :title="house.name" :priced="Object.values(sourceGlass).every(g=>g.stocks.every(s=>s.supply==='inventory'||s.price_cents>0))"/></template></main></template>
