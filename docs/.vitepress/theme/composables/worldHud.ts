import { ref } from 'vue'

/** Shared HUD state so top-nav and city page stay in sync. */
export const hudActive = ref(false)
export const hudScope = ref<string | null>(null)
export const hudDay = ref<number | null>(null)
export const hudSpeedLabel = ref('')
export const hudFocusLabel = ref('')
export const hudTickNonce = ref(0)

export function setHudFromClock(opts: {
  active: boolean
  scope: string | null
  world_day: number
  speed_label: string
  focusLabel?: string
}) {
  hudActive.value = opts.active
  hudScope.value = opts.scope
  hudDay.value = opts.active ? opts.world_day : null
  hudSpeedLabel.value = opts.speed_label
  if (opts.focusLabel !== undefined) hudFocusLabel.value = opts.focusLabel
}

export function clearHud() {
  hudActive.value = false
  hudScope.value = null
  hudDay.value = null
  hudSpeedLabel.value = ''
  hudFocusLabel.value = ''
  hudTickNonce.value = 0
}
