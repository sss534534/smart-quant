-- 量化交易系统数据库初始化脚本
-- MySQL 8.0+

-- 创建数据库
CREATE DATABASE IF NOT EXISTS quant_system DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE quant_system;

-- 策略相关表
CREATE TABLE `strategies` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT '主键 ID',
  `name` VARCHAR(100) NOT NULL COMMENT '策略名称',
  `code` VARCHAR(50) NOT NULL COMMENT '策略代码',
  `type` VARCHAR(50) NOT NULL COMMENT '策略类型',
  `description` TEXT COMMENT '策略描述',
  `params` JSON NOT NULL DEFAULT '{}' COMMENT '策略参数',
  `status` VARCHAR(20) DEFAULT 'active' COMMENT '状态',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_code` (`code`),
  KEY `idx_status` (`status`),
  KEY `idx_type` (`type`),
  KEY `idx_created_at` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='策略表';

CREATE TABLE `strategy_signals` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT '主键 ID',
  `strategy_id` INT NOT NULL COMMENT '策略 ID',
  `code` VARCHAR(50) NOT NULL COMMENT '股票代码',
  `action` VARCHAR(20) NOT NULL COMMENT '操作',
  `price` FLOAT NOT NULL COMMENT '触发价格',
  `quantity` INT DEFAULT 100 COMMENT '建议数量',
  `reason` TEXT COMMENT '信号理由',
  `strength` FLOAT DEFAULT 1.0 COMMENT '信号强度',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '信号产生时间',
  PRIMARY KEY (`id`),
  KEY `idx_strategy_id` (`strategy_id`),
  KEY `idx_code` (`code`),
  KEY `idx_action` (`action`),
  KEY `idx_created_at` (`created_at`),
  KEY `idx_strategy_code` (`strategy_id`, `code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='策略信号表';

-- 订单相关表
CREATE TABLE `orders` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT '主键 ID',
  `order_no` VARCHAR(64) NOT NULL COMMENT '订单号',
  `strategy_id` INT COMMENT '策略 ID',
  `code` VARCHAR(50) NOT NULL COMMENT '股票代码',
  `direction` ENUM('buy','sell') NOT NULL COMMENT '交易方向',
  `order_type` ENUM('limit','market') DEFAULT 'limit' COMMENT '订单类型',
  `price` FLOAT COMMENT '委托价格',
  `quantity` INT NOT NULL COMMENT '委托数量',
  `filled_quantity` INT DEFAULT 0 COMMENT '成交数量',
  `avg_price` FLOAT COMMENT '成交均价',
  `status` ENUM('pending','submitted','partially_filled','filled','cancelled','rejected') DEFAULT 'pending' COMMENT '订单状态',
  `submit_time` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '提交时间',
  `update_time` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `filled_time` DATETIME COMMENT '成交时间',
  `reject_reason` TEXT COMMENT '拒绝原因',
  `extra` JSON COMMENT '扩展信息',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_order_no` (`order_no`),
  KEY `idx_strategy_id` (`strategy_id`),
  KEY `idx_code` (`code`),
  KEY `idx_direction` (`direction`),
  KEY `idx_status` (`status`),
  KEY `idx_submit_time` (`submit_time`),
  KEY `idx_code_status` (`code`, `status`),
  KEY `idx_strategy_status` (`strategy_id`, `status`),
  KEY `idx_direction_status` (`direction`, `status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='订单表';

CREATE TABLE `trades` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT '主键 ID',
  `order_no` VARCHAR(64) NOT NULL COMMENT '订单号',
  `code` VARCHAR(50) NOT NULL COMMENT '股票代码',
  `direction` ENUM('buy','sell') NOT NULL COMMENT '交易方向',
  `price` FLOAT NOT NULL COMMENT '成交价格',
  `quantity` INT NOT NULL COMMENT '成交数量',
  `commission` FLOAT DEFAULT 0 COMMENT '佣金',
  `slip` FLOAT DEFAULT 0 COMMENT '滑点',
  `submit_time` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '提交时间',
  `trade_time` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '成交时间',
  `extra` JSON COMMENT '扩展信息',
  PRIMARY KEY (`id`),
  KEY `idx_order_no` (`order_no`),
  KEY `idx_code` (`code`),
  KEY `idx_direction` (`direction`),
  KEY `idx_trade_time` (`trade_time`),
  KEY `idx_code_trade_time` (`code`, `trade_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='成交表';

-- 持仓相关表
CREATE TABLE `positions` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT '主键 ID',
  `code` VARCHAR(50) NOT NULL COMMENT '股票代码',
  `name` VARCHAR(100) COMMENT '股票名称',
  `direction` ENUM('long','short') DEFAULT 'long' COMMENT '持仓方向',
  `quantity` INT DEFAULT 0 COMMENT '持仓数量',
  `avg_cost` FLOAT COMMENT '持仓成本',
  `avg_price` FLOAT COMMENT '持仓均价',
  `current_price` FLOAT COMMENT '当前价格',
  `frozen_quantity` INT DEFAULT 0 COMMENT '冻结数量',
  `status` ENUM('active','closed','liquidated') DEFAULT 'active' COMMENT '持仓状态',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '开仓时间',
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `closed_at` DATETIME COMMENT '平仓时间',
  `extra` JSON COMMENT '扩展信息',
  PRIMARY KEY (`id`),
  KEY `idx_code` (`code`),
  KEY `idx_status` (`status`),
  KEY `idx_direction` (`direction`),
  KEY `idx_code_status` (`code`, `status`),
  KEY `idx_created_at` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='持仓表';

CREATE TABLE `accounts` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT '主键 ID',
  `account_no` VARCHAR(64) NOT NULL COMMENT '账户号',
  `account_type` VARCHAR(50) DEFAULT 'cash' COMMENT '账户类型',
  `balance` FLOAT DEFAULT 0 COMMENT '可用资金',
  `frozen_balance` FLOAT DEFAULT 0 COMMENT '冻结资金',
  `total_deposited` FLOAT DEFAULT 0 COMMENT '累计入金',
  `total_withdrawn` FLOAT DEFAULT 0 COMMENT '累计出金',
  `total_profit` FLOAT DEFAULT 0 COMMENT '累计盈亏',
  `status` VARCHAR(20) DEFAULT 'active' COMMENT '账户状态',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_account_no` (`account_no`),
  KEY `idx_status` (`status`),
  KEY `idx_account_type` (`account_type`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='账户表';

CREATE TABLE `account_logs` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT '主键 ID',
  `account_no` VARCHAR(64) NOT NULL COMMENT '账户号',
  `type` VARCHAR(50) NOT NULL COMMENT '类型',
  `amount` FLOAT COMMENT '金额',
  `balance_after` FLOAT COMMENT '变更后余额',
  `description` TEXT COMMENT '描述',
  `related_order_no` VARCHAR(64) COMMENT '关联订单号',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '发生时间',
  PRIMARY KEY (`id`),
  KEY `idx_account_no` (`account_no`),
  KEY `idx_type` (`type`),
  KEY `idx_created_at` (`created_at`),
  KEY `idx_account_type` (`account_no`, `type`),
  KEY `idx_account_created` (`account_no`, `created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='账户流水表';

-- 回测相关表
CREATE TABLE `backtests` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT '主键 ID',
  `name` VARCHAR(200) NOT NULL COMMENT '回测名称',
  `strategy_id` INT NOT NULL COMMENT '策略 ID',
  `code_list` JSON DEFAULT '[]' COMMENT '测试股票列表',
  `start_date` DATETIME NOT NULL COMMENT '开始日期',
  `end_date` DATETIME NOT NULL COMMENT '结束日期',
  `initial_capital` FLOAT DEFAULT 100000 COMMENT '初始资金',
  `commission_rate` FLOAT DEFAULT 0.0003 COMMENT '佣金率',
  `slip_rate` FLOAT DEFAULT 0.001 COMMENT '滑点率',
  `status` VARCHAR(50) DEFAULT 'running' COMMENT '状态',
  `progress` INT DEFAULT 0 COMMENT '进度',
  `params` JSON DEFAULT '{}' COMMENT '回测参数',
  `created_by` VARCHAR(100) COMMENT '创建者',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `completed_at` DATETIME COMMENT '完成时间',
  `error_msg` TEXT COMMENT '错误信息',
  PRIMARY KEY (`id`),
  KEY `idx_strategy_id` (`strategy_id`),
  KEY `idx_status` (`status`),
  KEY `idx_created_at` (`created_at`),
  KEY `idx_strategy_status` (`strategy_id`, `status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='回测表';

CREATE TABLE `backtest_results` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT '主键 ID',
  `backtest_id` INT NOT NULL COMMENT '回测 ID',
  `total_return` FLOAT COMMENT '总收益率',
  `annual_return` FLOAT COMMENT '年化收益率',
  `sharpe_ratio` FLOAT COMMENT '夏普比率',
  `sortino_ratio` FLOAT COMMENT '索提诺比率',
  `calmar_ratio` FLOAT COMMENT '卡尔玛比率',
  `max_drawdown` FLOAT COMMENT '最大回撤',
  `max_drawdown_duration` INT COMMENT '最大回撤持续时间',
  `win_rate` FLOAT COMMENT '胜率',
  `profit_factor` FLOAT COMMENT '盈利因子',
  `avg_win` FLOAT COMMENT '平均盈利',
  `avg_loss` FLOAT COMMENT '平均亏损',
  `largest_win` FLOAT COMMENT '最大单笔盈利',
  `largest_loss` FLOAT COMMENT '最大单笔亏损',
  `total_trades` INT COMMENT '总交易次数',
  `winning_trades` INT DEFAULT 0 COMMENT '盈利次数',
  `losing_trades` INT DEFAULT 0 COMMENT '亏损次数',
  `start_balance` FLOAT COMMENT '起始资金',
  `end_balance` FLOAT COMMENT '结束资金',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_backtest_id` (`backtest_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='回测结果表';

CREATE TABLE `backtest_trades` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT '主键 ID',
  `backtest_id` INT NOT NULL COMMENT '回测 ID',
  `code` VARCHAR(50) NOT NULL COMMENT '股票代码',
  `date` DATETIME NOT NULL COMMENT '交易日期',
  `direction` VARCHAR(10) NOT NULL COMMENT '方向',
  `price` FLOAT NOT NULL COMMENT '价格',
  `quantity` INT NOT NULL COMMENT '数量',
  `commission` FLOAT DEFAULT 0 COMMENT '佣金',
  `slip` FLOAT DEFAULT 0 COMMENT '滑点',
  `pnl` FLOAT COMMENT '盈亏',
  `equity` FLOAT COMMENT '累计权益',
  `drawdown` FLOAT COMMENT '当前回撤',
  PRIMARY KEY (`id`),
  KEY `idx_backtest_id` (`backtest_id`),
  KEY `idx_code` (`code`),
  KEY `idx_date` (`date`),
  KEY `idx_direction` (`direction`),
  KEY `idx_backtest_code` (`backtest_id`, `code`),
  KEY `idx_backtest_date` (`backtest_id`, `date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='回测交易记录表';

CREATE TABLE `equity_curves` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT '主键 ID',
  `backtest_id` INT NOT NULL COMMENT '回测 ID',
  `date` DATETIME NOT NULL COMMENT '日期',
  `equity` FLOAT COMMENT '累计权益',
  `cumulative_return` FLOAT COMMENT '累计收益率',
  `drawdown` FLOAT COMMENT '当前回撤',
  PRIMARY KEY (`id`),
  KEY `idx_backtest_id` (`backtest_id`),
  KEY `idx_date` (`date`),
  KEY `idx_backtest_date` (`backtest_id`, `date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='权益曲线表';

-- 风控相关表
CREATE TABLE `risk_limits` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT '主键 ID',
  `limit_name` VARCHAR(100) NOT NULL COMMENT '限额名称',
  `risk_type` VARCHAR(50) NOT NULL COMMENT '风险类型',
  `limit_value` FLOAT NOT NULL COMMENT '限额值',
  `warning_value` FLOAT COMMENT '警告值',
  `description` TEXT COMMENT '描述',
  `enabled` BOOLEAN DEFAULT TRUE COMMENT '是否启用',
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  KEY `idx_risk_type` (`risk_type`),
  KEY `idx_enabled` (`enabled`),
  KEY `idx_type_enabled` (`risk_type`, `enabled`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='风控限额表';

CREATE TABLE `risk_checks` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT '主键 ID',
  `order_no` VARCHAR(64) COMMENT '订单号',
  `code` VARCHAR(50) NOT NULL COMMENT '股票代码',
  `direction` VARCHAR(20) NOT NULL COMMENT '方向',
  `price` FLOAT NOT NULL COMMENT '价格',
  `quantity` INT NOT NULL COMMENT '数量',
  `risk_type` VARCHAR(50) NOT NULL COMMENT '检查类型',
  `limit_value` FLOAT COMMENT '限额值',
  `actual_value` FLOAT COMMENT '实际值',
  `passed` BOOLEAN NOT NULL COMMENT '是否通过',
  `level` VARCHAR(20) DEFAULT 'normal' COMMENT '风险等级',
  `message` TEXT COMMENT '检查信息',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '检查时间',
  PRIMARY KEY (`id`),
  KEY `idx_order_no` (`order_no`),
  KEY `idx_code` (`code`),
  KEY `idx_risk_type` (`risk_type`),
  KEY `idx_passed` (`passed`),
  KEY `idx_level` (`level`),
  KEY `idx_created_at` (`created_at`),
  KEY `idx_code_risk_type` (`code`, `risk_type`),
  KEY `idx_code_level` (`code`, `level`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='风控检查记录表';

CREATE TABLE `risk_reports` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT '主键 ID',
  `report_date` DATETIME NOT NULL COMMENT '报告日期',
  `total_trades` INT DEFAULT 0 COMMENT '总交易笔数',
  `risk_alerts` INT DEFAULT 0 COMMENT '风险预警次数',
  `risk_blocked` INT DEFAULT 0 COMMENT '风控拦截次数',
  `total_position_value` FLOAT DEFAULT 0 COMMENT '总持仓市值',
  `total_pnl` FLOAT DEFAULT 0 COMMENT '总盈亏',
  `max_position_pct` FLOAT DEFAULT 0 COMMENT '最大持仓占比',
  `max_single_trade_pct` FLOAT DEFAULT 0 COMMENT '最大单笔占比',
  `daily_loss_limit` FLOAT DEFAULT 0 COMMENT '当日亏损限额',
  `current_daily_loss` FLOAT DEFAULT 0 COMMENT '当日累计亏损',
  `risk_value` FLOAT DEFAULT 0 COMMENT '在险价值',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '报告时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_report_date` (`report_date`),
  KEY `idx_created_at` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='风控日报表';

-- 市场数据相关表
CREATE TABLE `market_data` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT '主键 ID',
  `code` VARCHAR(50) NOT NULL COMMENT '股票代码',
  `data_type` VARCHAR(50) NOT NULL COMMENT '数据类型',
  `timestamp` DATETIME NOT NULL COMMENT '时间戳',
  `open` FLOAT COMMENT '开盘价',
  `high` FLOAT COMMENT '最高价',
  `low` FLOAT COMMENT '最低价',
  `close` FLOAT NOT NULL COMMENT '收盘价',
  `volume` BIGINT COMMENT '成交量',
  `amount` FLOAT COMMENT '成交额',
  `open_interest` FLOAT COMMENT '持仓量',
  `vwap` FLOAT COMMENT '加权均价',
  `extra` JSON COMMENT '扩展数据',
  PRIMARY KEY (`id`),
  KEY `idx_code` (`code`),
  KEY `idx_data_type` (`data_type`),
  KEY `idx_timestamp` (`timestamp`),
  KEY `idx_code_timestamp` (`code`, `timestamp`),
  KEY `idx_code_data_type` (`code`, `data_type`),
  KEY `idx_code_data_timestamp` (`code`, `data_type`, `timestamp`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='市场数据表';

CREATE TABLE `stock_info` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT '主键 ID',
  `code` VARCHAR(50) NOT NULL COMMENT '股票代码',
  `name` VARCHAR(100) NOT NULL COMMENT '股票名称',
  `exchange` VARCHAR(50) NOT NULL COMMENT '交易所',
  `sector` VARCHAR(100) COMMENT '所属行业',
  `market_cap` FLOAT COMMENT '总市值',
  `total_shares` FLOAT COMMENT '总股本',
  `float_shares` FLOAT COMMENT '流通股本',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_code` (`code`),
  KEY `idx_exchange` (`exchange`),
  KEY `idx_sector` (`sector`),
  KEY `idx_name` (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='股票信息表';

CREATE TABLE `calendar` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT '主键 ID',
  `trade_date` DATETIME NOT NULL COMMENT '交易日期',
  `is_holiday` BOOLEAN DEFAULT FALSE COMMENT '是否节假日',
  `market_status` VARCHAR(50) DEFAULT 'open' COMMENT '市场状态',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_trade_date` (`trade_date`),
  KEY `idx_is_holiday` (`is_holiday`),
  KEY `idx_market_status` (`market_status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='交易日历表';

-- 用户表（用于认证和授权）
CREATE TABLE `users` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT '主键 ID',
  `username` VARCHAR(50) NOT NULL COMMENT '用户名',
  `password_hash` VARCHAR(255) NOT NULL COMMENT '密码哈希',
  `email` VARCHAR(100) COMMENT '邮箱',
  `phone` VARCHAR(20) COMMENT '手机号',
  `role` VARCHAR(20) DEFAULT 'user' COMMENT '角色：admin/user/viewer',
  `status` VARCHAR(20) DEFAULT 'active' COMMENT '状态',
  `last_login_at` DATETIME COMMENT '最后登录时间',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_username` (`username`),
  UNIQUE KEY `uk_email` (`email`),
  KEY `idx_role` (`role`),
  KEY `idx_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户表';

-- 用户Token表
CREATE TABLE `user_tokens` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT '主键 ID',
  `user_id` INT NOT NULL COMMENT '用户 ID',
  `token` VARCHAR(255) NOT NULL COMMENT 'Token',
  `token_type` VARCHAR(20) DEFAULT 'access' COMMENT 'Token类型',
  `expires_at` DATETIME NOT NULL COMMENT '过期时间',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_token` (`token`),
  KEY `idx_user_id` (`user_id`),
  KEY `idx_expires_at` (`expires_at`),
  KEY `idx_user_token` (`user_id`, `token_type`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户Token表';

-- 操作日志表
CREATE TABLE `operation_logs` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT '主键 ID',
  `user_id` INT COMMENT '用户 ID',
  `action` VARCHAR(50) NOT NULL COMMENT '操作类型',
  `resource` VARCHAR(100) COMMENT '资源',
  `resource_id` VARCHAR(50) COMMENT '资源 ID',
  `details` JSON COMMENT '详情',
  `ip_address` VARCHAR(50) COMMENT 'IP地址',
  `user_agent` VARCHAR(500) COMMENT 'User Agent',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  KEY `idx_user_id` (`user_id`),
  KEY `idx_action` (`action`),
  KEY `idx_resource` (`resource`),
  KEY `idx_created_at` (`created_at`),
  KEY `idx_user_action` (`user_id`, `action`),
  KEY `idx_resource_action` (`resource`, `action`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='操作日志表';

-- 插入默认数据
-- 默认管理员用户（密码: admin123）
INSERT INTO `users` (`username`, `password_hash`, `email`, `role`) VALUES
('admin', '$2b$12$LJ3m4ys3Lk0TSwHjQ/3PKOQxQm7VxQxQxQxQxQxQxQxQxQxQxQxQ', 'admin@quant.com', 'admin');

-- 默认账户
INSERT INTO `accounts` (`account_no`, `balance`, `total_deposited`) VALUES
('ACC001', 100000.00, 100000.00);

-- 默认风控限额
INSERT INTO `risk_limits` (`limit_name`, `risk_type`, `limit_value`, `warning_value`, `description`) VALUES
('最大持仓占比', 'position_percentage', 0.2, 0.15, '单只股票最大持仓比例'),
('最大单笔交易', 'single_trade_limit', 100000.00, 50000.00, '单笔交易最大金额'),
('最大单日亏损', 'daily_limit', 50000.00, 20000.00, '单日最大亏损限额'),
('最大回撤', 'drawdown', 0.2, 0.1, '最大回撤限额'),
('最大持仓亏损', 'max_position_loss', 30000.00, 10000.00, '持仓最大亏损限额');

-- 默认策略
INSERT INTO `strategies` (`name`, `code`, `type`, `description`, `params`) VALUES
('均线策略', 'ma_cross', 'technical', '双均线交叉策略', '{"fast_period": 5, "slow_period": 20}'),
('MACD 策略', 'macd_strategy', 'technical', 'MACD 金叉死叉策略', '{"fast_period": 12, "slow_period": 26, "signal_period": 9}'),
('网格策略', 'grid_strategy', 'grid', '固定网格交易策略', '{"grid_size": 0.02, "base_quantity": 100}'),
('RSI均值回归策略', 'rsi_mean_reversion', 'technical', 'RSI超买超卖策略', '{"rsi_period": 14, "oversold": 30, "overbought": 70}'),
('布林带策略', 'bollinger_band', 'technical', '布林带突破策略', '{"period": 20, "std": 2}');

-- 默认日历（最近交易日）
INSERT INTO `calendar` (`trade_date`, `market_status`)
SELECT DATE_SUB(CURDATE(), INTERVAL n DAY), 'open'
FROM (SELECT 0 AS n UNION ALL SELECT 1 UNION ALL SELECT 2 UNION ALL SELECT 3 UNION ALL SELECT 4
     UNION ALL SELECT 5 UNION ALL SELECT 6 UNION ALL SELECT 7 UNION ALL SELECT 8 UNION ALL SELECT 9
     UNION ALL SELECT 10 UNION ALL SELECT 11 UNION ALL SELECT 12 UNION ALL SELECT 13 UNION ALL SELECT 14
     UNION ALL SELECT 15 UNION ALL SELECT 16 UNION ALL SELECT 17 UNION ALL SELECT 18 UNION ALL SELECT 19
     UNION ALL SELECT 20 UNION ALL SELECT 21 UNION ALL SELECT 22 UNION ALL SELECT 23 UNION ALL SELECT 24
     UNION ALL SELECT 25 UNION ALL SELECT 26 UNION ALL SELECT 27 UNION ALL SELECT 28 UNION ALL SELECT 29
     UNION ALL SELECT 30 UNION ALL SELECT 31 UNION ALL SELECT 32 UNION ALL SELECT 33 UNION ALL SELECT 34
     UNION ALL SELECT 35 UNION ALL SELECT 36 UNION ALL SELECT 37 UNION ALL SELECT 38 UNION ALL SELECT 39
     UNION ALL SELECT 40 UNION ALL SELECT 41 UNION ALL SELECT 42 UNION ALL SELECT 43 UNION ALL SELECT 44
     UNION ALL SELECT 45 UNION ALL SELECT 46 UNION ALL SELECT 47 UNION ALL SELECT 48 UNION ALL SELECT 49
     UNION ALL SELECT 50 UNION ALL SELECT 51 UNION ALL SELECT 52 UNION ALL SELECT 53 UNION ALL SELECT 54
     UNION ALL SELECT 55 UNION ALL SELECT 56 UNION ALL SELECT 57 UNION ALL SELECT 58 UNION ALL SELECT 59
     UNION ALL SELECT 60 UNION ALL SELECT 61 UNION ALL SELECT 62 UNION ALL SELECT 63 UNION ALL SELECT 64
     UNION ALL SELECT 65 UNION ALL SELECT 66 UNION ALL SELECT 67 UNION ALL SELECT 68 UNION ALL SELECT 69
     UNION ALL SELECT 70 UNION ALL SELECT 71 UNION ALL SELECT 72 UNION ALL SELECT 73 UNION ALL SELECT 74
     UNION ALL SELECT 75 UNION ALL SELECT 76 UNION ALL SELECT 77 UNION ALL SELECT 78 UNION ALL SELECT 79
     UNION ALL SELECT 80 UNION ALL SELECT 81 UNION ALL SELECT 82 UNION ALL SELECT 83 UNION ALL SELECT 84
     UNION ALL SELECT 85 UNION ALL SELECT 86 UNION ALL SELECT 87 UNION ALL SELECT 88 UNION ALL SELECT 89
     UNION ALL SELECT 90 UNION ALL SELECT 91 UNION ALL SELECT 92 UNION ALL SELECT 93 UNION ALL SELECT 94
     UNION ALL SELECT 95 UNION ALL SELECT 96 UNION ALL SELECT 97 UNION ALL SELECT 98 UNION ALL SELECT 99
     UNION ALL SELECT 100 UNION ALL SELECT 101 UNION ALL SELECT 102 UNION ALL SELECT 103 UNION ALL SELECT 104
     UNION ALL SELECT 105 UNION ALL SELECT 106 UNION ALL SELECT 107 UNION ALL SELECT 108 UNION ALL SELECT 109
     UNION ALL SELECT 110 UNION ALL SELECT 111 UNION ALL SELECT 112 UNION ALL SELECT 113 UNION ALL SELECT 114
     UNION ALL SELECT 115 UNION ALL SELECT 116 UNION ALL SELECT 117 UNION ALL SELECT 118 UNION ALL SELECT 119
     UNION ALL SELECT 120 UNION ALL SELECT 121 UNION ALL SELECT 122 UNION ALL SELECT 123 UNION ALL SELECT 124
     UNION ALL SELECT 125 UNION ALL SELECT 126 UNION ALL SELECT 127 UNION ALL SELECT 128 UNION ALL SELECT 129
     UNION ALL SELECT 130 UNION ALL SELECT 131 UNION ALL SELECT 132 UNION ALL SELECT 133 UNION ALL SELECT 134
     UNION ALL SELECT 135 UNION ALL SELECT 136 UNION ALL SELECT 137 UNION ALL SELECT 138 UNION ALL SELECT 139
     UNION ALL SELECT 140 UNION ALL SELECT 141 UNION ALL SELECT 142 UNION ALL SELECT 143 UNION ALL SELECT 144
     UNION ALL SELECT 145 UNION ALL SELECT 146 UNION ALL SELECT 147 UNION ALL SELECT 148 UNION ALL SELECT 149
     UNION ALL SELECT 150) AS numbers
WHERE NOT EXISTS (
    SELECT 1 FROM calendar WHERE DATE_FORMAT(trade_date, '%Y-%m-%d') = DATE_FORMAT(DATE_SUB(CURDATE(), INTERVAL n DAY), '%Y-%m-%d')
);