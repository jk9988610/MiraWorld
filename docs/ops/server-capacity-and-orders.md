# 服务器容量、缓存与高并发下单

本文记录 MiraWorld / bykc 当前云服务器（`8.133.252.224`）的压测结论、内存与缓存分工，以及以「电商平台下单」为类比的高并发架构经验。供后续扩容、优化 nginx、接入订单系统时参考。

**服务器概况（2026-09-12 实测）**

| 项目 | 数值 |
|------|------|
| 规格 | 2 vCPU Intel Xeon，1.6 GB 内存 |
| 系统盘 | 40 GB，使用率约 9% |
| 外网 | HTTP 80 / HTTPS 443 |
| 主要服务 | nginx、bykc-api（:8000）、miraworld-auth（:8787）、MiraWorld 静态站（`/miraworld/`） |

---

## 1. 压测结论：瓶颈在哪里

2026-09-12 对静态站与 API 分别单开压测（ab / wrk，100 并发）。

### 1.1 吞吐与延迟

| 目标 | RPS（约） | P50 延迟 | 失败率 |
|------|-----------|----------|--------|
| `/miraworld/` 静态首页 | 412～457 | ~196 ms | 0% |
| `/api/health` | 372～406 | ~220 ms | 0%（wrk 偶发 5 超时） |

### 1.2 本机 vs 外网

| 端点 | 服务器本机 curl | 外网访问 |
|------|-----------------|----------|
| `/miraworld/` | **~2 ms** | **~200 ms 起** |
| `/api/health` | **~7 ms** | **~200 ms 起** |
| ping RTT | — | **~205 ms** |

**结论：**

- 算力不是瓶颈：压测时 CPU 负载 < 1.0，uvicorn 进程 CPU < 1%。
- 外网用户的主要延迟来自 **公网 RTT（约 200 ms）**，而非服务端处理。
- 高并发下次要瓶颈是 **TCP 连接数 / TIME_WAIT 堆积**（API 压测后 TIME_WAIT 可达数千）。
- 当前 nginx **未配置** gzip、`Cache-Control`、`proxy_cache`、API 限流。

### 1.3 架构示意

```
外网用户
    │  ~200ms RTT（主要延迟来源）
    ▼
nginx :80 / :443
    ├─ /miraworld/  → 磁盘静态文件（本机 ~2ms）
    ├─ /api/*       → bykc-api uvicorn :8000（本机 ~7ms）
    └─ /auth/*      → miraworld-auth uvicorn :8787
```

---

## 2. 内存分工：能跑多少程序

1.6 GB 内存可理解为固定大小的「工作台」。能同时跑多少服务，取决于各进程 **常驻内存 + 峰值内存**，而非磁盘上装了多少程序。

### 2.1 当前占用（约）

| 占用方 | 约内存 | 作用 |
|--------|--------|------|
| Linux 内核 | ~100 MB | 调度、网络、文件缓存 |
| 阿里云监控等 | ~150 MB | argusagent、AliYunDun 等 |
| nginx | ~10 MB | HTTP 接入、反向代理 |
| bykc-api（uvicorn） | ~50 MB | 业务 API |
| miraworld-auth | ~35 MB | 认证服务 |
| 文件系统缓存（buff/cache） | ~1 GB | 内核自动缓存已读文件 |
| **可用余量** | **~1.1 GB** | 可再部署 DB、Redis、更多 worker |

### 2.2 文本优先、少做图片

| 选择 | 好处 |
|------|------|
| 内容以 Markdown / JSON / 纯文本为主 | 体积小，易 CDN 缓存，API 内存占用低 |
| 不做图片上传与托管 | 不占 uvicorn 内存，不拖磁盘 IO |
| 列表分页 | 单次响应小，连接占用时间短 |

在同等内存下，**文本型业务**比图片/文件型可多支撑数倍并发连接。

---

## 3. 缓存由谁负责

```
用户浏览器  →  缓存 HTML/JS/CSS、短时接口结果
     ↓ 未命中
nginx       →  静态资源、gzip；API 一般只转发
     ↓
应用层      →  热点数据（会话、库存余量）→ Redis 或进程内 LRU
     ↓
数据库      →  查询缓冲、索引页
     ↓
磁盘        →  订单、库存、日志（持久化）
```

| 层级 | 负责方 | 适合缓存的内容 | 当前状态 |
|------|--------|----------------|----------|
| 浏览器 | 前端 | 带 hash 的 `/assets/*`、不常变列表 | 未配 Cache-Control |
| 反向代理 | nginx | `/miraworld/assets/`、gzip 压缩结果 | 未开 |
| 应用 | Redis（可选） | 会话、库存快照、限流计数 | 未部署 |
| 数据库 | PostgreSQL / SQLite | 热数据页 | 视业务库而定 |

**原则：** 越靠近用户的缓存越省服务器；订单、库存等强一致数据以数据库为准，不能只放进程内存。

### 3.1 推荐静态资源缓存头

| 资源 | 建议 `Cache-Control` |
|------|----------------------|
| `/miraworld/assets/*`（文件名含 hash） | `public, max-age=31536000, immutable` |
| `/miraworld/*.html` | `public, max-age=300`（5 分钟） |
| `/api/*` | `no-store` 或 `private, max-age=0` |

---

## 4. 高并发下的合理布局（文档站 + API）

在 **不扩容机器** 的前提下，优先「少打源站、少重复传输」：

### 优先级 1（零成本低，效果明显）

- nginx 为 `/miraworld/assets/` 开启 **gzip + 长缓存**
- HTML 短缓存（约 5 分钟）
- `/api/*` **限流**（如 `limit_req`），防止恶意刷接口

### 优先级 2（小改动，稳定性提升）

- bykc-api：`uvicorn --workers 2`（与 CPU 核数一致）
- nginx 对上游 API 使用 **keepalive** 连接池
- 前端对用户信息、列表等做 **短时客户端缓存**（30s～5min）

### 优先级 3（有预算时）

- 阿里云 **CDN** 托管 `/miraworld/assets/`
- 头像/大文件走 **OSS**，不经 API 进程
- 完善域名与 HTTPS 证书

### 4.1 文档站合理并发（优化缓存后）

| 场景 | 估算 |
|------|------|
| 有浏览器缓存的浏览 | 500～1000 在线用户（大部分请求不打源站） |
| 冷启动静态请求 | ~400 并发请求/秒 |
| 轻量 API（health、读列表） | ~200～400 RPS |

---

## 5. 电商下单类比：请求如何被「签收」

许多用户同时点击「购买」时，不能为每个请求无限开线程，而应 **限流 → 校验 → 扣库存写单 → 异步通知**。

### 5.1 文本订单简化流程

```
用户点击购买
    ↓
nginx 限流（单 IP / 全站 QPS 上限）
    ↓
API 校验登录、参数、幂等键（防重复提交）
    ↓
查库存（DB 或 Redis）
    ↓
同一事务：扣库存 + 插入订单
    ↓
返回订单号（支付、发货可异步）
    ↓
（可选）消息队列 → 后台 worker 通知、对账
```

### 5.2 与健康检查的差别

| 类型 | 服务端工作量 | 本机耗时（约） |
|------|--------------|----------------|
| `GET /api/health` | 几乎无状态 | ~7 ms |
| 下单（文本） | 鉴权 + 读库存 + 写订单 + 日志 | **20～100 ms** |
| 含支付回调 | 第三方签名、对账 | **100 ms～秒级** |

压测得到的 **~400 RPS 针对轻接口**；下单属于重接口，实际能力会低一个数量级以上。

### 5.3 保证不崩溃的手段

1. **限流**：超出能力返回「系统繁忙」，而不是堆满内存。
2. **队列削峰**：先快速入队并返回「处理中」，worker 按能力写库。
3. **库存原子扣减**：`UPDATE stock SET n=n-1 WHERE n>0` 或 Redis `DECR`。
4. **幂等**：同一 `client_order_id` 只生成一张订单。
5. **短事务**：事务内只做扣库存 + 插订单；支付、通知放事务外。
6. **固定大小连接池**：DB 连接例如 10～20，避免每请求新建连接。

---

## 6. 本机订单吞吐估算（文本订单、无图片）

以下为 **工程估算**，用于容量规划，非 SLA 承诺。假设：校验 + 扣库存 + 写一条订单记录。

### 6.1 三档架构

#### A. 最简（单 uvicorn + 单库，同步下单）

```
用户 → nginx → 1× uvicorn → DB
```

| 指标 | 约 |
|------|-----|
| 可持续 | **10～30 单/秒** |
| 短时突发 | ~50 单/秒（延迟上升、TIME_WAIT 增多） |
| SQLite | 更接近 **5～15 单/秒** |
| 小规格 PostgreSQL | **20～50 单/秒**（视索引与事务） |

#### B. 推荐（2 worker + 限流 + Redis 缓存库存）

```
用户 → nginx 限流 → 2× uvicorn → Redis 扣库存 → PostgreSQL 落单
```

| 指标 | 约 |
|------|-----|
| 可持续 | **30～80 单/秒** |
| 峰值（限流内） | **100～150 请求/秒** 被接受 |
| 额外内存 | Redis ~30 MB + Postgres ~100～200 MB |

#### C. 队列削峰（大促思路，仍单机）

```
用户 → API 入队 → 返回「排队中」 → 多个 worker 消费写库
```

| 指标 | 约 |
|------|-----|
| 每秒可「签收」请求 | **200～500**（仅入队） |
| 每秒真正落库 | 仍受 B 档限制，约 **30～80 单/秒** |

### 6.2 换算成「一天能接多少单」

以 B 档 sustained **30 单/秒** 为例（全天满负载不现实，仅供量级感受）：

| 时长 | 约订单数 |
|------|----------|
| 1 分钟 | ~1,800 |
| 1 小时持续高峰 | ~10 万 |
| 更现实：高峰 1 小时 5,000 单 | 平均约 1.4 单/秒，机器很轻松 |

对 **文字向、中小规模** 产品，架构合理时 **日订单几万级** 通常够用；瓶颈更常在支付与运营，而非 2 核 CPU。

---

## 7. nginx 配置参考（待实施）

以下片段可并入 `deploy/nginx-miraworld.conf` 或服务器 `snippets`，部署前请在测试环境验证。

```nginx
# 静态资源：gzip + 长期缓存
location ^~ /miraworld/assets/ {
    root /var/www/html;
    gzip on;
    gzip_types text/css application/javascript application/json;
    expires 1y;
    add_header Cache-Control "public, immutable";
}

# HTML 短缓存
location ^~ /miraworld/ {
    root /var/www/html;
    index index.html;
    try_files $uri $uri.html /miraworld/index.html;
    expires 5m;
    add_header Cache-Control "public, max-age=300";
}

# API 限流（需在 http 块定义 limit_req_zone）
# limit_req_zone $binary_remote_addr zone=api:10m rate=30r/s;
# location /api/ {
#     limit_req zone=api burst=50 nodelay;
#     proxy_pass http://127.0.0.1:8000/;
#     proxy_http_version 1.1;
#     proxy_set_header Connection "";
# }
```

---

## 8. 压测工具（仓库内）

| 文件 | 用途 |
|------|------|
| `deploy/stress_test.py` | Python 分级并发压测 |
| `deploy/run_stress_suite.sh` | ab + wrk + 远程指标采集 |
| `deploy/collect_metrics.py` | SSH 拉取服务器快照 |
| `deploy/server_metrics.sh` | 远程执行的指标脚本 |

示例：

```bash
# 本地压测
python3 deploy/stress_test.py

# 完整套件（需 SSH 密钥）
bash deploy/run_stress_suite.sh

# 查看服务器状态
python3 deploy/collect_metrics.py status
```

---

## 9. 相关链接

- 部署说明：仓库根目录 `readme.txt`
- nginx 片段：`deploy/nginx-miraworld.conf`
- 线上地址：http://8.133.252.224/miraworld/
- API 健康检查：http://8.133.252.224/api/health

---

## 10. 修订记录

| 日期 | 说明 |
|------|------|
| 2026-09-12 | 初版：压测结论、内存与缓存、下单流程与容量估算 |
