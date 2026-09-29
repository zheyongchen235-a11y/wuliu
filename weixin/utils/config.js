/**
 * 全局配置。
 *
 * 注意：微信开发者工具中需勾选「详情 → 本地设置 → 不校验合法域名、web-view（业务域名）、
 * TLS 版本以及 HTTPS 证书」，否则无法访问本机 http 后端。
 * 真机调试或上线时请改为已备案的 https 域名。
 */
const BASE_URL = 'http://127.0.0.1:8000'
const API_PREFIX = '/api/v1'

module.exports = {
  BASE_URL,
  API_PREFIX,
  BASE: BASE_URL + API_PREFIX,
  APP_NAME: '车辆智能调度',
}