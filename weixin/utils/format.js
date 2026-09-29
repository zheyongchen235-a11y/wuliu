/**
 * 展示层格式化工具：金额、日期、状态、货物类型。
 */

const CARGO_LABELS = {
  general: '普通货物',
  fresh: '生鲜冷链',
  fragile: '易碎品',
  bulk: '大宗货物',
}

const STATUS_LABELS = {
  pending_pay: '待支付',
  paid: '已支付待调度',
  scheduled: '已排车',
  delivering: '配送中',
  delivered: '已送达',
  completed: '已完成',
  cancelled: '已取消',
}

// 状态 -> 主题色（字体色 / 背景色）
const STATUS_THEME = {
  pending_pay: { color: '#e8503a', bg: '#fdeceb' },
  paid: { color: '#c78a00', bg: '#fdf5e0' },
  scheduled: { color: '#2a5298', bg: '#e9f0fd' },
  delivering: { color: '#0e8f8f', bg: '#e3f6f6' },
  delivered: { color: '#2f9e44', bg: '#e8f7ec' },
  completed: { color: '#2f9e44', bg: '#e8f7ec' },
  cancelled: { color: '#8a90a0', bg: '#f0f1f5' },
}

const STATUS_ORDER = [
  'pending_pay',
  'paid',
  'scheduled',
  'delivering',
  'delivered',
  'completed',
]

function amount(value) {
  const num = Number(value || 0)
  return num.toFixed(2)
}

function money(value) {
  return '¥' + amount(value)
}

/** "2026-09-29T10:00:00+00:00" -> "2026-09-29 18:00"（UTC → 本地简化展示） */
function datetime(value) {
  if (!value) return '-'
  const text = String(value).replace('T', ' ').replace('Z', '')
  return text.slice(0, 16)
}

function dateOnly(value) {
  if (!value) return '-'
  return String(value).slice(0, 10)
}

function statusText(status) {
  return STATUS_LABELS[status] || status || '-'
}

function statusTheme(status) {
  return STATUS_THEME[status] || { color: '#8a90a0', bg: '#f0f1f5' }
}

function cargoText(type) {
  return CARGO_LABELS[type] || type || '普通货物'
}

function windowText(win) {
  if (win === 'AM') return '上午'
  if (win === 'PM') return '下午'
  return '全天'
}

/** 为订单对象补齐展示字段，避免 WXML 中做复杂逻辑 */
function decorateOrder(order) {
  if (!order) return order
  const theme = statusTheme(order.status)
  return Object.assign({}, order, {
    status_text: statusText(order.status),
    status_color: theme.color,
    status_bg: theme.bg,
    cargo_text: cargoText(order.cargo_type),
    window_text: windowText(order.time_window),
    deliver_window_text: windowText(order.deliver_window),
    amount_text: money(order.amount),
    created_text: datetime(order.created_at),
    expect_text: dateOnly(order.expect_date),
    paid_text: datetime(order.paid_at),
    can_pay: order.status === 'pending_pay',
    can_cancel: order.status === 'pending_pay' || order.status === 'paid',
    can_confirm: ['scheduled', 'delivering', 'delivered'].indexOf(order.status) >= 0,
    has_dispatch: !!order.plate,
  })
}

module.exports = {
  CARGO_LABELS: CARGO_LABELS,
  STATUS_LABELS: STATUS_LABELS,
  STATUS_ORDER: STATUS_ORDER,
  amount: amount,
  money: money,
  datetime: datetime,
  dateOnly: dateOnly,
  statusText: statusText,
  statusTheme: statusTheme,
  cargoText: cargoText,
  windowText: windowText,
  decorateOrder: decorateOrder,
}