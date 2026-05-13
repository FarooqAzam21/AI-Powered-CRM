import { useEffect, useRef } from "react";

export default function useSocket(userId, onMessage) {
  const socketRef = useRef(null);

  useEffect(() => {
    if (!userId) return;

    socketRef.current = new WebSocket(
      `ws://127.0.0.1:8000/ws/${userId}`
    );

    socketRef.current.onmessage = (event) => {
      onMessage(event.data);
    };

    return () => socketRef.current.close();
  }, [userId]);

  const sendMessage = (msg) => {
    socketRef.current?.send(msg);
  };

  return { sendMessage };
}
