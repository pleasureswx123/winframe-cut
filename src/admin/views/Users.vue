<script setup lang="ts">
import {ref,onMounted} from 'vue'
import {Search,Plus,Users,ArrowRight} from 'lucide-vue-next'
import {ElMessageBox,ElMessage,type FormInstance} from 'element-plus'
import {api,errorText} from '../../api'
import type {User,Page} from '../../business'
const items=ref<User[]>([]),total=ref(0),page=ref(1),q=ref(''),error=ref('')
async function load(){error.value='';try{const {data}=await api.get<Page<User>>('/admin/users',{params:{page:page.value,q:q.value}});items.value=data.items;total.value=data.total}catch(e){error.value=errorText(e)}}
const dialog=ref(false),form=ref<FormInstance>(),creating=ref(false),createError=ref('')
const draft=ref({username:'',display_name:'',password:''})
const rules={username:[{required:true,message:'请输入用户名'},{pattern:/^[a-zA-Z0-9_-]{3,40}$/,message:'3～40 位字母、数字、下划线或短横线'}],password:[{required:true,message:'请输入初始密码'},{min:10,max:128,message:'密码长度为 10～128 位'}]}
function openCreate(){draft.value={username:'',display_name:'',password:''};createError.value='';dialog.value=true}
async function create(){
 if(!await form.value?.validate().catch(()=>false))return
 creating.value=true;createError.value=''
 try{await api.post('/admin/users',draft.value);dialog.value=false;draft.value.password='';page.value=1;q.value='';await load();ElMessage.success('用户已创建，请将账号和初始密码发放给用户')}catch(e){createError.value=errorText(e)}finally{creating.value=false}
}
const resetDialog=ref(false),resetForm=ref<FormInstance>(),resetTarget=ref<User|null>(null),resetting=ref(false),resetError=ref('')
const resetDraft=ref({password:'',confirmation:''})
const resetRules={password:[{required:true,message:'请输入新密码'},{min:10,max:128,message:'密码长度为 10～128 位'}],confirmation:[{required:true,message:'请再次输入新密码'},{validator:(_:unknown,value:string,done:(e?:Error)=>void)=>done(value===resetDraft.value.password?undefined:new Error('两次输入的密码不一致'))}]}
function openReset(user:User){resetTarget.value=user;resetDraft.value={password:'',confirmation:''};resetError.value='';resetDialog.value=true}
function clearReset(){resetDraft.value={password:'',confirmation:''};resetTarget.value=null;resetError.value=''}
async function resetPassword(){
 if(resetting.value||!resetTarget.value||!await resetForm.value?.validate().catch(()=>false))return
 resetting.value=true;resetError.value=''
 try{await api.post('/admin/users/'+resetTarget.value.id+'/password',{password:resetDraft.value.password});resetDialog.value=false;resetDraft.value={password:'',confirmation:''};ElMessage.success('密码已重置，原登录已失效。请将新密码告知用户重新登录')}catch(e){resetError.value=errorText(e)}finally{resetting.value=false}
}
onMounted(load)
async function toggle(u:User){try{await ElMessageBox.confirm(`确认${u.active?'禁用':'启用'}用户 ${u.username}？禁用会立即使其登录失效。`,'账号状态');await api.patch('/admin/users/'+u.id,{active:!u.active});await load()}catch(e){if(e!=='cancel'&&e!=='close')error.value=errorText(e)}}
</script>
<template>
<main class="platform-page admin-workspace">
 <div class="page-heading admin-page-heading"><div><span class="admin-eyebrow">ACCOUNTS / 账号管理</span><h1>用户管理</h1><p class="muted">统一发放制作平台账号，管理用户权限与业务数据。</p></div><el-button type="primary" @click="openCreate"><Plus :size="16"/>添加用户</el-button></div>
 <el-alert v-if="error" :title="error" type="error" :closable="false"/>
 <section class="panel admin-list-panel">
  <div class="admin-list-toolbar"><div class="admin-section-title"><span class="admin-section-icon"><Users :size="21"/></span><h2>平台账号 <span class="admin-count">{{total}} 个</span></h2></div><div class="admin-search"><el-input v-model="q" clearable placeholder="搜索用户名或显示名称" aria-label="搜索用户" @clear="page=1;load()" @keyup.enter="page=1;load()"><template #prefix><Search :size="15"/></template></el-input><el-button @click="page=1;load()">搜索</el-button></div></div>
  <el-table :data="items" class="admin-data-table" empty-text="没有找到符合条件的用户">
   <el-table-column label="用户名" min-width="180"><template #default="{row}"><div class="admin-user-cell"><span class="admin-user-avatar">{{row.username.slice(0,1).toUpperCase()}}</span><strong>{{row.username}}</strong></div></template></el-table-column>
   <el-table-column label="显示名称" min-width="140"><template #default="{row}">{{row.display_name||'未设置'}}</template></el-table-column>
   <el-table-column label="角色" min-width="120"><template #default="{row}"><span class="admin-role" :class="{privileged:row.role==='admin'}">{{row.role==='admin'?'管理员':'普通用户'}}</span></template></el-table-column>
   <el-table-column label="状态" min-width="100"><template #default="{row}"><span class="admin-status" :class="{inactive:!row.active}">{{row.active?'启用':'禁用'}}</span></template></el-table-column>
   <el-table-column label="操作" min-width="320"><template #default="{row}"><div class="admin-row-actions"><router-link :to="'/users/'+row.id" class="admin-data-link">查看数据<ArrowRight :size="14"/></router-link><el-button v-if="row.role!=='admin'" text type="primary" @click="openReset(row)">重置密码</el-button><el-button v-if="row.role!=='admin'" text :type="row.active?'danger':'primary'" @click="toggle(row)">{{row.active?'禁用':'启用'}}</el-button></div></template></el-table-column>
  </el-table>
  <div class="admin-list-footer"><span>共 {{total}} 个账号</span><el-pagination v-model:current-page="page" :total="total" :page-size="20" layout="prev,pager,next" @current-change="load"/></div>
 </section><el-dialog v-model="dialog" title="添加制作平台用户" width="min(480px,94vw)" destroy-on-close :close-on-click-modal="false" :show-close="!creating"><p class="muted">创建普通用户账号，用户只能访问自己的客户、项目与窗型。</p><el-alert v-if="createError" :title="createError" type="error" :closable="false"/><el-form ref="form" :model="draft" :rules="rules" label-position="top" :disabled="creating"><el-form-item label="用户名" prop="username"><el-input v-model="draft.username" autocomplete="off" maxlength="40"/></el-form-item><el-form-item label="显示名称"><el-input v-model="draft.display_name" maxlength="80"/></el-form-item><el-form-item label="初始密码" prop="password"><el-input v-model="draft.password" type="password" show-password autocomplete="new-password" maxlength="128"/></el-form-item></el-form><template #footer><el-button :disabled="creating" @click="dialog=false">取消</el-button><el-button type="primary" :loading="creating" @click="create">创建用户</el-button></template></el-dialog><el-dialog v-model="resetDialog" title="重置用户密码" width="min(480px,94vw)" destroy-on-close :close-on-click-modal="false" :close-on-press-escape="!resetting" :show-close="!resetting" @closed="clearReset"><p class="muted" style="margin-bottom:16px">账号：<strong>{{resetTarget?.username}}</strong>（{{resetTarget?.display_name}}）</p><el-alert title="重置后，旧密码和该用户所有已登录会话立即失效；用户需要使用新密码重新登录。" type="warning" :closable="false"/><el-alert v-if="resetError" :title="resetError" type="error" :closable="false"/><el-form ref="resetForm" :model="resetDraft" :rules="resetRules" :disabled="resetting" label-position="top" style="margin-top:20px"><el-form-item label="新密码" prop="password"><el-input v-model="resetDraft.password" type="password" show-password autocomplete="new-password" maxlength="128"/></el-form-item><el-form-item label="确认新密码" prop="confirmation"><el-input v-model="resetDraft.confirmation" type="password" show-password autocomplete="new-password" maxlength="128"/></el-form-item></el-form><template #footer><el-button :disabled="resetting" @click="resetDialog=false">取消</el-button><el-button type="primary" :loading="resetting" @click="resetPassword">确认重置密码</el-button></template></el-dialog></main></template>
