export const T = 2000
export const categories = ['window_frame','window_mullion','window_bead','sash_frame','sash_mullion','sash_bead'] as const
export type Category = typeof categories[number]
export const labels: Record<Category,string> = {window_frame:'窗户外框',window_mullion:'窗户中挺',window_bead:'窗户压线',sash_frame:'窗扇外框',sash_mullion:'窗扇中挺',sash_bead:'窗扇压线'}
export interface Node {id:string;kind:'glass'|'empty'|'split'|'sash';axis?:'x'|'y'|null;position?:number|null;children:Node[]}
export interface Project {schema_version:1;name:string;width:number;height:number;quantity:number;profiles:Record<Category,{width:number;stock_key:string}>;root:Node;glass:GlassSettings}
export interface Rect {x:number;y:number;w:number;h:number}
export interface Part {id:string;category:Category;category_label:string;label:string;stock_key:string;width:number;length:number;short_length:number;angle:number;quantity:number;rect:Rect;polygon:number[][];start:number[]|null;end:number[]|null;center:number[]}
export interface Region {id:string;kind:Node['kind'];context:'window'|'sash';rect:Rect;opening?:Rect;glass?:Rect}
export interface Split {id:string;axis:'x'|'y';position:number;context:string;start:number[];end:number[];rect:Rect}
export interface Geometry {glasses:GlassPiece[];glass_count:number;glass_area:number;glass_warnings:string[];parts:Part[];regions:Region[];splits:Split[];summary:{category:Category;label:string;count:number;total_length:number}[];count:number;total_length:number}
export interface Stock {id:string;stock_key:string;length:number;price_cents:number;available:number|null}
export interface Settings {kerf:number;trim_start:number;trim_end:number;objective:'bars'|'cost';time_limit:number}
export interface Segment {instance:string;part_id:string;label:string;category:Category;length:number;short_length:number;angle:number;from_tick:number;to_tick:number;front_loss:number;back_loss:number;cut_start:number;cut_end:number}
export interface Bar {id:string;stock_id:string;stock_key:string;length:number;price_cents:number;pieces:Segment[];loss:number;remnant:number;trim_start:number;trim_end:number}
export interface Plan {status:string;primary_proven:boolean;bar_count:number;cost_cents:number;total_stock:number;total_parts:number;total_loss:number;total_remnant:number;manufacturing_rule:string;groups:{stock_key:string;status:string;primary_proven:boolean;primary_bound:number;primary_value:number;bars:Bar[]}[];purchase:{stock_id:string;stock_key:string;length:number;price_cents:number;count:number;cost_cents:number}[]}
export const mm = (ticks:number) => (ticks/T).toFixed(5).replace(/\.?0+$/,'') || '0'
export const money = (cents:number) => (cents/100).toFixed(2)
export const clone = <V>(v:V):V => JSON.parse(JSON.stringify(v))
export function walk(node:Node,id:string):Node|undefined {return node.id===id?node:node.children.map(c=>walk(c,id)).find(Boolean)}

export interface GlassStock {id:string;width:number;height:number;price_cents:number;available:number|null}
export interface GlassSettings {width_deduction:number;height_deduction:number;kerf:number;allow_rotate:boolean;objective:'sheets'|'cost';stocks:GlassStock[]}
export interface GlassPiece {id:string;region_id:string;context:string;label:string;width:number;height:number;quantity:number;rect:Rect;area:number;overlap:{x:number;y:number}}
export interface GlassCut {index:number;instance:string;axis:'x'|'y';at:number;region:Rect;kerf_rect:Rect;kept:Rect;remainder:Rect}
export interface GlassSheet {id:string;stock_id:string;width:number;height:number;price_cents:number;glass_area:number;loss_area:number;remnant_area:number;pieces:{instance:string;part_id:string;width:number;height:number;rotated:boolean;rect:Rect}[];cuts:GlassCut[];remnants:Rect[]}
export interface GlassPlan {status:string;primary_proven:boolean;sheet_count:number;cost_cents:number;total_stock_area:number;total_glass_area:number;loss_area:number;remnant_area:number;lower_bound:number;sheets:GlassSheet[];purchase:{stock_id:string;width:number;height:number;count:number;cost_cents:number}[]}
export const areaM2=(ticks:number)=>(ticks/T/T/1e6).toFixed(6).replace(/\.?0+$/,'')||'0'
export const defaultGlass=():GlassSettings=>({width_deduction:30*T,height_deduction:30*T,kerf:0,allow_rotate:true,objective:'sheets',stocks:[{id:'示例板材-2440x1830',width:2440*T,height:1830*T,price_cents:0,available:null}]})
