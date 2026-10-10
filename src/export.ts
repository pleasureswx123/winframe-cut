export function download(name:string,content:string,type='application/json'){
  const url=URL.createObjectURL(new Blob([content],{type}));const a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)
}
export function csv(rows:(string|number)[][]){
  return '\ufeff'+rows.map(row=>row.map(v=>{let text=String(v);if(/^[=+@\t\r]/.test(text)||(/^\-/.test(text)&&!/^\-\d+(\.\d+)?$/.test(text)))text="'"+text;return '"'+text.replaceAll('"','""')+'"'}).join(',')).join('\r\n')
}
