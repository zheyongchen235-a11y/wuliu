// Cloudflare Worker：静态资源托管 + 同源反向代理
//
// 目的：让访客只需要访问 workers.dev 一个域名即可使用全部功能。
//   - /api/* 与 /ws/* 在 Cloudflare 内部转发到本机后端（经 cloudflared 隧道），
//     不经过访客自己的网络，因此不受访客网络环境影响，也无需跨域。
//   - 其余请求交给静态资源（env.ASSETS）处理。
//
// 注意：下面 BACKEND 是 Cloudflare 临时隧道地址，重启 cloudflared 后会变化，需同步更新。

const BACKEND = 'https://lone-hanging-manitoba-themselves.trycloudflare.com'

export default {
  async fetch(request, env) {
    const url = new URL(request.url)
    const path = url.pathname

    // 需要转发到后端的路径
    const isApi = path === '/api' || path.startsWith('/api/')
    const isWs = path === '/ws' || path.startsWith('/ws/')

    if (isApi || isWs) {
      const target = BACKEND + path + url.search
      // 原样转发（含 WebSocket 的 Upgrade 头）
      return fetch(new Request(target, request))
    }

    // 其余请求走静态资源（未命中时由 not_found_handling 回退到 index.html）
    return env.ASSETS.fetch(request)
  },
}