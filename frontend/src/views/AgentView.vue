<template>
  <div>
    <a-page-header
      title="智能调度 Agent"
      sub-title="LangGraph 编排 · OR-Tools CP-SAT 求解 · DeepSeek 大模型解释"
      style="padding-left: 0"
    >
      <template #extra>
        <a-space>
          <a-tag :color="llmEnabled ? 'purple' : 'default'">
            {{ llmEnabled ? `${llmProvider} / ${llmModel}` : '规则化解释 (mock)' }}
          </a-tag>
          <a-tag v-if="task" :color="statusColor(task.status)">{{ statusLabel(task.status) }}</a-tag>
        </a-space>
      </template>
    </a-page-header>

    <!-- Agent 控制台 -->
    <a-card size="small" title="Agent 控制台" style="margin-bottom: 16px">
      <a-form layout="inline">
        <a-form-item label="调度日期">
          <a-date-picker v-model:value="form.schedule_date" value-format="YYYY-MM-DD" style="width: 150px" />
        </a-form-item>
        <a-form-item label="时段">
          <a-select v-model:value="form.time_window" style="width: 110px">
            <a-select-option value="all">全天</a-select-option>
            <a-select-option value="AM">上午</a-select-option>
            <a-select-option value="PM">下午</a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item label="规则版本">
          <a-input v-model:value="form.rule_version" placeholder="默认当前激活" style="width: 130px" />
        </a-form-item>
        <a-form-item>
          <a-button type="primary" :loading="starting" :disabled="running" @click="onCreateAndStart">
            <thunderbolt-outlined /> 创建并启动 Agent
          </a-button>
        </a-form-item>
        <a-form-item>
          <a-button :disabled="!task" @click="loadAll">刷新</a-button>
        </a-form-item>
      </a-form>
      <div v-if="task" style="margin-top: 8px; color: #888; font-size: 12px">
        当前任务：{{ task.id }}（{{ task.schedule_date }} / {{ task.time_window }}）
        <a-button type="link" size="small" @click="$router.push(`/tasks/${task.id}`)">查看任务详情</a-button>
      </div>
    </a-card>

    <!-- 11 阶段流程可视化 -->
    <a-card size="small" title="Agent 执行流程（11 阶段）" style="margin-bottom: 16px">
      <div class="pipeline">
        <template v-for="(s, i) in stages" :key="s.key">
          <div class="pnode" :class="[stageStatus(s), { branch: s.branch }]">
            <div class="pnode-head">
              <span class="pnode-idx">{{ i + 1 }}</span>
              <span class="pnode-state">{{ stageStateLabel(stageStatus(s)) }}</span>
            </div>
            <div class="pnode-title">{{ s.title }}</div>
            <div class="pnode-desc">{{ s.desc }}</div>
          </div>
          <div v-if="i < stages.length - 1" class="parrow">➜</div>
        </template>
      </div>
      <a-progress :percent="progress" :status="progressStatus" style="margin-top: 12px" />
    </a-card>

    <a-row :gutter="16">
      <a-col :span="15">
        <!-- 候选方案 + 人工确认 -->
        <a-card size="small" title="候选方案与人工确认">
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
              <template v-if="column.dataIndex === 'avg_load_rate'">{{ (record.avg_load_rate * 100).toFixed(1) }}%</template>
              <template v-if="column.dataIndex === 'four_two_usage'">{{ (record.four_two_usage * 100).toFixed(1) }}%</template>
              <template v-if="column.dataIndex === 'estimated_cost'">¥{{ record.estimated_cost.toFixed(0) }}</template>
              <template v-if="column.dataIndex === 'score'">
                {{ record.score ? record.score.total_score.toFixed(4) : '-' }}
              </template>
            </template>
          </a-table>
          <a-empty v-if="!plans.length" description="Agent 尚未生成候选方案" style="margin: 16px 0" />
          <div style="margin-top: 12px">
            <a-space>
              <a-button type="primary" :disabled="!canConfirm" :loading="confirming" @click="onConfirm(true)">
                <check-outlined /> 确认采用
              </a-button>
              <a-button :disabled="!canConfirm" @click="onConfirm(false)">
                <close-outlined /> 拒绝并重排
              </a-button>
              <a-button :loading="replanning" :disabled="!task" @click="onReplan">
                <reload-outlined /> 触发异常重排
              </a-button>
            </a-space>
          </div>
        </a-card>

        <!-- LLM 方案解释 -->
        <a-card size="small" style="margin-top: 16px">
          <template #title>
            <robot-outlined /> 方案解释（大模型生成）
          </template>
          <template #extra>
            <a-tag :color="llmEnabled ? 'purple' : 'default'">{{ llmEnabled ? 'DeepSeek' : 'mock' }}</a-tag>
          </template>
          <pre class="text-block">{{ agentState.plan_explanation || '尚未生成（需 Agent 运行至「方案解释」阶段）' }}</pre>
        </a-card>

        <!-- 调度报告 -->
        <a-card size="small" title="调度报告" style="margin-top: 16px" v-if="report">
          <pre class="text-block">{{ report.content }}</pre>
        </a-card>
      </a-col>

      <a-col :span="9">
        <!-- 实时执行日志 -->
        <a-card size="small" title="实时执行日志">
          <div class="log-box">
            <div v-for="(m, i) in messages" :key="i" class="log-line">
              <a-tag :color="wsStatusColor(m.status)" style="margin-right: 6px">{{ m.status }}</a-tag>
              <span class="log-node">[{{ m.node }}]</span>
              <span class="log-progress">{{ m.progress }}%</span>
              <span>{{ m.message }}</span>
            </div>
            <a-empty v-if="!messages.length" description="暂无日志，启动 Agent 后实时推送" />
          </div>
        </a-card>

        <!-- 任务信息 -->
        <a-card size="small" title="任务信息" style="margin-top: 16px" v-if="task">
          <a-descriptions :column="1" size="small">
            <a-descriptions-item label="任务ID">{{ task.id }}</a-descriptions-item>
            <a-descriptions-item label="调度日期">{{ task.schedule_date }}</a-descriptions-item>
            <a-descriptions-item label="时段">{{ task.time_window }}</a-descriptions-item>
            <a-descriptions-item label="规则版本">{{ task.rule_version }}</a-descriptions-item>
            <a-descriptions-item label="当前节点">{{ task.current_node || '-' }}</a-descriptions-item>
            <a-descriptions-item label="下一步">{{ (agentState.next_nodes || []).join(', ') || '-' }}</a-descriptions-item>
            <a-descriptions-item label="候选方案数">{{ agentState.candidate_count ?? 0 }}</a-descriptions-item>
            <a-descriptions-item label="重排次数">{{ task.replan_count }}</a-descriptions-item>
            <a-descriptions-item label="校验错误">
              <span v-if="(agentState.validation_errors || []).length" style="color: #ff4d4f">
                {{ agentState.validation_errors.join('; ') }}
              </span>
              <span v-else>无</span>
            </a-descriptions-item>
            <a-descriptions-item label="错误">{{ task.error_message || '-' }}</a-descriptions-item>
          </a-descriptions>
        </a-card>

        <!-- Agent 能力说明 -->
        <a-card size="small" title="Agent 能力" style="margin-top: 16px">
          <ul class="ability">
            <li v-for="s in stages" :key="s.key">
              <b>{{ s.title }}</b> — {{ s.desc }}
            </li>
          </ul>
        </a-card>
      </a-col>
    </a-row>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue'
import { message } from 'ant-design-vue'
import {
  ThunderboltOutlined,
  RobotOutlined,
  ReloadOutlined,
  CheckOutlined,
  CloseOutlined,
} from '@ant-design/icons-vue'
import { api, openProgressSocket } from '../api'

function todayStr() {
  const d = new Date()
  const p = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`
}

const form = reactive({ schedule_date: todayStr(), time_window: 'AM', rule_version: '' })

const task = ref(null)
const plans = ref([])
const report = ref(null)
const agentState = ref({})
const messages = ref([])
const progress = ref(0)
const nodeStatus = reactive({})
const selectedPlanId = ref(null)
const starting = ref(false)
const confirming = ref(false)
const replanning = ref(false)
const ws = ref(null)
let poller = null

const llmEnabled = computed(() => !!agentState.value.llm_enabled)
const llmProvider = computed(() => agentState.value.llm_provider || 'mock')
const llmModel = computed(() => agentState.value.llm_model || '')

const running = computed(() => task.value && ['running', 'replanning'].includes(task.value.status))
const canConfirm = computed(
  () => task.value && task.value.status === 'awaiting_confirmation' && selectedPlanId.value
)
const progressStatus = computed(() => {
  if (!task.value) return 'active'
  if (task.value.status === 'failed') return 'exception'
  if (task.value.status === 'completed') return 'success'
  return 'active'
})

// 11 阶段：调度任务创建 / 数据感知 / 约束解析 / 规则校验 / 多方案生成 /
// 方案评分 / 方案解释 / 人工确认 / 下发执行 / 异常重排 / 调度报告生成
const stages = [
  { key: 'task_created', title: '调度任务创建', desc: '创建调度任务并发起工作流' },
  { key: 'data_perception', title: '数据感知', desc: '拉取门店/车辆/线路/货量与规则快照' },
  { key: 'constraint_parse', title: '约束解析', desc: '解析硬约束/软约束与评分权重' },
  { key: 'rule_validation', title: '规则校验', desc: '校验数据与规则冲突' },
  { key: 'plan_generation', title: '多方案生成', desc: 'CP-SAT 生成 4 套候选方案' },
  { key: 'plan_scoring', title: '方案评分', desc: '五维加权评分并排序' },
  { key: 'plan_explanation', title: '方案解释', desc: '大模型生成方案比选解释' },
  { key: 'human_confirmation', title: '人工确认', desc: '调度员确认/拒绝方案' },
  { key: 'dispatch_execution', title: '下发执行', desc: '下发 TMS 并写执行记录' },
  { key: 'replan', title: '异常重排', desc: '异常监控与局部重排', branch: true },
  { key: 'report_generation', title: '调度报告生成', desc: '生成报告与 AI 执行总结' },
]

function stageIndex(key) {
  return stages.findIndex((s) => s.key === key)
}

function stageStatus(s) {
  if (s.key === 'task_created') return task.value ? 'done' : 'pending'
  if (s.branch) return task.value && task.value.replan_count > 0 ? 'done' : 'pending'
  const st = nodeStatus[s.key]
  if (st === 'done') return 'done'
  if (st === 'error') return 'error'
  if (st === 'awaiting_confirmation') return 'paused'
  if (st === 'running') return 'running'
  const cur = task.value && task.value.current_node
  if (cur && cur === s.key) return 'running'
  const ci = stageIndex(cur)
  const mi = stageIndex(s.key)
  if (ci >= 0 && mi >= 0 && mi < ci) return 'done'
  if (task.value && ['completed', 'dispatched', 'confirmed'].includes(task.value.status)) return 'done'
  return 'pending'
}

function stageStateLabel(st) {
  return { done: '已完成', running: '运行中', pending: '待执行', error: '异常', paused: '等待确认' }[st] || st
}

const planColumns = [
  { title: '选择', dataIndex: 'plan_id', width: 70 },
  { title: '方案', dataIndex: 'name' },
  { title: '策略', dataIndex: 'strategy', width: 130 },
  { title: '趟次', dataIndex: 'total_trips', width: 60 },
  { title: '车辆', dataIndex: 'used_vehicles', width: 60 },
  { title: '装载率', dataIndex: 'avg_load_rate', width: 80 },
  { title: '4m2使用率', dataIndex: 'four_two_usage', width: 90 },
  { title: '成本', dataIndex: 'estimated_cost', width: 80 },
  { title: '评分', dataIndex: 'score', width: 80 },
]

function strategyLabel(s) {
  return {
    '4m2_priority': '四米二优先',
    'cost_min': '成本最低',
    'big_small_priority': '大包小包保障',
    'load_balance': '装载率均衡',
  }[s] || s
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

async function loadAll() {
  if (!task.value) return
  const id = task.value.id
  try {
    const [t, ps, st] = await Promise.all([
      api.getTask(id),
      api.listPlans(id).catch(() => []),
      api.getAgentState(id).catch(() => ({})),
    ])
    task.value = t
    plans.value = ps
    agentState.value = st || {}
    if (!selectedPlanId.value && ps.length) selectedPlanId.value = ps[0].plan_id
    if (typeof st?.replan_count === 'number') task.value.replan_count = st.replan_count
    try {
      report.value = await api.getReport(id)
    } catch (e) {
      report.value = null
    }
  } catch (e) {
    message.error('加载失败: ' + e.message)
  }
}

async function onCreateAndStart() {
  if (!form.schedule_date) {
    message.warning('请选择调度日期')
    return
  }
  starting.value = true
  try {
    const payload = { schedule_date: form.schedule_date, time_window: form.time_window }
    if (form.rule_version) payload.rule_version = form.rule_version
    const created = await api.createTask(payload)
    task.value = created
    plans.value = []
    report.value = null
    agentState.value = {}
    messages.value = []
    progress.value = 0
    selectedPlanId.value = null
    Object.keys(nodeStatus).forEach((k) => delete nodeStatus[k])
    connectWs(created.id)
    await api.startTask(created.id)
    message.success('Agent 已启动，正在执行 11 阶段工作流')
    setTimeout(loadAll, 1500)
  } catch (e) {
    message.error('启动失败: ' + e.message)
  } finally {
    starting.value = false
  }
}

async function onConfirm(approved) {
  if (!selectedPlanId.value) {
    message.warning('请先选择方案')
    return
  }
  confirming.value = true
  try {
    await api.confirmTask(task.value.id, {
      approved,
      plan_id: selectedPlanId.value,
      operator: 'agent-console',
      comment: approved ? 'Agent 控制台确认' : '拒绝并要求重排',
    })
    message.success(approved ? '已确认，Agent 继续下发执行' : '已拒绝，Agent 将重新生成方案')
    setTimeout(loadAll, 1200)
  } catch (e) {
    message.error('确认失败: ' + e.message)
  } finally {
    confirming.value = false
  }
}

async function onReplan() {
  replanning.value = true
  try {
    await api.replanTask(task.value.id, { trigger: 'manual', reason: 'Agent 控制台手动触发重排' })
    message.success('已触发异常重排')
    setTimeout(loadAll, 1200)
  } catch (e) {
    message.error('重排失败: ' + e.message)
  } finally {
    replanning.value = false
  }
}

function connectWs(taskId) {
  if (ws.value) {
    try { ws.value.close() } catch (e) { /* ignore */ }
  }
  ws.value = openProgressSocket(taskId, (msg) => {
    messages.value.unshift(msg)
    if (messages.value.length > 80) messages.value.pop()
    if (msg.node) nodeStatus[msg.node] = msg.status
    if (typeof msg.progress === 'number') progress.value = msg.progress
    if (['done', 'error', 'awaiting_confirmation'].includes(msg.status)) loadAll()
  })
}

onMounted(async () => {
  // 自动加载最近一次调度任务，便于直接观察 Agent 执行
  try {
    const list = await api.listTasks({ limit: 20 })
    if (list && list.length) {
      const latest = list.slice().sort((a, b) => String(b.created_at).localeCompare(String(a.created_at)))[0]
      task.value = latest
      connectWs(latest.id)
      await loadAll()
    }
  } catch (e) {
    /* 忽略：无任务时展示空态 */
  }
  poller = setInterval(loadAll, 4000)
})

onUnmounted(() => {
  if (ws.value) ws.value.close()
  if (poller) clearInterval(poller)
})
</script>

<style scoped>
.pipeline {
  display: flex;
  flex-wrap: wrap;
  align-items: stretch;
  gap: 6px;
}
.pnode {
  flex: 0 0 auto;
  width: 152px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 8px 10px;
  background: #fafafa;
  transition: all 0.2s;
}
.pnode-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 4px;
}
.pnode-idx {
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: #d9d9d9;
  color: #fff;
  font-size: 11px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}
.pnode-state {
  font-size: 11px;
  color: #999;
}
.pnode-title {
  font-size: 13px;
  font-weight: 600;
}
.pnode-desc {
  font-size: 11px;
  color: #888;
  margin-top: 2px;
  line-height: 1.4;
}
.pnode.done {
  border-color: #52c41a;
  background: #f6ffed;
}
.pnode.done .pnode-idx {
  background: #52c41a;
}
.pnode.running {
  border-color: #1677ff;
  background: #e6f4ff;
  box-shadow: 0 0 0 2px rgba(22, 119, 255, 0.15);
}
.pnode.running .pnode-idx {
  background: #1677ff;
}
.pnode.paused {
  border-color: #faad14;
  background: #fffbe6;
}
.pnode.paused .pnode-idx {
  background: #faad14;
}
.pnode.error {
  border-color: #ff4d4f;
  background: #fff2f0;
}
.pnode.error .pnode-idx {
  background: #ff4d4f;
}
.pnode.branch {
  border-style: dashed;
}
.parrow {
  display: flex;
  align-items: center;
  color: #bfbfbf;
  font-size: 13px;
}
.text-block {
  white-space: pre-wrap;
  font-family: inherit;
  margin: 0;
  line-height: 1.6;
}
.log-box {
  max-height: 320px;
  overflow: auto;
  background: #fafafa;
  border-radius: 6px;
  padding: 8px;
  font-size: 12px;
}
.log-line {
  padding: 2px 0;
  border-bottom: 1px dashed #f0f0f0;
}
.log-node {
  color: #1677ff;
  margin-right: 4px;
}
.log-progress {
  color: #999;
  margin-right: 4px;
}
.ability {
  margin: 0;
  padding-left: 18px;
  font-size: 12px;
  color: #666;
  line-height: 1.9;
}
:deep(.row-selected) {
  background: #e6f4ff;
}
</style>
