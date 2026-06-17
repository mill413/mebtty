export function formatFileSize(size) {
  if (size === null || size === undefined || Number.isNaN(Number(size))) return ''

  const units = ['B', 'KiB', 'MiB', 'GiB', 'TiB']
  let value = Number(size)
  let unitIndex = 0

  while (value >= 1024 && unitIndex < units.length - 1) {
    value /= 1024
    unitIndex += 1
  }

  if (unitIndex === 0) return `${value} ${units[unitIndex]}`

  const rounded = value.toFixed(value >= 10 ? 1 : 2)
  return `${rounded.replace(/\.0+$/, '').replace(/(\.\d*[1-9])0+$/, '$1')} ${units[unitIndex]}`
}
