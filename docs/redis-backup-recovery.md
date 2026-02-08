# Redis 备份与恢复

## 概述

BITRUN 使用 Redis 7 (AOF 持久化) 存储以下数据：
- JWT 黑名单（token 注销记录）
- 策略状态缓存
- 速率限制计数器
- 登录失败追踪
- 仪表盘缓存
- 市场数据缓存
- 账户余额缓存
- 每日权益快照（P&L 计算）

## 持久化配置

生产环境默认开启 AOF (Append Only File)：

```bash
# docker-compose.prod.yml
command: redis-server --appendonly yes --maxmemory 256mb --maxmemory-policy allkeys-lru --requirepass ${REDIS_PASSWORD}
```

## 备份方式

### 方式一：RDB 快照（推荐定期备份）

```bash
# 触发 RDB 快照
docker exec bitrun-redis redis-cli -a $REDIS_PASSWORD BGSAVE

# 等待完成
docker exec bitrun-redis redis-cli -a $REDIS_PASSWORD LASTSAVE

# 复制快照文件
docker cp bitrun-redis:/data/dump.rdb ./backups/redis_$(date +%Y%m%d_%H%M%S).rdb
```

### 方式二：AOF 文件备份

```bash
# 触发 AOF 重写（压缩文件大小）
docker exec bitrun-redis redis-cli -a $REDIS_PASSWORD BGREWRITEAOF

# 复制 AOF 文件
docker cp bitrun-redis:/data/appendonly.aof ./backups/redis_aof_$(date +%Y%m%d_%H%M%S).aof
```

### 方式三：Volume 备份

```bash
# 停止 Redis（确保数据一致性）
docker stop bitrun-redis

# 备份 volume
docker run --rm -v bitrun_redis_data:/data -v $(pwd)/backups:/backup alpine \
  tar czf /backup/redis_volume_$(date +%Y%m%d_%H%M%S).tar.gz -C /data .

# 重启 Redis
docker start bitrun-redis
```

## 恢复方式

### 从 RDB 恢复

```bash
# 停止 Redis
docker stop bitrun-redis

# 复制 RDB 到 volume
docker cp ./backups/redis_YYYYMMDD_HHMMSS.rdb bitrun-redis:/data/dump.rdb

# 重启 Redis
docker start bitrun-redis
```

### 从 Volume 备份恢复

```bash
# 停止 Redis
docker stop bitrun-redis

# 恢复 volume
docker run --rm -v bitrun_redis_data:/data -v $(pwd)/backups:/backup alpine \
  sh -c "rm -rf /data/* && tar xzf /backup/redis_volume_YYYYMMDD_HHMMSS.tar.gz -C /data"

# 重启 Redis
docker start bitrun-redis
```

## 自动备份（Cron）

建议每日自动备份 RDB 快照：

```bash
# crontab -e
0 2 * * * /path/to/bitrun/scripts/deploy.sh backup-redis >> /var/log/bitrun-redis-backup.log 2>&1
```

## 数据丢失影响

Redis 数据主要是缓存和临时状态，**完全丢失的影响较小**：

| 数据类型 | 丢失影响 | 恢复方式 |
|---------|---------|---------|
| JWT 黑名单 | 已注销的 token 可能暂时有效（token 最多 1 小时过期） | 自动恢复 |
| 策略状态缓存 | 无影响（从 DB 重新加载） | 自动恢复 |
| 速率限制计数 | 短暂无限制（60 秒后恢复） | 自动恢复 |
| 每日权益快照 | 当日 P&L 可能显示异常 | 次日自动恢复 |
| 市场/余额缓存 | 无影响（10-30 秒内重新拉取） | 自动恢复 |
