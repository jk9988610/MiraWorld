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

  return { world, loadWorld, visit }
}
