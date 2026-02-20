# BitRun Frontend

BitRun 前端应用 - AI 驱动的加密货币交易代理平台用户界面。

## 技术栈

| 技术 | 版本 | 说明 |
|------|------|------|
| Next.js | 16 | React 框架 (App Router) |
| React | 19 | UI 库 |
| TypeScript | 5 | 类型安全 |
| Tailwind CSS | 4 | 原子化 CSS |
| shadcn/ui | - | 基于 Radix UI 的组件库 |
| Zustand | - | 状态管理 |
| SWR | - | 数据获取 |
| next-intl | - | 国际化 |
| Recharts | - | 图表库 |

## 项目结构

```
frontend/
├── src/
│   ├── app/[locale]/           # 国际化路由
│   │   ├── (auth)/             #   认证页面
│   │   ├── (dashboard)/        #   仪表盘页面
│   │   │   ├── overview/       #     首页
│   │   │   ├── agents/         #     Agent 管理
│   │   │   ├── strategies/     #     策略配置
│   │   │   ├── accounts/       #     账户管理
│   │   │   ├── models/         #     AI 模型
│   │   │   ├── backtest/       #     回测
│   │   │   ├── decisions/      #     决策记录
│   │   │   ├── analytics/      #     数据分析
│   │   │   ├── wallet/         #     钱包管理
│   │   │   ├── channel/        #     通知渠道
│   │   │   ├── marketplace/    #     策略市场
│   │   │   ├── settings/       #     设置
│   │   │   └── admin/          #     管理后台
│   │   └── (landing)/          #   落地页
│   ├── components/             # React 组件
│   │   ├── ui/                 #   shadcn/ui 基础组件
│   │   ├── strategy-studio/    #   策略工作室
│   │   ├── charts/             #   图表组件
│   │   └── ...                 #   其他组件
│   ├── hooks/                  # 自定义 Hooks
│   ├── lib/api/                # API 客户端
│   ├── stores/                 # Zustand 状态管理
│   ├── messages/               # i18n 翻译 (en.json / zh.json)
│   └── providers/              # React Context Providers
├── e2e/                        # Playwright E2E 测试
└── __tests__/                  # Jest 单元测试
```

## 开发

### 环境要求

- Node.js 20+
- npm / yarn / pnpm / bun

### 本地开发

```bash
# 安装依赖
npm install

# 配置环境变量
cp .env.local.example .env.local
# 编辑 .env.local 设置 API 地址

# 启动开发服务器
npm run dev
```

访问 http://localhost:3000

### Docker 开发

```bash
# 使用根目录的 docker-compose
cd ..
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d
```

## 构建

```bash
# 生产构建
npm run build

# 启动生产服务
npm start
```

## 测试

```bash
# 单元测试
npm test

# 监视模式
npm run test:watch

# 覆盖率
npm run test:coverage

# E2E 测试
npm run test:e2e
```

## 环境变量

详见 `.env.local.example`：

| 变量 | 说明 |
|------|------|
| `NEXT_PUBLIC_API_URL` | 后端 API 地址 |
| `NEXT_PUBLIC_WS_URL` | WebSocket 地址 |
| `NEXT_PUBLIC_BRAND_*` | 品牌定制相关变量 |

## 国际化

支持中文和英文，翻译文件位于 `src/messages/`：

- `zh.json` - 简体中文
- `en.json` - English

使用方式：

```tsx
import { useTranslations } from 'next-intl';

export function MyComponent() {
  const t = useTranslations('module');
  return <Button>{t('buttonLabel')}</Button>;
}
```

## 相关文档

- [开发者指南](../docs/development.md)
- [API 参考](../docs/api-reference.md)
- [架构概览](../docs/architecture.md)
