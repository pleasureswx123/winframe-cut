<script setup lang="ts">
import {ref,onMounted} from 'vue'
import {useRoute} from 'vue-router'
import {ElMessageBox} from 'element-plus'
import {ArrowLeft,ArrowRight,Plus,Search,PanelsTopLeft,Scissors,MapPin,House as HouseIcon,Layers} from 'lucide-vue-next'
import {api,errorText} from '../api'
import type {Customer,House,WindowRecord,Page} from '../business'
import {mm} from '../types'
const route=useRoute(),house=ref<House|null>(null),customer=ref<Customer|null>(null),items=ref<WindowRecord[]>([]),error=ref(''),page=ref(1),total=ref(0),q=ref(''),loading=ref(false)
async function load(){loading.value=true;error.value='';try{house.value=(await api.get<House>('/houses/'+route.params.id)).data;customer.value=null;customer.value=(await api.get<Customer>('/customers/'+house.value.customer_id)).data;const {data}=await api.get<Page<WindowRecord>>('/windows',{params:{house_id:route.params.id,page:page.value,page_size:12,q:q.value}});items.value=data.items;total.value=data.total}catch(e){error.value=errorText(e)}finally{loading.value=false}}
onMounted(load)
async function remove(row:WindowRecord){try{await ElMessageBox.confirm('确认删除窗型“'+row.name+'”？','删除窗型',{type:'warning'});await api.delete('/windows/'+row.id);await load()}catch(e){if(e!=='cancel'&&e!=='close')error.value=errorText(e)}}
</script>
<template>
<main class="platform-page customer-workspace house-workspace">
<el-alert v-if="error" :title="error" type="error" :closable="false"/>
<template v-if="house">
<div class="page-heading house-page-heading"><div><router-link class="house-back" :to="'/customers/'+house.customer_id+'/houses'"><ArrowLeft :size="14"/>客户房屋</router-link><div class="house-title-row"><h1>{{house.name}}</h1><router-link v-if="customer" class="project-customer-tag" :to="'/customers/'+customer.id+'/houses'"><span>所属客户</span>{{customer.name}}</router-link></div><div class="house-metadata"><span v-if="house.layout"><HouseIcon :size="14"/>{{house.layout}}</span><span v-if="house.address"><MapPin :size="14"/>{{house.address}}</span><span v-if="!house.layout&&!house.address">按楼层与房间管理窗型，支持单窗和整项目排料。</span></div></div><div class="action-row house-actions"><router-link :to="{path:'/design',query:{houseId:house.id}}"><el-button type="primary"><Plus :size="16"/>新增窗型</el-button></router-link><router-link :to="'/houses/'+house.id+'/cutting'"><el-button><Scissors :size="16"/>整项目统一排料</el-button></router-link></div></div>
<section class="panel customer-library window-library"><div class="customer-library-toolbar"><div class="customer-library-title"><h2>项目窗型</h2><span>{{loading?'加载中':(q?'匹配 ':'')+total+' 种窗型'}}</span></div><div class="search-row"><el-input v-model="q" :prefix-icon="Search" aria-label="搜索窗型名称" placeholder="搜索窗型名称" clearable @clear="page=1;load()" @keyup.enter="page=1;load()"/><el-button @click="page=1;load()">搜索</el-button></div></div>
<section v-loading="loading" class="entity-grid" :class="{'has-items':items.length}"><article v-for="row in items" :key="row.id" class="panel entity-card customer-card window-card"><div class="customer-card-heading"><span class="customer-card-icon"><PanelsTopLeft :size="22"/></span><div><span class="window-location">{{row.floor||'未标楼层'}} / {{row.room||'未标位置'}}</span><h2>{{row.name}}</h2></div><span class="window-quantity">{{row.project.quantity}} 樘</span></div><div class="window-dimensions"><strong>{{mm(row.project.width)}} <span>×</span> {{mm(row.project.height)}}</strong><small>mm · 整窗尺寸</small></div><p class="customer-detail"><Layers :size="14"/>{{row.glass_material}}</p><div class="action-row"><router-link :to="{path:'/design',query:{windowId:row.id}}"><el-button type="primary" plain>编辑窗型<ArrowRight :size="14"/></el-button></router-link><router-link :to="{path:'/cutting',query:{windowId:row.id}}"><el-button>单窗排料</el-button></router-link><el-button type="danger" text @click="remove(row)">删除</el-button></div></article></section>
<div v-if="!loading&&!items.length&&!error" class="customer-empty"><div class="customer-empty-icon"><component :is="q?Search:PanelsTopLeft" :size="34" :stroke-width="1.4"/></div><h2>{{q?'未找到匹配的窗型':'添加这个项目的第一个窗型'}}</h2><p>{{q?'换个名称试试，或清空搜索查看全部窗型。':'为每个房间建立窗型，记录尺寸和制作数量，再按单窗或整个项目安排下料。'}}</p><el-button v-if="q" @click="q='';page=1;load()">清空搜索</el-button><router-link v-else :to="{path:'/design',query:{houseId:house.id}}"><el-button type="primary"><Plus :size="16"/>新增窗型</el-button></router-link><div v-if="!q" class="customer-flow"><span><PanelsTopLeft :size="15"/>设计窗型</span><ArrowRight :size="14"/><span><Layers :size="15"/>保存到项目</span><ArrowRight :size="14"/><span><Scissors :size="15"/>计算排料</span></div></div>
<el-pagination v-if="total>12" v-model:current-page="page" :page-size="12" :total="total" layout="prev,pager,next" @current-change="load"/>
</section>
</template>
</main>
</template>
