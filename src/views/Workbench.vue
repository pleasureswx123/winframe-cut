<script setup lang="ts">
import {nameMode,locationName} from '../windowNaming'
import { newId } from "../id"
import { ref, computed, watch, nextTick } from 'vue'
import { useRoute, useRouter, onBeforeRouteUpdate, onBeforeRouteLeave } from 'vue-router'
import { ElMessageBox, ElMessage, type FormInstance } from 'element-plus'
import { PanelsTopLeft, MousePointer2, Columns2, Rows2, Undo2, Redo2, Save, FolderOpen, Download, Upload, ChevronRight, ArrowUpRight, Maximize, Settings2, Layers, Scissors, House, MapPin, Building2, ArchiveRestore, Plus } from 'lucide-vue-next'
import { useWorkshop } from '../store'
import { api, errorText } from '../api'
import type { Customer, House as HouseRecord } from '../business'
import { clone, categories, labels, mm, T, walk, type Project, type Node, type Region } from '../types'
import { download } from '../export'
import LengthInput from '../components/LengthInput.vue'
import WindowCanvas from '../components/WindowCanvas.vue'
import PartsTable from '../components/PartsTable.vue'
import CutPlanner from '../components/CutPlanner.vue'
import QuickProject from '../components/QuickProject.vue'
const s=useWorkshop(),route=useRoute(),router=useRouter()
const target=(path:string)=>({path,query:s.savedId?{windowId:s.savedId}:{houseId:s.context.house_id}})
watch(()=>s.savedId,id=>{if(!leaveDialog.value&&!actionBusy.value&&s.project&&route.params.tab&&route.query.windowId!==(id??undefined))void router.replace(target(route.path))})
const ownerCustomer=ref<Customer|null>(null),ownerHouse=ref<HouseRecord|null>(null),ownerLoading=ref(false)
const ownerLabel=computed(()=>ownerCustomer.value&&ownerHouse.value?ownerCustomer.value.name+' / '+ownerHouse.value.name:'')
watch(()=>s.context.house_id,async(id,_,onCleanup)=>{
 let active=true;onCleanup(()=>{active=false})
 ownerCustomer.value=null;ownerHouse.value=null;ownerLoading.value=!!id
 if(!id)return
 try{
  const {data:house}=await api.get<HouseRecord>('/houses/'+id)
  const {data:customer}=await api.get<Customer>('/customers/'+house.customer_id)
  if(active){ownerHouse.value=house;ownerCustomer.value=customer}
 }catch{}finally{if(active)ownerLoading.value=false}
},{immediate:true})
const mobilePanel=ref('canvas')
watch(mobilePanel,async()=>{
  await nextTick()
  if(window.matchMedia('(max-width:760px)').matches)document.querySelector('.design-layout')?.scrollIntoView({block:'start'})
})
const tab=computed(()=>String(route.params.tab??'design'))
const draft=ref<Project|null>(null),form=ref<FormInstance>(),resizeMode=ref('absolute'),advanced=ref<string[]>([])
const dialog=ref(false),splitForm=ref<FormInstance>(),splitDraft=ref({id:'',axis:'x' as 'x'|'y',position:0,editing:false})
const library=ref(false),saved=ref<{id:string;name:string;updated:string}[]>([]),file=ref<HTMLInputElement>()
watch(()=>s.project,p=>{draft.value=p?clone(p):null},{immediate:true})
const draftDirty=computed(()=>!!draft.value&&JSON.stringify(draft.value)!==JSON.stringify(s.project))
const namingForm=ref<FormInstance>()
const customName=computed(()=>!!s.project&&nameMode(s.project)==='custom')
function syncName(){if(s.project&&!customName.value){s.project.name_mode='auto';s.project.name=locationName(s.context.floor,s.context.room);if(draft.value){draft.value.name=s.project.name;draft.value.name_mode='auto'}s.persist()}}
function toggleName(value:string|number|boolean){if(!s.project)return;s.project.name_mode=value?'custom':'auto';syncName();s.persist()}
watch(()=>[s.context.floor,s.context.room,s.project?.name_mode],()=>syncName(),{immediate:true})
watch(()=>[s.project?.name,s.project?.name_mode],()=>{if(draft.value&&s.project){draft.value.name=s.project.name;draft.value.name_mode=s.project.name_mode}},{flush:'sync'})
watch(draftDirty,value=>{s.parameterDraftDirty=value})
const cutEditor=ref<InstanceType<typeof CutPlanner>>(),actionBusy=ref(false),leaveDialog=ref(false),leaveError=ref(''),leaveIntent=ref<'leave'|'new'>('leave')
let resolveLeave:((value:boolean)=>void)|undefined
const hasChanges=computed(()=>s.dirty||draftDirty.value||s.glassDraftDirty)
async function saveCurrent(){
 if(!await namingForm.value?.validate().catch(()=>false))return false
 if(draftDirty.value&&!await applyParameters())return false
 if(s.glassDraftDirty&&!await cutEditor.value?.applyPending())return false
 await nextTick()
 const ok=await s.save()
 if(ok)ElMessage.success('窗型已保存')
 else ElMessage.error(s.error||'保存期间内容发生变化，请再次保存')
 return ok
}
function finishLeave(value:boolean){leaveDialog.value=false;resolveLeave?.(value);resolveLeave=undefined}
async function saveAndLeave(){
 actionBusy.value=true;leaveError.value=''
 try{if(await saveCurrent())finishLeave(true);else leaveError.value=s.error||'保存未完成，请继续编辑并检查参数。'}finally{actionBusy.value=false}
}
function discardAndLeave(){s.discardLocalDraft();finishLeave(true)}
function confirmLeave(intent:'leave'|'new'='leave'){
 leaveIntent.value=intent
 if(s.busy||s.saving||actionBusy.value){ElMessage.warning('请等待当前操作完成');return Promise.resolve(false)}
 if(!hasChanges.value)return Promise.resolve(true)
 if(resolveLeave)return Promise.resolve(false)
 leaveError.value='';leaveDialog.value=true;return new Promise<boolean>(resolve=>{resolveLeave=resolve})
}
onBeforeRouteLeave(()=>!s.userId||!s.project?true:confirmLeave())
async function addWindow(){
 if(actionBusy.value||s.busy||s.saving)return
 if(!await confirmLeave('new'))return
 actionBusy.value=true
 try{if(await s.createNextWindow()){await nextTick();await router.replace(target('/design'));mobilePanel.value='parameters';await nextTick();form.value?.clearValidate();document.querySelector<HTMLInputElement>('.parameter-panel input')?.focus();ElMessage.success('已新增窗型，请填写名称和安装位置')}}finally{actionBusy.value=false}
}

function canEdit(){if(draftDirty.value){mobilePanel.value='parameters';ElMessage.warning('请先应用尺寸参数，再修改窗型结构');return false}return !s.busy}
async function showParameterError(){
  mobilePanel.value='parameters'
  advanced.value=['glass','widths','profiles']
  await nextTick()
  const field=document.querySelector<HTMLElement>('.parameter-panel .is-error, .parameter-panel .invalid-input')
  field?.scrollIntoView({block:'center',behavior:'smooth'})
  field?.querySelector<HTMLInputElement>('input')?.focus({preventScroll:true})
}
function discardParameters(){
  if(!s.project||s.busy)return
  draft.value=clone(s.project)
  form.value?.clearValidate()
}
const activityTone=computed(()=>s.busy||s.saving||s.solving||s.glassSolving?'processing':hasChanges.value?'warning':s.savedId?'saved':'neutral')
const activity=computed(()=>s.busy?'正在更新尺寸…':s.saving?'正在保存窗型…':s.solving||s.glassSolving?'正在计算切割方案…':draftDirty.value||s.glassDraftDirty?'有参数待应用':s.dirty?'有未保存修改':s.savedAt?'窗型已保存 · '+s.savedAt:'当前工作区 · 可导出项目备份')
onBeforeRouteUpdate(async()=>{
  if(actionBusy.value||s.saving)return true
  if(s.glassDraftDirty){ElMessage.warning('请先应用玻璃排料参数，再切换页面');return false}
  if(!draftDirty.value)return true
  try{await ElMessageBox.confirm('尺寸参数尚未应用。请先应用并通过尺寸校验，再切换页面。','参数尚未应用',{confirmButtonText:'应用并继续',cancelButtonText:'留在当前页'});return await applyParameters()}
  catch{return false}
})
const rules={name:[{required:true,message:'请输入项目名称',trigger:'blur'}],width:[{validator:(_:unknown,v:number,done:(e?:Error)=>void)=>done(Number.isFinite(v)&&v>0?undefined:new Error('请输入有效宽度')),trigger:'blur'}],height:[{validator:(_:unknown,v:number,done:(e?:Error)=>void)=>done(Number.isFinite(v)&&v>0?undefined:new Error('请输入有效高度')),trigger:'blur'}]}
const currentNode=computed(()=>s.project?walk(s.project.root,s.selected):undefined)
const selectedSplit=computed(()=>s.geometry?.splits.find(x=>x.id===s.selected))
const parentSash=computed(()=>{
  function find(n:Node,parent:Node|null):Node|null{if(n.id===s.selected)return parent;for(const c of n.children){const v=find(c,n.kind==='sash'?n:parent);if(v)return v}return null}
  return s.project?find(s.project.root,null):null
})
const pendingRegion=computed(()=>s.geometry?.regions.find(x=>x.id===splitDraft.value.id))
const pendingEnds=computed(()=>{
  const r=pendingRegion.value?.rect;if(!r)return ''
  const p=splitDraft.value.position
  return splitDraft.value.axis==='x'?`(${mm(p)}, ${mm(r.y)}) → (${mm(p)}, ${mm(r.y+r.h)})`:`(${mm(r.x)}, ${mm(p)}) → (${mm(r.x+r.w)}, ${mm(p)})`
})
async function applyParameters(){
  if(!draft.value||!s.project||s.busy)return false
  if(!await form.value?.validate().catch(()=>false)){await showParameterError();return false}
  const next=clone(draft.value),old=s.project
  if(resizeMode.value==='proportional'){
    function resize(n:Node){if(n.kind==='split'&&n.position!=null)n.position=Math.round(n.position*(n.axis==='x'?next.width/old!.width:next.height/old!.height)/2)*2;n.children.forEach(resize)}
    resize(next.root)
  }
  const ok=await s.commit(next)
  if(ok)mobilePanel.value='canvas'
  if(ok)ElMessage.success('尺寸已更新，全部构件已重新计算')
  return ok
}
function draw(id:string,axis:'x'|'y',position:number){if(!canEdit())return;splitDraft.value={id,axis,position,editing:false};dialog.value=true}
function editSplit(id:string){if(!canEdit())return;const split=s.geometry?.splits.find(x=>x.id===id);if(!split)return;s.selected=id;splitDraft.value={id,axis:split.axis,position:split.position,editing:true};dialog.value=true}
function addSplit(axis:'x'|'y'){
  const r=s.region;if(!r)return
  draw(r.id,axis,Math.round((axis==='x'?r.rect.x+r.rect.w/2:r.rect.y+r.rect.h/2)/2)*2)
}
async function confirmSplit(){
  if(!await splitForm.value?.validate().catch(()=>false))return
  const {id,axis,position,editing}=splitDraft.value
  if(!Number.isSafeInteger(position)){ElMessage.error('请输入有效的精确坐标');return}
  const success=await s.changeNode(id,n=>{
    n.kind='split';n.axis=axis;n.position=position
    if(!editing){const uid=newId();n.children=[{id:`r-${uid}-a`,kind:'glass',children:[]},{id:`r-${uid}-b`,kind:'glass',children:[]}]}
  })
  if(success){dialog.value=false;s.tool='select'}
}
async function setKind(kind:'glass'|'empty'|'sash'){
  if(!currentNode.value||!canEdit())return
  if(currentNode.value.children.length){try{await ElMessageBox.confirm('这会移除所选区域内的中挺、窗扇和压线，并按新用途重新生成。可通过撤销恢复。','替换区域结构',{confirmButtonText:'替换',cancelButtonText:'取消',type:'warning'})}catch{return}}
  await s.changeNode(s.selected,n=>{n.kind=kind;n.axis=null;n.position=null;n.children=kind==='sash'?[{id:'s-'+newId(),kind:'glass',children:[]}]:[]})
}
async function reset(mode:'sample'|'blank'){
  try{await ElMessageBox.confirm('当前窗型会被替换，可以通过撤销恢复。','切换窗型',{confirmButtonText:'继续',cancelButtonText:'取消'});if(mode==='sample')await s.loadSample();else await s.blank()}catch(e){if(e!=='cancel'&&e!=='close')s.error=errorText(e)}
}
async function openLibrary(){await router.push('/houses/'+s.context.house_id)}
async function loadSaved(id:string){await router.push({path:'/design',query:{windowId:id}})}
async function importLegacy(){const token=s.workspaceToken();try{await ElMessageBox.confirm('仅在确认这份本机旧草稿属于你时导入。将作为当前项目的新窗型保存。','导入旧草稿');const raw=localStorage.getItem('winframe-workspace-v1');if(!raw)throw Error('没有本机旧草稿');await s.applyImport(JSON.parse(raw),token)}catch(e){if(token===s.workspaceToken()&&e!=='cancel'&&e!=='close')s.error=errorText(e)}}
function exportProject(){download(`${s.project!.name}.winframe.json`,JSON.stringify({project:s.project,stocks:s.stocks,settings:s.settings},null,2))}
async function importProject(event:Event){
  const input=event.target as HTMLInputElement,f=input.files?.[0];if(!f)return
  const token=s.workspaceToken()
  try{
    if(f.size>2_000_000)throw new Error('项目文件不能超过 2 MB')
    const value=JSON.parse(await f.text())
    if(await s.applyImport(value,token))ElMessage.success('项目已导入')
  }catch(e){if(token===s.workspaceToken())s.error=errorText(e)}finally{input.value=''}
}
const regionLabel=(r:Region)=>`${r.id} · ${r.kind==='split'?'中挺分区':r.kind==='sash'?'窗扇':r.kind==='empty'?'留空':'玻璃'}`
</script>
<template>
<div class="app-shell">
<el-dialog v-model="leaveDialog" :title="leaveIntent==='new'?'是否保存当前窗型后新建？':'保存当前窗型后继续？'" width="480px" :close-on-click-modal="false" :close-on-press-escape="!actionBusy" :show-close="!actionBusy" @closed="finishLeave(false)"><p>当前窗型有未保存修改。保存后，可在项目中继续查看和排料。</p><el-alert v-if="leaveError" :title="leaveError" type="error" :closable="false"/><template #footer><el-button :disabled="actionBusy" @click="finishLeave(false)">{{leaveIntent==='new'?'取消':'继续编辑'}}</el-button><el-button :disabled="actionBusy" @click="discardAndLeave">{{leaveIntent==='new'?'不保存并新建':'不保存离开'}}</el-button><el-button type="primary" :loading="actionBusy" @click="saveAndLeave">{{leaveIntent==='new'?'保存并新建':'保存并离开'}}</el-button></template></el-dialog>
<header class="app-header workbench-toolbar no-print">
<div class="workbench-identity"><div class="workbench-context-summary"><span class="workbench-label" :title="ownerLabel">{{ownerLabel||(ownerLoading?'正在加载归属…':'窗型工作台')}}</span><span class="workbench-name" :title="s.project?.name">{{s.project?.name || '未命名窗型'}}</span></div></div>
<nav aria-label="窗型工作流程"><router-link :to="target('/design')"><Maximize :size="16"/>窗型设计</router-link><router-link :to="target('/materials')"><Layers :size="16"/>构件清单</router-link><router-link :to="target('/cutting')"><Scissors :size="16"/>切割排料</router-link></nav>
<div class="header-right"><el-button :title="ownerHouse?'查看'+ownerHouse.name+'的全部窗型':'查看当前项目的全部窗型'" @click="openLibrary"><FolderOpen :size="16"/>项目窗型</el-button></div>
</header>
<main v-if="s.project&&draft&&s.geometry" class="main-layout" :class="{'wide-layout':tab!=='design'}">
<div class="page-intro no-print"><div><nav class="ownership-breadcrumb" aria-label="当前窗型归属"><template v-if="ownerCustomer&&ownerHouse"><router-link :to="'/customers/'+ownerCustomer.id+'/houses'"><small>客户</small>{{ownerCustomer.name}}</router-link><ChevronRight :size="13"/><router-link :to="'/houses/'+ownerHouse.id"><small>项目</small>{{ownerHouse.name}}</router-link><ChevronRight :size="13"/></template><span v-else class="ownership-pending">{{ownerLoading?'正在加载所属客户与项目…':'所属客户与项目暂不可用'}}</span><span aria-current="page"><small>窗型</small>{{s.project.name}}</span></nav><h1>{{tab==='design'?'窗型设计':tab==='materials'?'构件清单':'切割排料'}}</h1><p>{{s.project.name}} <span>／ {{mm(s.project.width)}} × {{mm(s.project.height)}} mm · {{s.project.quantity}} 樘</span></p></div><div class="intro-actions"><el-button @click="file?.click()"><Upload :size="15"/>导入</el-button><el-button :disabled="draftDirty||s.glassDraftDirty||s.busy" @click="exportProject"><Download :size="15"/>导出项目</el-button></div></div>
<div class="window-action-bar no-print"><span class="save-state" :class="'save-state--'+activityTone" role="status" aria-live="polite">{{activity}}</span><div><el-button :disabled="s.busy||s.saving||actionBusy" @click="addWindow()"><Plus :size="16"/>新增窗型</el-button><el-button type="primary" :loading="s.saving" :disabled="s.busy||actionBusy" @click="saveCurrent"><Save :size="15"/>{{!hasChanges&&s.savedId?'已保存':'保存窗型'}}</el-button></div></div>
<div class="workflow-bar no-print"><div class="workflow-links"><router-link :to="target('/design')"><b>1</b> 设计窗型</router-link><ChevronRight :size="14"/><router-link :to="target('/materials')"><b>2</b> 核对清单</router-link><ChevronRight :size="14"/><router-link :to="target('/cutting')"><b>3</b> 计算排料</router-link></div></div>
<section class="panel window-context no-print" aria-label="窗型信息">
<div class="window-context-heading"><div class="window-context-title"><span class="window-context-icon"><House :size="19"/></span><div><h2>窗型归属与安装信息</h2><router-link class="window-context-owner" :to="'/houses/'+s.context.house_id">{{ownerLabel||'返回所属房屋项目'}}<ChevronRight :size="13"/></router-link></div></div><span class="window-context-caption">用于项目管理与下料追溯</span></div>
<el-form ref="namingForm" :model="s.project" class="window-context-form" label-position="top" :disabled="s.busy||s.saving" @submit.prevent><el-form-item label="楼层"><el-input v-model="s.context.floor" :prefix-icon="Building2" placeholder="例如：二楼" maxlength="60" @change="s.persist"/></el-form-item><el-form-item label="安装位置"><el-input v-model="s.context.room" :prefix-icon="MapPin" placeholder="例如：主卧南窗" maxlength="100" @change="s.persist"/></el-form-item><el-form-item class="window-name-field" label="窗型名称" prop="name" :rules="[{required:true,whitespace:true,message:'请输入窗型名称',trigger:'blur'}]"><div class="window-name-control"><el-input v-if="s.project" v-model="s.project.name" :readonly="!customName" maxlength="100" :placeholder="customName?'请输入自定义名称':'填写楼层和安装位置后自动生成'" @input="s.persist"/><el-checkbox :model-value="customName" @change="toggleName">自定义名称</el-checkbox></div><small class="window-name-hint">{{customName?'名称由你填写，修改安装位置不会覆盖。':'根据楼层和安装位置自动生成，无需重复填写。'}}</small></el-form-item><el-form-item label="玻璃材料（规格、厚度、颜色）"><el-input v-model="s.context.glass_material" :prefix-icon="Layers" placeholder="例如：透明 5mm" maxlength="100" @change="s.persist"/></el-form-item></el-form>
<div class="window-context-footer"><p>修改后请保存窗型，整项目排料使用已保存的信息。</p><div class="window-context-actions"><el-button text :disabled="s.busy||s.saving" @click="importLegacy"><ArchiveRestore :size="15"/>导入本机旧草稿</el-button><QuickProject/></div></div>
</section>
<input ref="file" type="file" accept=".json" hidden @change="importProject"/>
<el-alert v-if="s.error" class="global-error" :title="s.error" type="error" show-icon :closable="true" @close="s.error=''"/>
<div v-if="draftDirty" class="pending-changes no-print" role="status"><div><strong>尺寸参数待应用</strong><span>画布与清单仍显示上次有效尺寸。</span></div><div class="action-row"><el-button :disabled="s.busy" @click="discardParameters">恢复已应用参数</el-button><el-button type="primary" :loading="s.busy" @click="applyParameters">应用并更新画布</el-button></div></div><div class="metrics no-print"><div><span>型材构件总数</span><strong>{{s.geometry.count}}<small>根</small></strong></div><div><span>构件总长</span><strong>{{(s.geometry.total_length/T/1000).toFixed(3)}}<small>m</small></strong></div><div><span>自动玻璃</span><strong>{{s.geometry.glass_count}}<small>块</small></strong></div><div class="metric-note"><span class="precision-symbol">◎</span><div><b>尺寸驱动，逐根可追溯</b><span>独立几何计算 · 自动生成清单</span></div></div></div>
<el-alert v-for="warning in s.geometry.glass_warnings" :key="warning" :title="warning" type="warning" :closable="false" class="global-error"/>
<div v-if="tab==='design'" class="mobile-design-tabs no-print" role="group" aria-label="设计面板"><el-button :type="mobilePanel==='canvas'?'primary':''" @click="mobilePanel='canvas'">画布</el-button><el-button :type="mobilePanel==='parameters'?'primary':''" @click="mobilePanel='parameters'">尺寸参数{{draftDirty?' · 待应用':''}}</el-button><el-button :type="mobilePanel==='region'?'primary':''" @click="mobilePanel='region'">区域与中挺</el-button></div>
<div v-if="tab==='design'" class="design-layout" :class="'mobile-panel-'+mobilePanel">
<aside class="panel parameter-panel"><div class="panel-heading"><h3><Settings2 :size="17"/>设计参数</h3><span class="eyebrow">01</span></div>
<el-form ref="form" :model="draft" :rules="rules" :disabled="s.busy" label-position="top" @submit.prevent><div class="two-cols"><el-form-item label="整体宽度" prop="width"><LengthInput v-model="draft.width" label="整体宽度" :min="2"/></el-form-item><el-form-item label="整体高度" prop="height"><LengthInput v-model="draft.height" label="整体高度" :min="2"/></el-form-item></div><el-form-item label="生产数量 / 樘"><el-input-number v-model="draft.quantity" :min="1" :max="100" :precision="0"/></el-form-item>
<el-collapse v-model="advanced" class="parameter-groups"><el-collapse-item title="玻璃扣减 · 调整下料尺寸" name="glass"><div class="two-cols"><el-form-item label="玻璃宽度总减量"><LengthInput v-model="draft.glass.width_deduction" label="玻璃宽度总减量"/></el-form-item><el-form-item label="玻璃高度总减量"><LengthInput v-model="draft.glass.height_deduction" label="玻璃高度总减量"/></el-form-item></div><p class="muted">玻璃 = 净区域 − 总减量，居中放置。默认宽、高各减 30 mm，每边退让 15 mm。</p>
</el-collapse-item><el-collapse-item title="型材宽度 · 外框、中挺、压线" name="widths"><div class="two-cols"><el-form-item v-for="c in categories" :key="c" :label="labels[c]" :prop="`profiles.${c}.width`" :rules="[{validator:(_:unknown,v:number,done:(e?:Error)=>void)=>done(Number.isFinite(v)&&v>0?undefined:new Error('宽度必须大于零'))}]"><LengthInput v-model="draft.profiles[c].width" :label="labels[c]+'宽度'" :min="2"/></el-form-item></div>
</el-collapse-item></el-collapse><el-form-item label="修改尺寸时，中挺位置"><el-select v-model="resizeMode"><el-option value="absolute" label="保持绝对坐标"/><el-option value="proportional" label="按整体宽高同比例调整"/></el-select></el-form-item>
<el-collapse v-model="advanced"><el-collapse-item title="原料型号映射" name="profiles"><p class="muted">仅当截面、颜色与材质确实相同时才使用相同型号。</p><el-form-item v-for="c in categories" :key="c" :label="labels[c]"><el-input v-model="draft.profiles[c].stock_key" maxlength="60"/></el-form-item></el-collapse-item></el-collapse>
<div class="parameter-submit"><el-button type="primary" class="full-button" :loading="s.busy" :disabled="!draftDirty" @click="applyParameters">{{draftDirty?'应用参数并更新画布':'参数已应用'}}</el-button><el-button class="return-canvas" text @click="mobilePanel='canvas'">返回画布</el-button></div></el-form>
<div class="template-actions"><el-button text @click="reset('sample')">载入示例窗型</el-button></div></aside>
<section class="drawing-panel"><div class="drawing-toolbar"><div class="tool-buttons"><el-tooltip content="选择区域"><el-button :type="s.tool==='select'?'primary':''" aria-label="选择区域" @click="s.tool='select'"><MousePointer2 :size="17"/></el-button></el-tooltip><el-tooltip content="在区域内点击，添加竖中挺"><el-button :type="s.tool==='x'?'primary':''" aria-label="绘制竖中挺" @click="s.tool='x'"><Columns2 :size="17"/>竖中挺</el-button></el-tooltip><el-tooltip content="在区域内点击，添加横中挺"><el-button :type="s.tool==='y'?'primary':''" aria-label="绘制横中挺" @click="s.tool='y'"><Rows2 :size="17"/>横中挺</el-button></el-tooltip></div><div><el-button text :disabled="!s.history.length||s.busy||draftDirty" aria-label="撤销" @click="s.undo"><Undo2 :size="17"/></el-button><el-button text :disabled="!s.future.length||s.busy||draftDirty" aria-label="重做" @click="s.redo"><Redo2 :size="17"/></el-button></div></div>
<WindowCanvas @draw="draw" @edit-split="editSplit"/>
<el-button class="mobile-region-button" :disabled="!s.region" @click="mobilePanel='region'">编辑选区 · {{s.region?mm(s.region.rect.w)+' × '+mm(s.region.rect.h)+' mm':'请先选择区域'}} <ChevronRight :size="16"/></el-button>
<div class="canvas-hint"><MousePointer2 :size="15"/><span>{{s.tool==='select'?'点击玻璃区查看尺寸；点击金色中挺编辑精确位置。':'点击目标区域放置中挺，再输入精确坐标确认。先画的中挺贯通，后画的在分区边界处对接。'}}</span></div>
<div class="material-strip"><div v-for="item in s.geometry.summary" :key="item.category"><span>{{item.label}}</span><b>{{item.count}} <small>根</small></b></div><div class="glass-count-summary"><span>玻璃</span><b>{{s.geometry.glass_count}} <small>块</small></b></div></div>
</section>
<aside class="panel inspector"><div class="panel-heading"><h3>当前选区</h3><el-button class="return-canvas" text @click="mobilePanel='canvas'">返回画布</el-button></div><el-select v-model="s.selected" filterable placeholder="选择区域" aria-label="区域列表"><el-option v-for="r in s.geometry.regions" :key="r.id" :value="r.id" :label="regionLabel(r)"/></el-select>
<template v-if="s.region"><div class="region-badge">{{s.region.context==='sash'?'窗扇内部':'窗户内部'}} / {{s.region.kind==='split'?'中挺分隔':s.region.kind==='sash'?'窗扇区域':s.region.kind==='empty'?'留空区域':'玻璃区域'}}</div><div class="region-size">{{mm(s.region.rect.w)}} <span>×</span> {{mm(s.region.rect.h)}}<small>净区域尺寸 / mm</small></div><dl class="coordinates"><dt>左上角</dt><dd>({{mm(s.region.rect.x)}}, {{mm(s.region.rect.y)}})</dd><dt>右下角</dt><dd>({{mm(s.region.rect.x+s.region.rect.w)}}, {{mm(s.region.rect.y+s.region.rect.h)}})</dd></dl>
<template v-if="s.region.opening"><div class="subtle-box"><span>压线内可见开口</span><b>{{mm(s.region.opening.w)}} × {{mm(s.region.opening.h)}} mm</b><small>可见开口与玻璃下料尺寸不同</small></div></template>
<div v-if="s.region.glass" class="subtle-box"><span>玻璃下料尺寸 · 自动生成</span><b>{{mm(s.region.glass.w)}} × {{mm(s.region.glass.h)}} mm</b><small>玻璃居中，压线在前；尺寸随分区更新。</small></div>
<div class="section-divider">区域用途</div><div class="region-actions"><el-button :type="currentNode?.kind==='glass'?'primary':''" plain @click="setKind('glass')">安装玻璃</el-button><el-button v-if="s.region.context==='window'" :type="currentNode?.kind==='sash'?'primary':''" plain @click="setKind('sash')">安装窗扇</el-button><el-button :type="currentNode?.kind==='empty'?'primary':''" plain @click="setKind('empty')">留空</el-button></div>
<template v-if="currentNode?.kind==='glass'||currentNode?.kind==='empty'"><div class="section-divider">通过中挺分隔</div><div class="region-actions"><el-button @click="addSplit('x')"><Columns2 :size="15"/>竖向分隔</el-button><el-button @click="addSplit('y')"><Rows2 :size="15"/>横向分隔</el-button></div></template>
<template v-if="selectedSplit"><div class="subtle-box"><span>中挺中心线 {{selectedSplit.axis.toUpperCase()}}</span><b>{{mm(selectedSplit.position)}} mm</b><small>起点 ({{selectedSplit.start.map(mm).join(', ')}})<br/>终点 ({{selectedSplit.end.map(mm).join(', ')}})</small></div><el-button class="full-button" @click="editSplit(s.selected)">编辑中挺位置</el-button><el-button class="full-button" type="danger" plain @click="setKind('glass')">移除分隔并合并为玻璃区</el-button></template>
<el-button v-if="parentSash" text class="full-button" @click="s.selected=parentSash!.id">选择所属窗扇 <ArrowUpRight :size="14"/></el-button>
</template><div class="inspector-note">中挺以中心线定位，并扣除自身宽度。区域用途改变后，构件数量与长度自动重新计算。</div></aside>
</div>
<PartsTable v-else-if="tab==='materials'"/>
<CutPlanner v-else ref="cutEditor"/>
<footer class="workspace-footer no-print"><span>窗序 / WINFRAME CUT</span><span>矩形窗型 · 精确坐标 · 账号存档</span><router-link v-if="tab==='design'" :to="target('/materials')">查看构件清单 <ChevronRight :size="14"/></router-link></footer>
</main>
<div v-else class="loading-screen"><PanelsTopLeft :size="36"/><h2>正在载入工作台</h2><p v-if="s.error">{{s.error}}</p><el-button v-if="s.error" @click="s.init">重新连接</el-button></div>
<el-dialog v-model="dialog" :close-on-click-modal="false" :title="splitDraft.editing?'编辑中挺精确位置':'添加中挺'" width="min(480px, calc(100vw - 24px))" destroy-on-close><el-alert v-if="s.error" :title="s.error" type="error" :closable="false" style="margin-bottom:16px"/><el-form ref="splitForm" :model="splitDraft" label-position="top"><el-form-item label="方向"><el-radio-group v-model="splitDraft.axis" :disabled="splitDraft.editing"><el-radio-button value="x">竖中挺（X 坐标）</el-radio-button><el-radio-button value="y">横中挺（Y 坐标）</el-radio-button></el-radio-group></el-form-item><el-form-item :label="`距整窗${splitDraft.axis==='x'?'左边':'顶部'}的中心线坐标`" prop="position" :rules="[{required:true,message:'请输入中心线坐标'}]"><LengthInput v-model="splitDraft.position" label="中挺中心线坐标"/></el-form-item><div class="subtle-box"><span>中挺起点 → 终点（mm）</span><b>{{pendingEnds}}</b><small>宽度 {{pendingRegion?mm(s.project!.profiles[pendingRegion.context==='sash'?'sash_mullion':'window_mullion'].width):''}} mm；端点由所在区域边界确定。</small></div><p class="muted">新增中挺默认在两侧安装玻璃。边界过窄时会拒绝生成；可以调整宽度或位置。</p></el-form><template #footer><el-button @click="dialog=false">取消</el-button><el-button type="primary" :loading="s.busy" @click="confirmSplit">确认并计算</el-button></template></el-dialog>
<el-drawer v-model="library" title="项目窗型存档" size="min(420px, 100vw)"><p class="muted">窗型存档保存几何与型材参数；导出项目文件可同时保存原料规格和切割设置。</p><el-empty v-if="!saved.length" description="暂无存档，点击保存窗型创建"/><div v-for="p in saved" :key="p.id" class="saved-project"><div><b>{{p.name}}</b><small>{{new Date(p.updated).toLocaleString('zh-CN')}}</small></div><el-button @click="loadSaved(p.id)">打开</el-button></div></el-drawer>
</div>
</template>
