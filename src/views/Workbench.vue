<script setup lang="ts">
import { newId } from "../id"
import { ref, computed, watch, nextTick } from 'vue'
import { useRoute, onBeforeRouteUpdate } from 'vue-router'
import { ElMessageBox, ElMessage, type FormInstance } from 'element-plus'
import { PanelsTopLeft, MousePointer2, Columns2, Rows2, Undo2, Redo2, Save, FolderOpen, Download, Upload, ChevronRight, ArrowUpRight, Maximize, Settings2, Layers, Scissors } from 'lucide-vue-next'
import { useWorkshop } from '../store'
import { api, errorText } from '../api'
import { clone, categories, labels, mm, T, walk, type Project, type Node, type Region } from '../types'
import { download } from '../export'
import LengthInput from '../components/LengthInput.vue'
import WindowCanvas from '../components/WindowCanvas.vue'
import PartsTable from '../components/PartsTable.vue'
import CutPlanner from '../components/CutPlanner.vue'
const s=useWorkshop(),route=useRoute()
const mobilePanel=ref('canvas')
watch(mobilePanel,async()=>{
  await nextTick()
  if(window.matchMedia('(max-width:760px)').matches)document.querySelector('.mobile-design-tabs')?.scrollIntoView({block:'start'})
})
const tab=computed(()=>String(route.params.tab??'design'))
const draft=ref<Project|null>(null),form=ref<FormInstance>(),resizeMode=ref('absolute'),advanced=ref<string[]>([])
const dialog=ref(false),splitForm=ref<FormInstance>(),splitDraft=ref({id:'',axis:'x' as 'x'|'y',position:0,editing:false})
const library=ref(false),saved=ref<{id:string;name:string;updated:string}[]>([]),file=ref<HTMLInputElement>()
watch(()=>s.project,p=>{if(p)draft.value=clone(p)},{immediate:true})
const draftDirty=computed(()=>!!draft.value&&JSON.stringify(draft.value)!==JSON.stringify(s.project))
function canEdit(){if(draftDirty.value){ElMessage.warning('请先应用左侧参数，再修改窗型结构');return false}return !s.busy}
onBeforeRouteUpdate(async()=>{
  if(s.glassDraftDirty){ElMessage.warning('请先应用玻璃排料参数，再切换页面');return false}
  if(!draftDirty.value)return true
  try{await ElMessageBox.confirm('左侧参数尚未应用。请先应用并通过尺寸校验，再切换页面。','参数尚未应用',{confirmButtonText:'应用并继续',cancelButtonText:'留在当前页'});return await applyParameters()}
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
  if(!draft.value||!s.project||!await form.value?.validate().catch(()=>false))return false
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
async function openLibrary(){try{saved.value=(await api.get('/projects')).data;library.value=true}catch(e){s.error=errorText(e)}}
async function loadSaved(id:string){try{const {data}=await api.get<Project>(`/projects/${id}`);if(await s.commit(data)){s.savedId=id;library.value=false}}catch(e){s.error=errorText(e)}}
function exportProject(){download(`${s.project!.name}.winframe.json`,JSON.stringify({project:s.project,stocks:s.stocks,settings:s.settings},null,2))}
async function importProject(event:Event){
  const input=event.target as HTMLInputElement,f=input.files?.[0];if(!f)return
  try{
    if(f.size>2_000_000)throw new Error('项目文件不能超过 2 MB')
    const value=JSON.parse(await f.text());const {data}=await api.post('/validate',value)
    if(await s.commit(data.project)){s.stocks=data.stocks;s.settings=data.settings;s.savedId=null;s.persist();ElMessage.success('项目已导入')}
  }catch(e){s.error=errorText(e)}finally{input.value=''}
}
const regionLabel=(r:Region)=>`${r.id} · ${r.kind==='split'?'中挺分区':r.kind==='sash'?'窗扇':r.kind==='empty'?'留空':'玻璃'}`
</script>
<template>
<div class="app-shell">
<header class="app-header no-print"><div class="brand"><div class="brand-mark"><PanelsTopLeft :size="25" :stroke-width="1.5"/></div><div><strong>窗序<span>WINFRAME</span></strong><small>精密设计 · 智能下料</small></div></div><nav><router-link to="/design"><Maximize :size="16"/>窗型设计</router-link><router-link to="/materials"><Layers :size="16"/>构件清单</router-link><router-link to="/cutting"><Scissors :size="16"/>切割排料</router-link></nav><div class="header-right"><span class="local-badge"><i class="status-dot"/>本机工作区</span><el-button @click="openLibrary"><FolderOpen :size="16"/>窗型存档</el-button></div></header>
<main v-if="s.project&&draft&&s.geometry" class="main-layout" :class="{'wide-layout':tab!=='design'}">
<div class="page-intro no-print"><div><div class="breadcrumb">工作台 <ChevronRight :size="12"/> {{tab==='design'?'窗型设计':tab==='materials'?'构件清单':'切割排料'}}</div><h1>{{tab==='design'?'让每一毫米，都有依据。':tab==='materials'?'从窗型，到每一根构件。':'精确切割，让好材料物尽其用。'}}</h1><p>{{s.project.name}} <span>／ {{mm(s.project.width)}} × {{mm(s.project.height)}} mm · {{s.project.quantity}} 樘</span></p></div><div class="intro-actions"><el-button @click="file?.click()"><Upload :size="15"/>导入</el-button><el-button :disabled="draftDirty||s.glassDraftDirty||s.busy" @click="exportProject"><Download :size="15"/>导出项目</el-button><el-button type="primary" :loading="s.busy" :disabled="draftDirty||s.glassDraftDirty||s.saving" @click="s.save"><Save :size="15"/>{{s.savedAt?'已保存 '+s.savedAt:'保存窗型'}}</el-button></div></div>
<input ref="file" type="file" accept=".json" hidden @change="importProject"/>
<el-alert v-if="s.error" class="global-error" :title="s.error" type="error" show-icon :closable="true" @close="s.error=''"/>
<el-alert v-if="draftDirty" title="参数尚未应用：画布与清单仍显示上次有效尺寸，请应用参数后再下料。" type="warning" show-icon :closable="false" class="global-error"/><div class="metrics no-print"><div><span>型材构件总数</span><strong>{{s.geometry.count}}<small>根</small></strong></div><div><span>构件总长</span><strong>{{(s.geometry.total_length/T/1000).toFixed(3)}}<small>m</small></strong></div><div><span>自动玻璃</span><strong>{{s.geometry.glass_count}}<small>块</small></strong></div><div class="metric-note"><span class="precision-symbol">◎</span><div><b>尺寸驱动，逐根可追溯</b><span>独立几何计算 · 自动生成清单</span></div></div></div>
<el-alert v-for="warning in s.geometry.glass_warnings" :key="warning" :title="warning" type="warning" :closable="false" class="global-error"/>
<div v-if="tab==='design'" class="mobile-design-tabs no-print" role="group" aria-label="设计面板"><el-button :type="mobilePanel==='canvas'?'primary':''" @click="mobilePanel='canvas'">画布</el-button><el-button :type="mobilePanel==='parameters'?'primary':''" @click="mobilePanel='parameters'">尺寸参数{{draftDirty?' · 待应用':''}}</el-button><el-button :type="mobilePanel==='region'?'primary':''" @click="mobilePanel='region'">区域与中挺</el-button></div>
<div v-if="tab==='design'" class="design-layout" :class="'mobile-panel-'+mobilePanel">
<aside class="panel parameter-panel"><div class="panel-heading"><h3><Settings2 :size="17"/>设计参数</h3><span class="eyebrow">01</span></div>
<el-form ref="form" :model="draft" :rules="rules" label-position="top"><el-form-item label="窗型名称" prop="name"><el-input v-model="draft.name" maxlength="100"/></el-form-item><div class="two-cols"><el-form-item label="整体宽度" prop="width"><LengthInput v-model="draft.width" label="整体宽度" :min="2"/></el-form-item><el-form-item label="整体高度" prop="height"><LengthInput v-model="draft.height" label="整体高度" :min="2"/></el-form-item></div><el-form-item label="生产数量 / 樘"><el-input-number v-model="draft.quantity" :min="1" :max="100" :precision="0"/></el-form-item>
<div class="section-divider">玻璃尺寸总减量 <span>mm</span></div><div class="two-cols"><el-form-item label="玻璃宽度总减量"><LengthInput v-model="draft.glass.width_deduction" label="玻璃宽度总减量"/></el-form-item><el-form-item label="玻璃高度总减量"><LengthInput v-model="draft.glass.height_deduction" label="玻璃高度总减量"/></el-form-item></div><p class="muted">玻璃 = 净区域 − 总减量，居中放置。默认宽、高各减 30 mm，每边退让 15 mm。</p>
<div class="section-divider">型材宽度 <span>mm</span></div><div class="two-cols"><el-form-item v-for="c in categories" :key="c" :label="labels[c]" :prop="`profiles.${c}.width`" :rules="[{validator:(_:unknown,v:number,done:(e?:Error)=>void)=>done(Number.isFinite(v)&&v>0?undefined:new Error('宽度必须大于零'))}]"><LengthInput v-model="draft.profiles[c].width" :label="labels[c]+'宽度'" :min="2"/></el-form-item></div>
<el-form-item label="修改整体尺寸时，中挺位置"><el-select v-model="resizeMode"><el-option value="absolute" label="保持绝对坐标"/><el-option value="proportional" label="按整体宽高同比例调整"/></el-select></el-form-item>
<el-collapse v-model="advanced"><el-collapse-item title="原料型号映射" name="profiles"><p class="muted">仅当截面、颜色与材质确实相同时才使用相同型号。</p><el-form-item v-for="c in categories" :key="c" :label="labels[c]"><el-input v-model="draft.profiles[c].stock_key" maxlength="60"/></el-form-item></el-collapse-item></el-collapse>
<el-button type="primary" class="full-button" :loading="s.busy" @click="applyParameters">应用参数并重新计算</el-button></el-form>
<div class="template-actions"><el-button text @click="reset('blank')">新建空白窗型</el-button><el-button text @click="reset('sample')">Blender 基准</el-button></div></aside>
<section class="drawing-panel"><div class="drawing-toolbar"><div class="tool-buttons"><el-tooltip content="选择区域"><el-button :type="s.tool==='select'?'primary':''" aria-label="选择区域" @click="s.tool='select'"><MousePointer2 :size="17"/></el-button></el-tooltip><el-tooltip content="在区域内点击，添加竖中挺"><el-button :type="s.tool==='x'?'primary':''" aria-label="绘制竖中挺" @click="s.tool='x'"><Columns2 :size="17"/>竖中挺</el-button></el-tooltip><el-tooltip content="在区域内点击，添加横中挺"><el-button :type="s.tool==='y'?'primary':''" aria-label="绘制横中挺" @click="s.tool='y'"><Rows2 :size="17"/>横中挺</el-button></el-tooltip></div><div><el-button text :disabled="!s.history.length||s.busy||draftDirty" aria-label="撤销" @click="s.undo"><Undo2 :size="17"/></el-button><el-button text :disabled="!s.future.length||s.busy||draftDirty" aria-label="重做" @click="s.redo"><Redo2 :size="17"/></el-button></div></div>
<WindowCanvas @draw="draw" @edit-split="editSplit"/>
<el-button class="mobile-region-button" @click="mobilePanel='region'">编辑选中区域 · 玻璃 / 窗扇 / 中挺</el-button>
<div class="canvas-hint"><MousePointer2 :size="15"/><span>{{s.tool==='select'?'点击玻璃区查看尺寸；点击金色中挺编辑精确位置。':'点击目标区域放置中挺，再输入精确坐标确认。先画的中挺贯通，后画的在分区边界处对接。'}}</span></div>
<div class="material-strip"><div v-for="item in s.geometry.summary" :key="item.category"><span>{{item.label}}</span><b>{{item.count}} <small>根</small></b></div><div class="glass-count-summary"><span>玻璃</span><b>{{s.geometry.glass_count}} <small>块</small></b></div></div>
</section>
<aside class="panel inspector"><div class="panel-heading"><h3>区域与连接</h3><span class="eyebrow">02</span></div><el-select v-model="s.selected" filterable placeholder="选择区域" aria-label="区域列表"><el-option v-for="r in s.geometry.regions" :key="r.id" :value="r.id" :label="regionLabel(r)"/></el-select>
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
<CutPlanner v-else/>
<footer class="workspace-footer no-print"><span>窗序 / WINFRAME CUT</span><span>矩形窗型 · 精确坐标 · 本机保存</span><router-link v-if="tab==='design'" to="/materials">查看构件清单 <ChevronRight :size="14"/></router-link></footer>
</main>
<div v-else class="loading-screen"><PanelsTopLeft :size="36"/><h2>正在载入工作台</h2><p v-if="s.error">{{s.error}}</p><el-button v-if="s.error" @click="s.init">重新连接</el-button></div>
<el-dialog v-model="dialog" :title="splitDraft.editing?'编辑中挺精确位置':'添加中挺'" width="min(480px, calc(100vw - 24px))" destroy-on-close><el-alert v-if="s.error" :title="s.error" type="error" :closable="false" style="margin-bottom:16px"/><el-form ref="splitForm" :model="splitDraft" label-position="top"><el-form-item label="方向"><el-radio-group v-model="splitDraft.axis" :disabled="splitDraft.editing"><el-radio-button value="x">竖中挺（X 坐标）</el-radio-button><el-radio-button value="y">横中挺（Y 坐标）</el-radio-button></el-radio-group></el-form-item><el-form-item :label="`距整窗${splitDraft.axis==='x'?'左边':'顶部'}的中心线坐标`" prop="position" :rules="[{required:true,message:'请输入中心线坐标'}]"><LengthInput v-model="splitDraft.position" label="中挺中心线坐标"/></el-form-item><div class="subtle-box"><span>中挺起点 → 终点（mm）</span><b>{{pendingEnds}}</b><small>宽度 {{pendingRegion?mm(s.project!.profiles[pendingRegion.context==='sash'?'sash_mullion':'window_mullion'].width):''}} mm；端点由所在区域边界确定。</small></div><p class="muted">新增中挺默认在两侧安装玻璃。边界过窄时会拒绝生成；可以调整宽度或位置。</p></el-form><template #footer><el-button @click="dialog=false">取消</el-button><el-button type="primary" :loading="s.busy" @click="confirmSplit">确认并计算</el-button></template></el-dialog>
<el-drawer v-model="library" title="本机窗型存档" size="min(420px, 100vw)"><p class="muted">窗型存档保存几何与型材参数；导出项目文件可同时保存原料规格和切割设置。</p><el-empty v-if="!saved.length" description="暂无存档，点击保存窗型创建"/><div v-for="p in saved" :key="p.id" class="saved-project"><div><b>{{p.name}}</b><small>{{new Date(p.updated).toLocaleString('zh-CN')}}</small></div><el-button @click="loadSaved(p.id)">打开</el-button></div></el-drawer>
</div>
</template>
