import { useEffect, useRef } from "react";

export default function useSocket(userId, onMessage) {
  const socketRef = useRef(null);
  const onMessageRef = useRef(onMessage);

  useEffect(() => {
    onMessageRef.current = onMessage;
  }, [onMessage]);

  useEffect(() => {
    if (!userId) return;

    const token = localStorage.getItem("token");
    if (!token) return;

    const socket = new WebSocket(`ws://127.0.0.1:8000/ws/${userId}?token=${encodeURIComponent(token)}`);
    socketRef.current = socket;

    socket.onopen = () => {
      socket.send(JSON.stringify({ action: "subscribe", channel: "analytics" }));
    };

    socket.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);
        onMessageRef.current?.(payload);
      } catch {
        onMessageRef.current?.(event.data);
      }
    };

    const heartbeat = setInterval(() => {
      if (socket.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify({ action: "ping" }));
      }
    }, 30000);

    return () => {
      clearInterval(heartbeat);
      socket.close();
    };
  }, [userId]);

  const sendMessage = (msg) => {
    if (socketRef.current?.readyState === WebSocket.OPEN) {
      socketRef.current.send(typeof msg === "string" ? msg : JSON.stringify(msg));
    }
  };

  return { sendMessage };
}
