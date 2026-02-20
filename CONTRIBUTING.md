# Contributing to BitRun

感谢你对 BitRun 项目感兴趣！本文档说明如何为项目做出贡献。

## 目录

- [行为准则](#行为准则)
- [如何贡献](#如何贡献)
- [开发流程](#开发流程)
- [代码规范](#代码规范)
- [提交规范](#提交规范)
- [测试规范](#测试规范)

## 行为准则

请阅读并遵守我们的行为准则。我们致力于提供友好、安全和欢迎的环境。

## 如何贡献

### 报告 Bug

1. 检查 [Issues](https://github.com/xBitRun/BitRun/issues) 中是否已有相同问题
2. 如果没有，创建新 Issue，包含：
   - 清晰的标题
   - 复现步骤
   - 预期行为 vs 实际行为
   - 环境信息 (OS, Node.js 版本, Docker 版本等)
   - 相关日志

### 提交功能请求

1. 在 Issues 中创建功能请求
2. 清楚描述功能及其使用场景
3. 等待维护者反馈

### 提交代码

1. Fork 仓库
2. 创建功能分支 (`git checkout -b feature/amazing-feature`)
3. 进行修改
4. 确保测试通过
5. 提交 Pull Request

## 开发流程

### 环境搭建

```bash
# 克隆仓库
git clone https://github.com/xBitRun/BitRun.git
cd BitRun

# 一键启动开发环境
./scripts/quick-start.sh

# 或手动启动
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d
```

### 分支策略

- `main` - 主分支，稳定版本
- `feature/*` - 新功能开发
- `fix/*` - Bug 修复
- `refactor/*` - 代码重构

### Pull Request 流程

1. 确保 PR 标题清晰描述改动
2. 在 PR 描述中关联相关 Issue
3. 确保所有 CI 检查通过
4. 等待代码审查
5. 根据反馈进行修改

## 代码规范

### 后端 (Python)

- 使用 `black` 格式化代码
- 使用 `ruff` 进行 lint 检查
- 使用类型注解
- 所有 IO 操作使用 `async/await`

```bash
cd backend
black app/
ruff check app/
```

### 前端 (TypeScript/React)

- 使用 ESLint + Prettier
- 使用函数组件 + Hooks
- 遵循 shadcn/ui 组件规范

```bash
cd frontend
npm run lint
```

### 国际化 (i18n)

**禁止在组件中硬编码用户可见文本：**

```tsx
// ❌ 错误
<Button>点击我</Button>

// ✅ 正确
const t = useTranslations('module');
<Button>{t('buttonLabel')}</Button>
```

## 提交规范

### Commit Message 格式

```
<emoji> <type>: <主标题>

<可选的详细说明>
```

### Emoji 和类型

| Emoji | Type | 用途 |
|-------|------|------|
| ✨ | feat | 新功能 |
| 🐛 | fix | Bug 修复 |
| 🎨 | style | UI 样式调整 |
| ♻️ | refactor | 代码重构 |
| 📝 | docs | 文档更新 |
| 🔧 | chore | 配置/依赖更新 |
| ✅ | test | 测试相关 |
| 🚀 | perf | 性能优化 |

### 示例

```
✨ feat: 新增用户登录功能

🐛 fix: 修复订单提交失败问题
- 修正签名参数格式
- 添加错误重试机制
```

### 规则

- 标题使用中文，简洁明了，不超过 50 字符
- 动词开头（新增/修复/优化/调整/重构）
- 每次提交只做一件事
- 相关联的改动合并为一次提交

## 测试规范

### 测试覆盖率

项目要求 **80%+ 测试覆盖率**

### 测试类型

1. **单元测试** - 测试单个函数/组件
2. **集成测试** - 测试 API 端点、数据库操作
3. **E2E 测试** - 测试关键用户流程

### 运行测试

```bash
# 后端
cd backend
pytest --cov=app

# 前端
cd frontend
npm test -- --coverage

# E2E
npm run test:e2e
```

### TDD 工作流

1. 编写失败的测试
2. 编写最小实现代码使测试通过
3. 重构代码
4. 确保测试仍然通过

## 数据库迁移

修改数据模型后：

```bash
cd backend

# 生成迁移脚本
alembic revision --autogenerate -m "描述变更内容"

# 运行迁移
alembic upgrade head
```

## 文档更新

如果 PR 涉及以下内容，请同步更新文档：

- 新功能 → 更新 README.md 和相关 docs/
- API 变更 → 更新 docs/api-reference.md
- 架构变更 → 更新 docs/architecture.md
- 新环境变量 → 更新 .env.example 和 README.md

## 获取帮助

- 提交 Issue: https://github.com/xBitRun/BitRun/issues
- 阅读文档: 查看 `docs/` 目录

---

感谢你的贡献！🎉
