// app.js
const auth = require('./utils/auth')

App({
  globalData: {
    user: null,
  },

  onLaunch() {
    // 恢复本地缓存的用户信息
    this.globalData.user = wx.getStorageSync('wx_user') || null
  },

  /** 供页面调用：把登录用户同步到全局与缓存 */
  setUser(user) {
    this.globalData.user = user || null
    if (user) {
      wx.setStorageSync('wx_user', user)
    } else {
      wx.removeStorageSync('wx_user')
    }
  },

  isLogged() {
    return !!auth.getToken()
  },
})