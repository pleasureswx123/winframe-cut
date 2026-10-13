import axios from 'axios'
export const api = axios.create({baseURL:'/api',timeout:240000})
let csrf='',epoch=0
let expired:()=>void=()=>{}
export function setApiSession(token:string){csrf=token;epoch++}
export function onSessionExpired(handler:()=>void){expired=handler}
api.interceptors.request.use(config=>{
  config.headers.set('X-Client-Epoch',String(epoch))
  if(csrf)config.headers.set('X-CSRF-Token',csrf)
  return config
})
api.interceptors.response.use(response=>{
  if(response.config.headers.get('X-Client-Epoch')!==String(epoch))throw new axios.CanceledError('账号已切换')
  return response
},error=>{
  if(error.config?.headers?.get('X-Client-Epoch')===String(epoch)&&error.response?.status===401&&!error.config.url?.startsWith('/auth/'))expired()
  return Promise.reject(error)
})
export function errorText(e:unknown) {
  if(axios.isAxiosError(e)) {
    const detail=e.response?.data?.detail
    if(Array.isArray(detail)) return detail.map(v=>`${v.loc?.slice(1).join('.')}：${v.msg}`).join('；')
    return typeof detail==='string'?detail:'无法连接计算服务，请确认后端已启动。'
  }
  return e instanceof Error?e.message:String(e)
}
