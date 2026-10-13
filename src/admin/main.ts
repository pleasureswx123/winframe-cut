import {createApp} from 'vue'
import {createPinia} from 'pinia'
import {createRouter,createWebHashHistory} from 'vue-router'
import ElementPlus from 'element-plus'
import zhCn from 'element-plus/es/locale/lang/zh-cn'
import 'element-plus/dist/index.css'
import '../style.css'
import '../platform.css'
import './admin.css'
import {useAuth} from '../auth'
import App from './App.vue'
import Login from '../views/Login.vue'
import Dashboard from './views/Dashboard.vue'
import Users from './views/Users.vue'
import UserData from './views/UserData.vue'
const pinia=createPinia()
const router=createRouter({history:createWebHashHistory(),routes:[{path:'/',component:Dashboard},{path:'/login',component:Login,props:{admin:true}},{path:'/users',component:Users},{path:'/users/:id',component:UserData},{path:'/:pathMatch(.*)*',redirect:'/'}]})
router.beforeEach(async to=>{const auth=useAuth(pinia);await auth.restore();if(to.path!=='/login'&&auth.user?.role!=='admin')return '/login';if(to.path==='/login'&&auth.user?.role==='admin')return '/'})
createApp(App).use(pinia).use(router).use(ElementPlus,{locale:zhCn}).mount('#app')
