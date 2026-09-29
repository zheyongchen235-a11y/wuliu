/**
 * 请求封装：统一拼接前缀、注入 C 端令牌、解包 { code, message, data }。
 */
const { BASE } = require('./config')

const TOKEN_KEY = 'wx_token'
const USER_KEY = 'wx_user'

function getToken() {
  return wx.getStorageSync(TOKEN_KEY) || ''
}

function setToken(token) {
  if (token) {
    wx.setStorageSync(TOKEN_KEY, token)
  }
}

function setUser(user) {
  if (user) {
    wx.setStorageSync(USER_KEY, user)
  }
}

function getUser() {
  return wx.getStorageSync(USER_KEY) || null
}

function clearAuth() {
  wx.removeStorageSync(TOKEN_KEY)
  wx.removeStorageSync(USER_KEY)
}

function toast(message) {
  wx.showToast({ title: String(message || '').slice(0, 40), icon: 'none', duration: 2200 })
}

/**
 * @param {Object} options
 * @param {string} options.url      以 / 开头的接口路径，如 /wx/orders
 * @param {string} [options.method] GET / POST / PUT / DELETE
 * @param {Object} [options.data]
 * @param {boolean} [options.auth]  是否携带令牌，默认 true
 * @param {boolean} [options.loading] 是否展示 loading，默认 false
 */
function request(options) {
  const opts = options || {}
  const method = (opts.method || 'GET').toUpperCase()
  const withAuth = opts.auth !== false

  return new Promise(function (resolve, reject) {
    if (opts.loading) {
      wx.showLoading({ title: opts.loadingText || '加载中', mask: true })
    }

    const header = { 'Content-Type': 'application/json' }
    if (withAuth && getToken()) {
      header.Authorization = 'Bearer ' + getToken()
    }

    wx.request({
      url: BASE + opts.url,
      method: method,
      data: opts.data || {},
      header: header,
      timeout: 30000,
      success: function (res) {
        const body = res.data || {}
        const status = res.statusCode

        if (status === 401 || status === 403) {
          if (status === 401) {
            clearAuth()
            toast('登录已过期，请重新登录')
            setTimeout(function () {
              wx.redirectTo({ url: '/pages/login/login' })
            }, 800)
          } else {
            toast(body.detail || body.message || '无权访问')
          }
          reject(body)
          return
        }

        if (status >= 200 && status < 300 && body.code === 0) {
          resolve(body.data)
          return
        }

        let msg = body.message || body.detail
        if (msg && typeof msg === 'object') {
          // FastAPI 422 校验错误
          msg = (msg[0] && (msg[0].msg || msg[0].loc)) || '参数有误'
        }
        toast(msg || '请求失败(' + status + ')')
        reject(body)
      },
      fail: function (err) {
        toast('网络异常，请确认后端服务已启动')
        reject(err)
      },
      complete: function () {
        if (opts.loading) {
          wx.hideLoading()
        }
      },
    })
  })
}

module.exports = {
  request,
  getToken,
  setToken,
  setUser,
  getUser,
  clearAuth,
  toast,
}