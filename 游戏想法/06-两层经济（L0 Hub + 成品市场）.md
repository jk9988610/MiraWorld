# 06 · 两层经济（L0 Hub + 成品市场）

> **高新城方向定稿：仅 L0 环境层 + L1+ 玩家高新层；经市场流转；无中层；无 Market Pulse**  
> 上位：[01-设计总纲](./01-设计总纲.md) · [04-乌托邦经济](./04-乌托邦经济.md) · [05-版本路线](./05-版本路线.md)

---

## 一、一句话

**底层（L0）自管产能与 Hub 供给；上层（L1+）向 Hub 买包、一步产终品、挂成品市场；买家从市场买后即 deploy / 满足需求。**  
不做玩家点对点供货链，不做 item 再加工，不做 Market Pulse 抽象。

---

## 二、为什么只要两层

| 层 | 谁 | 变更频率 | 对开发者 |
|----|-----|----------|----------|
| **L0** | 程序/策划 | 高（热更配置） | 独立 tick、独立 smoke；服务上层而不绑上层代码 |
| **L1+** | 玩家公司 + institution | 中（新品类/kind） | 只认 **Hub 价表 + offer 市场 + recipe/on_acquire** 三个契约 |

**不做中层（现阶段）：** 无玩家集配、无玩家冶炼、无 item→item 生产链。将来若加，也只是 Hub 多几种 `resource_id`，仍经市场卖，不点对点。

**潮灯市（面/legacy）：** 可作试验场冻结；**高新城** 按本文开城（零上层建筑、高新终品、Hub 五包）。

---

## 三、两个市场（不是点对点）

| 市场 | 卖什么 | 谁买 | API 方向 |
|------|--------|------|----------|
| **L0 Hub** | 供给包 `power` / `connectivity` / … | 上层所有 institution（生产用） | `hub.list` · 生产 tick 内扣款扣库存 |
| **成品市场** | 上层 `item_*` 终品 | 市民组 tick · NPC 机构 procurement · 玩家个人 | 现有 **offer + order**；`settled` → `on_acquire` |

```
L0 内部（玩家不可见）
  能源 / 算力 / 元器件基地 / … → Hub 库存 + 市价

L1+ institution
  Hub 买包 ──recipe──►  institution 成品仓
  挂 offer ──► 成品市场

买家（市民 / NPC 机构 / 玩家）
  成品市场下单 ──settled──► 买了即用（不进 recipe）
```

**纪律：** 生产 **只** 从 Hub 买包；终品 **只** 从成品市场买；**禁止** institution ↔ institution 私下合同或定向供货。

---

## 四、四条实现纪律（写代码前必守）

1. **L1+ 生产 inputs 白名单**：仅 `hub.resource_id`；**禁止** `item_id` 作 recipe 输入。  
2. **L1+ 生产采购**：仅 Hub；**禁止** 从成品市场买货当原料。  
3. **L1+ 销售**：终品 **仅** 通过 `offer` 进成品市场；**禁止** institution 直转 item 给另一 institution。  
4. **成品市场成交**：`order.settled` 必须走 `on_acquire`（SATISFY / DEPLOY）；**禁止** 进 institution 生产仓或当 inputs。

---

## 五、层间流转（回答「L0 买了会不会变上层」）

| 阶段 | L0 | L1+ |
|------|-----|-----|
| Hub 采购 | 供给包库存↓ · hub 收 credits | **无** L0 stack |
| 生产 | 供给包按 recipe 再扣 | **成品 item** 进 institution 库存 |
| 成品出售 | — | offer → 市场 |
| 市场购买 | — | 买家 `on_acquire`；**item 不再变回 L0 包** |

**变上层的只有 recipe 的 outputs**；L0 供给包始终在 Hub 账本，不以物品形式出现在上层背包。

---

## 六、L0 Hub 供给包（首发建议 5 种）

| resource_id | UI 名 | 上层谁用 |
|-------------|-------|----------|
| `power` | 电力额度 | 全行业 |
| `connectivity` | 算力与网络 | 软件园、芯片工作室 |
| `components` | 通用元器件包 | 设备厂 |
| `silicon_service` | 流片与制程服务 | 芯片工作室 |
| `facility` | 产业空间与运维 | 所有 kind（按系数） |

配置目录（实现向）：

```
server/config/l0/
  resources.json      # 供给包定义、单位、标签
  facilities.json     # L0 内部产能（不对玩家暴露）
  hub_pricing.json    # 指导价、波动、补贴
server/config/l1/
  recipes.json        # inputs 仅 resource_id
  items.json          # 终品 + on_acquire
  building_kinds.json # software_house / device_plant / …
```

**L0 tick 职责：** 自产 → 更新 Hub 库存与市价 → 福利 grant / 生存底（抽象，不经过玩家食品链）。

---

## 七、L1+ 玩家层（高新、无食品）

### 机构 kind（首发 2～4）

| kind | 示例终品 |
|------|----------|
| `software_house` | 城市 OS 套件、企业云 ERP |
| `device_plant` | 智能终端、安全网关 |
| `chip_studio` | 控制 SoC 模块（P1） |
| `biotech_lab` | 诊断盒、实验自动化（P1） |

**recipe：** `inputs: [{ resource, qty }]` → `outputs: [{ item_id, qty }]`；**一步终品**，无 item 中间态。

**公司：** v2.1 已有 `company` → 多 institution → slots（NPC 岗）+ 生产 line + offers。

---

## 八、成品市场与买家

### 8.1 市民组（C 端）

- tick 扫 `active_offers(city)`，按 **pref**（`device` / `software` / `service` / `medical`）打分购买。  
- `settled` → `SATISFY_PREF`（组 satisfaction 等）；**不** 进组背包。  
- Spotlight 仍 **姓+职业**（高新 slot：算法员、QC…）。

### 8.2 NPC 机构（B/G 端）

- 新步骤 **institution_procurement**：与市民组 **同一 offer 市场**。  
- 筛选：`on_acquire.institution` 非空 + kind 匹配 + 钱包够 + **市价最低**（同价可配置 tie-break）。  
- `settled` → `DEPLOY_INST` / `BUFF_INST` / `ENABLE_SLOT`；**不** 再加工。

### 8.3 玩家个人

- 可市场下单进背包；**不参与** institution 生产链（除非另开玩法）。

### 8.4 玩家机构互买

- **不做点对点**；若 B 机构需要 deploy 类终品，**在成品市场** 买任意卖家的 offer。  
- 买了 **即用**，**不能** 进 recipe。

---

## 九、买了即用（效果表摘要）

| 买家 | 效果类型 | 说明 |
|------|----------|------|
| pop_group | `SATISFY_PREF` | 满足 tech 类偏好；ledger `effect_apply` |
| institution | `DEPLOY_INST` 等 | 机构 deploy 行；可能 ENABLE_SLOT / BUFF |
| player | `PLAYER_USE`（可选） | 非主闭环 |

**终品不得作为任何 recipe 的 inputs。** 详见讨论稿（C 端 6 件 + B 端 6 件）Implement 时写入 `items.json` 或 `item_effects.json`。

**不用 Market Pulse：** 玩家感知靠 **Hub 市价、自己的 offer 成交量/挂单时长、同类市价带**；闭环靠现有 payroll / welfare / procurement 钱包，不新增脉搏指标。

---

## 十、日 tick 顺序（高新城）

```
① l0_tick
   产能 → hub 库存 → hub 市价（供需 + 指导价）

② institution_production
   enabled line：hub 扣 L0 包（市价）→ 产 item 进 institution 库存

③ institution_payroll
   在岗组 wallet（≥ 最低工资）

④ city_welfare_subsidy
   无岗组补贴（L0 抽象民生，非玩家食品）

⑤ market_procurement
   · pop_group：扫 offers 购买
   · system institution：扫 offers 购买（deploy 类）

⑥ order settled → on_acquire → ledger / spotlight

⑦ economy_audit（可选断言）
```

与 [04-乌托邦经济](./04-乌托邦经济.md) §四顺序兼容：**把原 ① institution_production 拆成 l0_tick + 真·production**；采购合并为 ⑤。

---

## 十一、Hub schema 草案

### resources.json（片段）

```json
{
  "resources": [
    {
      "id": "power",
      "display": "电力额度",
      "unit": "MWh",
      "guide_price": 10
    },
    {
      "id": "components",
      "display": "通用元器件包",
      "unit": "lot",
      "guide_price": 25
    }
  ]
}
```

### 运行时（每 city 每 tick）

| 表/字段 | 说明 |
|---------|------|
| `hub_inventory(city, resource_id, qty)` | L0 卖出后扣减 |
| `hub_prices(city, resource_id, price_credits)` | 当日市价 |
| `hub_ledger` | `hub_sale` / `restock` / `subsidy` |

 institution 生产时：

```
cost = Σ (qty × hub_prices[resource])
institution.wallet -= cost   // 或 company.wallet，配置默认
hub_inventory -= qty
```

---

## 十二、开发者优势（摘要）

| 点 | 说明 |
|----|------|
| **接口少** | 上层只依赖 Hub 价表 + offer + recipe/on_acquire |
| **L0 热更** | 改 `l0/*` 即可调产能/价/补贴，上层 recipe 可不动 |
| **测试分片** | `run_l0_tick` / mock hub / production / market smoke 分层 |
| **审计** | Hub 售出 ≈ 上层消耗；市场卖出 ≈ effect_apply 次数 |
| **与现网衔接** | offer、order、company、institution、tick cron 可渐进扩展 |
| **未来中层** | 若加 `module_kit`，仍挂 Hub 卖；契约不变 |

---

## 十三、与旧文档关系

| 文档 | 关系 |
|------|------|
| [04-乌托邦经济](./04-乌托邦经济.md) | 市民组、工资、补贴、Spotlight、tick 骨架 **保留** |
| [03-玩家操作与分工](./03-玩家操作与分工.md) | 开店/offer/当班 **保留**；食品上层 **高新城不做** |
| 潮灯市 legacy | 陈师傅面、food pref **不扩展**；新场按本文 |

---

## 十四、验收（实现阶段）

1. institution 生产 **仅** 耗 Hub 包，产 **item** 进库存。  
2. 成品 **仅** 经 offer 成交；pop 与 NPC 机构 **同一市场**。  
3. settled 必触发 `on_acquire`；无 item→recipe。  
4. 无 institution 点对点 API。  
5. smoke：Hub 有价 → 生产 1 件 → 挂 offer → cron 1 日 → audit 平衡。

---

## 十五、明确不做（本文范围）

- ❌ 中层（集配、冶炼、玩家物流枢纽）  
- ❌ Market Pulse / 产业贡献度抽象  
- ❌ 点对点 institution 合同  
- ❌ item 作 recipe inputs / 再加工  
- ❌ 玩家食品链、L0 鲜料直接进上层背包  
- ❌ 玩家操作 L0 设施  

---

*定稿 · 2026-09-14 · 讨论共识落稿*
