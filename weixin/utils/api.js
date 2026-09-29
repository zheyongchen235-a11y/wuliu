/**
 * 后端接口清单（全部走 FastAPI）。
 */
const { request } = require('./request')

module.exports = {
  // ---------- 登录 / 用户 ----------
  login: function (data) {
    return request({ url: '/wx/login', method: 'POST', data: data, auth: false })
  },
  getProfile: function () {
    return request({ url: '/wx/profile' })
  },
  updateProfile: function (data) {
    return request({ url: '/wx/profile', method: 'PUT', data: data })
  },

  // ---------- 门店 / 估价 ----------
  getStores: function () {
    return request({ url: '/wx/stores' })
  },
  estimate: function (data) {
    return request({ url: '/wx/estimate', method: 'POST', data: data })
  },

  // ---------- 订单 ----------
  createOrder: function (data) {
    return request({ url: '/wx/orders', method: 'POST', data: data, loading: true, loadingText: '提交中' })
  },
  getOrders: function (params) {
    const query = params || {}
    const parts = []
    if (query.status) parts.push('status=' + query.status)
    parts.push('page=' + (query.page || 1))
    parts.push('page_size=' + (query.pageSize || 10))
    return request({ url: '/wx/orders?' + parts.join('&') })
  },
  getOrderDetail: function (orderId) {
    return request({ url: '/wx/orders/' + orderId })
  },
  payOrder: function (orderId, data) {
    return request({
      url: '/wx/orders/' + orderId + '/pay',
      method: 'POST',
      data: data || { channel: 'wechat_mock' },
      loading: true,
      loadingText: '支付中',
    })
  },
  cancelOrder: function (orderId) {
    return request({ url: '/wx/orders/' + orderId + '/cancel', method: 'POST', loading: true, loadingText: '处理中' })
  },
  confirmOrder: function (orderId) {
    return request({ url: '/wx/orders/' + orderId + '/confirm', method: 'POST', loading: true, loadingText: '处理中' })
  },

  // ---------- 支付流水 ----------
  getPayments: function (params) {
    const query = params || {}
    return request({ url: '/wx/payments?page=' + (query.page || 1) + '&page_size=' + (query.pageSize || 10) })
  },
}