<script setup lang="ts">
import {useRouter,useRoute} from 'vue-router'
import {ElMessageBox} from 'element-plus'
import {PanelsTopLeft,ContactRound,ArrowUpRight,UserRound,LogOut} from 'lucide-vue-next'
import './studio.css'
import {useAuth} from './auth'
import { useWorkshop } from './store'
const auth=useAuth(),s=useWorkshop(),router=useRouter(),route=useRoute()
async function logout(){if(s.dirty||s.parameterDraftDirty||s.glassDraftDirty){try{await ElMessageBox.confirm('当前窗型尚未保存，确认退出账号？本账号草稿会保留。','退出登录')}catch{return}}await auth.logout();await router.replace('/login')}
</script>
<template><header v-if="auth.user" class="studio-header no-print" :class="{'is-workbench':!!route.params.tab}"><div class="studio-header-inner"><router-link to="/customers" class="studio-brand" aria-label="窗序制作平台首页"><span class="studio-brand-icon"><PanelsTopLeft :size="23"/></span><span><strong>窗序 <small>WINFRAME</small></strong><span class="studio-brand-caption">制作平台</span></span></router-link><nav class="studio-nav" aria-label="制作平台导航"><router-link to="/customers" title="查看全部客户与项目" :class="{selected:route.path.startsWith('/customers')||route.path.startsWith('/houses')}" :aria-current="route.path.startsWith('/customers')||route.path.startsWith('/houses')?'page':undefined"><ContactRound :size="17"/>客户与项目</router-link></nav><div class="studio-account-actions"><a v-if="auth.user.role==='admin'" href="/admin.html" class="studio-admin-link">管理平台<ArrowUpRight :size="15"/></a><div class="studio-account"><span class="studio-avatar"><UserRound :size="18"/></span><span><b>{{auth.user.display_name}}</b><small>个人工作区</small></span></div><el-button text aria-label="退出登录" title="退出登录" @click="logout"><LogOut :size="17"/><span class="studio-logout-text">退出登录</span></el-button></div></div></header><router-view :key="$route.path.startsWith('/customers')?$route.fullPath:undefined"/></template>
