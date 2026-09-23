<template>
  <div class="login-wrap">
    <a-card class="login-card" :bordered="false">
      <div class="login-header">
        <h1>车辆智能调度 Agent</h1>
        <p class="sub">RBAC 智能调度平台</p>
      </div>
      <a-form
        :model="form"
        layout="vertical"
        @finish="onSubmit"
        autocomplete="off"
      >
        <a-form-item name="username" :rules="[{ required: true, message: '请输入用户名' }]">
          <a-input v-model:value="form.username" size="large" placeholder="用户名">
            <template #prefix><user-outlined /></template>
          </a-input>
        </a-form-item>
        <a-form-item name="password" :rules="[{ required: true, message: '请输入密码' }]">
          <a-input-password v-model:value="form.password" size="large" placeholder="密码" @pressEnter="onSubmit">
            <template #prefix><lock-outlined /></template>
          </a-input-password>
        </a-form-item>
        <a-button type="primary" size="large" block html-type="submit" :loading="loading">登 录</a-button>
      </a-form>
      <a-alert
        class="hint"
        type="info"
        show-icon
        :message="`演示账号：admin/admin123 · dispatcher/dispatcher123 · viewer/viewer123`"
      />
    </a-card>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useStore } from 'vuex'
import { message } from 'ant-design-vue'
import { UserOutlined, LockOutlined } from '@ant-design/icons-vue'

const router = useRouter()
const route = useRoute()
const store = useStore()
const loading = ref(false)
const form = ref({ username: 'admin', password: 'admin123' })

async function onSubmit() {
  loading.value = true
  try {
    await store.dispatch('auth/login', form.value)
    message.success('登录成功')
    const redirect = route.query.redirect || '/'
    router.replace(redirect)
  } catch (e) {
    message.error(e.message || '登录失败')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-wrap {
  height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
}
.login-card {
  width: 380px;
  border-radius: 12px;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.2);
}
.login-header {
  text-align: center;
  margin-bottom: 24px;
}
.login-header h1 {
  font-size: 22px;
  margin: 0 0 4px;
  color: #1e3c72;
}
.login-header .sub {
  color: #888;
  font-size: 13px;
  margin: 0;
}
.hint {
  margin-top: 16px;
  font-size: 12px;
}
</style>
