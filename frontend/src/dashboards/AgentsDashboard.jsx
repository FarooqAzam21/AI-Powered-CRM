import { useState } from "react";
import Sidebar from "../Components/Sidebar";
import ChatWindow from "../Components/ChatWindow";
import ChatInput from "../Components/ChatInput";
import useSocket from "../hooks/useSocket";
import { useAuth } from "../context/AuthContext";

export default function AgentDashboard() {
  const { user } = useAuth();
  const [messages, setMessages] = useState([]);

  const { sendMessage } = useSocket(user.email, (msg) =>
    setMessages((prev) => [...prev, msg])
  );

  return (
    <div className="flex h-screen bg-gradient-to-br from-slate-900 to-slate-800">
      <Sidebar items={["Tickets", "Analytics"]} />
      <div className="flex flex-col flex-1">
        <ChatWindow messages={messages} />
        <ChatInput onSend={sendMessage} />
      </div>
    </div>
  );
}
