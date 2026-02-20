# GitHub Secrets 配置指南

所有敏感配置都通过 GitHub Secrets 管理，部署时自动注入到服务器。

## 配置路径

```
仓库 → Settings → Secrets and variables → Actions → Repository secrets
```

## 必须配置的 Secrets

| Secret 名称 | 说明 | 示例/生成方式 |
|------------|------|--------------|
| `SERVER_HOST` | 服务器 IP 地址 | `123.45.67.89` |
| `SERVER_USER` | SSH 用户名 | `root` |
| `SSH_PRIVATE_KEY` | SSH 私钥内容 | `-----BEGIN RSA PRIVATE KEY-----\n...` |
| `FRONTEND_DOMAIN` | 前端域名 | `app.example.com` |
| `BACKEND_DOMAIN` | 后端域名 | `api.example.com` |
| `POSTGRES_PASSWORD` | 数据库密码 | `openssl rand -base64 24 \| tr -d '/+='` |
| `JWT_SECRET` | JWT 签名密钥 | `openssl rand -base64 32` |
| `DATA_ENCRYPTION_KEY` | 数据加密密钥 | `openssl rand -base64 32` |
| `REDIS_PASSWORD` | Redis 密码 | `openssl rand -base64 24 \| tr -d '/+='` |

## 可选配置的 Secrets

| Secret 名称 | 说明 | 用途 |
|------------|------|------|
| `TELEGRAM_BOT_TOKEN` | Telegram Bot Token | 部署失败通知 |
| `TELEGRAM_CHAT_ID` | Telegram Chat ID | 部署失败通知 |
| `DISCORD_WEBHOOK_URL` | Discord Webhook URL | 应用内通知 |

---

## 一键生成 Secrets 值

在本地终端运行以下命令，生成所有密钥：

```bash
echo "POSTGRES_PASSWORD=$(openssl rand -base64 24 | tr -d '/+=')"
echo "JWT_SECRET=$(openssl rand -base64 32)"
echo "DATA_ENCRYPTION_KEY=$(openssl rand -base64 32)"
echo "REDIS_PASSWORD=$(openssl rand -base64 24 | tr -d '/+=')"
```

## SSH 私钥配置

1. **生成密钥对**（如果没有）：
   ```bash
   ssh-keygen -t rsa -b 4096 -C "github-deploy" -f github-deploy -N ""
   ```

2. **将公钥添加到服务器**：
   ```bash
   ssh-copy-id -i github-deploy.pub root@你的服务器IP
   ```

3. **将私钥内容添加到 GitHub Secret**：
   ```bash
   cat github-deploy
   ```
   复制完整内容（包括 `-----BEGIN` 和 `-----END` 行）

---

## 配置清单

在 GitHub 配置完成后，确认以下各项：

- [ ] `SERVER_HOST` - 服务器 IP
- [ ] `SERVER_USER` - SSH 用户
- [ ] `SSH_PRIVATE_KEY` - SSH 私钥
- [ ] `FRONTEND_DOMAIN` - `app.example.com`
- [ ] `BACKEND_DOMAIN` - `api.example.com`
- [ ] `POSTGRES_PASSWORD` - 数据库密码
- [ ] `JWT_SECRET` - JWT 密钥
- [ ] `DATA_ENCRYPTION_KEY` - 加密密钥
- [ ] `REDIS_PASSWORD` - Redis 密码

配置完成后，推送到 `main` 分支即可自动部署。
