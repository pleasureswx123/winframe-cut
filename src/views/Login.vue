<script setup lang="ts">
import {ref} from 'vue'
import {ArrowLeft,ArrowRight,UserRound,LockKeyhole} from 'lucide-vue-next'
import WindowLogo from '../components/WindowLogo.vue'
import {useRouter} from 'vue-router'
import {type FormInstance} from 'element-plus'
import {useAuth} from '../auth'
import {errorText} from '../api'
const props=defineProps<{admin?:boolean}>()
const auth=useAuth(),router=useRouter(),form=ref<FormInstance>(),busy=ref(false),error=ref('')
const data=ref({username:'',password:'',display_name:''})
const rules={username:[{required:true,message:'请输入用户名'},{pattern:/^[a-zA-Z0-9_-]{3,40}$/,message:'3～40 位字母、数字、下划线或短横线'}],password:[{required:true,message:'请输入密码'},{max:128,message:'密码最多 128 位'}]}
async function submit(){
  if(busy.value)return
  if(!await form.value?.validate().catch(()=>false))return
  busy.value=true;error.value=''
  try{
    await auth.login(data.value.username,data.value.password)
    if(props.admin&&auth.user?.role!=='admin'){await auth.logout();throw Error('此入口仅供平台管理员使用')}
    await router.replace(props.admin?'/':'/customers')
  }catch(e){error.value=errorText(e)}finally{busy.value=false}
}
</script>
<template>
<main class="login-page branded-login">
  <section class="login-card panel" aria-labelledby="login-title">
    <div class="login-brand"><WindowLogo/><div><strong>窗序</strong><span>WINFRAME</span></div><span class="login-platform-tag">{{admin?'管理平台':'制作平台'}}</span></div>
    <div class="login-heading"><h1 id="login-title">{{admin?'登录管理平台':'登录制作平台'}}</h1><p>{{admin?'管理平台用户，查看客户与项目数据。':'从客户与项目开始，完成窗型设计与切割排料。'}}</p></div>
    <el-alert v-if="error" :title="error" type="error" show-icon :closable="false"/>
    <el-form ref="form" :model="data" :rules="rules" :disabled="busy" label-position="top" size="large">
      <el-form-item label="用户名" prop="username"><el-input v-model="data.username" :prefix-icon="UserRound" placeholder="请输入用户名" autocomplete="username" maxlength="40"/></el-form-item>
      <el-form-item label="密码" prop="password"><el-input v-model="data.password" :prefix-icon="LockKeyhole" placeholder="请输入密码" type="password" show-password autocomplete="current-password" maxlength="128" @keyup.enter="submit"/></el-form-item>
      <el-button class="full-button login-submit" type="primary" size="large" :loading="busy" @click="submit">{{busy?'正在登录…':'登录'}}<ArrowRight v-if="!busy" :size="17"/></el-button>
    </el-form>
    <div class="login-card-footer"><a v-if="admin" href="/#/login" class="login-switch"><ArrowLeft :size="16"/>返回制作平台</a><p v-else>账号由管理员统一发放<br/><span>忘记密码？请联系管理员重置。</span></p></div>
  </section>
  <p class="login-page-caption">窗序 · 窗型设计与智能下料</p>
</main>
</template>
<style scoped>
.branded-login{position:relative;min-height:100dvh;align-content:center;gap:22px;padding:40px 20px;background:radial-gradient(ellipse at 25% 20%,#e1ece5 0,transparent 55%),#f5f5ef}
.branded-login .login-card{width:100%;max-width:460px;padding:36px;border-radius:18px;border:1px solid #e0e7df;box-shadow:0 16px 48px #254e4010}
.login-brand{display:flex;align-items:center;gap:14px;padding-bottom:26px;border-bottom:1px solid #e9eee7}
.login-brand>svg{flex-shrink:0}
.login-brand strong{display:block;font-size:26px;letter-spacing:3px;line-height:1.3;color:#25483b}
.login-brand>div>span{display:block;margin-top:5px;font-size:10px;letter-spacing:2.6px;color:#73877c}
.login-platform-tag{margin-left:auto;padding:6px 10px;border:1px solid #dde8df;border-radius:6px;background:#f1f6f2;font-size:11px;white-space:nowrap;color:#52735f}
.login-heading{margin:26px 0}
.branded-login h1{font-size:24px;line-height:1.4;margin:0 0 10px;letter-spacing:0}
.login-heading p{font-size:13px;line-height:1.8;color:#78897e;margin:0}
.branded-login .el-form{margin-top:24px}
.branded-login :deep(.el-form-item){margin-bottom:24px}
.branded-login :deep(.el-form-item__label){font-size:13px;color:#425e4f;padding-bottom:7px}
.branded-login :deep(.el-input__wrapper){min-height:44px;border-radius:8px;background:#fafcf9}
.branded-login :deep(.el-input__prefix){margin-right:6px;color:#8a9e91}
.login-submit{width:100%;height:46px;margin-top:4px;border-radius:8px;font-size:15px;letter-spacing:2px}
.login-card-footer{border-top:1px solid #e9eee7;margin-top:26px;padding-top:20px;text-align:center}
.login-switch{display:inline-flex;align-items:center;justify-content:center;gap:8px;min-height:40px;padding:0 14px;border-radius:8px;color:#52735f;font-size:13px;transition:background .15s,color .15s}
.login-switch:hover{background:#edf4ee;color:#285347}
.login-switch:focus-visible{outline:2px solid #52735f;outline-offset:3px}
.login-card-footer p{font-size:12px;color:#62796a;line-height:1.9;margin:0}
.login-card-footer p span{color:#8b9b8e}
.login-page-caption{margin:0;font-size:11px;letter-spacing:1.5px;color:#899a8b;text-align:center}
@media(max-width:480px){.branded-login{padding:28px 16px;gap:18px}.branded-login .login-card{padding:26px 22px}.login-brand{gap:12px}.login-platform-tag{padding:5px 7px}.branded-login h1{font-size:22px}}
</style>
