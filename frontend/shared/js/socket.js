// ResQRoute Real-Time WebSocket Manager
class ResQSocket {
  constructor() {
    this.socket = null;
    this.listeners = new Map();
    this.reconnectInterval = 2500;
    this.isConnected = false;
    this.connect();
  }

  connect() {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const host = window.location.host || "127.0.0.1:8000";
    const url = `${protocol}//${host}/ws`;

    console.log(`[ResQSocket] Connecting to ${url}...`);
    try {
      this.socket = new WebSocket(url);

      this.socket.onopen = () => {
        console.log("[ResQSocket] Connected successfully.");
        this.isConnected = true;
        this.emitStatus(true);
      };

      this.socket.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);
          this.handleMessage(msg);
        } catch (e) {
          console.error("[ResQSocket] Error parsing message:", e);
        }
      };

      this.socket.onclose = () => {
        console.warn("[ResQSocket] Connection closed. Reconnecting in 2.5s...");
        this.isConnected = false;
        this.emitStatus(false);
        setTimeout(() => this.connect(), this.reconnectInterval);
      };

      this.socket.onerror = (err) => {
        console.error("[ResQSocket] Socket error:", err);
      };
    } catch (e) {
      console.error("[ResQSocket] Connection failed:", e);
      setTimeout(() => this.connect(), this.reconnectInterval);
    }
  }

  on(eventType, callback) {
    if (!this.listeners.has(eventType)) {
      this.listeners.set(eventType, []);
    }
    this.listeners.get(eventType).push(callback);
  }

  handleMessage(msg) {
    const type = msg.type;
    if (this.listeners.has(type)) {
      this.listeners.get(type).forEach((cb) => cb(msg));
    }
    // Global listener
    if (this.listeners.has("*")) {
      this.listeners.get("*").forEach((cb) => cb(msg));
    }
  }

  send(data) {
    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
      this.socket.send(typeof data === "string" ? data : JSON.stringify(data));
    }
  }

  emitStatus(connected) {
    const el = document.getElementById("connection-status-badge");
    if (el) {
      el.innerHTML = connected
        ? `<span class="inline-block w-2.5 h-2.5 rounded-full bg-emerald-500 mr-2 animate-pulse"></span><span class="text-emerald-400 text-xs font-semibold">LIVE CONNECTED</span>`
        : `<span class="inline-block w-2.5 h-2.5 rounded-full bg-red-500 mr-2"></span><span class="text-red-400 text-xs font-semibold">RECONNECTING...</span>`;
    }
  }
}

window.resqSocket = new ResQSocket();
