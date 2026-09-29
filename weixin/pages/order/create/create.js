// pages/order/create/create.js
const api = require('../../../utils/api')
const auth = require('../../../utils/auth')
const fmt = require('../../../utils/format')

function today() {
  const d = new Date()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return d.getFullYear() + '-' + m + '-' + day
}

function num(v) {
  const n = Number(v)
  return isNaN(n) ? 0 : n
}

Page({
  data: {
    stores: [],
    storeIndex: 0,
    store: null,
    cargoOptions: [
      { value: 'general', label: '普通货物' },
      { value: 'fresh', label: '生鲜冷链' },
      { value: 'fragile', label: '易碎品' },
      { value: 'bulk', label: '大宗货物' },
    ],
    windowOptions: [
      { value: 'AM', label: '上午' },
      { value: 'PM', label: '下午' },
    ],
    cargoType: 'general',
    weight: '',
    timeWindow: 'AM',
    expectDate: today(),
    contactName: '',
    contactPhone: '',
    remark: '',
    estimate: null,
    submitting: false,
  },

  onLoad() {
    const user = auth.getUser() || {}
    this.setData({
      contactName: user.nickname || '',
      contactPhone: user.phone || '',
    })
    this.loadStores()
  },

  onShow() {
    if (!auth.isLogged()) {
      wx.redirectTo({ url: '/pages/login/login' })
      return
    }
    // 从首页/门店点「去下单」带入的门店
    const app = getApp()
    const pendingId = app.globalData.pendingStoreId
    if (pendingId && this.data.stores.length) {
      const idx = this.data.stores.findIndex(function (s) {
        return s.id === pendingId
      })
      if (idx >= 0 && idx !== this.data.storeIndex) {
        this.applyStore(idx)
      }
      app.globalData.pendingStoreId = null
    }
  },

  loadStores() {
    const that = this
    const app = getApp()
    api
      .getStores()
      .then(function (stores) {
        const list = (stores || []).map(function (s) {
          return Object.assign({}, s, {
            timeText: fmt.windowText(s.time_window),
            distanceText: s.longitude ? s.longitude.toFixed(2) + ',' + s.latitude.toFixed(2) : '坐标未维护',
          })
        })
        that.setData({ stores: list })
        if (!list.length) return
        const pendingId = app.globalData.pendingStoreId
        let idx = 0
        if (pendingId) {
          const i = list.findIndex(function (s) {
            return s.id === pendingId
          })
          if (i >= 0) idx = i
          app.globalData.pendingStoreId = null
        }
        that.applyStore(idx)
      })
      .catch(function () {})
  },

  applyStore(index) {
    const store = this.data.stores[index]
    if (!store) return
    const patch = { storeIndex: index, store: store }
    // 门店有固定时段时自动跟随
    if (store.time_window === 'AM' || store.time_window === 'PM') {
      patch.timeWindow = store.time_window
    }
    this.setData(patch)
    this.refreshEstimate()
  },

  onStoreChange(e) {
    this.applyStore(Number(e.detail.value))
  },

  onCargoTap(e) {
    this.setData({ cargoType: e.currentTarget.dataset.value })
  },

  onWindowTap(e) {
    this.setData({ timeWindow: e.currentTarget.dataset.value })
    this.refreshEstimate()
  },

  onWeightInput(e) {
    this.setData({ weight: e.detail.value })
    this.refreshEstimate()
  },

  onDateChange(e) {
    this.setData({ expectDate: e.detail.value })
  },

  onContactNameInput(e) {
    this.setData({ contactName: e.detail.value })
  },

  onContactPhoneInput(e) {
    this.setData({ contactPhone: e.detail.value })
  },

  onRemarkInput(e) {
    this.setData({ remark: e.detail.value })
  },

  refreshEstimate() {
    const that = this
    const store = this.data.store
    const weight = num(this.data.weight)
    if (!store || weight <= 0) {
      this.setData({ estimate: null })
      return
    }
    // 简单防抖
    if (this._timer) clearTimeout(this._timer)
    this._timer = setTimeout(function () {
      api
        .estimate({
          store_id: store.id,
          weight: weight,
          cargo_type: that.data.cargoType,
          time_window: that.data.timeWindow,
        })
        .then(function (res) {
          that.setData({
            estimate: Object.assign({}, res, {
              amount_text: fmt.money(res.amount),
              distanceText: res.distance_km + ' km',
              window_text: fmt.windowText(that.data.timeWindow),
              breakdown: (res.breakdown || []).map(function (b) {
                return Object.assign({}, b, { amount_text: fmt.amount(b.amount) })
              }),
            }),
          })
        })
        .catch(function () {})
    }, 300)
  },

  submitOrder() {
    const that = this
    const d = this.data
    if (!d.store) {
      wx.showToast({ title: '请选择配送门店', icon: 'none' })
      return
    }
    const weight = num(d.weight)
    if (weight <= 0) {
      wx.showToast({ title: '请填写有效货量', icon: 'none' })
      return
    }
    if (!d.contactPhone || String(d.contactPhone).length < 6) {
      wx.showToast({ title: '请填写联系电话', icon: 'none' })
      return
    }
    if (this.data.submitting) return
    this.setData({ submitting: true })

    api
      .createOrder({
        store_id: d.store.id,
        weight: weight,
        cargo_type: d.cargoType,
        time_window: d.timeWindow,
        expect_date: d.expectDate,
        contact_name: d.contactName || null,
        contact_phone: String(d.contactPhone),
        remark: d.remark || null,
      })
      .then(function (order) {
        wx.showToast({ title: '下单成功', icon: 'success' })
        that.setData({ submitting: false })
        setTimeout(function () {
          wx.navigateTo({ url: '/pages/pay/pay?id=' + order.id })
        }, 600)
      })
      .catch(function () {
        that.setData({ submitting: false })
      })
  },
})