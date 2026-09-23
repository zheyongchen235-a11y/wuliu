import { api, getToken, setToken, clearToken } from '../api'

export default {
  namespaced: true,
  state: () => ({
    user: null, // { id, username, nickname, is_super, roles, permissions, menus, ... }
    loaded: false,
  }),
  getters: {
    isLogin: (s) => !!s.user,
    isSuper: (s) => !!s.user?.is_super,
    hasPerm: (s) => (code) => {
      if (!s.user) return false
      if (s.user.is_super) return true
      if (!code) return true
      return (s.user.permissions || []).includes(code)
    },
    hasRole: (s) => (code) => {
      if (!s.user) return false
      if (s.user.is_super) return true
      return (s.user.roles || []).includes(code)
    },
  },
  mutations: {
    SET_USER(state, user) {
      state.user = user
      state.loaded = true
    },
    CLEAR(state) {
      state.user = null
      state.loaded = false
    },
  },
  actions: {
    async login({ commit }, { username, password }) {
      const data = await api.login({ username, password })
      setToken(data.access_token, data.refresh_token)
      const me = await api.getMe()
      commit('SET_USER', me)
      return me
    },
    async fetchMe({ commit }) {
      if (!getToken()) return null
      try {
        const me = await api.getMe()
        commit('SET_USER', me)
        return me
      } catch (e) {
        clearToken()
        commit('CLEAR')
        return null
      }
    },
    async logout({ commit }) {
      try {
        await api.logout()
      } catch (e) {
        /* ignore */
      }
      clearToken()
      commit('CLEAR')
    },
  },
}
