import {defineStore} from 'pinia'
import {ref} from 'vue'
import {api,onSessionExpired,setApiSession} from './api'
import {useWorkshop} from './store'
import type {User} from './business'

export const useAuth=defineStore('auth',()=>{
  const user=ref<User|null>(null),ready=ref(false)
  function clear(){user.value=null;setApiSession('');useWorkshop().resetSession()}
  function accept(data:{user:User;csrf_token:string}){setApiSession(data.csrf_token);user.value=data.user;useWorkshop().setUser(data.user.id);ready.value=true}
  async function restore(){
    if(ready.value)return
    try{accept((await api.get('/auth/me')).data)}catch{clear()}finally{ready.value=true}
  }
  async function login(username:string,password:string){clear();accept((await api.post('/auth/login',{username,password})).data)}
  async function logout(){try{await api.post('/auth/logout')}finally{clear()}}
  onSessionExpired(()=>{clear();window.location.hash='/login'})
  return {user,ready,restore,login,logout}
})
