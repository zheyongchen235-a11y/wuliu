/**
 * 登录：wx.login 拿 code → 后端换取令牌（后端支持 mock / 真实微信双模式）。
 */
const api = require('./api')
const store = require('./request')

/** 调用微信官方登录接口获取临时 code */
function getLoginCode() {
  return new Promise(function (resolve, reject) {
    wx.login({
      success: function (res) {
        if (res && res.code) {
          resolve(res.code)
        } else {
          reject(new Error('wx.login 未返回 code'))
        }
      },
      fail: reject,
    })
  })
}

/**
 * 登录（首次自动注册）。
 * @param {Object} [profile] { nickname, avatar, gender }
 */
function login(profile) {
  const extra = profile || {}
  return getLoginCode().then(function (code) {
    return api.login({
      code: code,
      nickname: extra.nickname || null,
      avatar: extra.avatar || null,
      gender: extra.gender === undefined ? null : extra.gender,
    })
  }).then(function (data) {
    store.setToken(data.token)
    store.setUser(data.user)
    const app = getApp()
    if (app && app.setUser) {
      app.setUser(data.user)
    }
    return data
  })
}

function isLogged() {
  return !!store.getToken()
}

function logout() {
  store.clearAuth()
  const app = getApp()
  if (app && app.setUser) {
    app.setUser(null)
  }
}

module.exports = {
  getLoginCode: getLoginCode,
  login: login,
  isLogged: isLogged,
  logout: logout,
  getToken: store.getToken,
  getUser: store.getUser,
}