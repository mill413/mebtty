import assert from 'node:assert/strict'
import test from 'node:test'

import { DEFAULT_TERMINAL_LINE_HEIGHT } from '../src/utils/terminal-options.js'

test('uses flush terminal rows for block and Powerline glyphs', () => {
  assert.equal(DEFAULT_TERMINAL_LINE_HEIGHT, 1)
})
