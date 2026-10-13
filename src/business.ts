import type {Project,Stock,Settings,GlassSettings} from './types'
export interface User {id:string;username:string;display_name:string;role:'user'|'admin';active:boolean}
export interface Customer {id:string;owner_id:string;name:string;phone:string;address:string;notes:string;updated:string}
export interface House {custom_profiles?:boolean;custom_glass?:boolean;id:string;owner_id:string;customer_id:string;name:string;address:string;layout:string;notes:string;stocks:Stock[];settings:Settings;glass_groups:Record<string,GlassSettings>;updated:string}
export interface WindowRecord {id:string;owner_id:string;house_id:string;name:string;floor:string;room:string;glass_material:string;project:Project;stocks:Stock[];settings:Settings;updated:string}
export interface Page<T> {items:T[];total:number;page:number;page_size:number}
export const defaultSettings=():Settings=>({kerf:6000,trim_start:0,trim_end:0,reusable_min:1000000,objective:'bars',time_limit:10})
export function houseInput(h:House){return {custom_profiles:h.custom_profiles??false,custom_glass:h.custom_glass??false,customer_id:h.customer_id,name:h.name,address:h.address,layout:h.layout,notes:h.notes,stocks:h.stocks,settings:h.settings,glass_groups:h.glass_groups}}
