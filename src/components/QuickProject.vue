<script setup lang="ts">
import {ref} from 'vue'
import {FolderPlus} from 'lucide-vue-next'
import {useRouter} from 'vue-router'
import {type FormInstance,ElMessage} from 'element-plus'
import {api,errorText} from '../api'
import {useWorkshop} from '../store'
const s=useWorkshop(),router=useRouter(),visible=ref(false),form=ref<FormInstance>(),busy=ref(false),error=ref(''),createdCustomer=ref('')
const draft=ref({customer_name:'',phone:'',house_name:'',address:'',layout:''})
function open(){createdCustomer.value='';error.value='';draft.value={customer_name:'',phone:'',house_name:'',address:'',layout:''};visible.value=true}
async function save(){
 if(!await form.value?.validate().catch(()=>false))return
 busy.value=true;error.value='';const token=s.workspaceToken()
 try{
  if(!createdCustomer.value)createdCustomer.value=(await api.post('/customers',{name:draft.value.customer_name,phone:draft.value.phone,address:draft.value.address})).data.id
  const {data}=await api.post('/houses',{customer_id:createdCustomer.value,name:draft.value.house_name,address:draft.value.address,layout:draft.value.layout})
  if(token!==s.workspaceToken())return
  s.context.house_id=data.id;s.savedId=null;s.invalidate();s.persist();visible.value=false
  await router.replace({path:'/design',query:{houseId:data.id}})
  ElMessage.success('已建立客户与房屋项目，请保存当前窗型')
 }catch(e){if(token===s.workspaceToken())error.value=errorText(e)}finally{busy.value=false}
}
</script>
<template><el-button text :disabled="s.busy||s.saving" @click="open"><FolderPlus :size="15"/>新建客户与项目</el-button><el-dialog v-model="visible" title="为当前窗型新建客户与项目" :close-on-click-modal="false" :show-close="!busy" width="min(520px,94vw)"><p class="muted">当前设计会作为新项目的新窗型，原存档保留。建立后点击保存窗型完成归档。</p><el-alert v-if="error" :title="error" type="error" :closable="false"/><el-form ref="form" :model="draft" label-position="top" :disabled="busy"><el-form-item label="客户名称" prop="customer_name" :rules="[{required:true,whitespace:true,message:'请输入客户名称'}]"><el-input v-model="draft.customer_name" :disabled="!!createdCustomer" maxlength="100"/></el-form-item><el-form-item label="联系电话"><el-input v-model="draft.phone" :disabled="!!createdCustomer" maxlength="40"/></el-form-item><el-form-item label="房屋项目名称" prop="house_name" :rules="[{required:true,whitespace:true,message:'请输入房屋项目名称'}]"><el-input v-model="draft.house_name" maxlength="100"/></el-form-item><el-form-item label="地址"><el-input v-model="draft.address" maxlength="300"/></el-form-item><el-form-item label="户型描述"><el-input v-model="draft.layout" maxlength="100"/></el-form-item></el-form><template #footer><el-button :disabled="busy" @click="visible=false">取消</el-button><el-button :loading="busy" type="primary" @click="save">建立并使用新项目</el-button></template></el-dialog></template>
