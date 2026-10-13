<script setup lang="ts">
import {ref,onMounted,computed} from 'vue'
import {ArrowLeft,ArrowRight,Search,Users,House as HouseIcon,PanelsTopLeft,MapPin,Layers,ShieldCheck} from 'lucide-vue-next'
import {useRoute} from 'vue-router'
import {api,errorText} from '../../api'
import type {Customer,House,WindowRecord,Page} from '../../business'
import {mm,labels,type Geometry,type Category} from '../../types'
const route=useRoute(),tab=ref('customers'),items=ref<(Customer|House|WindowRecord)[]>([]),page=ref(1),total=ref(0),q=ref(''),error=ref(''),parent=ref(''),detail=ref<(WindowRecord&{geometry:Geometry})|null>(null),dialog=ref(false)
const parentName=ref(''),detailTab=ref('profiles')
const tabLabel=computed(()=>tab.value==='customers'?'客户':tab.value==='houses'?'房屋项目':'窗型')
const profileRows=computed(()=>detail.value?Object.entries(detail.value.project.profiles).map(([key,profile])=>({...profile,label:labels[key as Category]})):[])
async function load(){error.value='';try{const {data}=await api.get<Page<Customer|House|WindowRecord>>(`/admin/users/${route.params.id}/${tab.value}`,{params:{page:page.value,q:q.value,...(parent.value?{[tab.value==='houses'?'customer_id':'house_id']:parent.value}:{})}});items.value=data.items;total.value=data.total}catch(e){error.value=errorText(e)}}
onMounted(load)
function selectTab(value:string){tab.value=value;parent.value='';parentName.value='';page.value=1;q.value='';load()}
function clearParent(){parent.value='';parentName.value='';page.value=1;load()}
function descend(row:Customer|House|WindowRecord){parent.value=row.id;parentName.value=row.name;tab.value=tab.value==='customers'?'houses':'windows';page.value=1;q.value='';load()}
async function inspect(row:Customer|House|WindowRecord){try{detail.value=(await api.get('/admin/windows/'+row.id)).data;detailTab.value='profiles';dialog.value=true}catch(e){error.value=errorText(e)}}
</script>
<template><main class="platform-page admin-workspace">
 <router-link to="/users" class="admin-back"><ArrowLeft :size="15"/>返回用户列表</router-link>
 <div class="page-heading admin-page-heading"><div><span class="admin-eyebrow">WORKSPACE / 业务数据</span><h1>用户业务数据</h1><p class="muted">按客户、房屋项目和窗型逐层查看用户的业务资料。</p></div><span class="admin-readonly"><ShieldCheck :size="16"/>只读浏览</span></div>
 <el-alert v-if="error" :title="error" type="error" :closable="false"/>
 <div class="admin-data-nav" role="tablist" aria-label="业务数据分类"><button v-for="entry in [{id:'customers',label:'客户',icon:Users},{id:'houses',label:'房屋项目',icon:HouseIcon},{id:'windows',label:'窗型',icon:PanelsTopLeft}]" :key="entry.id" role="tab" :aria-selected="tab===entry.id" :class="{selected:tab===entry.id}" @click="selectTab(entry.id)"><component :is="entry.icon" :size="18"/>{{entry.label}}</button></div>
 <section class="panel admin-list-panel">
  <div class="admin-list-toolbar"><div class="admin-section-title"><h2>{{tabLabel}}列表 <span class="admin-count">{{total}} 项</span></h2></div><div class="admin-search"><el-input v-model="q" clearable :placeholder="'搜索'+tabLabel+'名称'" :aria-label="'搜索'+tabLabel" @clear="page=1;load()" @keyup.enter="page=1;load()"><template #prefix><Search :size="15"/></template></el-input><el-button @click="page=1;load()">搜索</el-button></div></div>
  <div v-if="parent" class="admin-filter-scope"><span>当前范围：<strong>{{parentName}}</strong>下的{{tabLabel}}</span><el-button text type="primary" @click="clearParent">查看全部{{tabLabel}}</el-button></div>
  <section class="entity-grid admin-entity-grid">
   <article v-for="row in items" :key="row.id" class="admin-entity-card">
    <div class="admin-entity-heading"><span class="admin-section-icon"><Users v-if="'phone' in row" :size="21"/><HouseIcon v-else-if="'layout' in row" :size="21"/><PanelsTopLeft v-else :size="21"/></span><div><span class="admin-card-kind">{{tabLabel}}</span><h2>{{row.name}}</h2></div></div>
    <div class="admin-entity-body">
     <template v-if="'phone' in row"><p><span>联系电话</span><strong>{{row.phone||'未填写'}}</strong></p><p><span>客户地址</span><strong>{{row.address||'未填写'}}</strong></p><p v-if="row.notes" class="admin-card-note">{{row.notes}}</p></template>
     <template v-else-if="'layout' in row"><p><span>房屋户型</span><strong>{{row.layout||'未填写'}}</strong></p><p><span>项目地址</span><strong>{{row.address||'未填写'}}</strong></p><div class="admin-card-tags"><span>型材规格 {{row.stocks.length}} 种</span><span>{{Object.keys(row.glass_groups).join('、')||'未配置玻璃材料'}}</span></div><p v-if="row.notes" class="admin-card-note">{{row.notes}}</p></template>
     <template v-else><div class="admin-window-dimensions">{{mm(row.project.width)}}<span>×</span>{{mm(row.project.height)}}<small>mm</small></div><p class="admin-location"><MapPin :size="14"/>{{[row.floor,row.room].filter(Boolean).join(' / ')||'未填写安装位置'}}</p><p class="admin-location"><Layers :size="14"/>{{row.glass_material||'未填写玻璃材料'}}<span class="admin-count">{{row.project.quantity}} 樘</span></p></template>
    </div>
    <div class="admin-card-footer"><el-button v-if="tab!=='windows'" @click="descend(row)">{{tab==='customers'?'查看房屋项目':'查看项目窗型'}}<ArrowRight :size="14"/></el-button><el-button v-else @click="inspect(row)">查看窗型详情<ArrowRight :size="14"/></el-button></div>
   </article>
  </section>
  <el-empty v-if="!items.length" :description="q?'未找到匹配的'+tabLabel:'暂无'+tabLabel+'数据'" :image-size="90"/>
  <div class="admin-list-footer"><span>共 {{total}} 项{{tabLabel}}</span><el-pagination v-model:current-page="page" :total="total" :page-size="20" layout="prev,pager,next" @current-change="load"/></div>
 </section><el-dialog v-model="dialog" title="窗型详情" class="admin-window-dialog" width="min(1040px,94vw)" top="4vh" destroy-on-close>
 <template v-if="detail">
  <div class="admin-detail-overview">
   <div class="admin-detail-preview"><div class="admin-preview-label"><PanelsTopLeft :size="15"/>窗型结构预览</div><svg :viewBox="`0 0 ${detail.project.width} ${detail.project.height}`" role="img" aria-label="窗型结构预览"><polygon v-for="p in detail.geometry.parts" :key="p.id" :points="p.polygon.map(x=>x.join(',')).join(' ')" fill="#426e5b" stroke="#fff" stroke-width="500"/></svg><span class="admin-preview-scale">{{mm(detail.project.width)}} × {{mm(detail.project.height)}} mm</span></div>
   <div class="admin-detail-info"><span class="admin-readonly"><ShieldCheck :size="14"/>只读资料</span><h2>{{detail.name}}</h2><dl><div><dt>整体尺寸</dt><dd>{{mm(detail.project.width)}} × {{mm(detail.project.height)}} <small>mm</small></dd></div><div><dt>制作数量</dt><dd>{{detail.project.quantity}} 樘</dd></div><div><dt>楼层</dt><dd>{{detail.floor||'未填写'}}</dd></div><div><dt>安装位置</dt><dd>{{detail.room||'未填写'}}</dd></div><div class="admin-detail-material"><dt>玻璃材料</dt><dd>{{detail.glass_material||'未填写'}}</dd></div></dl></div>
  </div>
  <el-tabs v-model="detailTab" class="admin-detail-tabs">
   <el-tab-pane :label="'构件参数 · '+profileRows.length" name="profiles"><p class="admin-detail-note">各类构件对应的原料型号与型材宽度，单位为毫米。</p><el-table :data="profileRows" class="admin-detail-table"><el-table-column prop="label" label="构件类别" min-width="140"/><el-table-column prop="stock_key" label="原料型号" min-width="160"/><el-table-column label="宽度 / mm" width="140" align="right"><template #default="{row}">{{mm(row.width)}}</template></el-table-column></el-table></el-tab-pane>
   <el-tab-pane :label="'型材原料 · '+detail.stocks.length" name="stocks"><p class="admin-detail-note">当前窗型保存的原料规格与可用数量。</p><el-table :data="detail.stocks" class="admin-detail-table" empty-text="未配置型材原料"><el-table-column prop="stock_key" label="原料型号" min-width="130"/><el-table-column prop="id" label="规格名称" min-width="180" show-overflow-tooltip/><el-table-column label="长度 / mm" min-width="120" align="right"><template #default="{row}">{{mm(row.length)}}</template></el-table-column><el-table-column label="来源" width="110"><template #default="{row}">{{row.supply==='inventory'?'已有库存':'采购原料'}}</template></el-table-column><el-table-column label="可用数量" min-width="140" align="right"><template #default="{row}">{{row.available==null?'不限（可采购）':row.available+' 根'}}</template></el-table-column></el-table></el-tab-pane>
   <el-tab-pane :label="'玻璃原板 · '+detail.project.glass.stocks.length" name="glass"><p class="admin-detail-note">当前窗型保存的玻璃原板尺寸与可用数量。</p><el-table :data="detail.project.glass.stocks" class="admin-detail-table" empty-text="未配置玻璃原板"><el-table-column prop="id" label="规格名称" min-width="180" show-overflow-tooltip/><el-table-column label="原板尺寸 / mm" min-width="180"><template #default="{row}">{{mm(row.width)}} × {{mm(row.height)}}</template></el-table-column><el-table-column label="来源" width="110"><template #default="{row}">{{row.supply==='inventory'?'已有库存':'采购原料'}}</template></el-table-column><el-table-column label="可用数量" min-width="140" align="right"><template #default="{row}">{{row.available==null?'不限（可采购）':row.available+' 张'}}</template></el-table-column></el-table></el-tab-pane>
  </el-tabs>
 </template>
 <template #footer><span class="admin-detail-footer-note">资料仅供查看，修改请前往制作平台。</span><el-button @click="dialog=false">关闭详情</el-button></template>
 </el-dialog></main></template>
