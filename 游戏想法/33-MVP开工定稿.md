# MVP 开工定稿（v1.0 · 可执行）

> 状态：**开发唯一执行清单**  
> 记录时间：2026-09-13  
> 上位规范：[32-四象统一定稿](./32-四象统一定稿.md) · [34-品牌命名与版本规划](./34-品牌命名与版本规划.md)  
> 品牌：**MiraWorld**（中文见 `34`）

---

## 一、MVP 一句话

**在潮灯市注册 → 打卡 → 找陈师傅点标准汤面（15 点）→ 取餐进背包 → 读系统通知。**

三支柱：**探索 · 点菜 · 通知**。无主线、无弹窗、无提现。

---

## 二、范围（IN / OUT）

### ✅ v1.0 必须交付

| 四象 | 交付 |
|------|------|
| **人** | handle 注册登录；NPC 配置（小林、陈师傅等） |
| **地** | 潮灯市；可选逛点 spot 彩蛋打卡 |
| **事** | `visit` `order` `message` `ledger` |
| **物** | `item` + `offer`（陈师傅 · 标准汤面）+ `stack` |
| **钱** | 新手 300 点；托管 15 点；分账 ledger |

| 界面 | 页面 |
|------|------|
| 壳层底栏 | 地图 · 通知 · 背包 · 我的（**无「我要」**） |
| 游戏页 | 潮灯市、陈师傅菜单、订单详情 |

### ❌ v1.0 明确不做

玩家开店、往来私信、配送、家园、雇人、auto、悬赏、投票、律师、Blueprint、穿戴、多币种。

详见 [34](./34-品牌命名与版本规划.md) 路线图。

---

## 三、演示脚本（验收用）

```
1. 注册 handle「测试旅人」→ 落在潮灯市，余额 300 点
2. 地图 → 打卡潮灯市（可选：晚霞岸 spot 彩蛋）
3. 找陈师傅 → 看到 offer「标准汤面 · 15 点」
4. 下单 → order 状态 escrowed → processing → ready
5. 取餐 → stack +1 一碗面；余额 285 点
6. 通知列表 → 一条 message「面好了」
7. /me → 显示 handle、市、余额、打卡记录
```

**通过标准：** 新人 20 分钟内无口头协助走通；L2 真扣真给（余额与背包一致）。

---

## 四、实现阶段（按序开工）

### Phase 0 — 已有 ✅

- VitePress 站点、auth API、nginx

### Phase 1 — 人 + 地 + 壳（第一个可演示里程碑） ✅

- [x] `miraworld.db` 合并迁移
- [x] `users`: `handle`, `password_hash`, `city`, `wallet_credits`, `bio`
- [x] 注册默认 `city=潮灯市`, `wallet_credits=300`
- [x] handle 主登录；email 可选
- [x] `GET /api/world` 读 `locations.json`（市 + spots + npc）
- [x] `POST /api/records/visit` 打卡市 / spot
- [x] GameShell 底栏骨架
- [x] 页面：潮灯市地图、/me

**Phase 1 不做了：** 订单、背包、通知

### Phase 2 — 事 + 物（MVP 闭环）

- [x] `stacks` 表
- [x] `records` 分表或统一表：`orders`, `messages`, `visits`, `ledger_entries`
- [x] `GET /api/catalog` → items + offers
- [x] `POST /api/records/order` 下单（校验余额 → escrow → ledger）
- [x] 订单状态机：`created → escrowed → processing → ready → completed → settled`
- [x] NPC 厨房：processing 可定时/即时 → ready
- [x] `POST /api/records/order/{id}/pickup` 取餐 → stack +1
- [x] `GET /api/records/messages` 系统通知
- [x] 分账 ledger（陈师傅份额可合并进平台或记 payload，MVP 简化为 platform fee 一行）
- [x] 页面：陈师傅菜单、订单详情、通知、背包

### Phase 3 — 打磨（上线前）

- [ ] 帮助页（四象 + 点 + 无提现）
- [ ] 空状态 / 错误文案
- [ ] 移动端底栏
- [ ] 备份脚本
- [ ] 走通 §三 演示脚本 10 次无错

---

## 五、数据模型（v1.0）

### 5.1 players

```sql
CREATE TABLE players (
  id INTEGER PRIMARY KEY,
  handle TEXT UNIQUE NOT NULL,
  password_hash TEXT NOT NULL,
  email TEXT,
  city TEXT NOT NULL DEFAULT '潮灯市',
  wallet_credits INTEGER NOT NULL DEFAULT 0,
  bio TEXT DEFAULT '',
  created_at TEXT NOT NULL
);
```

（现有 `users` 表迁移时可 rename 或兼容。）

### 5.2 stacks

```sql
CREATE TABLE stacks (
  player_id INTEGER NOT NULL,
  item_id TEXT NOT NULL,
  qty INTEGER NOT NULL DEFAULT 0,
  PRIMARY KEY (player_id, item_id)
);
```

### 5.3 records — orders

```sql
CREATE TABLE orders (
  id TEXT PRIMARY KEY,
  buyer_id INTEGER NOT NULL,
  seller_kind TEXT NOT NULL,      -- 'npc'
  seller_id TEXT NOT NULL,        -- 'npc_chen'
  city TEXT NOT NULL,
  offer_id TEXT NOT NULL,
  status TEXT NOT NULL,
  price_credits INTEGER NOT NULL,
  escrow_credits INTEGER NOT NULL,
  payload_json TEXT DEFAULT '{}',
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
```

### 5.4 records — messages

```sql
CREATE TABLE messages (
  id INTEGER PRIMARY KEY,
  to_player_id INTEGER NOT NULL,
  from_kind TEXT NOT NULL,        -- 'system' | 'npc' | 'player'
  from_id TEXT,
  body TEXT NOT NULL,
  ref_type TEXT,                  -- 'order'
  ref_id TEXT,
  read_at TEXT,
  created_at TEXT NOT NULL
);
```

### 5.5 records — visits

```sql
CREATE TABLE visits (
  player_id INTEGER NOT NULL,
  city TEXT NOT NULL,
  spot_id TEXT,                   -- NULL = 只打卡市
  first_at TEXT NOT NULL,
  last_at TEXT NOT NULL,
  PRIMARY KEY (player_id, city, spot_id)
);
```

### 5.6 records — ledger

```sql
CREATE TABLE ledger_entries (
  id INTEGER PRIMARY KEY,
  player_id INTEGER NOT NULL,
  amount INTEGER NOT NULL,
  type TEXT NOT NULL,             -- newbie_grant | escrow | settle | ...
  ref_type TEXT,
  ref_id TEXT,
  created_at TEXT NOT NULL
);
```

**v1.0 不建表：** shops, employees, homes, bounties, traces。

---

## 六、API 清单（v1.0）

前缀：`/miraworld/api`

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/auth/register` | handle, password, → 300 点 |
| POST | `/auth/login` | |
| GET | `/me` | player + stacks 摘要 + visit 数 |
| GET | `/world` | cities, spots, npcs |
| POST | `/records/visit` | `{ city, spot_id? }` |
| GET | `/catalog` | items + offers |
| POST | `/records/order` | `{ offer_id }` |
| GET | `/records/orders` | 我的订单 |
| GET | `/records/orders/{id}` | 详情 + status |
| POST | `/records/orders/{id}/pickup` | 取餐 |
| GET | `/records/messages` | 通知列表 |
| POST | `/records/messages/{id}/read` | 标已读 |
| GET | `/stacks` | 背包 |

---

## 七、配置（已有 / 待补）

| 文件 | 状态 |
|------|------|
| `schema.json` | ✅ |
| `locations.json` | ✅ |
| `items.json` | ✅ |
| `offers.json` | ✅ |
| `welcome.json` | 待补：`newbie_credits: 300` |

---

## 八、前端页面

| 路由 | 内容 |
|------|------|
| `/miraworld/` | 帮助 / 入口 |
| `/miraworld/city` | 潮灯市 + spots |
| `/miraworld/npc/chen` | 陈师傅 · offers |
| `/miraworld/orders/:id` | 订单里程碑 |
| `/miraworld/messages` | 通知 |
| `/miraworld/stacks` | 背包 |
| `/miraworld/me` | 我的 |

壳层：**地图 · 通知 · 背包 · 我的**

---

## 九、上线自检（10 条）

- [ ] §三 演示脚本走通
- [ ] 未登录可看 lore；玩游戏需登录
- [ ] 零推送、无弹窗
- [ ] 余额不足有提示
- [ ] 订单与 stack、ledger 一致
- [ ] 移动端底栏可用
- [ ] 帮助页：四象 + 点 + 无提现
- [ ] 单库备份
- [ ] 功能与 [29](./29-MVP发布会与路线图.md) 发布会话术一致
- [ ] 新功能均能映射 [32](./32-四象统一定稿.md) 四象

---

## 十、下一步（开工顺序）

1. **读本文 + `32`** → 建分支 `cursor/mvp-phase1-6db4`
2. **Phase 1**：DB 迁移 + handle 登录 + world/visit + GameShell
3. **Phase 2**：order 闭环 + messages + stacks
4. **Phase 3**：文案 + 自测 → PR
5. 每 Phase 结束可演示；不跳步做 v1.2 功能

---

*本文取代旧版 `29` §五 建表草案中与四象冲突部分；发布会叙事仍以 `29` §七 为准。*
