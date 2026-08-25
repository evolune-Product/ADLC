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

// ─── Workspace rooms ─────────────────────────────────────────────────────────
//
// Two rooms, two jobs. `channel:` carries the message firehose for the channel
// you are looking at and is joined and left as you navigate. `user:` carries
// sidebar-level facts — an unread bumped, a channel read on your phone — and is
// joined once for the session, because a DM that arrives while you are on the
// Runs page has to light up the sidebar there too.

export function joinChannelRoom(channelId: string): void {
  getSocket().emit('join_channel', { channel_id: channelId })
}

export function leaveChannelRoom(channelId: string): void {
  getSocket().emit('leave_channel', { channel_id: channelId })
}

export function joinUserRoom(userId: string): void {
  getSocket().emit('join_user', { user_id: userId })
}
