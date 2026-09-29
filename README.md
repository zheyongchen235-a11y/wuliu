# 车辆智能调度 Agent + RBAC 系统

> 基于 LangGraph Agent 工作流 + OR-Tools CP-SAT 求解器的车辆智能调度系统，集成微信小程序 C 端下单、完整 RBAC 权限管理与 DeepSeek 大模型方案解释的三端一体平台。

## 项目简介

本项目实现了一个物流配送车辆的智能调度 Agent：以 LangGraph 编排多节点工作流，结合 OR-Tools CP-SAT 约束规划求解器生成多套候选调度方案，经五维加权评分后由 DeepSeek 大模型生成自然语言比选解释，支持人工确认下发与异常重排。

平台共三端，统一调用同一套 FastAPI 后端接口：

| 端 | 目录 | 使用者 | 说明 |
|----|------|--------|------|
| 微信小程序 | `weixin/` | 门店客户（普通用户） | 微信一键登录 → 在线下单 → 模拟支付 → 查看智能调度结果与配送车辆/司机 |
| Vue3 管理后台 | `frontend/` | 管理员 / 调度员 | 调度任务、方案比选、客户订单调度、C 端用户与支付流水、RBAC 系统管理 |
| FastAPI 后端 | `backend/` | —— | 统一 API + LangGraph 工作流 + CP-SAT 求解器 + MySQL 8 |

同时内置完整的 RBAC（基于角色的访问控制）后台管理系统，含用户、角色、权限、字典、参数、日志六大管理模块。

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端框架 | FastAPI + Uvicorn |
| Agent 编排 | LangGraph（15 节点工作流 + checkpointer + human-in-the-loop） |
| 求解器 | OR-Tools CP-SAT（4 种方案 + 5 维加权评分） |
| ORM | SQLAlchemy 2.0 |
| 数据库 | MySQL 8.0（演示可切 SQLite） |
| 认证鉴权 | JWT + bcrypt + RBAC 中间件（双 scope：admin / wx） |
| 大模型 | DeepSeek（OpenAI 兼容接口，默认 mock 可切换） |
| 管理前端 | Vue 3 + Ant Design Vue 4 |
| 小程序端 | 微信原生（WXML / WXSS / JS），微信官方登录 `wx.login` + `jscode2session` |
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

### 二、客户端业务（微信小程序）

| 页面 | 说明 |
|------|------|
| 登录 | 微信官方 `wx.login` 获取 code → 后端 `jscode2session` 换取会话（mock/真实双模式），不使用用户名密码 |
| 首页 | 订单状态概览、常用门店快捷下单、最近订单 |
| 在线下单 | 选门店 / 货物类型 / 货量 / 配送时段 / 期望日期，实时预估运费与距离 |
| 收银台 | 模拟支付（微信支付 mock / 平台余额），生成支付流水 |
| 我的订单 | 状态筛选、下拉刷新、上拉分页、取消订单、确认收货 |
| 订单详情 | 状态轨迹时间轴、智能调度结果（车辆 / 车型 / 司机 / 司机电话 / 配送时段 / 预计送达）、支付流水 |
| 我的 | 用户资料、订单四宫格、支付流水、修改昵称与手机号、退出登录 |

管理端新增三个页面：**客户订单管理**（含创建调度任务与状态流转）、**小程序用户管理**（启停 / 备注）、**支付流水**。

### 三、系统管理（RBAC）

| 模块 | 说明 |
|------|------|
| 用户管理 | 用户 CRUD、角色分配、重置密码、启停 |
| 角色管理 | 角色 CRUD、权限分配、菜单分配、数据范围 |
| 权限管理 | 权限点（按钮/接口级）CRUD |
| 字典管理 | 数据源 + 数据项二级管理（车辆类型/地形/任务状态等） |
| 参数管理 | 系统参数 CRUD（求解时限/重排次数等） |
| 日志管理 | 操作日志自动记录 + 查询/删除/清空 |

### 四、Agent 工作流

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

### C 端（微信小程序）表（4 张）

| 表名 | 说明 |
|------|------|
| `wx_user` | 小程序用户表（openid / unionid / session_key / 昵称 / 头像 / 手机号 / 启停），与 `rbac_user` 完全隔离 |
| `customer_order` | 客户订单表（门店 / 货物 / 货量 / 金额 / 状态机 / 调度回填的车辆·司机·时段·预计送达） |
| `payment_record` | 支付流水表（模拟支付，含流水号 / 渠道 / 交易号 / 状态） |
| `order_status_log` | 订单状态流转日志（用于订单轨迹时间轴） |

订单状态机：

```
待支付 → 已支付待调度 → 已排车 → 配送中 → 已送达 → 已完成
   ↘ 已取消
```

> 建库 SQL 脚本位于 `sql/schema.sql`（38 张建表语句）与 `sql/data.sql`（演示数据），由
> `backend/scripts/export_schema_sql.py` 从当前库导出，可直接导入 MySQL 8 还原完整演示环境。

## 项目结构

```
.
├── backend/                  # 后端
│   ├── app/
│   │   ├── api/               # 路由（auth/users/roles/permissions/menus/depts
│   │   │                      #   /dicts/params/logs/scheduling/rules/reports/ws
│   │   │                      #   /wx 小程序端 /customer 客户端管理）
│   │   ├── models/            # 数据模型（rbac/basic/rules/scheduling/execution/customer）
│   │   ├── schemas/           # Pydantic 模型
│   │   ├── services/          # 业务服务（auth/wx/order/scheduling/execution/...）
│   │   ├── solver/            # CP-SAT 求解器 + 启发式 + 评分
│   │   ├── workflow/          # LangGraph 工作流（graph/nodes/state/checkpoint）
│   │   ├── llm/               # LLM 解释与报告生成（DeepSeek/OpenAI/mock）
│   │   ├── config.py          # 配置（环境变量 + .env）
│   │   ├── database.py        # SQLAlchemy 引擎
│   │   ├── main.py            # FastAPI 入口 + JWT 中间件 + 审计日志中间件
│   │   └── seed.py            # 种子数据（业务 + RBAC + C 端演示数据）
│   ├── scripts/
│   │   └── export_schema_sql.py  # 导出 sql/schema.sql 与 sql/data.sql
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
├── frontend/                  # 管理端 Vue3 + Ant Design Vue
│   ├── src/
│   │   ├── api/               # axios + API 方法
│   │   ├── layouts/           # 主布局（动态菜单 + 权限控制）
│   │   ├── router/            # 路由 + 守卫
│   │   ├── store/             # Vuex auth 模块
│   │   └── views/             # 页面（业务 + system 系统管理 + customer 客户端管理）
│   ├── vue.config.js
│   └── Dockerfile
├── weixin/                    # 微信小程序端（原生 WXML/WXSS/JS）
│   ├── utils/                 # config / request / api / auth / format
│   ├── pages/
│   │   ├── login/             # 微信一键登录
│   │   ├── index/             # 首页
│   │   ├── order/create       # 在线下单
│   │   ├── order/list         # 我的订单
│   │   ├── order/detail       # 订单详情（含调度结果与轨迹）
│   │   ├── pay/               # 模拟收银台
│   │   └── mine/              # 我的 + 支付流水
│   └── project.config.json
├── sql/                       # MySQL 8 建表 SQL 与测试数据
│   ├── schema.sql
│   └── data.sql
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

**前端（管理端）：**

```powershell
cd frontend
npm install
npm run serve            # 启动前端 http://localhost:8080
```

**微信小程序端：**

1. 用微信开发者工具「导入项目」，目录选择 `weixin/`，AppID 使用你自己的小程序 AppID（或测试号）。
2. 修改 `weixin/utils/config.js` 中的 `BASE_URL` 指向后端地址（默认 `http://127.0.0.1:8000`）。
3. 开发者工具中勾选「详情 → 本地设置 → 不校验合法域名…」（项目已默认关闭 `urlCheck`），否则无法访问本机 http 后端。
4. 真机调试 / 上线时需将 `BASE_URL` 改为已备案的 HTTPS 域名并在微信后台配置 request 合法域名。

### 方式三：数据库脚本导入（MySQL 8）

```powershell
mysql -uroot -p < sql/schema.sql   # 建库 + 38 张表
mysql -uroot -p < sql/data.sql     # 导入演示数据
```

> 或直接执行 `py -3.12 -m app.seed` 在 `backend/` 目录下自动建表并写入种子数据与 C 端演示数据。
> 需要重新导出当前库的 SQL 时执行：`cd backend; py -3.12 scripts/export_schema_sql.py`

### 方式四：Docker 一体化

```powershell
docker-compose up -d
```

## 访问与默认账号

- 管理后台：http://localhost:8080
- 接口文档：http://localhost:8000/docs
- 微信小程序：微信开发者工具导入 `weixin/` 目录

| 账号 | 密码 | 角色 | 权限 |
|------|------|------|------|
| admin | admin123 | 超级管理员 | 全部模块 |
| dispatcher | dispatcher123 | 调度员 | 业务模块 |
| viewer | viewer123 | 只读用户 | 仅查看 |

小程序端**不使用用户名密码**，直接点击「微信一键登录」；演示环境默认 mock 模式（由 code 派生 openid），
已内置 3 个演示小程序用户与 6 张不同状态的订单便于查看页面效果。

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

### 微信小程序登录

小程序端**不使用用户名密码**，走微信官方登录流程：小程序 `wx.login()` 拿到 `code` → 后端调用
`https://api.weixin.qq.com/sns/jscode2session` 换取 `openid` → 颁发 `scope=wx` 的 JWT。
实现位于 [services/wx.py](file:///c:/Users/123/Desktop/车辆智能调度%20Agent%20项目/backend/app/services/wx.py)。

支持 **mock / 真实双模式**，通过环境变量切换：

| 环境变量 | 说明 | 默认 |
|----------|------|------|
| `WX_APP_ID` | 小程序 AppID | 空 |
| `WX_APP_SECRET` | 小程序 AppSecret | 空 |
| `SCHED_WX_MOCK_LOGIN` | 未配置 AppID 时是否允许 mock 登录 | `true` |

- 配置了 `WX_APP_ID` / `WX_APP_SECRET`：调用微信官方接口，返回真实 `openid` / `session_key` / `unionid`。
- 未配置但 `SCHED_WX_MOCK_LOGIN=true`：由 `code` 派生稳定的 `mock_xxxx` openid，本地无需证书即可联调。
- 未配置且 `SCHED_WX_MOCK_LOGIN=false`：登录接口直接返回 `503`，避免生产环境误用 mock 身份。

> C 端用户写入独立的 `wx_user` 表，与后台 `rbac_user` 完全隔离；两套 JWT 通过 `scope`（admin / wx）区分，
> C 端 token 无法访问管理端接口。

## 核心特性

- **Agent 工作流**：LangGraph 编排，状态持久化（checkpointer），支持断点续跑与人工确认中断
- **多方案比选**：CP-SAT 生成 4 套方案，五维加权评分自动推荐最优
- **大模型解释**：DeepSeek 生成方案比选分析与执行总结
- **RBAC 权限**：用户/角色/权限/菜单/部门五级权限模型，接口级鉴权
- **三端业务闭环**：小程序下单 → 模拟支付 → 管理端一键创建调度任务 → CP-SAT 求解回填车辆/司机/时段 → 小程序查看结果并确认收货
- **双 scope 认证**：`admin`（后台）与 `wx`（小程序）两套 JWT，用户体系隔离，C 端 token 无法访问管理接口
- **实时进度**：WebSocket 推送工作流节点执行进度
- **审计日志**：自动记录所有写操作到日志表
- **字典与参数**：运行时配置，无需改代码

## 后续可扩展

- 接入真实 TMS / OMS 接口
- PostgreSQL 生产数据库
- Celery + RabbitMQ 异步任务队列
- LangSmith 可观测性
- 更多 LLM 提供商接入
