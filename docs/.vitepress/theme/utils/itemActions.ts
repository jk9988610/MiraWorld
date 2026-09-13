/** 按 items.json tags 决定可用操作（对齐 36） */

export interface ItemActions {
  consume: boolean
  use: boolean
  put: boolean
}

export function actionsForTags(tags: string[] = []): ItemActions {
  const hasFood = tags.includes('food')
  const consumable = tags.includes('consumable')
  const tool = tags.includes('tool')
  return {
    consume: hasFood && consumable,
    use: tool,
    put: true,
  }
}
