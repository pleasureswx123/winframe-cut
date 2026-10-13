import type {Project} from './types'
export function nameMode(project:Project){return project.name_mode??(project.name==='未命名窗型'?'auto':'custom')}
export function locationName(floor:string,room:string){return [floor.trim(),room.trim()].filter(Boolean).join('·').slice(0,100)||'未命名窗型'}
