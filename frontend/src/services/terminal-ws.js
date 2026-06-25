import api from './api'

export class TerminalWebSocket {
  constructor(sessionId, terminal, { onConnect, onDisconnect, onCwdChange, onStatusChange } = {}) {
    this.sessionId = sessionId
    this.terminal = terminal
    this.ws = null
    this.heartbeatInterval = null
    this.heartbeatTimeout = null
    this.reconnectTimer = null
    this.reconnectAttempts = 0
    this.inputDisposable = null
    this.connected = false
    this.intentionalClose = false
    this.serverClosed = false
    this.hadError = false
    this.onConnect = onConnect
    this.onDisconnect = onDisconnect
    this.onCwdChange = onCwdChange
    this.onStatusChange = onStatusChange
  }

  connect() {
    this.intentionalClose = false
    this.serverClosed = false
    this.hadError = false
    this.openSocket()
  }

  async openSocket() {
    let ticket
    try {
      const { data } = await api.post(`/api/sessions/${this.sessionId}/ws-ticket`)
      ticket = data.ticket
    } catch (error) {
      if (this.intentionalClose) return
      this.connected = false
      this.hadError = true
      this.terminal.write('\r\n\x1b[31m[Unable to authorize terminal connection]\x1b[0m\r\n')
      if (error?.response?.status !== 401 && error?.response?.status !== 403 && error?.response?.status !== 404) {
        this.scheduleReconnect()
      }
      return
    }

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const wsUrl = `${protocol}//${window.location.host}/api/terminal/ws/${this.sessionId}?ticket=${encodeURIComponent(ticket)}`
    const ws = new WebSocket(wsUrl)
    this.ws = ws
    ws.binaryType = 'arraybuffer'

    ws.onopen = () => {
      if (this.ws !== ws) return
      this.connected = true
      this.reconnectAttempts = 0
      this.clearReconnectTimer()
      this.startHeartbeat()
      this.setupTerminalInput()
      this.onConnect?.()
    }

    ws.onmessage = (event) => {
      if (this.ws !== ws) return
      const data = new Uint8Array(event.data)
      if (data.length < 5) return

      const opcode = data[0]
      const length = new DataView(data.buffer, 1, 4).getUint32(0, false)
      const payload = data.slice(5, 5 + length)

      switch (opcode) {
        case 0x02: // OUTPUT
          this.terminal.write(payload)
          break
        case 0x04: // HEARTBEAT response
          this.clearHeartbeatTimeout()
          break
        case 0x05: // CLOSE
          this.terminal.write('\r\n[Session closed by server]\r\n')
          this.connected = false
          this.serverClosed = true
          break
        case 0x06: // ERROR
          this.terminal.write(`\r\n\x1b[31m[Error] ${new TextDecoder().decode(payload)}\x1b[0m\r\n`)
          break
        case 0x07: // CWD
          this.onCwdChange?.(new TextDecoder().decode(payload))
          break
        case 0x08: // STATUS
          try {
            this.onStatusChange?.(JSON.parse(new TextDecoder().decode(payload)))
          } catch {
            // Ignore malformed status payloads.
          }
          break
      }
    }

    ws.onclose = () => {
      if (this.ws !== ws) return
      const wasConnected = this.connected
      this.connected = false
      this.stopHeartbeat()
      if (wasConnected) this.onDisconnect?.()
      if (!this.intentionalClose && !this.serverClosed) {
        this.scheduleReconnect()
      } else if (!this.intentionalClose && !this.hadError) {
        this.terminal.write('\r\n\x1b[90m[Connection closed]\x1b[0m\r\n')
      }
    }

    ws.onerror = () => {
      if (this.ws !== ws) return
      this.connected = false
      this.hadError = true
    }
  }

  setupTerminalInput() {
    if (this.inputDisposable) return
    this.inputDisposable = this.terminal.onData((data) => {
      this.sendPacket(0x01, new TextEncoder().encode(data))
    })
  }

  sendResize(cols, rows) {
    const payload = new Uint8Array(4)
    new DataView(payload.buffer).setUint16(0, cols, false)
    new DataView(payload.buffer).setUint16(2, rows, false)
    this.sendPacket(0x03, payload)
  }

  sendPacket(opcode, payload) {
    if (this.ws?.readyState !== WebSocket.OPEN) return
    const packet = new Uint8Array(5 + payload.length)
    packet[0] = opcode
    new DataView(packet.buffer, 1, 4).setUint32(0, payload.length, false)
    packet.set(payload, 5)
    this.ws.send(packet)
  }

  sendData(text) {
    this.sendPacket(0x01, new TextEncoder().encode(text))
  }

  startHeartbeat() {
    this.stopHeartbeat()
    this.heartbeatInterval = setInterval(() => {
      this.sendHeartbeat()
    }, 15000)
    this.sendHeartbeat()
  }

  sendHeartbeat() {
    if (this.ws?.readyState !== WebSocket.OPEN) return
    if (this.heartbeatTimeout) {
      this.reconnectNow()
      return
    }

    this.sendPacket(0x04, new Uint8Array(0))
    this.heartbeatTimeout = setTimeout(() => {
      this.heartbeatTimeout = null
      this.reconnectNow()
    }, 10000)
  }

  stopHeartbeat() {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval)
      this.heartbeatInterval = null
    }
    this.clearHeartbeatTimeout()
  }

  clearHeartbeatTimeout() {
    if (this.heartbeatTimeout) {
      clearTimeout(this.heartbeatTimeout)
      this.heartbeatTimeout = null
    }
  }

  clearReconnectTimer() {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer)
      this.reconnectTimer = null
    }
  }

  reconnectNow() {
    if (this.intentionalClose) return
    const wasConnected = this.connected
    this.connected = false
    this.stopHeartbeat()
    if (wasConnected) this.onDisconnect?.()
    try {
      this.ws?.close()
    } catch {}
    this.scheduleReconnect(0)
  }

  scheduleReconnect(delay = null) {
    if (this.intentionalClose || this.reconnectTimer) return

    const reconnectDelay = delay ?? Math.min(1000 * 2 ** this.reconnectAttempts, 10000)
    this.reconnectAttempts += 1

    if (this.reconnectAttempts === 1) {
      this.terminal.write('\r\n\x1b[90m[Connection lost, reconnecting...]\x1b[0m\r\n')
    }

    this.reconnectTimer = setTimeout(async () => {
      this.reconnectTimer = null
      if (this.intentionalClose) return

      try {
        await api.post(`/api/sessions/${this.sessionId}/reconnect`)
        this.connect()
      } catch (error) {
        if (error?.response?.status === 401 || error?.response?.status === 403 || error?.response?.status === 404) {
          this.terminal.write('\r\n\x1b[31m[Unable to reconnect terminal]\x1b[0m\r\n')
          return
        }
        this.scheduleReconnect()
      }
    }, reconnectDelay)
  }

  disconnect() {
    this.intentionalClose = true
    this.clearReconnectTimer()
    this.stopHeartbeat()
    if (this.inputDisposable) {
      this.inputDisposable.dispose()
      this.inputDisposable = null
    }
    this.sendPacket(0x05, new Uint8Array(0))
    this.ws?.close()
    this.connected = false
  }
}
