import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { api, errorText } from './api'
import { clone, categories, T, walk, defaultGlass, type GlassPlan, type Project, type Geometry, type Stock, type Settings, type Plan, type Node } from './types'

export const useWorkshop = defineStore('workshop',()=>{
  const project=ref<Project|null>(null),geometry=ref<Geometry|null>(null),stocks=ref<Stock[]>([])
  const settings=ref<Settings>({kerf:3*T,trim_start:0,trim_end:0,objective:'bars',time_limit:10})
  const glassDraftDirty=ref(false)
  const glassPlan=ref<GlassPlan|null>(null),glassSolving=ref(false)
  const plan=ref<Plan|null>(null),selected=ref(''),tool=ref<'select'|'x'|'y'>('select')
  const busy=ref(false),solving=ref(false),error=ref(''),savedId=ref<string|null>(null),savedAt=ref('')
  const history=ref<Project[]>([]),future=ref<Project[]>([])
  const region=computed(()=>geometry.value?.regions.find(r=>r.id===selected.value))
  let calcRevision=0,solveRevision=0,glassRevision=0
  const invalidate=()=>{plan.value=null;glassPlan.value=null;solveRevision++;glassRevision++}
  function persist(){
    if(!project.value)return
    const hasInvalidNumber=(v:unknown):boolean=>typeof v==='number'?!Number.isFinite(v):v!==null&&typeof v==='object'?Object.values(v).some(hasInvalidNumber):false
    if(hasInvalidNumber({project:project.value,stocks:stocks.value,settings:settings.value}))return
    try{localStorage.setItem('winframe-workspace-v1',JSON.stringify({project:project.value,stocks:stocks.value,settings:settings.value}))}
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
    try{
      const raw=localStorage.getItem('winframe-workspace-v1')
      if(raw){
        const value=JSON.parse(raw)
        if(await commit(value.project,false)){
          try{await api.post('/validate',value);stocks.value=value.stocks;settings.value=value.settings}
          catch{defaultStocks();error.value='窗型已恢复；上次原料参数未填写完整，已恢复默认规格，请重新核对。'}
          persist();return
        }
      }
    }catch{error.value='本地草稿无法恢复，已加载基准窗型。'}
    try{const {data}=await api.get<Project>('/sample');await commit(data,false);defaultStocks();persist()}catch(e){error.value=errorText(e)}
  }
  async function loadSample(){const {data}=await api.get<Project>('/sample');if(await commit(data)){savedId.value=null;defaultStocks();persist()}}
  async function blank(){if(!project.value)return;const p=clone(project.value);p.name='未命名窗型';p.root={id:'root',kind:'glass',children:[]};if(await commit(p))savedId.value=null}
  async function changeNode(id:string,fn:(n:Node)=>void){if(!project.value)return false;const p=clone(project.value);const n=walk(p.root,id);if(!n)return false;fn(n);return commit(p)}
  async function undo(){const p=history.value.at(-1);if(p&&project.value){const old=clone(project.value);if(await commit(p,false)){history.value.pop();future.value.push(old);savedId.value=null}}}
  async function redo(){const p=future.value.at(-1);if(p&&project.value){const old=clone(project.value);if(await commit(p,false)){future.value.pop();history.value.push(old);savedId.value=null}}}
  async function solve(){
    if(!project.value||solving.value||busy.value)return
    error.value='';plan.value=null;solving.value=true
    const rev=++solveRevision,payload=JSON.stringify({project:project.value,stocks:stocks.value,settings:settings.value})
    try{const {data}=await api.post<Plan>('/optimize',JSON.parse(payload));if(rev===solveRevision&&payload===JSON.stringify({project:project.value,stocks:stocks.value,settings:settings.value}))plan.value=data}
    catch(e){if(rev===solveRevision)error.value=errorText(e)}finally{solving.value=false}
  }
  async function solveGlass(){
    if(!project.value||glassSolving.value||busy.value)return
    error.value='';glassPlan.value=null;glassSolving.value=true
    const rev=++glassRevision,payload=JSON.stringify(project.value)
    try{const {data}=await api.post<GlassPlan>('/optimize-glass',JSON.parse(payload));if(rev===glassRevision&&payload===JSON.stringify(project.value))glassPlan.value=data}
    catch(e){if(rev===glassRevision)error.value=errorText(e)}finally{glassSolving.value=false}
  }
  const saving=ref(false)
  async function save(){
    if(!project.value||busy.value||saving.value||glassDraftDirty.value)return
    const snapshot=clone(project.value),target=savedId.value,revision=calcRevision
    saving.value=true
    try{
      const {data}=target?await api.put(`/projects/${target}`,snapshot):await api.post('/projects',snapshot)
      // 请求期间切换或修改窗型后，不把旧请求的存档编号绑定给新窗型。
      if(revision===calcRevision&&target===savedId.value){savedId.value=data.id;savedAt.value=new Date().toLocaleTimeString('zh-CN');persist()}
    }catch(e){error.value=errorText(e)}finally{saving.value=false}
  }

  return {saving,glassDraftDirty,glassPlan,glassSolving,solveGlass,project,geometry,stocks,settings,plan,selected,tool,busy,solving,error,savedAt,savedId,history,future,region,init,commit,loadSample,blank,changeNode,undo,redo,solve,save,invalidate,persist}
})
