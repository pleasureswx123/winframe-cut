<script setup lang="ts">
import { ref, watch } from 'vue'
import { mm } from '../types'
const props=withDefaults(defineProps<{modelValue:number;label?:string;min?:number;disabled?:boolean}>(),{min:0})
const emit=defineEmits<{ 'update:modelValue':[value:number] }>()
const text=ref(mm(props.modelValue)),invalid=ref(false)
watch(()=>props.modelValue,v=>{if(Number.isFinite(v)){text.value=mm(v);invalid.value=false}})
function apply(){
  if(!/^-?\d+(\.\d{1,3})?$/.test(text.value)){invalid.value=true;emit('update:modelValue',NaN);return}
  const v=Number(text.value)*2000
  if(!Number.isSafeInteger(Math.round(v))||Math.abs(v-Math.round(v))>1e-5||v<props.min||v>200000000){invalid.value=true;emit('update:modelValue',NaN);return}
  emit('update:modelValue',Math.round(v));invalid.value=false;text.value=mm(Math.round(v))
}
</script>
<template><div class="length-input"><el-input v-model="text" inputmode="decimal" :aria-label="label" :disabled="disabled" :class="{'invalid-input':invalid}" @change="apply" @blur="apply"><template #suffix>mm</template></el-input><small v-if="invalid" class="field-error">请输入有效尺寸（最多三位小数）</small></div></template>
