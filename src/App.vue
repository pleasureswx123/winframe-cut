<script setup lang="ts">
import { onMounted } from 'vue'
import { useWorkshop } from './store'
const s=useWorkshop();onMounted(()=>s.init())
</script>
<template><router-view/></template>
