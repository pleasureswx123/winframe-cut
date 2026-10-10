import axios from 'axios'
export const api = axios.create({baseURL:'/api',timeout:240000})
export function errorText(e:unknown) {
  if(axios.isAxiosError(e)) {
    const detail=e.response?.data?.detail
    if(Array.isArray(detail)) return detail.map(v=>`${v.loc?.slice(1).join('.')}：${v.msg}`).join('；')
    return typeof detail==='string'?detail:'无法连接计算服务，请确认后端已启动。'
  }
  return e instanceof Error?e.message:String(e)
}
