# 量化投资系统

一个基于微服务架构的生产级量化投资系统，提供完整的策略开发、回测、交易和风控功能。

## 系统架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        Web Frontend                            │
│                    (Vue.js + Element Plus)                      │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                      API Gateway (Nginx)                        │
└─────────────────────────────────────────────────────────────────┘
                                │
        ┌───────────────────────┼───────────────────────┐
        │                       │                       │
        ▼                       ▼                       ▼
┌───────────────┐    ┌───────────────┐    ┌───────────────┐
│  Data Service │    │Strategy Engine│    │Backtest Service│
│    (8006)     │    │    (8001)     │    │    (8002)     │
└───────────────┘    └───────────────┘    └───────────────┘
        │                       │                       │
        └───────────────────────┼───────────────────────┘
                                │
        ┌───────────────────────┼───────────────────────┐
        │                       │                       │
        ▼                       ▼                       ▼
┌───────────────┐    ┌───────────────┐    ┌───────────────┐
│Trading Service│    │Portfolio Svc  │    │ Risk Service  │
│    (8003)     │    │    (8004)     │    │    (8005)     │
└───────────────┘    └───────────────┘    └───────────────┘
        │                       │                       │
        └───────────────────────┼───────────────────────┘
                                │
                    ┌───────────┴───────────┐
                    │                       │
                    ▼                       ▼
            ┌───────────────┐    ┌───────────────┐
            │     MySQL     │    │     Redis     │
            │   (3306)      │    │   (6379)      │
            └───────────────┘    └───────────────┘
```

## 技术栈

### 后端

- **Python 3.10+**
- **FastAPI** - 高性能异步Web框架
- **SQLAlchemy** - ORM和数据库操作
- **Pydantic** - 数据验证和序列化
- **Redis** - 缓存和消息队列
- **MySQL** - 关系型数据库

### 前端

- **Vue.js 3** - 渐进式JavaScript框架
- **Element Plus** - UI组件库
- **ECharts** - 数据可视化
- **Vite** - 构建工具

### 基础设施

- **Docker** - 容器化
- **Docker Compose** - 多容器编排
- **Nginx** - 反向代理和负载均衡

## 核心功能

### 1. 数据服务 (Data Service)

- 实时行情数据获取
- 历史K线数据查询
- 股票基本信息管理
- 交易日日历

### 2. 策略引擎 (Strategy Engine)

- 策略CRUD管理
- 策略信号生成
- 因子库管理
- 策略运行控制

### 3. 回测服务 (Backtest Service)

- 历史回测执行
- 回测结果分析
- 权益曲线生成
- 交易记录管理

### 4. 交易服务 (Trading Service)

- 订单管理
- 成交记录
- 模拟交易
- 实盘交易接口

### 5. 组合服务 (Portfolio Service)

- 持仓管理
- 资金账户管理
- 盈亏计算
- 组合分析

### 6. 风控服务 (Risk Service)

- 风险限额管理
- 实时风险监控
- 风险报告生成
- 风险预警

## 快速开始

### 环境要求

- Docker 20.10+
- Docker Compose 2.0+

### 启动系统

```bash
# 克隆项目
git clone <repository-url>
cd quant-investment-system

# 启动所有服务
docker-compose up -d

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f
```

### 访问服务

- **Web前端**: http://localhost:3000
- **API网关**: http://localhost:80
- **策略引擎API**: http://localhost:8001/docs
- **数据服务API**: http://localhost:8006/docs
- **回测服务API**: http://localhost:8002/docs
- **交易服务API**: http://localhost:8003/docs
- **组合服务API**: http://localhost:8004/docs
- **风控服务API**: http://localhost:8005/docs

## 开发指南

### 项目结构

```
quant-investment-system/
├── services/
│   ├── common/              # 公共模块
│   │   ├── config.py       # 配置管理
│   │   ├── database.py     # 数据库连接
│   │   ├── redis_client.py # Redis客户端
│   │   ├── logging.py      # 日志配置
│   │   ├── exceptions.py   # 异常处理
│   │   ├── middleware.py    # 中间件
│   │   ├── validation.py   # 数据验证
│   │   ├── health.py       # 健康检查
│   │   └── models/         # 数据模型
│   ├── data-service/       # 数据服务
│   ├── strategy-engine/    # 策略引擎
│   ├── backtest-service/   # 回测服务
│   ├── trading-service/    # 交易服务
│   ├── portfolio-service/  # 组合服务
│   └── risk-service/       # 风控服务
├── web-frontend/           # Web前端
├── tests/                  # 测试代码
├── docs/                   # 文档
├── docker-compose.yml      # Docker编排
└── nginx.conf             # Nginx配置
```

### 添加新服务

1. 在 `services/` 目录下创建新服务目录
2. 创建 `app/main.py` 作为服务入口
3. 使用 `common` 模块提供的工具
4. 在 `docker-compose.yml` 中添加服务配置
5. 在 `nginx.conf` 中添加路由配置

### 代码规范

- 使用类型提示
- 编写文档字符串
- 遵循PEP 8规范
- 添加单元测试
- 使用统一的错误处理

## 配置管理

### 环境变量

系统支持通过环境变量进行配置，主要配置项包括：

```bash
# 数据库配置
MYSQL_HOST=mysql
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=quant123
MYSQL_DATABASE=quant_system

# Redis配置
REDIS_HOST=redis
REDIS_PORT=6379

# Tushare配置
TUSHARE_TOKEN=your_token

# 交易配置
TRADING_ENABLED=false
TRADING_MODE=simulation

# 日志配置
LOG_LEVEL=INFO
LOG_FORMAT=json
```

### 配置文件

也可以使用 `.env` 文件进行配置：

```env
ENVIRONMENT=development
SERVICE_NAME=quant-system
DEBUG=true
```

## 测试

### 运行测试

```bash
# 安装测试依赖
pip install -r tests/requirements-test.txt

# 运行所有测试
pytest

# 运行特定测试
pytest tests/test_strategy_api.py

# 生成测试报告
pytest --cov=services --cov-report=html
```

### 测试结构

```
tests/
├── conftest.py              # pytest配置
├── test_strategy_api.py     # 策略API测试
├── test_data_service.py     # 数据服务测试
├── test_backtest.py         # 回测测试
├── test_trading.py          # 交易测试
├── test_portfolio.py        # 组合测试
├── test_risk.py             # 风控测试
└── requirements-test.txt    # 测试依赖
```

## 部署

### 开发环境

```bash
docker-compose up -d
```

### 生产环境

```bash
# 使用生产配置
docker-compose -f docker-compose.prod.yml up -d
```

### 监控

- **健康检查**: `GET /health`
- **服务指标**: `GET /metrics`
- **Prometheus**: 配置Prometheus抓取指标
- **Grafana**: 可视化监控面板

## API文档

每个服务都提供自动生成的API文档：

- **Swagger UI**: `http://localhost:{port}/docs`
- **ReDoc**: `http://localhost:{port}/redoc`

## 贡献指南

1. Fork 项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建 Pull Request

## 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情
