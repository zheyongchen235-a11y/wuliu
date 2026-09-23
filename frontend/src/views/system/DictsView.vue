<template>
  <div>
    <div class="toolbar">
      <a-space>
        <a-input v-model:value="filters.keyword" placeholder="字典编码/名称" allow-clear style="width:220px" @pressEnter="load" />
        <a-button @click="load"><template #icon><reload-outlined /></template>刷新</a-button>
      </a-space>
      <a-button type="primary" v-if="hasPerm('system:dict:create')" @click="openCreate"><template #icon><plus-outlined /></template>新建字典</a-button>
    </div>
    <a-table :columns="cols" :data-source="rows" rowKey="id" :pagination="{ pageSize: 20 }" size="middle">
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'enabled'">
          <a-tag :color="record.enabled ? 'green' : 'default'">{{ record.enabled ? '启用' : '停用' }}</a-tag>
        </template>
        <template v-if="column.key === 'action'">
          <a-space>
            <a-button size="small" @click="openItems(record)">数据项</a-button>
            <a-button v-if="hasPerm('system:dict:update')" size="small" @click="openEdit(record)">编辑</a-button>
            <a-popconfirm v-if="hasPerm('system:dict:delete')" title="确认删除该字典及其数据项？" @confirm="remove(record)">
              <a-button size="small" danger>删除</a-button>
            </a-popconfirm>
          </a-space>
        </template>
      </template>
    </a-table>

    <!-- 字典编辑弹窗 -->
    <a-modal v-model:open="visible" :title="editing.id ? '编辑字典' : '新建字典'" @ok="submit" :confirm-loading="submitting">
      <a-form layout="vertical">
        <a-form-item label="字典编码" required>
          <a-input v-model:value="editing.code" :disabled="!!editing.id" placeholder="如 veh_type" />
        </a-form-item>
        <a-form-item label="字典名称" required>
          <a-input v-model:value="editing.name" />
        </a-form-item>
        <a-form-item label="描述">
          <a-textarea v-model:value="editing.description" :rows="2" />
        </a-form-item>
        <a-form-item label="启用">
          <a-switch v-model:checked="editing.enabled" />
        </a-form-item>
      </a-form>
    </a-modal>

    <!-- 数据项管理抽屉 -->
    <a-drawer :open="itemsVisible" @close="itemsVisible = false" :width="640" :title="`数据项管理 - ${currentDict?.name || ''}`">
      <div style="margin-bottom:12px">
        <a-button type="primary" v-if="hasPerm('system:dict:create')" @click="openItemCreate"><plus-outlined />新增数据项</a-button>
      </div>
      <a-table :columns="itemCols" :data-source="items" rowKey="id" :pagination="false" size="small">
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'enabled'">
            <a-tag :color="record.enabled ? 'green' : 'default'">{{ record.enabled ? '启用' : '停用' }}</a-tag>
          </template>
          <template v-if="column.key === 'action'">
            <a-space>
              <a-button v-if="hasPerm('system:dict:update')" size="small" @click="openItemEdit(record)">编辑</a-button>
              <a-popconfirm v-if="hasPerm('system:dict:delete')" title="确认删除？" @confirm="removeItem(record)">
                <a-button size="small" danger>删除</a-button>
              </a-popconfirm>
            </a-space>
          </template>
        </template>
      </a-table>

      <a-modal v-model:open="itemVisible" :title="itemEditing.id ? '编辑数据项' : '新增数据项'" @ok="submitItem" :confirm-loading="itemSubmitting">
        <a-form layout="vertical">
          <a-form-item label="显示文本" required>
            <a-input v-model:value="itemEditing.label" />
          </a-form-item>
          <a-form-item label="实际值" required>
            <a-input v-model:value="itemEditing.value" />
          </a-form-item>
          <a-form-item label="排序">
            <a-input-number v-model:value="itemEditing.sort" :min="0" style="width:100%" />
          </a-form-item>
          <a-form-item label="备注">
            <a-input v-model:value="itemEditing.remark" />
          </a-form-item>
          <a-form-item label="启用">
            <a-switch v-model:checked="itemEditing.enabled" />
          </a-form-item>
        </a-form>
      </a-modal>
    </a-drawer>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useStore } from 'vuex'
import { message } from 'ant-design-vue'
import { ReloadOutlined, PlusOutlined } from '@ant-design/icons-vue'
import { api } from '../../api'

const store = useStore()
const hasPerm = (c) => store.getters['auth/hasPerm'](c)

const filters = ref({ keyword: '' })
const rows = ref([])
const cols = [
  { title: '编码', dataIndex: 'code', key: 'code' },
  { title: '名称', dataIndex: 'name', key: 'name' },
  { title: '描述', dataIndex: 'description', key: 'description', ellipsis: true },
  { title: '状态', key: 'enabled', width: 90 },
  { title: '操作', key: 'action', width: 240 },
]

const visible = ref(false)
const submitting = ref(false)
const editing = ref({})

async function load() {
  try {
    const data = await api.listDicts({ keyword: filters.value.keyword || undefined })
    rows.value = Array.isArray(data) ? data : (data.items || [])
  } catch (e) {
    message.error(e.message)
  }
}
function openCreate() {
  editing.value = { code: '', name: '', description: '', enabled: true }
  visible.value = true
}
function openEdit(r) {
  editing.value = { ...r }
  visible.value = true
}
async function submit() {
  if (!editing.value.code || !editing.value.name) {
    message.warning('请填写编码和名称')
    return
  }
  submitting.value = true
  try {
    if (editing.value.id) {
      await api.updateDict(editing.value.id, {
        name: editing.value.name,
        description: editing.value.description,
        enabled: editing.value.enabled,
      })
    } else {
      await api.createDict(editing.value)
    }
    message.success('保存成功')
    visible.value = false
    load()
  } catch (e) {
    message.error(e.message)
  } finally {
    submitting.value = false
  }
}
async function remove(r) {
  try {
    await api.deleteDict(r.id)
    message.success('已删除')
    load()
  } catch (e) {
    message.error(e.message)
  }
}

// 数据项
const itemsVisible = ref(false)
const currentDict = ref(null)
const items = ref([])
const itemCols = [
  { title: '文本', dataIndex: 'label', key: 'label' },
  { title: '值', dataIndex: 'value', key: 'value' },
  { title: '排序', dataIndex: 'sort', key: 'sort', width: 70 },
  { title: '状态', key: 'enabled', width: 80 },
  { title: '备注', dataIndex: 'remark', key: 'remark', ellipsis: true },
  { title: '操作', key: 'action', width: 160 },
]
const itemVisible = ref(false)
const itemSubmitting = ref(false)
const itemEditing = ref({})

async function openItems(r) {
  currentDict.value = r
  itemsVisible.value = true
  await loadItems()
}
async function loadItems() {
  if (!currentDict.value) return
  try {
    const data = await api.listDictItems(currentDict.value.id)
    items.value = Array.isArray(data) ? data : (data.items || [])
  } catch (e) {
    message.error(e.message)
  }
}
function openItemCreate() {
  itemEditing.value = { label: '', value: '', sort: 0, remark: '', enabled: true }
  itemVisible.value = true
}
function openItemEdit(r) {
  itemEditing.value = { ...r }
  itemVisible.value = true
}
async function submitItem() {
  if (!itemEditing.value.label || !itemEditing.value.value) {
    message.warning('请填写文本和值')
    return
  }
  itemSubmitting.value = true
  try {
    const dictId = currentDict.value.id
    if (itemEditing.value.id) {
      await api.updateDictItem(dictId, itemEditing.value.id, {
        label: itemEditing.value.label,
        value: itemEditing.value.value,
        sort: itemEditing.value.sort,
        remark: itemEditing.value.remark,
        enabled: itemEditing.value.enabled,
      })
    } else {
      await api.createDictItem(dictId, {
        label: itemEditing.value.label,
        value: itemEditing.value.value,
        sort: itemEditing.value.sort,
        remark: itemEditing.value.remark,
        enabled: itemEditing.value.enabled,
      })
    }
    message.success('保存成功')
    itemVisible.value = false
    loadItems()
  } catch (e) {
    message.error(e.message)
  } finally {
    itemSubmitting.value = false
  }
}
async function removeItem(r) {
  try {
    await api.deleteDictItem(currentDict.value.id, r.id)
    message.success('已删除')
    loadItems()
  } catch (e) {
    message.error(e.message)
  }
}

onMounted(load)
</script>

<style scoped>
.toolbar { display: flex; justify-content: space-between; margin-bottom: 16px; }
</style>
