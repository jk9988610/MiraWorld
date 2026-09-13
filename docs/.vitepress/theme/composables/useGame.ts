import { ref } from 'vue'

const API_BASE = '/miraworld/api'

export interface Npc {
  id: string
  display: string
  city: string
  role?: string
  greeting?: string
  extra?: string
}

export interface ExploreSpot {
  id: string
  name: string
  flavor?: string
}

export interface CityConfig {
  id: string
  city: string
  summary?: string
  explore_spots?: ExploreSpot[]
  npcs?: string[]
}

export interface WorldData {
  brand: { en: string; zh: string; tagline_zh?: string }
  onboarding_message: string
  cities: CityConfig[]
  npcs: Npc[]
  system_shop?: { display: string; person?: { id: string } }
}

export interface CatalogOffer {
  id: string
  seller: { kind: string; id: string; display: string }
  place: { city: string }
  gives: { item_id: string; qty: number }
  price_credits: number
  display: string
  active?: boolean
}

export interface CatalogData {
  items: Array<{ id: string; display: string; tags?: string[] }>
  offers: CatalogOffer[]
}

export interface OrderData {
  id: string
  buyer_id: number
  seller_kind: string
  seller_id: string
  status: string
  price_credits: number
  display: string
  item_id: string
  item_qty: number
  city: string
  offer_id: string
  created_at: string
  updated_at: string
}

export interface MessageData {
  id: number
  from_kind: string
  from_id?: string | null
  from_display?: string
  body: string
  ref_type?: string | null
  ref_id?: string | null
  read_at?: string | null
  created_at: string
}

export interface ShopData {
  player_id: number
  handle: string
  display_name: string
  city: string
  open: boolean
  created_at: string
}

export interface PlayerOfferData {
  id: string
  player_id: number
  item_id: string
  qty: number
  price_credits: number
  display: string
  active: boolean
  created_at: string
}

export interface ShopMeData {
  shop: ShopData | null
  registration_fee: number
  offers: PlayerOfferData[]
}

export interface MarketShopData {
  player_id: number
  handle: string
  display_name: string
  city: string
  offers: PlayerOfferData[]
}

export interface StackData {
  item_id: string
  display: string
  qty: number
  tags?: string[]
}

export interface GroundItem {
  spot_id: string
  item_id: string
  display: string
  qty: number
  tags?: string[]
  available: boolean
}

export interface VisitResult {
  first_visit: boolean
  city: string
  spot_id?: string | null
  message?: string
  ground?: GroundItem
}

export interface StackActionResult {
  item_id: string
  display: string
  qty: number
  message: string
  stacks: StackData[]
}

const world = ref<WorldData | null>(null)

async function parseJson<T>(res: Response): Promise<T> {
  const data = await res.json().catch(() => ({}))
  if (!res.ok) {
    throw new Error(typeof data.detail === 'string' ? data.detail : '请求失败')
  }
  return data as T
}

export function useGame() {
  async function loadWorld() {
    const res = await fetch(`${API_BASE}/world`, { credentials: 'include' })
    world.value = await parseJson<WorldData>(res)
    return world.value
  }

  async function visit(city: string, spotId?: string) {
    const res = await fetch(`${API_BASE}/records/visit`, {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ city, spot_id: spotId ?? null }),
    })
    return parseJson<VisitResult>(res)
  }

  async function spotPut(city: string, spotId: string) {
    const res = await fetch(`${API_BASE}/records/spot/put`, {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ city, spot_id: spotId }),
    })
    return parseJson<{ message: string; stacks: StackData[] }>(res)
  }

  async function spotConsume(city: string, spotId: string) {
    const res = await fetch(`${API_BASE}/records/spot/consume`, {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ city, spot_id: spotId }),
    })
    return parseJson<{ message: string }>(res)
  }

  async function spotUse(city: string, spotId: string) {
    const res = await fetch(`${API_BASE}/records/spot/use`, {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ city, spot_id: spotId }),
    })
    return parseJson<{ message: string }>(res)
  }

  async function loadCatalog() {
    const res = await fetch(`${API_BASE}/catalog`, { credentials: 'include' })
    return parseJson<CatalogData>(res)
  }

  async function placeOrder(offerId: string) {
    const res = await fetch(`${API_BASE}/records/order`, {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ offer_id: offerId }),
    })
    return parseJson<OrderData>(res)
  }

  async function loadOrder(orderId: string) {
    const res = await fetch(`${API_BASE}/records/orders/${encodeURIComponent(orderId)}`, {
      credentials: 'include',
    })
    return parseJson<OrderData>(res)
  }

  async function pickupOrder(orderId: string) {
    const res = await fetch(`${API_BASE}/records/orders/${encodeURIComponent(orderId)}/pickup`, {
      method: 'POST',
      credentials: 'include',
    })
    return parseJson<OrderData>(res)
  }

  async function loadMessages() {
    const res = await fetch(`${API_BASE}/records/messages`, { credentials: 'include' })
    return parseJson<{ messages: MessageData[] }>(res)
  }

  async function markMessageRead(messageId: number) {
    const res = await fetch(`${API_BASE}/records/messages/${messageId}/read`, {
      method: 'POST',
      credentials: 'include',
    })
    return parseJson<MessageData>(res)
  }

  async function loadStacks() {
    const res = await fetch(`${API_BASE}/stacks`, { credentials: 'include' })
    return parseJson<{ stacks: StackData[] }>(res)
  }

  async function consumeStack(itemId: string) {
    const res = await fetch(`${API_BASE}/stacks/${encodeURIComponent(itemId)}/consume`, {
      method: 'POST',
      credentials: 'include',
    })
    return parseJson<StackActionResult>(res)
  }

  async function useStack(itemId: string) {
    const res = await fetch(`${API_BASE}/stacks/${encodeURIComponent(itemId)}/use`, {
      method: 'POST',
      credentials: 'include',
    })
    return parseJson<StackActionResult>(res)
  }

  async function loadShopMe() {
    const res = await fetch(`${API_BASE}/shop/me`, { credentials: 'include' })
    return parseJson<ShopMeData>(res)
  }

  async function applyShop(displayName: string) {
    const res = await fetch(`${API_BASE}/shop/apply`, {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ display_name: displayName }),
    })
    return parseJson<ShopData>(res)
  }

  async function setShopOpen(isOpen: boolean) {
    const res = await fetch(`${API_BASE}/shop/open?is_open=${isOpen ? 'true' : 'false'}`, {
      method: 'PATCH',
      credentials: 'include',
    })
    return parseJson<ShopData>(res)
  }

  async function createShopOffer(body: {
    item_id: string
    display: string
    price_credits: number
    qty?: number
  }) {
    const res = await fetch(`${API_BASE}/shop/offers`, {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })
    return parseJson<PlayerOfferData>(res)
  }

  async function toggleShopOffer(offerId: string, active: boolean) {
    const res = await fetch(
      `${API_BASE}/shop/offers/${encodeURIComponent(offerId)}?active=${active ? 'true' : 'false'}`,
      { method: 'PATCH', credentials: 'include' },
    )
    return parseJson<PlayerOfferData>(res)
  }

  async function loadMarket(city = '潮灯市') {
    const res = await fetch(
      `${API_BASE}/shop/market?city=${encodeURIComponent(city)}`,
      { credentials: 'include' },
    )
    return parseJson<{ shops: MarketShopData[] }>(res)
  }

  async function loadSellingOrders() {
    const res = await fetch(`${API_BASE}/records/orders/selling`, { credentials: 'include' })
    return parseJson<{ orders: OrderData[] }>(res)
  }

  async function acceptOrder(orderId: string) {
    const res = await fetch(
      `${API_BASE}/records/orders/${encodeURIComponent(orderId)}/accept`,
      { method: 'POST', credentials: 'include' },
    )
    return parseJson<OrderData>(res)
  }

  async function markOrderReady(orderId: string) {
    const res = await fetch(
      `${API_BASE}/records/orders/${encodeURIComponent(orderId)}/ready`,
      { method: 'POST', credentials: 'include' },
    )
    return parseJson<OrderData>(res)
  }

  async function sendMessage(toHandle: string, body: string) {
    const res = await fetch(`${API_BASE}/records/messages/send`, {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ to_handle: toHandle, body }),
    })
    return parseJson<MessageData>(res)
  }

  return {
    world,
    loadWorld,
    visit,
    spotPut,
    spotConsume,
    spotUse,
    loadCatalog,
    placeOrder,
    loadOrder,
    pickupOrder,
    loadMessages,
    markMessageRead,
    loadStacks,
    consumeStack,
    useStack,
    loadShopMe,
    applyShop,
    setShopOpen,
    createShopOffer,
    toggleShopOffer,
    loadMarket,
    loadSellingOrders,
    acceptOrder,
    markOrderReady,
    sendMessage,
  }
}
