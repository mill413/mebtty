const SHIFTED_ASCII = {
  '`': '~',
  '1': '!',
  '2': '@',
  '3': '#',
  '4': '$',
  '5': '%',
  '6': '^',
  '7': '&',
  '8': '*',
  '9': '(',
  '0': ')',
  '-': '_',
  '=': '+',
  '[': '{',
  ']': '}',
  '\\': '|',
  ';': ':',
  "'": '"',
  ',': '<',
  '.': '>',
  '/': '?'
}

const ALT_NAVIGATION_KEYS = new Set([
  'ArrowUp',
  'ArrowDown',
  'ArrowLeft',
  'ArrowRight',
  'Home',
  'End',
  'PageUp',
  'PageDown'
])

export function shouldPreventTerminalBrowserShortcut(event = {}) {
  return event.key === 'Alt' || (event.altKey && ALT_NAVIGATION_KEYS.has(event.key))
}

function modifierParameter({ ctrl = false, alt = false, shift = false } = {}) {
  return 1 + (shift ? 1 : 0) + (alt ? 2 : 0) + (ctrl ? 4 : 0)
}

function applyCtrl(character) {
  if (character === '?' || character === '\x7f') return '\x7f'

  const upper = character.toUpperCase()
  const code = upper.charCodeAt(0)
  if (code >= 64 && code <= 95) {
    return String.fromCharCode(code - 64)
  }
  if (character === ' ') return '\x00'
  return character
}

export function applyTerminalModifiers(text, modifiers = {}) {
  if (!text) return text

  let result = text
  if ([...result].length === 1) {
    if (modifiers.shift) {
      result = SHIFTED_ASCII[result] || result.toUpperCase()
    }
    if (modifiers.ctrl) {
      result = applyCtrl(result)
    }
  }
  if (modifiers.alt) {
    result = `\x1b${result}`
  }
  return result
}

export function terminalKeySequence(key, modifiers = {}) {
  const modifier = modifierParameter(modifiers)
  const modified = modifier !== 1

  const cursorFinal = {
    arrowUp: 'A',
    arrowDown: 'B',
    arrowRight: 'C',
    arrowLeft: 'D',
    home: 'H',
    end: 'F'
  }[key]

  if (cursorFinal) {
    return modified ? `\x1b[1;${modifier}${cursorFinal}` : `\x1b[${cursorFinal}`
  }

  if (key === 'pageUp' || key === 'pageDown') {
    const number = key === 'pageUp' ? 5 : 6
    return modified ? `\x1b[${number};${modifier}~` : `\x1b[${number}~`
  }

  if (key === 'tab') {
    if (modifiers.shift && !modifiers.ctrl && !modifiers.alt) return '\x1b[Z'
    return applyTerminalModifiers('\t', modifiers)
  }

  if (key === 'escape') return '\x1b'
  return ''
}
