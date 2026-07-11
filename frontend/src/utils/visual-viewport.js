const HEIGHT_VARIABLE = '--visual-viewport-height'
const OFFSET_VARIABLE = '--visual-viewport-offset-top'

export function syncVisualViewport(viewport, style) {
  if (!viewport || !style) return
  style.setProperty(HEIGHT_VARIABLE, `${Math.round(viewport.height)}px`)
  style.setProperty(OFFSET_VARIABLE, `${Math.round(viewport.offsetTop || 0)}px`)
}

export function bindVisualViewport({
  viewport = globalThis.window?.visualViewport,
  style = globalThis.document?.documentElement?.style
} = {}) {
  if (!viewport || !style) return () => {}

  const sync = () => syncVisualViewport(viewport, style)
  sync()
  viewport.addEventListener('resize', sync)
  viewport.addEventListener('scroll', sync)

  return () => {
    viewport.removeEventListener('resize', sync)
    viewport.removeEventListener('scroll', sync)
    style.removeProperty(HEIGHT_VARIABLE)
    style.removeProperty(OFFSET_VARIABLE)
  }
}
