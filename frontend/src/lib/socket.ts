import { io, Socket } from 'socket.io-client'

let socket: Socket | null = null

export function getSocket(): Socket {
  if (!socket) {
    socket = io(import.meta.env.VITE_SOCKET_URL || 'http://localhost:8000', {
      auth: { token: localStorage.getItem('access_token') },
      autoConnect: false,
    })
  }
  return socket
}

export function connectSocket(): void {
  getSocket().connect()
}

export function disconnectSocket(): void {
  socket?.disconnect()
  socket = null
}

export function joinRunRoom(runId: string): void {
  getSocket().emit('join_run', { run_id: runId })
}

export function leaveRunRoom(runId: string): void {
  getSocket().emit('leave_run', { run_id: runId })
}
