# 车辆智能调度 Agent + RBAC 系统

> 基于 LangGraph Agent 工作流 + OR-Tools CP-SAT 求解器的车辆智能调度系统，集成完整 RBAC 权限管理与 DeepSeek 大模型方案解释。

## 项目简介

本项目实现了一个物流配送车辆的智能调度 Agent：以 LangGraph 编排多节点工作流，结合 OR-Tools CP-SAT 约束规划求解器生成多套候选调度方案，经五维加权评分后由 DeepSeek 大模型生成自然语言比选解释，支持人工确认下发与异常重排。同时内置完整的 RBAC（基于角色的访问控制）后台管理系统，含用户、角色、权限、字典、参数、日志六大管理模块。

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端框架 | FastAPI + Uvicorn |
| Agent 编排 | LangGraph（15 节点工作流 + checkpointer + human-in-the-loop） |
| 求解器 | OR-Tools CP-SAT（4 种方案 + 5 维加权评分） |
| ORM | SQLAlchemy 2.0 |
| 数据库 | MySQL 8.0（演示可切 SQLite） |
| 认证鉴权 | JWT + bcrypt + RBAC 中间件 |
| 大模型 | DeepSeek（OpenAI 兼容接口，默认 mock 可切换） |
| 前端框架 | Vue 3 + Ant Design Vue 4 |
| 实时通信 | WebSocket（调度进度推送） |
| 容器化 | Docker + docker-compose |

## 功能模块

### 一、调度业务

| 模块 | 说明 |
|------|------|
| 调度任务 | 创建调度任务 → Agent 工作流自动执行 → 人工确认 → 下发 TMS |
| 门店管理 | 30 家门店，含地形/时段/优先级/经纬度 |
| 车辆管理 | 4m2(28台) / big(3台) / small(9台)，含地形能力 |
| 线路管理 | 6 条配送线路，含地形分级 |
| 规则配置 | 地形规则/趟次规则/装载规则/约束配置版本管理 |
| 报表中心 | 调度报告 + 出勤/装载率/趟次达成统计 |

### 二、系统管理（RBAC）

| 模块 | 说明 |
|------|------|
| 用户管理 | 用户 CRUD、角色分配、重置密码、启停 |
| 角色管理 | 角色 CRUD、权限分配、菜单分配、数据范围 |
| 权限管理 | 权限点（按钮/接口级）CRUD |
| 字典管理 | 数据源 + 数据项二级管理（车辆类型/地形/任务状态等） |
| 参数管理 | 系统参数 CRUD（求解时限/重排次数等） |
| 日志管理 | 操作日志自动记录 + 查询/删除/清空 |

### 三、Agent 工作流

LangGraph StateGraph 共 15 个节点，含异常重排分支与人工确认中断：

```
加载任务 → 数据感知 → 约束解析 → 规则校验 → 方案生成 → 方案评分
  → 方案解释(LLM) → 人工确认(中断) → 下发执行 → 报告生成(LLM)
                                  ↘ 异常重排(最多 3 次) ↺
```

- **方案生成**：4 种候选方案（四米二优先 / 成本最低 / 大小包趟次保障 / 装载率均衡）
- **评分函数**：四米二使用率(0.30) + 装载率(0.25) + 趟次达成(0.25) + 成本(0.10) + 软约束(0.10)
- **大模型**：方案比选解释 + 执行总结由 DeepSeek 生成，失败自动回退规则化 mock

## 表设计

### RBAC 表（9 张）

| 表名 | 说明 |
|------|------|
| `rbac_user` | 用户表 |
| `rbac_role` | 角色表 |
| `rbac_permission` | 权限表 |
| `rbac_user_role` | 用户-角色中间表 |
| `rbac_role_permission` | 角色-权限中间表 |
| `sys_dict` | 数据源表（字典） |
| `sys_dict_item` | 数据项表 |
| `sys_param` | 系统参数表 |
| `sys_log` | 日志表 |

> 另含 `rbac_menu`（菜单表）、`rbac_dept`（部门表）、`rbac_role_menu`（角色-菜单中间表）用于菜单与组织管理。

### 业务表

仓库、线路、门店、门店-线路映射、车辆、车辆地形能力、司机、地形规则、趟次规则、装载规则、约束配置、调度任务、调度方案、调度报告、异常事件、执行记录等。

## 项目结构

```
.
├── backend/                  # 后端
│   ├── app/
│   │   ├── api/               # 路由（auth/users/roles/permissions/menus/depts
│   │   │                      #   /dicts/params/logs/scheduling/rules/reports/ws）
│   │   ├── models/            # 数据模型（rbac/basic/rules/scheduling/execution）
│   │   ├── schemas/           # Pydantic 模型
│   │   ├── services/          # 业务服务（auth/scheduling/execution/...）
│   │   ├── solver/            # CP-SAT 求解器 + 启发式 + 评分
│   │   ├── workflow/          # LangGraph 工作流（graph/nodes/state/checkpoint）
│   │   ├── llm/               # LLM 解释与报告生成（DeepSeek/OpenAI/mock）
│   │   ├── config.py          # 配置（环境变量 + .env）
│   │   ├── database.py        # SQLAlchemy 引擎
│   │   ├── main.py            # FastAPI 入口 + JWT 中间件 + 审计日志中间件
│   │   └── seed.py            # 种子数据（业务 + RBAC）
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
├── frontend/                  # 前端 Vue3 + Ant Design Vue
│   ├── src/
│   │   ├── api/               # axios + API 方法
│   │   ├── layouts/           # 主布局（动态菜单 + 权限控制）
│   │   ├── router/            # 路由 + 守卫
│   │   ├── store/             # Vuex auth 模块
│   │   └── views/             # 页面（业务 + system 系统管理）
│   ├── vue.config.js
│   └── Dockerfile
├── docker-compose.yml         # 一体化容器编排
└── start-dev.ps1              # Windows 一键启动
```

## 快速启动

### 方式一：本地一键（Windows）

```powershell
.\start-dev.ps1
```

### 方式二：手动启动

**后端：**

```powershell
cd backend
pip install -r requirements.txt
py -3.12 -m app.seed     # 初始化数据库 + 种子数据
py -3.12 -m app.run      # 启动后端 http://localhost:8000
```

**前端：**

```powershell
cd frontend
npm install
npm run serve            # 启动前端 http://localhost:8080
```

### 方式三：Docker 一体化

```powershell
docker-compose up -d
```

## 访问与默认账号

- 前端：http://localhost:8080
- 接口文档：http://localhost:8000/docs

| 账号 | 密码 | 角色 | 权限 |
|------|------|------|------|
| admin | admin123 | 超级管理员 | 全部模块 |
| dispatcher | dispatcher123 | 调度员 | 业务模块 |
| viewer | viewer123 | 只读用户 | 仅查看 |

## 配置说明

### 数据库

默认 MySQL，连接串（可由环境变量 `SCHED_DATABASE_URL` 覆盖）：

```
mysql+pymysql://sched:sched123@localhost:3306/scheduling?charset=utf8mb4
```

### 大模型（DeepSeek）

在 `backend/.env` 中配置（参考 `.env.example`）：

```env
SCHED_LLM_PROVIDER=deepseek
SCHED_LLM_MODEL=deepseek-chat
```

API Key 与 Base URL 自动从系统环境变量读取：

```
DEEPSEEK_API_KEY=sk-xxx
DEEPSEEK_API_BASE=https://api.deepseek.com
```

> 未配置 Key 时自动回退 mock（规则化解释），不影响流程运行。支持 OpenAI / 通义千问等 OpenAI 兼容接口。

## 核心特性

- **Agent 工作流**：LangGraph 编排，状态持久化（checkpointer），支持断点续跑与人工确认中断
- **多方案比选**：CP-SAT 生成 4 套方案，五维加权评分自动推荐最优
- **大模型解释**：DeepSeek 生成方案比选分析与执行总结
- **RBAC 权限**：用户/角色/权限/菜单/部门五级权限模型，接口级鉴权
- **实时进度**：WebSocket 推送工作流节点执行进度
- **审计日志**：自动记录所有写操作到日志表
- **字典与参数**：运行时配置，无需改代码

## 后续可扩展

- 接入真实 TMS / OMS 接口
- PostgreSQL 生产数据库
- Celery + RabbitMQ 异步任务队列
- LangSmith 可观测性
- 更多 LLM 提供商接入
