const PRIMARY_SHADE_STEPS = [50, 100, 200, 300, 400, 500, 600, 700, 800, 900, 950] as const

const SHADE_MIX: Record<(typeof PRIMARY_SHADE_STEPS)[number], { target: 'white' | 'black' | 'base'; amount: number }> =
  {
    50: { target: 'white', amount: 0.95 },
    100: { target: 'white', amount: 0.9 },
    200: { target: 'white', amount: 0.78 },
    300: { target: 'white', amount: 0.64 },
    400: { target: 'white', amount: 0.42 },
    500: { target: 'base', amount: 0 },
    600: { target: 'black', amount: 0.14 },
    700: { target: 'black', amount: 0.26 },
    800: { target: 'black', amount: 0.4 },
    900: { target: 'black', amount: 0.55 },
    950: { target: 'black', amount: 0.72 }
  }

type Rgb = { r: number; g: number; b: number }

function clampByte(value: number): number {
  return Math.max(0, Math.min(255, Math.round(value)))
}

function hexToRgb(hex: string): Rgb {
  const normalized = hex.replace('#', '')
  return {
    r: Number.parseInt(normalized.slice(0, 2), 16),
    g: Number.parseInt(normalized.slice(2, 4), 16),
    b: Number.parseInt(normalized.slice(4, 6), 16)
  }
}

function rgbToHex({ r, g, b }: Rgb): string {
  return `#${[r, g, b].map((v) => clampByte(v).toString(16).padStart(2, '0')).join('')}`
}

function mixColors(base: Rgb, target: Rgb, amount: number): Rgb {
  const ratio = Math.max(0, Math.min(1, amount))
  return {
    r: base.r * (1 - ratio) + target.r * ratio,
    g: base.g * (1 - ratio) + target.g * ratio,
    b: base.b * (1 - ratio) + target.b * ratio
  }
}

function getDocumentRoot(): HTMLElement | null {
  if (!import.meta.client) return null
  return document.documentElement
}

export function normalizeHexColor(value: string | null | undefined): string | null {
  const raw = String(value ?? '').trim().toLowerCase()
  if (!raw) return null
  return /^#[0-9a-f]{6}$/.test(raw) ? raw : null
}

function buildPrimaryPalette(baseHex: string): Record<(typeof PRIMARY_SHADE_STEPS)[number], string> {
  const base = hexToRgb(baseHex)
  const white: Rgb = { r: 255, g: 255, b: 255 }
  const black: Rgb = { r: 0, g: 0, b: 0 }

  const palette = {} as Record<(typeof PRIMARY_SHADE_STEPS)[number], string>
  for (const step of PRIMARY_SHADE_STEPS) {
    const config = SHADE_MIX[step]
    if (config.target === 'base') {
      palette[step] = baseHex
      continue
    }
    const target = config.target === 'white' ? white : black
    palette[step] = rgbToHex(mixColors(base, target, config.amount))
  }
  return palette
}

function clearPrimaryPalette(root: HTMLElement) {
  for (const step of PRIMARY_SHADE_STEPS) {
    root.style.removeProperty(`--color-primary-${step}`)
    root.style.removeProperty(`--ui-color-primary-${step}`)
    root.style.removeProperty(`--ui-primary-${step}`)
  }
  root.style.removeProperty('--ui-primary')
  root.removeAttribute('data-company-primary-color')
}

export function applyCompanyPrimaryColor(color: string | null | undefined): string | null {
  const root = getDocumentRoot()
  if (!root) return null

  const normalized = normalizeHexColor(color)
  if (!normalized) {
    clearPrimaryPalette(root)
    return null
  }

  const palette = buildPrimaryPalette(normalized)
  for (const step of PRIMARY_SHADE_STEPS) {
    const value = palette[step]
    root.style.setProperty(`--color-primary-${step}`, value)
    root.style.setProperty(`--ui-color-primary-${step}`, value)
    root.style.setProperty(`--ui-primary-${step}`, value)
  }
  root.style.setProperty('--ui-primary', normalized)
  root.setAttribute('data-company-primary-color', normalized)
  return normalized
}

export function resetCompanyPrimaryColor() {
  applyCompanyPrimaryColor(null)
}

export function resolveCompanyPrimaryColorFromMe(mePayload: unknown): string | null {
  const payload = mePayload as { memberships?: Array<{ status?: string; company?: { primary_color?: string } }> } | null
  const memberships = Array.isArray(payload?.memberships) ? payload?.memberships : []
  if (!memberships.length) return null

  const approved = memberships.find((m) => m?.status === 'approved') || memberships[0]
  return normalizeHexColor(approved?.company?.primary_color ?? null)
}
