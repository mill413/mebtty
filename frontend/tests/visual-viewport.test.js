import assert from 'node:assert/strict'
import test from 'node:test'

import { bindVisualViewport } from '../src/utils/visual-viewport.js'

class TestStyle {
  constructor() {
    this.values = new Map()
  }

  setProperty(name, value) {
    this.values.set(name, value)
  }

  removeProperty(name) {
    this.values.delete(name)
  }

  get(name) {
    return this.values.get(name)
  }
}

test('tracks visual viewport changes caused by an on-screen keyboard', () => {
  const viewport = new EventTarget()
  viewport.height = 1024
  viewport.offsetTop = 0
  const style = new TestStyle()

  const cleanup = bindVisualViewport({ viewport, style })
  assert.equal(style.get('--visual-viewport-height'), '1024px')
  assert.equal(style.get('--visual-viewport-offset-top'), '0px')

  viewport.height = 612
  viewport.offsetTop = 18
  viewport.dispatchEvent(new Event('resize'))
  assert.equal(style.get('--visual-viewport-height'), '612px')
  assert.equal(style.get('--visual-viewport-offset-top'), '18px')

  cleanup()
  assert.equal(style.get('--visual-viewport-height'), undefined)
  assert.equal(style.get('--visual-viewport-offset-top'), undefined)
})
