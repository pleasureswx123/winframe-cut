// 局域网 HTTP 也支持生成编号，不依赖仅限安全上下文的 randomUUID。
export function newId():string {
  return Array.from(crypto.getRandomValues(new Uint8Array(12)), n=>n.toString(16).padStart(2,'0')).join('')
}
