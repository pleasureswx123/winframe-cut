import { createApp } from 'vue'
import { createPinia } from 'pinia'
import { createRouter, createWebHashHistory } from 'vue-router'
import ElementPlus from 'element-plus'
import zhCn from 'element-plus/es/locale/lang/zh-cn'
import 'element-plus/dist/index.css'
import './style.css'
import App from './App.vue'
import Workbench from './views/Workbench.vue'
const router=createRouter({history:createWebHashHistory(),scrollBehavior:()=>({top:0}),routes:[{path:'/',redirect:'/design'},{path:'/:tab(design|materials|cutting)',component:Workbench}]})
createApp(App).use(createPinia()).use(router).use(ElementPlus,{locale:zhCn}).mount('#app')
