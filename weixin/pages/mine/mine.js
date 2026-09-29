// pages/mine/mine.js
const api = require('../../utils/api')
const auth = require('../../utils/auth')

Page({
  data: {
    user: {},
    initial: '微',
    shortOpenid: '-',
    stats: { pending_pay: 0, paid: 0, scheduled: 0, completed: 0 },
  },

  onShow() {
    if (!auth.isLogged()) {
      wx.redirectTo({ url: '/pages/login/login' })
      return
    }
    this.applyUser(auth.getUser() || {})
    this.loadStats()
    this.refreshProfile(true)
  },

  applyUser(user) {
    const id = user.id || ''
    this.setData({
      user: user,
      initial: (user.nickname || '微').slice(0, 1),
      shortOpenid: user.openid ? user.openid.slice(0, 6) + '****' + user.openid.slice(-4) : '-',
    })
  },

  loadStats() {
    const that = this
    api
      .getOrders({ page: 1, pageSize: 50 })
      .then(function (page) {
        const stats = { pending_pay: 0, paid: 0, scheduled: 0, completed: 0 }
        ;(page.items || []).forEach(function (o) {
          if (stats[o.status] !== undefined) stats[o.status] += 1
          if (o.status === 'delivered') stats.completed += 1
        })
        that.setData({ stats: stats })
      })
      .catch(function () {})
  },

  refreshProfile(silent) {
    const that = this
    api
      .getProfile()
      .then(function (user) {
        const app = getApp()
        if (app && app.setUser) app.setUser(user)
        that.applyUser(user)
        if (!silent) wx.showToast({ title: '资料已刷新', icon: 'success' })
      })
      .catch(function () {
        if (!silent) wx.showToast({ title: '刷新失败', icon: 'none' })
      })
  },

  editNickname() {
    const that = this
    wx.showModal({
      title: '修改昵称',
      editable: true,
      placeholderText: '请输入新的昵称',
      success: function (res) {
        if (!res.confirm || !res.content) return
        api.updateProfile({ nickname: res.content }).then(function (user) {
          const app = getApp()
          if (app && app.setUser) app.setUser(user)
          that.applyUser(user)
          wx.showToast({ title: '已修改', icon: 'success' })
        })
      },
    })
  },

  editPhone() {
    const that = this
    wx.showModal({
      title: '绑定手机号',
      editable: true,
      placeholderText: '请输入手机号',
      success: function (res) {
        if (!res.confirm || !res.content) return
        api.updateProfile({ phone: res.content }).then(function (user) {
          const app = getApp()
          if (app && app.setUser) app.setUser(user)
          that.applyUser(user)
          wx.showToast({ title: '已保存', icon: 'success' })
        })
      },
    })
  },

  goOrders() {
    const app = getApp()
    app.globalData.pendingOrderStatus = null
    wx.switchTab({ url: '/pages/order/list/list' })
  },

  goOrdersWithStatus(e) {
    const app = getApp()
    app.globalData.pendingOrderStatus = e.currentTarget.dataset.status
    wx.switchTab({ url: '/pages/order/list/list' })
  },

  goPayments() {
    wx.navigateTo({ url: '/pages/mine/payments' })
  },

  logout() {
    const that = this
    wx.showModal({
      title: '退出登录',
      content: '退出后需要重新使用微信登录',
      success: function (res) {
        if (!res.confirm) return
        auth.logout()
        wx.redirectTo({ url: '/pages/login/login' })
      },
    })
  },
})