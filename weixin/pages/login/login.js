// pages/login/login.js
const auth = require('../../utils/auth')

Page({
  data: {
    loading: false,
  },

  onLoad() {
    // 已登录则直接进入首页
    if (auth.isLogged()) {
      wx.switchTab({ url: '/pages/index/index' })
    }
  },

  handleLogin() {
    if (this.data.loading) return
    const that = this
    that.setData({ loading: true })

    auth
      .login()
      .then(function () {
        wx.showToast({ title: '登录成功', icon: 'success' })
        setTimeout(function () {
          wx.switchTab({ url: '/pages/index/index' })
        }, 500)
      })
      .catch(function (err) {
        console.warn('登录失败', err)
      })
      .then(function () {
        that.setData({ loading: false })
      })
  },
})