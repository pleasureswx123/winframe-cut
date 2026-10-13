import {build} from 'esbuild'
import assert from 'node:assert/strict'
await build({entryPoints:['src/windowNaming.ts'],bundle:true,platform:'node',format:'esm',outfile:'output/check-window-naming.mjs'})
const {nameMode,locationName}=await import('../output/check-window-naming.mjs')
assert.equal(locationName(' 一层 ',' 主卧东窗 '),'一层·主卧东窗')
assert.equal(locationName('',''),'未命名窗型')
assert.equal(locationName('','主卧'),'主卧')
assert.equal(locationName('层'.repeat(60),'窗'.repeat(100)).length,100)
assert.equal(nameMode({name:'未命名窗型'}),'auto')
assert.equal(nameMode({name:'旧窗型名称'}),'custom')
assert.equal(nameMode({name:'未命名窗型',name_mode:'custom'}),'custom')
console.log('通过：自动名称生成、空值、长度限制和旧名称兼容')
