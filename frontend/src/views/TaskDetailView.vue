<template>
  <div>
    <a-page-header
      :title="`任务 ${taskId.slice(0, 8)}`"
      :sub-title="task && task.schedule_date + ' / ' + (task && task.time_window)"
      @back="() => $router.push('/tasks')"
    >
      <template #extra>
        <a-tag v-if="task" :color="statusColor(task.status)">{{ statusLabel(task.status) }}</a-tag>
      </template>
    </a-page-header>

    <a-row :gutter="16" style="margin-top: 8px">
      <a-col :span="16">
        <a-card title="候选方案" size="small">
          <a-table
            :columns="planColumns"
            :data-source="plans"
            row-key="id"
            :pagination="false"
            size="small"
            :row-class-name="(r) => (task && task.selected_plan_id === r.plan_id ? 'row-selected' : '')"
          >
            <template #bodyCell="{ column, record }">
              <template v-if="column.dataIndex === 'plan_id'">
                <a-radio :checked="selectedPlanId === record.plan_id" @change="selectedPlanId = record.plan_id">{{ record.plan_id }}</a-radio>
              </template>
              <template v-if="column.dataIndex === 'strategy'">{{ strategyLabel(record.strategy) }}</template>
              <template v-if="column.dataIndex === 'solver_type'">
                <a-tag :color="record.solver_type === 'cpsat' ? 'purple' : 'blue'">{{ record.solver_type }}</a-tag>
              </template>
              <template v-if="column.dataIndex === 'avg_load_rate'">{{ (record.avg_load_rate * 100).toFixed(1) }}%</template>
              <template v-if="column.dataIndex === 'four_two_usage'">{{ (record.four_two_usage * 100).toFixed(1) }}%</template>
              <template v-if="column.dataIndex === 'big_small_achievement'">{{ (record.big_small_achievement * 100).toFixed(1) }}%</template>
              <template v-if="column.dataIndex === 'estimated_cost'">¥{{ record.estimated_cost.toFixed(0) }}</template>
              <template v-if="column.dataIndex === 'score'">
                <a-tooltip :title="record.score && record.score.explanation">
                  <span>{{ record.score ? record.score.total_score.toFixed(4) : '-' }}</span>
                </a-tooltip>
              </template>
              <template v-if="column.dataIndex === 'action'">
                <a-button size="small" type="link" @click="showPlanDetail(record)">明细</a-button>
              </template>
            </template>
          </a-table>

          <div style="margin-top: 12px">
            <a-space>
              <a-button
                type="primary"
                :disabled="!canConfirm"
                :loading="confirming"
                @click="onConfirm(true)"
              >确认采用</a-button>
              <a-button :disabled="!canConfirm" @click="onConfirm(false)">拒绝并重排</a-button>
              <a-button @click="onReplan" :loading="replanning" :disabled="!task">触发异常重排</a-button>
              <a-button @click="loadAll">刷新</a-button>
            </a-space>
          </div>
        </a-card>

        <a-card title="方案解释（LLM）" size="small" style="margin-top: 16px">
          <pre style="white-space: pre-wrap; font-family: inherit; margin: 0">{{ explanation || '尚未生成' }}</pre>
        </a-card>

        <a-card title="调度报告" size="small" style="margin-top: 16px" v-if="report">
          <pre style="white-space: pre-wrap; font-family: inherit; margin: 0">{{ report.content }}</pre>
        </a-card>
      </a-col>

      <a-col :span="8">
        <a-card title="实时进度" size="small">
          <a-steps :current="currentStepIndex" :status="progressStatus" direction="vertical" size="small">
            <a-step v-for="s in stepList" :key="s.key" :title="s.title" :description="s.desc" />
          </a-steps>
          <a-progress :percent="progress" :status="progressStatus" style="margin-top: 8px" />
          <div style="margin-top: 8px; max-height: 200px; overflow: auto; background: #fafafa; padding: 8px; font-size: 12px">
            <div v-for="(m, i) in messages" :key="i">
              <a-tag :color="wsStatusColor(m.status)">{{ m.status }}</a-tag>
              <span style="color: #888">[{{ m.node }}] {{ m.progress }}%</span>
              {{ m.message }}
            </div>
          </div>
        </a-card>

        <a-card title="任务信息" size="small" style="margin-top: 16px" v-if="task">
          <a-descriptions :column="1" size="small">
            <a-descriptions-item label="任务ID">{{ task.id }}</a-descriptions-item>
            <a-descriptions-item label="调度日期">{{ task.schedule_date }}</a-descriptions-item>
            <a-descriptions-item label="时段">{{ task.time_window }}</a-descriptions-item>
            <a-descriptions-item label="规则版本">{{ task.rule_version }}</a-descriptions-item>
            <a-descriptions-item label="当前节点">{{ task.current_node }}</a-descriptions-item>
            <a-descriptions-item label="重排次数">{{ task.replan_count }}</a-descriptions-item>
            <a-descriptions-item label="创建时间">{{ task.created_at }}</a-descriptions-item>
            <a-descriptions-item label="错误">{{ task.error_message || '-' }}</a-descriptions-item>
          </a-descriptions>
        </a-card>

        <a-card title="异常事件" size="small" style="margin-top: 16px">
          <a-list size="small" :data-source="exceptions" :locale="{ emptyText: '暂无异常' }">
            <template #renderItem="{ item }">
              <a-list-item>
                <a-list-item-meta>
                  <template #title>
                    <a-tag :color="severityColor(item.severity)">{{ item.severity }}</a-tag>
                    {{ item.title }}
                  </template>
                  <template #description>{{ item.event_type }} · {{ item.description || '-' }}</template>
                </a-list-item-meta>
              </a-list-item>
            </template>
          </a-list>
          <a-button size="small" type="dashed" block style="margin-top: 8px" @click="showException = true">
            上报异常
          </a-button>
        </a-card>
      </a-col>
    </a-row>

    <a-modal v-model:open="detailVisible" :title="`方案 ${currentDetail && currentDetail.plan_id} 明细`" width="900px" :footer="null">
      <a-table
        :columns="detailColumns"
        :data-source="currentDetail && currentDetail.details"
        row-key="id"
        :pagination="{ pageSize: 10 }"
        size="small"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.dataIndex === 'vehicle_type'">{{ vehicleTypeLabel(record.vehicle_type) }}</template>
          <template v-if="column.dataIndex === 'store_ids'">
            <a-tag v-for="s in record.store_ids" :key="s">{{ s }}</a-tag>
          </template>
        </template>
      </a-table>
    </a-modal>

    <a-modal v-model:open="showException" title="上报异常事件" @ok="onSubmitException">
      <a-form :label-col="{ span: 6 }">
        <a-form-item label="类型" required>
          <a-select v-model:value="excForm.event_type">
            <a-select-option value="vehicle_failure">车辆故障</a-select-option>
            <a-select-option value="driver_absence">司机缺勤</a-select-option>
            <a-select-option value="demand_change">货量变更</a-select-option>
            <a-select-option value="traffic">交通管制</a-select-option>
            <a-select-option value="terrain_lock">地形临时管控</a-select-option>
            <a-select-option value="other">其他</a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item label="严重程度">
          <a-radio-group v-model:value="excForm.severity">
            <a-radio value="info">info</a-radio>
            <a-radio value="warning">warning</a-radio>
            <a-radio value="critical">critical</a-radio>
          </a-radio-group>
        </a-form-item>
        <a-form-item label="标题" required><a-input v-model:value="excForm.title" /></a-form-item>
        <a-form-item label="描述"><a-textarea v-model:value="excForm.description" :rows="3" /></a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import { message } from 'ant-design-vue'
import { api, openProgressSocket } from '../api'

const route = useRoute()
const taskId = route.params.id

const task = ref(null)
const plans = ref([])
const exceptions = ref([])
const report = ref(null)
const explanation = ref('')

const selectedPlanId = ref(null)
const confirming = ref(false)
const replanning = ref(false)
const detailVisible = ref(false)
const currentDetail = ref(null)
const showException = ref(false)

const messages = ref([])
const progress = ref(0)
const ws = ref(null)

const stepList = [
  { key: 'load_task', title: '加载任务', desc: '' },
  { key: 'data_perception', title: '数据感知', desc: '' },
  { key: 'constraint_parse', title: '规则解析', desc: '' },
  { key: 'rule_validation', title: '规则校验', desc: '' },
  { key: 'plan_generation', title: '方案生成', desc: '' },
  { key: 'plan_scoring', title: '方案评分', desc: '' },
  { key: 'plan_explanation', title: '方案解释', desc: '' },
  { key: 'human_confirmation', title: '人工确认', desc: '' },
  { key: 'dispatch_execution', title: '下发执行', desc: '' },
  { key: 'report_generation', title: '报告生成', desc: '' },
]

const currentStepIndex = computed(() => {
  if (!task.value) return 0
  const idx = stepList.findIndex((s) => s.key === task.value.current_node)
  return idx < 0 ? 0 : idx
})

const progressStatus = computed(() => {
  if (!task.value) return 'active'
  if (task.value.status === 'failed') return 'exception'
  if (task.value.status === 'completed') return 'success'
  if (task.value.status === 'awaiting_confirmation') return 'pause'
  return 'active'
})

const canConfirm = computed(() => task.value && task.value.status === 'awaiting_confirmation' && selectedPlanId.value)

const planColumns = [
  { title: '选择', dataIndex: 'plan_id', width: 70 },
  { title: '方案', dataIndex: 'name' },
  { title: '策略', dataIndex: 'strategy', width: 140 },
  { title: '求解器', dataIndex: 'solver_type', width: 90 },
  { title: '趟次', dataIndex: 'total_trips', width: 70 },
  { title: '车辆', dataIndex: 'used_vehicles', width: 70 },
  { title: '装载率', dataIndex: 'avg_load_rate', width: 90 },
  { title: '4m2使用率', dataIndex: 'four_two_usage', width: 100 },
  { title: '大包小包达成', dataIndex: 'big_small_achievement', width: 120 },
  { title: '成本', dataIndex: 'estimated_cost', width: 90 },
  { title: '评分', dataIndex: 'score', width: 90 },
  { title: '操作', dataIndex: 'action', width: 80 },
]

const detailColumns = [
  { title: '车辆ID', dataIndex: 'vehicle_id' },
  { title: '车型', dataIndex: 'vehicle_type', width: 80 },
  { title: '趟次', dataIndex: 'trip_no', width: 60 },
  { title: '时段', dataIndex: 'time_window', width: 80 },
  { title: '装载量', dataIndex: 'load_amount', width: 90 },
  { title: '顺序', dataIndex: 'sequence', width: 60 },
  { title: '门店', dataIndex: 'store_ids' },
]

function vehicleTypeLabel(t) { return { '4m2': '四米二', big: '大包', small: '小包' }[t] || t }
function strategyLabel(s) {
  return { '4m2_priority': '四米二优先', 'cost_min': '成本最低', 'big_small_priority': '大包小包保障', 'load_balance': '装载率均衡' }[s] || s
}
function statusColor(s) {
  return { created: 'default', running: 'blue', awaiting_confirmation: 'orange', confirmed: 'cyan',
    dispatched: 'purple', completed: 'green', failed: 'red', replanning: 'gold' }[s] || 'default'
}
function statusLabel(s) {
  return { created: '已创建', running: '运行中', awaiting_confirmation: '等待确认', confirmed: '已确认',
    dispatched: '已下发', completed: '已完成', failed: '失败', replanning: '重排中' }[s] || s
}
function wsStatusColor(s) {
  return { running: 'blue', done: 'green', error: 'red', awaiting_confirmation: 'orange' }[s] || 'default'
}
function severityColor(s) {
  return { info: 'blue', warning: 'orange', critical: 'red' }[s] || 'default'
}

async function loadAll() {
  try {
    const [t, ps, excs] = await Promise.all([
      api.getTask(taskId),
      api.listPlans(taskId).catch(() => []),
      api.listExceptions(taskId).catch(() => []),
    ])
    task.value = t
    plans.value = ps
    exceptions.value = excs
    if (!selectedPlanId.value && ps.length) {
      // 默认推荐评分最高的方案
      selectedPlanId.value = ps[0].plan_id
    }
    explanation.value = ps[0] && ps[0].score && ps[0].score.explanation || ''
    try {
      report.value = await api.getReport(taskId)
    } catch (e) {
      report.value = null
    }
  } catch (e) {
    message.error('加载失败: ' + e.message)
  }
}

function showPlanDetail(plan) {
  currentDetail.value = plan
  detailVisible.value = true
}

async function onConfirm(approved) {
  if (!selectedPlanId.value) {
    message.warning('请先选择方案')
    return
  }
  confirming.value = true
  try {
    await api.confirmTask(taskId, {
      approved,
      plan_id: selectedPlanId.value,
      operator: 'dispatcher01',
      comment: approved ? '前端确认' : '拒绝并要求重排',
    })
    message.success(approved ? '已确认，开始下发' : '已拒绝，工作流将重排')
    setTimeout(loadAll, 1000)
  } catch (e) {
    message.error('确认失败: ' + e.message)
  } finally {
    confirming.value = false
  }
}

async function onReplan() {
  replanning.value = true
  try {
    await api.replanTask(taskId, { trigger: 'manual', reason: '调度员手动触发重排' })
    message.success('已触发重排')
    setTimeout(loadAll, 1000)
  } catch (e) {
    message.error('重排失败: ' + e.message)
  } finally {
    replanning.value = false
  }
}

const excForm = reactive({
  event_type: 'vehicle_failure', severity: 'warning', title: '', description: '',
})

async function onSubmitException() {
  if (!excForm.title) {
    message.warning('请填写标题')
    return
  }
  try {
    await api.createException(taskId, { ...excForm })
    message.success('已上报')
    showException.value = false
    excForm.title = ''
    excForm.description = ''
    await loadAll()
  } catch (e) {
    message.error('上报失败: ' + e.message)
  }
}

function connectWs() {
  ws.value = openProgressSocket(taskId, (msg) => {
    messages.value.unshift(msg)
    if (messages.value.length > 50) messages.value.pop()
    if (typeof msg.progress === 'number') progress.value = msg.progress
    if (msg.status === 'done' || msg.status === 'error' || msg.status === 'awaiting_confirmation') {
      loadAll()
    }
  })
}

let poller = null
onMounted(() => {
  loadAll()
  connectWs()
  poller = setInterval(loadAll, 5000)
})
onUnmounted(() => {
  if (ws.value) ws.value.close()
  if (poller) clearInterval(poller)
})
</script>

<style scoped>
:deep(.row-selected) {
  background: #e6f4ff;
}
</style>
