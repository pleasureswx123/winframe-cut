import { createApp } from 'vue'
import { createPinia } from 'pinia'
import { createRouter, createWebHashHistory } from 'vue-router'
import ElementPlus from 'element-plus'
import zhCn from 'element-plus/es/locale/lang/zh-cn'
import 'element-plus/dist/index.css'
import './style.css'
import './interaction.css'
import './platform.css'
import {useAuth} from './auth'
import {useWorkshop} from './store'
import Login from './views/Login.vue'
import Customers from './views/Customers.vue'
import Houses from './views/Houses.vue'
import HouseDetail from './views/HouseDetail.vue'
import App from './App.vue'
import Workbench from './views/Workbench.vue'
const pinia=createPinia()
const router=createRouter({history:createWebHashHistory(),scrollBehavior:()=>({top:0}),routes:[{path:'/',redirect:'/customers'},{path:'/login',component:Login},{path:'/customers',component:Customers},{path:'/customers/:customerId/houses',component:Houses},{path:'/houses/:id',component:HouseDetail},{path:'/houses/:id/cutting',component:()=>import('./views/HouseCutting.vue')},{path:'/:tab(design|materials|cutting)',component:Workbench},{path:'/:pathMatch(.*)*',redirect:'/customers'}]})
router.beforeEach(async to=>{
 const auth=useAuth(pinia);await auth.restore()
 if(!auth.user&&to.path!=='/login')return '/login'
 if(auth.user&&to.path==='/login')return '/customers'
 if(to.params.tab){
  const s=useWorkshop(pinia),id=String(to.query.windowId??''),houseId=String(to.query.houseId??'')
  if(id&&s.savedId!==id)await s.openWindow(id)
  else if(!id&&houseId&&(!s.project||s.savedId||s.context.house_id!==houseId))await s.newWindow(houseId)
  else if(!id&&!houseId&&!s.project)return '/customers'
 }
})
createApp(App).use(pinia).use(router).use(ElementPlus,{locale:zhCn}).mount('#app')
