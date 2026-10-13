<script setup lang="ts">
import {ref,onMounted} from 'vue'
import {Users,ContactRound,House as HouseIcon,PanelsTopLeft,ArrowRight} from 'lucide-vue-next'
import {api,errorText} from '../../api'
const counts=ref<Record<string,number>>({}),error=ref('')
const metrics=[{key:'users',label:'平台用户',note:'平台内全部账号',icon:Users},{key:'customers',label:'客户总数',note:'用户管理的客户资料',icon:ContactRound},{key:'houses',label:'房屋项目',note:'客户名下的房屋项目',icon:HouseIcon},{key:'windows',label:'窗型存档',note:'平台内已保存的窗型',icon:PanelsTopLeft}]
async function load(){try{counts.value=(await api.get('/admin/summary')).data}catch(e){error.value=errorText(e)}}
onMounted(load)
</script>
<template><main class="platform-page admin-dashboard">
<div class="page-heading admin-page-heading"><div><span class="admin-eyebrow">管理工作台 / OVERVIEW</span><h1>平台总览</h1><p class="muted">查看平台数据，管理用户及客户项目。</p></div><router-link to="/users"><el-button type="primary"><Users :size="16"/>管理用户<ArrowRight :size="16"/></el-button></router-link></div>
<el-alert v-if="error" :title="error" type="error" :closable="false"/>
<section class="admin-stats" aria-label="平台数据概览"><article v-for="metric in metrics" :key="metric.key" class="panel admin-stat-card"><div class="admin-stat-top"><span>{{metric.label}}</span><span class="admin-stat-icon"><component :is="metric.icon" :size="20"/></span></div><strong>{{counts[metric.key]??'—'}}</strong><p>{{metric.note}}</p></article></section>
</main></template>
