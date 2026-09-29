-- =====================================================================
--  车辆智能调度 Agent —— MySQL 8 数据库脚本
--  数据库：scheduling
--  字符集：utf8mb4 / utf8mb4_general_ci
--  由 backend/scripts/export_schema_sql.py 自动生成，请勿手工修改
-- =====================================================================

CREATE DATABASE IF NOT EXISTS `scheduling`
  DEFAULT CHARACTER SET utf8mb4
  DEFAULT COLLATE utf8mb4_general_ci;

USE `scheduling`;

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

DROP TABLE IF EXISTS `vehicle_terrain_capability`;
DROP TABLE IF EXISTS `scheduling_plan_score`;
DROP TABLE IF EXISTS `scheduling_plan_detail`;
DROP TABLE IF EXISTS `rbac_user_role`;
DROP TABLE IF EXISTS `payment_record`;
DROP TABLE IF EXISTS `order_status_log`;
DROP TABLE IF EXISTS `vehicle`;
DROP TABLE IF EXISTS `sys_dict_item`;
DROP TABLE IF EXISTS `store_route_mapping`;
DROP TABLE IF EXISTS `scheduling_task_snapshot`;
DROP TABLE IF EXISTS `scheduling_report`;
DROP TABLE IF EXISTS `scheduling_plan`;
DROP TABLE IF EXISTS `scheduling_confirmation`;
DROP TABLE IF EXISTS `replan_record`;
DROP TABLE IF EXISTS `rbac_user`;
DROP TABLE IF EXISTS `rbac_role_permission`;
DROP TABLE IF EXISTS `rbac_role_menu`;
DROP TABLE IF EXISTS `exception_event`;
DROP TABLE IF EXISTS `dispatch_record`;
DROP TABLE IF EXISTS `customer_order`;
DROP TABLE IF EXISTS `constraint_snapshot`;
DROP TABLE IF EXISTS `wx_user`;
DROP TABLE IF EXISTS `warehouse`;
DROP TABLE IF EXISTS `trip_rule`;
DROP TABLE IF EXISTS `terrain_rule`;
DROP TABLE IF EXISTS `sys_param`;
DROP TABLE IF EXISTS `sys_log`;
DROP TABLE IF EXISTS `sys_dict`;
DROP TABLE IF EXISTS `store`;
DROP TABLE IF EXISTS `scheduling_task`;
DROP TABLE IF EXISTS `route`;
DROP TABLE IF EXISTS `rbac_role`;
DROP TABLE IF EXISTS `rbac_permission`;
DROP TABLE IF EXISTS `rbac_menu`;
DROP TABLE IF EXISTS `rbac_dept`;
DROP TABLE IF EXISTS `load_rule`;
DROP TABLE IF EXISTS `driver`;
DROP TABLE IF EXISTS `constraint_config`;

-- ---------- constraint_config ----------
CREATE TABLE constraint_config (
	id VARCHAR(64) NOT NULL, 
	version VARCHAR(32) NOT NULL, 
	name VARCHAR(128) NOT NULL, 
	description TEXT, 
	hard_constraints JSON NOT NULL, 
	soft_constraints JSON NOT NULL, 
	weights JSON NOT NULL, 
	effective_from DATETIME, 
	effective_to DATETIME, 
	is_active BOOL NOT NULL, 
	created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, 
	updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, 
	PRIMARY KEY (id)
);

-- ---------- driver ----------
CREATE TABLE driver (
	id VARCHAR(64) NOT NULL, 
	name VARCHAR(64) NOT NULL, 
	phone VARCHAR(32), 
	organization_id VARCHAR(64), 
	status VARCHAR(16) NOT NULL, 
	created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, 
	updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, 
	PRIMARY KEY (id)
);

-- ---------- load_rule ----------
CREATE TABLE load_rule (
	id VARCHAR(64) NOT NULL, 
	vehicle_type VARCHAR(32) NOT NULL, 
	min_load INTEGER NOT NULL, 
	max_load INTEGER NOT NULL, 
	created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, 
	updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, 
	PRIMARY KEY (id), 
	UNIQUE (vehicle_type)
);

-- ---------- rbac_dept ----------
CREATE TABLE rbac_dept (
	id VARCHAR(64) NOT NULL, 
	parent_id VARCHAR(64), 
	name VARCHAR(128) NOT NULL, 
	code VARCHAR(64), 
	sort INTEGER NOT NULL, 
	enabled BOOL NOT NULL, 
	created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, 
	updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, 
	PRIMARY KEY (id), 
	FOREIGN KEY(parent_id) REFERENCES rbac_dept (id) ON DELETE SET NULL, 
	UNIQUE (code)
);

-- ---------- rbac_menu ----------
CREATE TABLE rbac_menu (
	id VARCHAR(64) NOT NULL, 
	parent_id VARCHAR(64), 
	name VARCHAR(64) NOT NULL, 
	path VARCHAR(256), 
	component VARCHAR(256), 
	icon VARCHAR(64), 
	type VARCHAR(16) NOT NULL COMMENT 'catalog | menu | button', 
	permission_code VARCHAR(128), 
	sort INTEGER NOT NULL, 
	visible BOOL NOT NULL, 
	keep_alive BOOL NOT NULL, 
	created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, 
	updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, 
	PRIMARY KEY (id), 
	FOREIGN KEY(parent_id) REFERENCES rbac_menu (id) ON DELETE SET NULL
);

-- ---------- rbac_permission ----------
CREATE TABLE rbac_permission (
	id VARCHAR(64) NOT NULL, 
	code VARCHAR(128) NOT NULL, 
	name VARCHAR(128) NOT NULL, 
	module VARCHAR(64) COMMENT '所属模块', 
	description TEXT, 
	created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, 
	updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, 
	PRIMARY KEY (id), 
	UNIQUE (code)
);

-- ---------- rbac_role ----------
CREATE TABLE rbac_role (
	id VARCHAR(64) NOT NULL, 
	code VARCHAR(64) NOT NULL, 
	name VARCHAR(128) NOT NULL, 
	description TEXT, 
	data_scope VARCHAR(16) NOT NULL COMMENT 'all | dept | self', 
	sort INTEGER NOT NULL, 
	enabled BOOL NOT NULL, 
	created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, 
	updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, 
	PRIMARY KEY (id), 
	UNIQUE (code)
);

-- ---------- route ----------
CREATE TABLE route (
	id VARCHAR(64) NOT NULL, 
	name VARCHAR(128) NOT NULL, 
	terrain_type VARCHAR(32) NOT NULL, 
	description TEXT, 
	enabled BOOL NOT NULL, 
	created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, 
	updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, 
	PRIMARY KEY (id)
);

-- ---------- scheduling_task ----------
CREATE TABLE scheduling_task (
	id VARCHAR(64) NOT NULL, 
	tenant_id VARCHAR(64) NOT NULL, 
	schedule_date DATE NOT NULL, 
	time_window VARCHAR(16) NOT NULL, 
	status VARCHAR(32) NOT NULL, 
	rule_version VARCHAR(32), 
	selected_plan_id VARCHAR(64), 
	replan_count INTEGER NOT NULL, 
	current_node VARCHAR(64), 
	error_message TEXT, 
	extra JSON, 
	created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, 
	updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, 
	PRIMARY KEY (id)
);

-- ---------- store ----------
CREATE TABLE store (
	id VARCHAR(64) NOT NULL, 
	name VARCHAR(128) NOT NULL, 
	address VARCHAR(256), 
	longitude FLOAT, 
	latitude FLOAT, 
	terrain_type VARCHAR(32) NOT NULL, 
	time_window VARCHAR(16) NOT NULL, 
	priority INTEGER NOT NULL, 
	enabled BOOL NOT NULL, 
	created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, 
	updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, 
	PRIMARY KEY (id)
);

-- ---------- sys_dict ----------
CREATE TABLE sys_dict (
	id VARCHAR(64) NOT NULL, 
	code VARCHAR(64) NOT NULL COMMENT '字典编码', 
	name VARCHAR(128) NOT NULL COMMENT '字典名称', 
	description VARCHAR(256), 
	enabled BOOL NOT NULL, 
	created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, 
	updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, 
	PRIMARY KEY (id), 
	UNIQUE (code)
);

-- ---------- sys_log ----------
CREATE TABLE sys_log (
	id VARCHAR(64) NOT NULL, 
	user_id VARCHAR(64), 
	username VARCHAR(64), 
	module VARCHAR(64) COMMENT '业务模块', 
	action VARCHAR(128) COMMENT '操作描述', 
	method VARCHAR(16) COMMENT 'HTTP 方法', 
	url VARCHAR(512), 
	params TEXT COMMENT '请求参数/体', 
	ip VARCHAR(64), 
	status INTEGER NOT NULL COMMENT 'HTTP 状态码', 
	error_msg TEXT, 
	latency_ms INTEGER NOT NULL COMMENT '耗时(ms)', 
	created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, 
	updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, 
	PRIMARY KEY (id)
);

-- ---------- sys_param ----------
CREATE TABLE sys_param (
	id VARCHAR(64) NOT NULL, 
	code VARCHAR(64) NOT NULL COMMENT '参数编码', 
	name VARCHAR(128) NOT NULL COMMENT '参数名称', 
	value VARCHAR(512) NOT NULL COMMENT '参数值', 
	type VARCHAR(16) NOT NULL COMMENT 'string | number | bool', 
	remark VARCHAR(256), 
	enabled BOOL NOT NULL, 
	created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, 
	updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, 
	PRIMARY KEY (id), 
	UNIQUE (code)
);

-- ---------- terrain_rule ----------
CREATE TABLE terrain_rule (
	id VARCHAR(64) NOT NULL, 
	terrain_type VARCHAR(32) NOT NULL, 
	description TEXT, 
	allowed_vehicle_types JSON NOT NULL, 
	created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, 
	updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, 
	PRIMARY KEY (id), 
	UNIQUE (terrain_type)
);

-- ---------- trip_rule ----------
CREATE TABLE trip_rule (
	id VARCHAR(64) NOT NULL, 
	vehicle_type VARCHAR(32) NOT NULL, 
	daily_trips INTEGER NOT NULL, 
	am_trips INTEGER NOT NULL, 
	pm_trips INTEGER NOT NULL, 
	created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, 
	updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, 
	PRIMARY KEY (id), 
	UNIQUE (vehicle_type)
);

-- ---------- warehouse ----------
CREATE TABLE warehouse (
	id VARCHAR(64) NOT NULL, 
	name VARCHAR(128) NOT NULL, 
	address VARCHAR(256), 
	organization_id VARCHAR(64), 
	created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, 
	updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, 
	PRIMARY KEY (id)
);

-- ---------- wx_user ----------
CREATE TABLE wx_user (
	id VARCHAR(64) NOT NULL, 
	openid VARCHAR(128) NOT NULL COMMENT '微信 openid', 
	unionid VARCHAR(128) COMMENT '微信 unionid', 
	session_key VARCHAR(128) COMMENT '会话密钥（真实模式写入）', 
	nickname VARCHAR(128), 
	avatar VARCHAR(512), 
	gender INTEGER NOT NULL COMMENT '0 未知 / 1 男 / 2 女', 
	phone VARCHAR(32), 
	enabled BOOL NOT NULL, 
	last_login_at VARCHAR(64), 
	remark VARCHAR(256), 
	created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, 
	updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, 
	PRIMARY KEY (id), 
	UNIQUE (openid)
);

-- ---------- constraint_snapshot ----------
CREATE TABLE constraint_snapshot (
	id VARCHAR(64) NOT NULL, 
	task_id VARCHAR(64) NOT NULL, 
	rule_version VARCHAR(32) NOT NULL, 
	hard_constraints JSON NOT NULL, 
	soft_constraints JSON NOT NULL, 
	weights JSON NOT NULL, 
	created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, 
	updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, 
	PRIMARY KEY (id), 
	FOREIGN KEY(task_id) REFERENCES scheduling_task (id) ON DELETE CASCADE
);

-- ---------- customer_order ----------
CREATE TABLE customer_order (
	id VARCHAR(64) NOT NULL, 
	order_no VARCHAR(32) NOT NULL COMMENT '订单号', 
	wx_user_id VARCHAR(64) NOT NULL, 
	store_id VARCHAR(64) NOT NULL, 
	store_name VARCHAR(128) COMMENT '门店名称快照', 
	contact_name VARCHAR(64), 
	contact_phone VARCHAR(32), 
	cargo_type VARCHAR(32) NOT NULL COMMENT '货物类型', 
	weight INTEGER NOT NULL COMMENT '货量(kg)', 
	time_window VARCHAR(16) NOT NULL COMMENT 'AM / PM / any', 
	expect_date DATE COMMENT '期望配送日期', 
	distance_km FLOAT NOT NULL, 
	amount NUMERIC(10, 2) NOT NULL COMMENT '应付金额(元)', 
	remark VARCHAR(512), 
	status VARCHAR(16) NOT NULL COMMENT 'pending_pay / paid / scheduled / delivering / delivered / completed / cancelled', 
	task_id VARCHAR(64) COMMENT '关联调度任务', 
	plan_id VARCHAR(32) COMMENT '采纳方案编号', 
	vehicle_id VARCHAR(64), 
	plate VARCHAR(32), 
	vehicle_type VARCHAR(32), 
	driver_id VARCHAR(64), 
	driver_name VARCHAR(64), 
	driver_phone VARCHAR(32), 
	deliver_window VARCHAR(16) COMMENT '实际配送时段', 
	estimated_arrival VARCHAR(64), 
	paid_at VARCHAR(64), 
	delivered_at VARCHAR(64), 
	completed_at VARCHAR(64), 
	cancelled_at VARCHAR(64), 
	created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, 
	updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, 
	PRIMARY KEY (id), 
	UNIQUE (order_no), 
	FOREIGN KEY(wx_user_id) REFERENCES wx_user (id) ON DELETE CASCADE, 
	FOREIGN KEY(store_id) REFERENCES store (id) ON DELETE CASCADE
);

-- ---------- dispatch_record ----------
CREATE TABLE dispatch_record (
	id VARCHAR(64) NOT NULL, 
	task_id VARCHAR(64) NOT NULL, 
	plan_id VARCHAR(32) NOT NULL, 
	dispatch_id VARCHAR(64), 
	target_system VARCHAR(32) NOT NULL, 
	status VARCHAR(32) NOT NULL, 
	payload JSON, 
	response JSON, 
	driver_task_ids JSON NOT NULL, 
	dispatched_at DATETIME, 
	error_message TEXT, 
	created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, 
	updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, 
	PRIMARY KEY (id), 
	FOREIGN KEY(task_id) REFERENCES scheduling_task (id) ON DELETE CASCADE
);

-- ---------- exception_event ----------
CREATE TABLE exception_event (
	id VARCHAR(64) NOT NULL, 
	task_id VARCHAR(64) NOT NULL, 
	event_type VARCHAR(64) NOT NULL, 
	severity VARCHAR(16) NOT NULL, 
	source VARCHAR(32) NOT NULL, 
	title VARCHAR(256) NOT NULL, 
	description TEXT, 
	affected_vehicle_ids JSON NOT NULL, 
	affected_store_ids JSON NOT NULL, 
	affected_trip_ids JSON NOT NULL, 
	extra JSON, 
	status VARCHAR(16) NOT NULL, 
	handled_at DATETIME, 
	created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, 
	updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, 
	PRIMARY KEY (id), 
	FOREIGN KEY(task_id) REFERENCES scheduling_task (id) ON DELETE CASCADE
);

-- ---------- rbac_role_menu ----------
CREATE TABLE rbac_role_menu (
	id VARCHAR(64) NOT NULL, 
	role_id VARCHAR(64) NOT NULL, 
	menu_id VARCHAR(64) NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uk_role_menu UNIQUE (role_id, menu_id), 
	FOREIGN KEY(role_id) REFERENCES rbac_role (id) ON DELETE CASCADE, 
	FOREIGN KEY(menu_id) REFERENCES rbac_menu (id) ON DELETE CASCADE
);

-- ---------- rbac_role_permission ----------
CREATE TABLE rbac_role_permission (
	id VARCHAR(64) NOT NULL, 
	role_id VARCHAR(64) NOT NULL, 
	permission_id VARCHAR(64) NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uk_role_perm UNIQUE (role_id, permission_id), 
	FOREIGN KEY(role_id) REFERENCES rbac_role (id) ON DELETE CASCADE, 
	FOREIGN KEY(permission_id) REFERENCES rbac_permission (id) ON DELETE CASCADE
);

-- ---------- rbac_user ----------
CREATE TABLE rbac_user (
	id VARCHAR(64) NOT NULL, 
	username VARCHAR(64) NOT NULL, 
	nickname VARCHAR(128), 
	email VARCHAR(128), 
	phone VARCHAR(32), 
	hashed_password VARCHAR(256) NOT NULL, 
	avatar VARCHAR(256), 
	dept_id VARCHAR(64), 
	is_super BOOL NOT NULL COMMENT '超级管理员', 
	enabled BOOL NOT NULL, 
	last_login_at VARCHAR(64), 
	created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, 
	updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, 
	PRIMARY KEY (id), 
	UNIQUE (username), 
	FOREIGN KEY(dept_id) REFERENCES rbac_dept (id) ON DELETE SET NULL
);

-- ---------- replan_record ----------
CREATE TABLE replan_record (
	id VARCHAR(64) NOT NULL, 
	task_id VARCHAR(64) NOT NULL, 
	replan_count INTEGER NOT NULL, 
	`trigger` VARCHAR(64) NOT NULL, 
	reason TEXT, 
	locked_trip_ids JSON NOT NULL, 
	before_plan_id VARCHAR(32), 
	after_plan_id VARCHAR(32), 
	strategy VARCHAR(32) NOT NULL, 
	created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, 
	updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, 
	PRIMARY KEY (id), 
	FOREIGN KEY(task_id) REFERENCES scheduling_task (id) ON DELETE CASCADE
);

-- ---------- scheduling_confirmation ----------
CREATE TABLE scheduling_confirmation (
	id VARCHAR(64) NOT NULL, 
	task_id VARCHAR(64) NOT NULL, 
	plan_id VARCHAR(32) NOT NULL, 
	approved BOOL NOT NULL, 
	adjustments JSON NOT NULL, 
	operator VARCHAR(64), 
	comment TEXT, 
	created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, 
	updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, 
	PRIMARY KEY (id), 
	FOREIGN KEY(task_id) REFERENCES scheduling_task (id) ON DELETE CASCADE
);

-- ---------- scheduling_plan ----------
CREATE TABLE scheduling_plan (
	id VARCHAR(64) NOT NULL, 
	task_id VARCHAR(64) NOT NULL, 
	plan_id VARCHAR(32) NOT NULL, 
	name VARCHAR(128) NOT NULL, 
	strategy VARCHAR(64) NOT NULL, 
	solver_type VARCHAR(32) NOT NULL, 
	status VARCHAR(32) NOT NULL, 
	total_load INTEGER NOT NULL, 
	total_trips INTEGER NOT NULL, 
	used_vehicles INTEGER NOT NULL, 
	avg_load_rate FLOAT NOT NULL, 
	big_small_achievement FLOAT NOT NULL, 
	four_two_usage FLOAT NOT NULL, 
	estimated_cost FLOAT NOT NULL, 
	summary JSON, 
	created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, 
	updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_plan_task_plan UNIQUE (task_id, plan_id), 
	FOREIGN KEY(task_id) REFERENCES scheduling_task (id) ON DELETE CASCADE
);

-- ---------- scheduling_report ----------
CREATE TABLE scheduling_report (
	id VARCHAR(64) NOT NULL, 
	task_id VARCHAR(64) NOT NULL, 
	report_type VARCHAR(32) NOT NULL, 
	content TEXT NOT NULL, 
	metrics JSON, 
	created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, 
	updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, 
	PRIMARY KEY (id), 
	FOREIGN KEY(task_id) REFERENCES scheduling_task (id) ON DELETE CASCADE
);

-- ---------- scheduling_task_snapshot ----------
CREATE TABLE scheduling_task_snapshot (
	id VARCHAR(64) NOT NULL, 
	task_id VARCHAR(64) NOT NULL, 
	stores JSON NOT NULL, 
	vehicles JSON NOT NULL, 
	routes JSON NOT NULL, 
	store_route_mappings JSON NOT NULL, 
	terrain_rules JSON NOT NULL, 
	demands JSON NOT NULL, 
	created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, 
	updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, 
	PRIMARY KEY (id), 
	FOREIGN KEY(task_id) REFERENCES scheduling_task (id) ON DELETE CASCADE
);

-- ---------- store_route_mapping ----------
CREATE TABLE store_route_mapping (
	id VARCHAR(64) NOT NULL, 
	store_id VARCHAR(64) NOT NULL, 
	route_id VARCHAR(64) NOT NULL, 
	is_primary BOOL NOT NULL, 
	created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, 
	updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, 
	PRIMARY KEY (id), 
	FOREIGN KEY(store_id) REFERENCES store (id) ON DELETE CASCADE, 
	FOREIGN KEY(route_id) REFERENCES route (id) ON DELETE CASCADE
);

-- ---------- sys_dict_item ----------
CREATE TABLE sys_dict_item (
	id VARCHAR(64) NOT NULL, 
	dict_id VARCHAR(64) NOT NULL, 
	label VARCHAR(128) NOT NULL COMMENT '显示文本', 
	value VARCHAR(128) NOT NULL COMMENT '实际值', 
	sort INTEGER NOT NULL, 
	enabled BOOL NOT NULL, 
	remark VARCHAR(256), 
	created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, 
	updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, 
	PRIMARY KEY (id), 
	FOREIGN KEY(dict_id) REFERENCES sys_dict (id) ON DELETE CASCADE
);

-- ---------- vehicle ----------
CREATE TABLE vehicle (
	id VARCHAR(64) NOT NULL, 
	plate VARCHAR(32) NOT NULL, 
	vehicle_type VARCHAR(32) NOT NULL, 
	min_load INTEGER NOT NULL, 
	max_load INTEGER NOT NULL, 
	max_trips_per_day INTEGER NOT NULL, 
	driver_id VARCHAR(64), 
	warehouse_id VARCHAR(64), 
	status VARCHAR(16) NOT NULL, 
	enabled BOOL NOT NULL, 
	created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, 
	updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, 
	PRIMARY KEY (id), 
	FOREIGN KEY(driver_id) REFERENCES driver (id), 
	FOREIGN KEY(warehouse_id) REFERENCES warehouse (id)
);

-- ---------- order_status_log ----------
CREATE TABLE order_status_log (
	id VARCHAR(64) NOT NULL, 
	order_id VARCHAR(64) NOT NULL, 
	from_status VARCHAR(16), 
	to_status VARCHAR(16) NOT NULL, 
	operator VARCHAR(16) NOT NULL COMMENT 'user / admin / system', 
	remark VARCHAR(256), 
	created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, 
	updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, 
	PRIMARY KEY (id), 
	FOREIGN KEY(order_id) REFERENCES customer_order (id) ON DELETE CASCADE
);

-- ---------- payment_record ----------
CREATE TABLE payment_record (
	id VARCHAR(64) NOT NULL, 
	payment_no VARCHAR(32) NOT NULL COMMENT '支付流水号', 
	order_id VARCHAR(64) NOT NULL, 
	wx_user_id VARCHAR(64), 
	amount NUMERIC(10, 2) NOT NULL, 
	channel VARCHAR(32) NOT NULL COMMENT '支付渠道(模拟)', 
	status VARCHAR(16) NOT NULL COMMENT 'pending / success / failed / refunded', 
	transaction_id VARCHAR(64) COMMENT '模拟第三方流水号', 
	paid_at VARCHAR(64), 
	remark VARCHAR(256), 
	created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, 
	updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, 
	PRIMARY KEY (id), 
	UNIQUE (payment_no), 
	FOREIGN KEY(order_id) REFERENCES customer_order (id) ON DELETE CASCADE
);

-- ---------- rbac_user_role ----------
CREATE TABLE rbac_user_role (
	id VARCHAR(64) NOT NULL, 
	user_id VARCHAR(64) NOT NULL, 
	role_id VARCHAR(64) NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uk_user_role UNIQUE (user_id, role_id), 
	FOREIGN KEY(user_id) REFERENCES rbac_user (id) ON DELETE CASCADE, 
	FOREIGN KEY(role_id) REFERENCES rbac_role (id) ON DELETE CASCADE
);

-- ---------- scheduling_plan_detail ----------
CREATE TABLE scheduling_plan_detail (
	id VARCHAR(64) NOT NULL, 
	plan_id VARCHAR(64) NOT NULL, 
	vehicle_id VARCHAR(64) NOT NULL, 
	vehicle_type VARCHAR(32) NOT NULL, 
	trip_no INTEGER NOT NULL, 
	time_window VARCHAR(16) NOT NULL, 
	store_ids JSON NOT NULL, 
	load_amount INTEGER NOT NULL, 
	sequence INTEGER NOT NULL, 
	status VARCHAR(32) NOT NULL, 
	created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, 
	updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, 
	PRIMARY KEY (id), 
	FOREIGN KEY(plan_id) REFERENCES scheduling_plan (id) ON DELETE CASCADE
);

-- ---------- scheduling_plan_score ----------
CREATE TABLE scheduling_plan_score (
	id VARCHAR(64) NOT NULL, 
	plan_id VARCHAR(64) NOT NULL, 
	total_score FLOAT NOT NULL, 
	score_4m2_usage FLOAT NOT NULL, 
	score_load_rate FLOAT NOT NULL, 
	score_trip_achievement FLOAT NOT NULL, 
	score_cost FLOAT NOT NULL, 
	score_soft_penalty FLOAT NOT NULL, 
	hard_constraint_violations JSON NOT NULL, 
	soft_constraint_violations JSON NOT NULL, 
	explanation TEXT, 
	created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, 
	updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, 
	PRIMARY KEY (id), 
	UNIQUE (plan_id), 
	FOREIGN KEY(plan_id) REFERENCES scheduling_plan (id) ON DELETE CASCADE
);

-- ---------- vehicle_terrain_capability ----------
CREATE TABLE vehicle_terrain_capability (
	id VARCHAR(64) NOT NULL, 
	vehicle_id VARCHAR(64) NOT NULL, 
	terrain_type VARCHAR(32) NOT NULL, 
	can_access BOOL NOT NULL, 
	created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, 
	updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, 
	PRIMARY KEY (id), 
	FOREIGN KEY(vehicle_id) REFERENCES vehicle (id) ON DELETE CASCADE
);


SET FOREIGN_KEY_CHECKS = 1;
