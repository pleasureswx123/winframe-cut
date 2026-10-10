<script setup lang="ts">
import { useWorkshop } from '../store'
import { mm, areaM2 } from '../types'
import { csv, download } from '../export'
const s=useWorkshop()
function exportGlass(){download(`${s.project!.name}-玻璃清单.csv`,csv([['玻璃编号','所属区域','类别','宽mm','高mm','数量','单块面积m²','左上Xmm','左上Ymm','左右覆盖mm','上下覆盖mm'],...s.geometry!.glasses.map(g=>[g.id,g.region_id,g.label,mm(g.width),mm(g.height),g.quantity,areaM2(g.area),mm(g.rect.x),mm(g.rect.y),mm(g.overlap.x),mm(g.overlap.y)])]),'text/csv;charset=utf-8')}
</script>
<template><section class="panel glass-schedule"><div class="panel-heading"><h2>玻璃下料清单 <small>{{s.geometry!.glass_count}} 块</small></h2><el-button :disabled="!!s.geometry!.glass_warnings.length" @click="exportGlass">导出玻璃 CSV</el-button></div><p class="muted">有压线的玻璃区自动生成；总面积 {{areaM2(s.geometry!.glass_area)}} m²。玻璃与型材分别排料。</p><div class="glass-list"><article v-for="g in s.geometry!.glasses" :key="g.id" class="glass-item"><div><b>{{g.label}}</b><small>{{g.id}}</small></div><strong>{{mm(g.width)}} × {{mm(g.height)}} <small>mm</small></strong><span>{{g.quantity}} 块 · {{areaM2(g.area)}} m² / 块</span><small>每边覆盖：左右 {{mm(g.overlap.x)}} / 上下 {{mm(g.overlap.y)}} mm</small></article></div><el-empty v-if="!s.geometry!.glass_count" description="当前窗型没有玻璃区域"/></section></template>
