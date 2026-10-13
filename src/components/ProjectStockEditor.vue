<script setup lang="ts">
import {ref,nextTick} from 'vue'
import {ElMessageBox,type FormInstance} from 'element-plus'
import {mm,money,T,type Stock,type GlassStock} from '../types'
import {newId} from '../id'
import LengthInput from './LengthInput.vue'
const props=defineProps<{modelValue:(Stock|GlassStock)[];mode:'profiles'|'glass';keys?:string[];material?:string}>()
const emit=defineEmits<{'update:modelValue':[value:any[]];change:[]}>()
const open=ref(false),form=ref<FormInstance>(),editing=ref(-1)
const blank=()=>({id:newId(),stock_key:props.keys?.[0]??'',length:6000*T,width:2440*T,height:1830*T,price_cents:0,available:null as number|null,supply:'purchase' as 'purchase'|'inventory'})
const draft=ref(blank())
function edit(index=-1,supply:'purchase'|'inventory'='purchase'){
 editing.value=index;draft.value=index<0?{...blank(),supply,available:supply==='inventory'?1:null}:{...blank(),...props.modelValue[index]}
 open.value=true;nextTick(()=>form.value?.clearValidate())
}
const positive=(_r:unknown,value:number,done:(error?:Error)=>void)=>done(Number.isSafeInteger(value)&&value>0&&value<=100000*T?undefined:new Error('请输入大于 0 的有效尺寸'))
const quantity=(_r:unknown,value:number|null,done:(error?:Error)=>void)=>done(value===null&&draft.value.supply==='purchase'||Number.isInteger(value)&&value!==null&&value>=0&&value<=500?undefined:new Error('库存需填写 0 至 500 的整数'))
async function confirm(){
 if(!await form.value?.validate().catch(()=>false))return
 const d=draft.value,common={id:d.id,supply:d.supply,price_cents:d.supply==='inventory'?0:d.price_cents,available:d.available}
 const value=props.mode==='profiles'?{...common,stock_key:d.stock_key,length:d.length}:{...common,width:d.width,height:d.height}
 const rows=[...props.modelValue];if(editing.value<0)rows.push(value);else rows[editing.value]=value
 emit('update:modelValue',rows);emit('change');open.value=false
}
async function remove(index:number){try{await ElMessageBox.confirm('仅从当前项目的排料配置中移除此规格，不会扣减实际库存。','移除原料',{type:'warning'});emit('update:modelValue',props.modelValue.filter((_,i)=>i!==index));emit('change')}catch{}}
</script>
<template><div class="project-material-editor"><div class="action-row" style="margin:16px 0"><el-button @click="edit(-1,'inventory')">添加库存余料</el-button><el-button @click="edit(-1,'purchase')">添加采购规格</el-button></div>
<el-table :data="modelValue" empty-text="请添加采购规格或已有库存"><el-table-column v-if="mode==='profiles'" prop="stock_key" label="型号" min-width="110"/><el-table-column label="来源" width="115"><template #default="{row}"><el-tag :type="row.supply==='inventory'?'success':'info'">{{row.supply==='inventory'?'已有库存':'需要采购'}}</el-tag></template></el-table-column><el-table-column label="可用尺寸" min-width="160"><template #default="{row}">{{mode==='profiles'?mm(row.length):mm(row.width)+' × '+mm(row.height)}} mm</template></el-table-column><el-table-column label="本次采购单价" min-width="130"><template #default="{row}">{{row.supply==='inventory'?'不计采购费用':row.price_cents?money(row.price_cents)+' 元':'未录价'}}</template></el-table-column><el-table-column label="可用数量" min-width="110"><template #default="{row}">{{row.available===null?'不限量':row.available+(mode==='profiles'?' 根':' 张')}}</template></el-table-column><el-table-column label="操作" width="125"><template #default="{row,$index}"><el-button link @click="edit($index)">编辑</el-button><el-button link type="danger" @click="remove($index)">移除</el-button></template></el-table-column></el-table>
<el-dialog v-model="open" :title="(editing<0?'添加':'编辑')+(material?material+' · ':'')+'原料'" width="min(520px,94vw)" append-to-body :close-on-click-modal="false"><el-form ref="form" :model="draft" label-position="top"><el-form-item label="来源"><el-radio-group v-model="draft.supply" @change="draft.supply==='inventory'&&(draft.available??=1)"><el-radio-button value="inventory">已有库存</el-radio-button><el-radio-button value="purchase">需要采购</el-radio-button></el-radio-group></el-form-item><el-alert :closable="false" type="info" :title="draft.supply==='inventory'?'已有库存仅用于本项目试算，不计本次采购费用，重复计算不会扣库存。':'采购规格可设置供应数量上限；留空表示可采购、不限量。'" style="margin-bottom:16px"/>
<el-form-item v-if="mode==='profiles'" prop="stock_key" label="原料型号" :rules="[{required:true,message:'请选择原料型号'}]"><el-select v-model="draft.stock_key"><el-option v-for="key in keys" :key="key" :label="key" :value="key"/></el-select></el-form-item><el-form-item v-if="mode==='profiles'" prop="length" label="可用长度" :rules="[{validator:positive}]"><LengthInput v-model="draft.length" label="可用长度"/></el-form-item><div v-else class="two-cols"><el-form-item prop="width" label="可用宽度" :rules="[{validator:positive}]"><LengthInput v-model="draft.width" label="可用宽度"/></el-form-item><el-form-item prop="height" label="可用高度" :rules="[{validator:positive}]"><LengthInput v-model="draft.height" label="可用高度"/></el-form-item></div><el-form-item prop="available" :label="draft.supply==='inventory'?'实际库存数量（必填）':'可采购数量上限（可留空）'" :rules="[{validator:quantity}]"><el-input-number :model-value="draft.available" :min="0" :max="500" :precision="0" :controls="false" @update:model-value="(v:number|undefined)=>draft.available=v??null"/></el-form-item><el-form-item v-if="draft.supply==='purchase'" prop="price_cents" label="采购单价 / 元" :rules="[{type:'number',min:0,max:10000000,required:true,message:'请输入有效单价'}]"><el-input-number :model-value="draft.price_cents/100" :min="0" :max="100000" :precision="2" :controls="false" @update:model-value="(v:number|undefined)=>draft.price_cents=Math.round((v??0)*100)"/></el-form-item></el-form><template #footer><el-button @click="open=false">取消</el-button><el-button type="primary" @click="confirm">确认</el-button></template></el-dialog></div></template>
