<script setup lang="ts">
withDefaults(defineProps<{size?:number}>(),{size:58})
</script>
<template><svg :width="size" :height="size" viewBox="0 0 64 64" fill="none" role="img" aria-label="窗序标志"><rect width="64" height="64" rx="18" fill="#285347"/><rect x="15" y="14" width="34" height="37" rx="3" stroke="#F4F8F3" stroke-width="2.4"/><path d="M15 25H49M29 25V51M29 38H49" stroke="#F4F8F3" stroke-width="2.4"/><path d="M20 19.5H29" stroke="#C9B68A" stroke-width="2.4" stroke-linecap="round"/><circle cx="44" cy="32" r="1.5" fill="#C9B68A"/></svg></template>
