// pages/mine/payments.js
const api = require('../../utils/api')
const auth = require('../../utils/auth')
const fmt = require('../../utils/format')

const PAGE_SIZE = 10

const CHANNEL_LABELS = {
  wechat_mock: '微信支付（模拟）',
  balance: '平台余额',
  cash: '货到付款',
}

const PAY_STATUS = {
  success: '支付成功',
  refunded: '已退款',
  pending: '处理中',
  failed: '支付失败',
}

Page({
  data: {
    payments: [],
    page: 1,
    hasMore: true,
    loading: false,
    total: 0,
    totalAmount: '¥0.00',
  },

  onLoad() {
    if (!auth.isLogged()) {
      wx.redirectTo({ url: '/pages/login/login' })
      return
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
    if (!this.data.hasMore || this.data.loading) return
    this.loadList(false)
  },

  loadList(reset) {
    const that = this
    const page = reset ? 1 : this.data.page + 1
    this.setData({ loading: true })

    return api
      .getPayments({ page: page, pageSize: PAGE_SIZE })
      .then(function (res) {
        const items = (res.items || []).map(function (p) {
          return Object.assign({}, p, {
            amount_text: fmt.money(p.amount),
            channel_text: CHANNEL_LABELS[p.channel] || p.channel,
            status_text: PAY_STATUS[p.status] || p.status,
            paid_text: fmt.datetime(p.paid_at || p.created_at),
          })
        })
        const list = reset ? items : that.data.payments.concat(items)

        let sum = 0
        list.forEach(function (p) {
          if (p.status === 'success') sum += Number(p.amount || 0)
        })
        that.setData({
          payments: list,
          page: page,
          total: res.total || 0,
          totalAmount: fmt.money(sum),
          hasMore: list.length < (res.total || 0),
        })
      })
      .catch(function () {})
      .then(function () {
        that.setData({ loading: false })
      })
  },
})