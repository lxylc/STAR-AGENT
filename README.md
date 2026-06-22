# 基于科大讯飞大模型与多智能体的个性化学习智能体系统

## 项目结构

```
study_system/
├── backend/          # Spring Boot 3.2 + MyBatis-Plus
├── profile_flask/    # 画像自主构建（自评+出题+星火判题）
├── frontend/         # Vue3 + Vite + Element Plus
├── docs/             # 模块设计文档
└── README.md
```

## APISecret 在哪里填？（重要）

任选一种方式：

### 方式一：直接改配置文件（最快）

编辑文件：

`backend/src/main/resources/application.yml`

找到：

```yaml
xfyun:
  app-id: 3d66baac
  api-key: 41d971d3b6c70e15c7a174aae86d0d8a
  api-secret: YOUR_API_SECRET_HERE   # ← 把这里改成你的 APISecret
```

### 方式二：本地 profile（推荐，避免泄露）

1. 复制 `backend/src/main/resources/application-local.yml.example` 为 `application-local.yml`
2. 在 `application-local.yml` 中填写 `xfyun.api-secret`
3. 启动命令加：`--spring.profiles.active=local`

### 方式三：环境变量（生产推荐）

Windows PowerShell：

```powershell
$env:XFYUN_API_SECRET="你的APISecret"
```

Linux/Mac：

```bash
export XFYUN_API_SECRET=你的APISecret
```

Spring Boot 会自动映射到 `xfyun.api-secret`。

---

## 环境要求

- JDK 17+
- Maven 3.8+
- MySQL 8.0
- Node.js 18+（前端）
- 讯飞控制台已开通 **星火认知大模型** WebAPI

## 快速启动

### 1. 数据库

```bash
mysql -u root -p < backend/src/main/resources/db/schema.sql
```

修改 `application.yml` 中 MySQL 用户名密码。

### 2. 后端

```bash
cd backend
mvn spring-boot:run
```

验证：http://127.0.0.1:8080/api/health

### 3. 前端

```bash
cd frontend
npm install
npm run dev
```

访问：http://localhost:5173

演示学生 ID 默认为 `1`（schema.sql 已插入 demo_student）。

### 4. 画像自主构建（Flask + MongoDB）

需先启动 **MongoDB**（默认 `27017`），对话记录存入 `learning_agent.profile_dialogue`。

```bash
mysql -u root -p learning_agent < profile_flask/db/schema-profile-build.sql
cd profile_flask
copy .env.example .env
pip install -r requirements.txt
python init_db.py --refresh-exercises
python app.py
```

前端 **画像构建**：http://localhost:5173/profile/dialogue（自评与校验题均在对话界面内完成）  
详见 [docs/模块1-画像自主构建.md](docs/模块1-画像自主构建.md)

## 当前进度

- [x] 项目骨架 + 讯飞星火统一封装
- [x] **模块1** 对话式学习画像构建（星火对话抽取）
- [x] **模块1b** 画像自主构建（Flask：自评+分层出题+星火判题+批量画像）
- [x] **模块2** 多智能体资源生成
- [x] **模块3** 学习路径与推送
- [x] **模块4** 多模态智能辅导（文字/图解/短视频脚本 + 资源上下文答疑）
- [x] **模块5** 学习效果评估（多维度分析 + 动态路径/推送调整）

## 错误 11200 AppIdNoAuthError

**含义**：WebSocket 已连通，但该 **AppId 没有当前 `domain` 模型版本的授权**（不是 APISecret 填错）。

**处理步骤**（按顺序）：

1. 登录 [讯飞开放平台控制台](https://console.xfyun.cn/)
2. 进入应用 `3d66baac` → **添加能力** → 开通 **星火认知大模型（WebAPI）**
3. 在 [星火官网](https://xinghuo.xfyun.cn/sparkapi) 或控制台 **领取/购买对应版本免费额度**（Lite 常为 0 元试用）
4. 修改 `application.yml` 使 **host-url 与 domain 成对**：

| 版本 | host-url | domain |
|------|----------|--------|
| Lite（默认，易开通） | `wss://spark-api.xf-yun.com/v1.1/chat` | `lite` |
| Pro | `wss://spark-api.xf-yun.com/v3.1/chat` | `generalv3` |
| Max | `wss://spark-api.xf-yun.com/v3.5/chat` | `generalv3.5` |

5. 重启后端，访问自检接口：http://127.0.0.1:8080/api/xfyun/config-check

若仅开通了 Lite，却使用 `generalv3.5`，必然报 11200。

## 下一步

模块2：`schema-module2.sql`；模块3：`schema-module3.sql`；模块5：`schema-module5.sql`（若库已存在）。

访问 http://localhost:5173/path 使用学习路径功能；http://localhost:5173/tutoring 智能辅导；http://localhost:5173/evaluation 效果评估。
