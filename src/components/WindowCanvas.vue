<script setup lang="ts">
import { ref, computed } from 'vue'
import { useWorkshop } from '../store'
import { mm, T, type Region } from '../types'
const s=useWorkshop(),zoom=ref(100),svg=ref<SVGSVGElement>()
const emit=defineEmits<{ draw:[id:string,axis:'x'|'y',position:number];editSplit:[id:string] }>()
const w=computed(()=>s.project!.width/T),h=computed(()=>s.project!.height/T)
const margin=computed(()=>Math.max(w.value,h.value)*0.085)
const font=computed(()=>Math.max(w.value,h.value)/45)
const leaves=computed(()=>s.geometry?.regions.filter(r=>r.kind==='glass'||r.kind==='empty')??[])
function clickRegion(e:MouseEvent,r:Region){
  s.selected=r.id
  if(s.tool==='select'||!svg.value)return
  const pt=svg.value.createSVGPoint();pt.x=e.clientX;pt.y=e.clientY
  const local=pt.matrixTransform(svg.value.getScreenCTM()!.inverse())
  emit('draw',r.id,s.tool,Math.round(s.tool==='x'?local.x:local.y)*T)
}
</script>
<template>
  <div class="canvas-shell">
    <div class="canvas-topline"><span><i class="status-dot"/> 实时尺寸视图</span><span>左上角原点 · 单位 mm</span></div>
    <div class="drawing-scroll">
      <svg v-if="s.project&&s.geometry" ref="svg" class="window-svg" :style="{width:zoom+'%',minWidth:zoom+'%',height:zoom+'%'}" :viewBox="`${-margin} ${-margin} ${w+2*margin} ${h+2*margin}`" role="img" aria-label="窗型设计画布">
        <defs><pattern id="glass-lines" width="32" height="32" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><line y2="32" stroke="#cbded8" stroke-width="1"/></pattern></defs>
        <g :font-size="font" font-family="inherit">
          <g stroke="#8aa39b" :stroke-width="font/35" fill="none">
            <path :d="`M0 ${-margin*.2} V${-margin*.6} H${w} V${-margin*.2}`"/><path :d="`M${-margin*.2} 0 H${-margin*.6} V${h} H${-margin*.2}`"/>
          </g>
          <text :x="w/2" :y="-margin*.7" text-anchor="middle" fill="#46645c">{{mm(s.project.width)}} mm</text>
          <text :transform="`translate(${-margin*.72},${h/2}) rotate(-90)`" text-anchor="middle" fill="#46645c">{{mm(s.project.height)}} mm</text>
          <g v-for="r in leaves" :key="r.id" class="region-hit" :class="{'drawing-tool':s.tool!=='select'}" @click.stop="clickRegion($event,r)">
            <rect :x="r.rect.x/T" :y="r.rect.y/T" :width="r.rect.w/T" :height="r.rect.h/T" :fill="r.kind==='empty'?'#f7faf8':r.context==='sash'?'#e5efe9':'#eaf3f0'"/>
            <rect v-if="r.glass" :x="r.glass.x/T" :y="r.glass.y/T" :width="r.glass.w/T" :height="r.glass.h/T" fill="#b8d9e0" stroke="#7eafb9" :stroke-width="font/30"><title>玻璃 {{mm(r.glass.w)}} × {{mm(r.glass.h)}} mm</title></rect>
            <text :x="(r.rect.x+r.rect.w/2)/T" :y="(r.rect.y+r.rect.h/2)/T-font*.25" text-anchor="middle" fill="#527368" :font-size="font*.9">{{mm(r.rect.w)}} × {{mm(r.rect.h)}}</text>
            <text :x="(r.rect.x+r.rect.w/2)/T" :y="(r.rect.y+r.rect.h/2)/T+font*1.05" text-anchor="middle" fill="#8ca49a" :font-size="font*.65">{{r.kind==='empty'?'留空':r.context==='sash'?'窗扇玻璃':'固定玻璃'}}</text>
          </g>
          <polygon v-for="p in s.geometry.parts" :key="p.id" :points="p.polygon.map(v=>v.map(n=>n/T).join(',')).join(' ')" :fill="p.category.includes('mullion')?'#bc8c45':p.category.includes('frame')?'#36584f':'#8fa69b'" stroke="#f8faf8" :stroke-width="font/30" :class="{'mullion-hit':p.category.includes('mullion')}" @click.stop="p.category.includes('mullion')&&emit('editSplit',p.id.slice(0,-2))"><title>{{p.id}} · {{p.category_label}} · {{mm(p.length)}} mm</title></polygon>
          <line v-for="split in s.geometry.splits" :key="'hit-'+split.id" class="touch-mullion-hit" :x1="split.start[0]!/T" :y1="split.start[1]!/T" :x2="split.end[0]!/T" :y2="split.end[1]!/T" stroke="transparent" stroke-width="16" vector-effect="non-scaling-stroke" @click.stop="s.tool==='select'&&emit('editSplit',split.id)" :style="{pointerEvents:s.tool==='select'?'stroke':'none'}"/>
          <rect v-if="s.region" :x="s.region.rect.x/T" :y="s.region.rect.y/T" :width="s.region.rect.w/T" :height="s.region.rect.h/T" fill="none" stroke="#c28c3e" :stroke-width="font*.12" :stroke-dasharray="`${font*.4} ${font*.2}`" pointer-events="none"/>
          <g stroke="#d48246" :stroke-width="font*.08"><path :d="`M${-font*.5} 0 H${font*.5} M0 ${-font*.5} V${font*.5}`"/></g>
          <text :x="font*.5" :y="-font*.25" :font-size="font*.6" fill="#ad773e">0,0</text>
        </g>
      </svg>
    </div>
    <div class="canvas-bottom"><span><i class="legend-frame"/>外框 <i class="legend-mullion"/>中挺 <i class="legend-bead"/>压线</span><div class="zoom"><el-button text aria-label="缩小画布" :disabled="zoom<=70" @click="zoom=Math.max(70,zoom-10)">−</el-button><span>{{zoom}}%</span><el-button text aria-label="放大画布" :disabled="zoom>=180" @click="zoom=Math.min(180,zoom+10)">+</el-button><el-button text @click="zoom=100">适应画布</el-button><el-slider v-model="zoom" :min="70" :max="180" :step="10" aria-label="画布缩放"/></div></div>
  </div>
</template>
