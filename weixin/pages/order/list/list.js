// pages/order/list/list.js
const api = require('../../../utils/api')
const auth = require('../../../utils/auth')
const fmt = require('../../../utils/format')

const PAGE_SIZE = 10

Page({
  data: {
    tabs: [
      { value: '', label: '全部' },
      { value: 'pending_pay', label: '待支付' },
      { value: 'paid', label: '待调度' },
      { value: 'scheduled', label: '已排车' },
      { value: 'completed', label: '已完成' },
    ],
    status: '',
    orders: [],
    page: 1,
    hasMore: true,
    loading: false,
    loadingMore: false,
  },

  onLoad() {
    if (!auth.isLogged()) {
      wx.redirectTo({ url: '/pages/login/login' })
      return
    }
    this.loadList(true)
  },

  onShow() {
    if (!auth.isLogged()) return
    // 从「我的」页四宫格带入的状态筛选
    const app = getApp()
    const pending = app.globalData.pendingOrderStatus
    if (pending !== undefined && pending !== null) {
      app.globalData.pendingOrderStatus = null
      this.setData({ status: pending })
    }
    this.loadList(true)
  },

  onPullDownRefresh() {
    const that = this
    this.loadList(true).then(function () {
      wx.stopPullDownRefresh()
      that.setData({})
    })
  },

  onReachBottom() {
    if (!this.data.hasMore || this.data.loadingMore) return
    this.loadList(false)
  },

  onTabTap(e) {
    const value = e.currentTarget.dataset.value
    if (value === this.data.status) return
    this.setData({ status: value })
    this.loadList(true)
  },

  loadList(reset) {
    const that = this
    const page = reset ? 1 : this.data.page + 1
    this.setData(reset ? { loading: true } : { loadingMore: true })

    return api
      .getOrders({ status: this.data.status, page: page, pageSize: PAGE_SIZE })
      .then(function (res) {
        const items = (res.items || []).map(fmt.decorateOrder)
        const list = reset ? items : that.data.orders.concat(items)
        that.setData({
          orders: list,
          page: page,
          hasMore: list.length < (res.total || 0),
        })
      })
      .catch(function () {})
      .then(function () {
        that.setData({ loading: false, loadingMore: false })
      })
  },

  goCreate() {
    wx.switchTab({ url: '/pages/order/create/create' })
  },

  goDetail(e) {
    wx.navigateTo({ url: '/pages/order/detail/detail?id=' + e.currentTarget.dataset.id })
  },

  noop() {},

  onPay(e) {
    wx.navigateTo({ url: '/pages/pay/pay?id=' + e.currentTarget.dataset.id })
  },

  onCancel(e) {
    const that = this
    const id = e.currentTarget.dataset.id
    wx.showModal({
      title: '取消订单',
      content: '确定要取消该订单吗？',
      success: function (res) {
        if (!res.confirm) return
        api.cancelOrder(id).then(function () {
          wx.showToast({ title: '已取消', icon: 'success' })
          that.loadList(true)
        })
      },
    })
  },

  onConfirm(e) {
    const that = this
    const id = e.currentTarget.dataset.id
    wx.showModal({
      title: '确认收货',
      content: '确认已收到全部货物？',
      success: function (res) {
        if (!res.confirm) return
        api.confirmOrder(id).then(function () {
          wx.showToast({ title: '已确认收货', icon: 'success' })
          that.loadList(true)
        })
      },
    })
  },
})