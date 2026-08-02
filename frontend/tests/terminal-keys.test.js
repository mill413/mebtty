import assert from 'node:assert/strict'
import test from 'node:test'

import {
  applyTerminalModifiers,
  shouldPreventTerminalBrowserShortcut,
  terminalKeySequence
} from '../src/utils/terminal-keys.js'

test('generates standard terminal navigation sequences', () => {
  assert.equal(terminalKeySequence('arrowLeft'), '\x1b[D')
  assert.equal(terminalKeySequence('arrowDown'), '\x1b[B')
  assert.equal(terminalKeySequence('arrowUp'), '\x1b[A')
  assert.equal(terminalKeySequence('arrowRight'), '\x1b[C')
  assert.equal(terminalKeySequence('home'), '\x1b[H')
  assert.equal(terminalKeySequence('end'), '\x1b[F')
  assert.equal(terminalKeySequence('pageUp'), '\x1b[5~')
  assert.equal(terminalKeySequence('pageDown'), '\x1b[6~')
})

test('adds terminal modifier parameters to navigation keys', () => {
  assert.equal(terminalKeySequence('arrowUp', { shift: true }), '\x1b[1;2A')
  assert.equal(terminalKeySequence('arrowLeft', { alt: true }), '\x1b[1;3D')
  assert.equal(terminalKeySequence('arrowRight', { ctrl: true }), '\x1b[1;5C')
  assert.equal(
    terminalKeySequence('pageDown', { ctrl: true, alt: true, shift: true }),
    '\x1b[6;8~'
  )
})

test('supports escape, tab, and shifted tab', () => {
  assert.equal(terminalKeySequence('escape'), '\x1b')
  assert.equal(terminalKeySequence('tab'), '\t')
  assert.equal(terminalKeySequence('tab', { shift: true }), '\x1b[Z')
})

test('applies one-shot modifiers to typed characters', () => {
  assert.equal(applyTerminalModifiers('c', { ctrl: true }), '\x03')
  assert.equal(applyTerminalModifiers('d', { ctrl: true }), '\x04')
  assert.equal(applyTerminalModifiers('a', { shift: true }), 'A')
  assert.equal(applyTerminalModifiers('1', { shift: true }), '!')
  assert.equal(applyTerminalModifiers('x', { alt: true }), '\x1bx')
  assert.equal(applyTerminalModifiers('c', { ctrl: true, alt: true }), '\x1b\x03')
})

test('does not alter pasted or composed multi-character input', () => {
  assert.equal(applyTerminalModifiers('hello', { ctrl: true, shift: true }), 'hello')
})

test('prevents browser shortcuts for terminal Alt navigation', () => {
  assert.equal(shouldPreventTerminalBrowserShortcut({ key: 'Alt', altKey: true }), true)
  assert.equal(shouldPreventTerminalBrowserShortcut({ key: 'ArrowUp', altKey: true }), true)
  assert.equal(shouldPreventTerminalBrowserShortcut({ key: 'ArrowLeft', altKey: true }), true)
  assert.equal(shouldPreventTerminalBrowserShortcut({ key: 'ArrowUp', altKey: false }), false)
  assert.equal(shouldPreventTerminalBrowserShortcut({ key: 'a', altKey: true }), false)
})
