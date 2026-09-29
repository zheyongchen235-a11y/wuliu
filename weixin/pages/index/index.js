// pages/index/index.js
const api = require('../../utils/api')
const auth = require('../../utils/auth')
const fmt = require('../../utils/format')

function greetingText() {
  const h = new Date().getHours()
  if (h < 6) return '凌晨好'
  if (h < 12) return '上午好'
  if (h < 14) return '中午好'
  if (h < 18) return '下午好'
  return '晚上好'
}

Page({
  data: {
    greeting: greetingText(),
    user: {},
    stats: { pending_pay: 0, scheduled: 0, delivering: 0, completed: 0 },
    stores: [],
    storeCount: 0,
    recentOrders: [],
    loading: false,
  },

  onLoad() {
    this.ensureLogin()
    this.loadStores()
  },

  onShow() {
    if (!this.ensureLogin()) return
    this.setData({ user: auth.getUser() || {} })
    this.loadOrders()
  },

  onPullDownRefresh() {
    const that = this
    Promise.all([this.loadStores(), this.loadOrders()]).then(function () {
      wx.stopPullDownRefresh()
      that.setData({ user: auth.getUser() || {} })
    })
  },

  ensureLogin() {
    if (!auth.isLogged()) {
      wx.redirectTo({ url: '/pages/login/login' })
      return false
    }
    return true
  },

  loadStores() {
    const that = this
    return api
      .getStores()
      .then(function (stores) {
        const list = (stores || []).map(function (s) {
          return Object.assign({}, s, {
            shortName: (s.name || '?').slice(0, 1),
            timeText: fmt.windowText(s.time_window) + '配送',
          })
        })
        that.setData({
          stores: list.slice(0, 6),
          storeCount: list.length,
        })
      })
      .catch(function () {})
  },

  loadOrders() {
    const that = this
    if (this.data.loading) return Promise.resolve()
    this.setData({ loading: true })
    return api
      .getOrders({ page: 1, pageSize: 50 })
      .then(function (page) {
        const items = (page.items || []).map(fmt.decorateOrder)
        const stats = { pending_pay: 0, scheduled: 0, delivering: 0, completed: 0 }
        items.forEach(function (o) {
          if (stats[o.status] !== undefined) stats[o.status] += 1
          if (o.status === 'delivered') stats.completed += 1
        })
        that.setData({
          stats: stats,
          recentOrders: items.slice(0, 3),
        })
      })
      .catch(function () {})
      .then(function () {
        that.setData({ loading: false })
      })
  },

  pickStore(e) {
    const id = e.currentTarget.dataset.id
    const app = getApp()
    app.globalData.pendingStoreId = id
    wx.switchTab({ url: '/pages/order/create/create' })
  },

  goCreate() {
    wx.switchTab({ url: '/pages/order/create/create' })
  },

  goOrders() {
    wx.switchTab({ url: '/pages/order/list/list' })
  },

  goPayments() {
    wx.navigateTo({ url: '/pages/mine/payments' })
  },

  goDetail(e) {
    wx.navigateTo({ url: '/pages/order/detail/detail?id=' + e.currentTarget.dataset.id })
  },
})