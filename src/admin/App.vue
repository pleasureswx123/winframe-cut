<script setup lang="ts">
import {useAuth} from '../auth'
import {useRouter,useRoute} from 'vue-router'
import {PanelsTopLeft,LayoutDashboard,Users,ArrowUpRight,LogOut,ShieldCheck} from 'lucide-vue-next'
const auth=useAuth(),router=useRouter(),route=useRoute()
async function logout(){await auth.logout();await router.replace('/login')}
</script>
<template>
<div class="admin-shell">
<header v-if="auth.user?.role==='admin'" class="admin-header no-print">
 <div class="admin-header-inner">
  <router-link to="/" class="admin-brand" aria-label="窗序管理平台首页"><span class="admin-brand-icon"><PanelsTopLeft :size="23"/></span><span><strong>窗序 <small>WINFRAME</small></strong><span class="admin-brand-caption">管理平台</span></span></router-link>
  <nav class="admin-menu" aria-label="管理平台导航">
   <router-link to="/" :class="{selected:route.path==='/'}" :aria-current="route.path==='/'?'page':undefined"><LayoutDashboard :size="17"/>平台总览</router-link>
   <router-link to="/users" :class="{selected:route.path.startsWith('/users')}" :aria-current="route.path.startsWith('/users')?'page':undefined"><Users :size="17"/>用户管理</router-link>
  </nav>
  <div class="admin-account-actions">
   <a href="/" class="admin-workshop-link">制作平台 <ArrowUpRight :size="15"/></a>
   <div class="admin-account"><span class="admin-avatar"><ShieldCheck :size="19"/></span><span><b>{{auth.user.display_name}}</b><small>平台管理员</small></span></div>
   <el-button text aria-label="退出登录" title="退出登录" @click="logout"><LogOut :size="17"/><span class="admin-logout-text">退出</span></el-button>
  </div>
 </div>
</header>
<router-view/>
</div>
</template>
