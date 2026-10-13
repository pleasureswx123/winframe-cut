import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { api, errorText } from './api'
import type {WindowRecord} from './business'
import {defaultSettings} from './business'
import { clone, categories, T, walk, defaultGlass, type GlassPlan, type Project, type Geometry, type Stock, type Settings, type Plan, type Node } from './types'

export const useWorkshop = defineStore('workshop',()=>{
  const project=ref<Project|null>(null),geometry=ref<Geometry|null>(null),stocks=ref<Stock[]>([])
  const settings=ref<Settings>(defaultSettings())
  const parameterDraftDirty=ref(false),glassDraftDirty=ref(false)
  const glassPlan=ref<GlassPlan|null>(null),glassSolving=ref(false)
  const plan=ref<Plan|null>(null),selected=ref(''),tool=ref<'select'|'x'|'y'>('select')
  const busy=ref(false),solving=ref(false),error=ref(''),savedId=ref<string|null>(null),savedAt=ref('')
  const history=ref<Project[]>([]),future=ref<Project[]>([])
  const region=computed(()=>geometry.value?.regions.find(r=>r.id===selected.value))
  let calcRevision=0,solveRevision=0,glassRevision=0
  const userId=ref(''),context=ref({house_id:'',floor:'',room:'',glass_material:'默认玻璃'}),savedSnapshot=ref('')
  let workspaceRevision=0
  const snapshot=()=>JSON.stringify({project:project.value,stocks:stocks.value,settings:settings.value,context:context.value})
  const dirty=computed(()=>!!project.value&&snapshot()!==savedSnapshot.value)
  const draftKey=()=>`winframe-workspace-v2:${userId.value}:${savedId.value||'new-'+context.value.house_id}`
  function clearWorkspace(){
    workspaceRevision++;calcRevision++;solveRevision++;glassRevision++
    project.value=null;geometry.value=null;stocks.value=[];plan.value=null;glassPlan.value=null
    settings.value=defaultSettings();selected.value='';tool.value='select'
    history.value=[];future.value=[];savedId.value=null;savedAt.value='';savedSnapshot.value=''
    busy.value=false;solving.value=false;glassSolving.value=false;saving.value=false;glassDraftDirty.value=false;parameterDraftDirty.value=false;error.value=''
    context.value={house_id:'',floor:'',room:'',glass_material:'默认玻璃'}
  }
  function resetSession(){clearWorkspace();userId.value=''}
  function setUser(id:string){if(userId.value!==id){resetSession();userId.value=id}}
  async function openWindow(id:string){
    clearWorkspace();const revision=workspaceRevision
    try{
      const {data}=await api.get<WindowRecord>(`/windows/${id}`)
      if(revision!==workspaceRevision)return
      context.value={house_id:data.house_id,floor:data.floor,room:data.room,glass_material:data.glass_material}
      savedId.value=id;stocks.value=data.stocks;settings.value={...defaultSettings(),...data.settings}
      const raw=localStorage.getItem(draftKey())
      if(await commit(data.project,false)){
        savedSnapshot.value=snapshot()
        if(raw){
          try{
            const draft=JSON.parse(raw)
            if(draft.savedId===id&&draft.context?.house_id===data.house_id){
              await api.post('/validate',{project:draft.project,stocks:draft.stocks,settings:draft.settings})
              if(revision!==workspaceRevision)return
              if(await commit(draft.project,false)){stocks.value=draft.stocks;settings.value={...defaultSettings(),...draft.settings};context.value=draft.context}
            }
          }catch{if(revision===workspaceRevision)error.value='本地草稿无效，已恢复服务器存档'}
        }
        if(revision===workspaceRevision)persist()
      }
    }catch(e){if(revision===workspaceRevision)error.value=errorText(e)}
  }
  async function newWindow(houseId:string){clearWorkspace();context.value.house_id=houseId;await init()}
  const invalidate=()=>{plan.value=null;glassPlan.value=null;solveRevision++;glassRevision++;solving.value=false;glassSolving.value=false}
  function persist(){
    if(!project.value)return
    const hasInvalidNumber=(v:unknown):boolean=>typeof v==='number'?!Number.isFinite(v):v!==null&&typeof v==='object'?Object.values(v).some(hasInvalidNumber):false
    if(hasInvalidNumber({project:project.value,stocks:stocks.value,settings:settings.value}))return
    if(!userId.value||!context.value.house_id)return
    try{localStorage.setItem(draftKey(),JSON.stringify({project:project.value,stocks:stocks.value,settings:settings.value,context:context.value,savedId:savedId.value}))}
    catch{error.value='浏览器草稿保存失败，请导出项目文件保存。'}
  }
  async function commit(next:Project,record=true){
    next=clone(next);next.glass={...defaultGlass(),...next.glass}
    const rev=++calcRevision;busy.value=true;error.value=''
    try{
      const {data}=await api.post<Geometry>('/calculate',next)
      if(rev!==calcRevision)return false
      if(record&&project.value){history.value.push(clone(project.value));if(history.value.length>60)history.value.shift();future.value=[]}
      project.value=clone(next);geometry.value=data;invalidate();savedAt.value=''
      if(!data.regions.some(r=>r.id===selected.value))selected.value=data.regions.find(r=>r.kind==='glass'||r.kind==='empty')?.id??''
      persist();return true
    }catch(e){if(rev===calcRevision)error.value=errorText(e);return false}
    finally{if(rev===calcRevision)busy.value=false}
  }
  function defaultStocks(){stocks.value=[...new Set(categories.map(k=>project.value!.profiles[k].stock_key))].map(key=>({id:key+'-6000',stock_key:key,length:6000*T,price_cents:0,available:null}))}
  async function init(){
    const revision=workspaceRevision
    try{
      const raw=localStorage.getItem(draftKey())
      if(raw){
        const value=JSON.parse(raw)
        if(await commit(value.project,false)){
          try{await api.post('/validate',{project:value.project,stocks:value.stocks,settings:value.settings});if(revision!==workspaceRevision)return;stocks.value=value.stocks;settings.value={...defaultSettings(),...value.settings};context.value=value.context;savedId.value=value.savedId??null}
          catch{if(revision!==workspaceRevision)return;defaultStocks();error.value='窗型已恢复；上次原料参数未填写完整，已恢复默认规格，请重新核对。'}
          persist();return
        }
      }
    }catch{error.value='本地草稿无法恢复，已加载基准窗型。'}
    try{const {data}=await api.get<Project>('/sample');if(revision!==workspaceRevision)return;data.name_mode='auto';data.name='未命名窗型';if(await commit(data,false)){defaultStocks();persist()}}catch(e){if(revision===workspaceRevision)error.value=errorText(e)}
  }
  async function loadSample(){if(saving.value)return;const revision=workspaceRevision;const {data}=await api.get<Project>('/sample');if(revision!==workspaceRevision)return;if(await commit(data)){savedId.value=null;defaultStocks();persist()}}
  const workspaceToken=()=>workspaceRevision
  async function applyImport(value:unknown,token=workspaceRevision){
    if(saving.value)return false
    const {data}=await api.post('/validate',value)
    if(token!==workspaceRevision)return false
    if(await commit(data.project)){stocks.value=data.stocks;settings.value={...defaultSettings(),...data.settings};savedId.value=null;persist();return true}
    return false
  }
  async function blank(){if(!project.value||saving.value)return;const p=clone(project.value);p.name='未命名窗型';p.root={id:'root',kind:'glass',children:[]};if(await commit(p))savedId.value=null}
  // 先校验新窗型，再切换工作区，避免失败时丢失当前编辑。
  async function createNextWindow(){
    if(!project.value||busy.value||saving.value)return false
    const revision=workspaceRevision,next=clone(project.value),previous=clone(context.value)
    next.name_mode='auto';next.name=previous.floor.trim()||'未命名窗型';next.quantity=1;next.root={id:'root',kind:'glass',children:[]}
    busy.value=true;error.value=''
    try{
      const {data}=await api.post<Geometry>('/calculate',next)
      if(revision!==workspaceRevision)return false
      clearWorkspace();context.value={house_id:previous.house_id,floor:previous.floor,room:'',glass_material:previous.glass_material}
      project.value=next;geometry.value=data;selected.value=data.regions[0]?.id??'';defaultStocks();persist();return true
    }catch(e){if(revision===workspaceRevision)error.value=errorText(e);return false}
    finally{if(revision===workspaceRevision)busy.value=false}
  }
  function discardLocalDraft(){localStorage.removeItem(draftKey())}
  async function changeNode(id:string,fn:(n:Node)=>void){if(!project.value)return false;const p=clone(project.value);const n=walk(p.root,id);if(!n)return false;fn(n);return commit(p)}
  async function undo(){const p=history.value.at(-1);if(p&&project.value){const old=clone(project.value);if(await commit(p,false)){history.value.pop();future.value.push(old)}}}
  async function redo(){const p=future.value.at(-1);if(p&&project.value){const old=clone(project.value);if(await commit(p,false)){future.value.pop();history.value.push(old)}}}
  async function solve(){
    if(!project.value||solving.value||busy.value)return
    error.value='';plan.value=null;solving.value=true
    const rev=++solveRevision,payload=JSON.stringify({project:project.value,stocks:stocks.value,settings:settings.value})
    try{const {data}=await api.post<Plan>('/optimize',JSON.parse(payload));if(rev===solveRevision&&payload===JSON.stringify({project:project.value,stocks:stocks.value,settings:settings.value}))plan.value=data}
    catch(e){if(rev===solveRevision)error.value=errorText(e)}finally{if(rev===solveRevision)solving.value=false}
  }
  async function solveGlass(){
    if(!project.value||glassSolving.value||busy.value)return
    error.value='';glassPlan.value=null;glassSolving.value=true
    const rev=++glassRevision,payload=JSON.stringify(project.value)
    try{const {data}=await api.post<GlassPlan>('/optimize-glass',JSON.parse(payload));if(rev===glassRevision&&payload===JSON.stringify(project.value))glassPlan.value=data}
    catch(e){if(rev===glassRevision)error.value=errorText(e)}finally{if(rev===glassRevision)glassSolving.value=false}
  }
  const saving=ref(false)
  async function save(){
    if(!project.value||busy.value||saving.value||glassDraftDirty.value||parameterDraftDirty.value)return false
    if(!context.value.house_id){error.value='请先选择客户和房屋项目';return false}
    const payload={...clone(context.value),project:clone(project.value),stocks:clone(stocks.value),settings:clone(settings.value)},target=savedId.value,workspace=workspaceRevision,state=snapshot(),oldKey=draftKey()
    saving.value=true;error.value=''
    try{
      const {data}=target?await api.put(`/windows/${target}`,payload):await api.post('/windows',payload)
      // 同一窗型继续编辑仍绑定已创建记录，但保持未保存状态；切换工作区则忽略响应。
      if(workspace===workspaceRevision&&target===savedId.value){savedId.value=data.id;savedSnapshot.value=state;savedAt.value=new Date().toLocaleTimeString('zh-CN');localStorage.removeItem(oldKey);persist();return !dirty.value}
      return false
    }catch(e){if(workspace===workspaceRevision)error.value=errorText(e);return false}finally{if(workspace===workspaceRevision)saving.value=false}
  }

  return {createNextWindow,discardLocalDraft,parameterDraftDirty,workspaceToken,applyImport,userId,context,dirty,setUser,resetSession,openWindow,newWindow,saving,glassDraftDirty,glassPlan,glassSolving,solveGlass,project,geometry,stocks,settings,plan,selected,tool,busy,solving,error,savedAt,savedId,history,future,region,init,commit,loadSample,blank,changeNode,undo,redo,solve,save,invalidate,persist}
})
