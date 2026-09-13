import { ref } from 'vue'

const API_BASE = '/miraworld/api'

export interface Npc {
  id: string
  display: string
  city: string
  role?: string
  greeting?: string
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
  body: string
  ref_type?: string | null
  ref_id?: string | null
  read_at?: string | null
  created_at: string
}

export interface StackData {
  item_id: string
  display: string
  qty: number
  tags?: string[]
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
    return parseJson<{ first_visit: boolean; city: string; spot_id?: string }>(res)
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

  return {
    world,
    loadWorld,
    visit,
    loadCatalog,
    placeOrder,
    loadOrder,
    pickupOrder,
    loadMessages,
    markMessageRead,
    loadStacks,
  }
}
