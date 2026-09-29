// pages/pay/pay.js
const api = require('../../utils/api')
const auth = require('../../utils/auth')
const fmt = require('../../utils/format')

Page({
  data: {
    orderId: '',
    order: null,
    channel: 'wechat_mock',
    paying: false,
    paid: false,
  },

  onLoad(options) {
    if (!auth.isLogged()) {
      wx.redirectTo({ url: '/pages/login/login' })
      return
    }
    const id = options && options.id
    if (!id) {
      wx.showToast({ title: '缺少订单参数', icon: 'none' })
      return
    }
    this.setData({ orderId: id })
    this.loadOrder()
  },

  loadOrder() {
    const that = this
    api
      .getOrderDetail(this.data.orderId)
      .then(function (order) {
        const decorated = fmt.decorateOrder(order)
        that.setData({
          order: decorated,
          paid: order.status !== 'pending_pay',
        })
      })
      .catch(function () {})
  },

  chooseChannel(e) {
    this.setData({ channel: e.currentTarget.dataset.value })
  },

  doPay() {
    const that = this
    if (this.data.paying) return
    this.setData({ paying: true })

    api
      .payOrder(this.data.orderId, { channel: this.data.channel })
      .then(function () {
        that.setData({ paying: false, paid: true })
        wx.showToast({ title: '支付成功', icon: 'success' })
      })
      .catch(function () {
        that.setData({ paying: false })
      })
  },

  goDetail() {
    wx.redirectTo({ url: '/pages/order/detail/detail?id=' + this.data.orderId })
  },

  goList() {
    wx.switchTab({ url: '/pages/order/list/list' })
  },
})