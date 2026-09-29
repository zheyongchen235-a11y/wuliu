// pages/order/detail/detail.js
const api = require('../../../utils/api')
const auth = require('../../../utils/auth')
const fmt = require('../../../utils/format')

const STATUS_DESC = {
  pending_pay: '订单已提交，请尽快完成支付',
  paid: '支付成功，管理员将尽快安排智能调度排车',
  scheduled: '智能调度已完成排车，车辆与司机已分配',
  delivering: '车辆已发车，正在配送途中',
  delivered: '货物已送达，请确认收货',
  completed: '订单已完成，感谢使用',
  cancelled: '订单已取消',
}

const CHANNEL_LABELS = {
  wechat_mock: '微信支付（模拟）',
  balance: '余额支付',
  cash: '货到付款',
}

const OPERATOR_LABELS = {
  user: '用户操作',
  admin: '管理员操作',
  system: '系统自动',
}

Page({
  data: {
    orderId: '',
    order: null,
    logs: [],
    statusDesc: '',
  },

  onLoad(options) {
    const id = options && options.id
    if (!id) {
      wx.showToast({ title: '缺少订单参数', icon: 'none' })
      return
    }
    if (!auth.isLogged()) {
      wx.redirectTo({ url: '/pages/login/login' })
      return
    }
    this.setData({ orderId: id })
    this.loadDetail()
  },

  onShow() {
    if (this.data.orderId && this.data.order) {
      this.loadDetail()
    }
    this.startPolling()
  },

  onHide() {
    this.stopPolling()
  },

  onUnload() {
    this.stopPolling()
  },

  loadDetail() {
    const that = this
    return api
      .getOrderDetail(this.data.orderId)
      .then(function (order) {
        const decorated = fmt.decorateOrder(order)
        const logs = (order.status_logs || [])
          .slice()
          .reverse()
          .map(function (log) {
            return {
              id: log.id,
              status_text: fmt.statusText(log.to_status),
              remark: log.remark,
              created_text: fmt.datetime(log.created_at),
              operator_text: OPERATOR_LABELS[log.operator] || log.operator,
            }
          })
        const payments = (order.payments || []).map(function (p) {
          return {
            id: p.id,
            payment_no: p.payment_no,
            amount_text: fmt.money(p.amount),
            channel_text: CHANNEL_LABELS[p.channel] || p.channel,
          }
        })
        that.setData({
          order: Object.assign(decorated, { payments: payments }),
          logs: logs,
          statusDesc: STATUS_DESC[order.status] || '',
        })
        return order
      })
      .catch(function () {})
  },

  /** 待调度状态下轮询，等待后端回填车辆/司机 */
  startPolling() {
    const that = this
    this.stopPolling()
    this._timer = setInterval(function () {
      if (!that.data.order) return
      if (that.data.order.status !== 'paid') {
        that.stopPolling()
        return
      }
      that.loadDetail()
    }, 5000)
  },

  stopPolling() {
    if (this._timer) {
      clearInterval(this._timer)
      this._timer = null
    }
  },

  callDriver() {
    const phone = this.data.order && this.data.order.driver_phone
    if (phone) {
      wx.makePhoneCall({ phoneNumber: String(phone) })
    }
  },

  onPay() {
    wx.navigateTo({ url: '/pages/pay/pay?id=' + this.data.orderId })
  },

  onCancel() {
    const that = this
    wx.showModal({
      title: '取消订单',
      content: '确定要取消该订单吗？',
      success: function (res) {
        if (!res.confirm) return
        api.cancelOrder(that.data.orderId).then(function () {
          wx.showToast({ title: '已取消', icon: 'success' })
          that.loadDetail()
        })
      },
    })
  },

  onConfirm() {
    const that = this
    wx.showModal({
      title: '确认收货',
      content: '确认已收到全部货物？',
      success: function (res) {
        if (!res.confirm) return
        api.confirmOrder(that.data.orderId).then(function () {
          wx.showToast({ title: '已确认收货', icon: 'success' })
          that.loadDetail()
        })
      },
    })
  },
})