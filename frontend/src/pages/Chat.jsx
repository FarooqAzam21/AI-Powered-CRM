import { useState } from "react";
import Sidebar from "../Components/Sidebar";
import ChatWindow from "../Components/ChatWindow";
import ChatInput from "../Components/ChatInput";
import API from "../srevices/api";

export default function Chat() {
  const [messages, setMessages] = useState([]);
  const [activeTicket, setActiveTicket] = useState(null);

  const sendMessage = async (text) => {
    const res = await API.post("/user/message", {
      message: text,
      tone: "friendly",
    });

    setMessages((prev) => [
      ...prev,
      { role: "user", message: text },
      { role: "bot", message: res.data.bot_reply },
    ]);
  };

  return (
    <div className="flex h-screen bg-[#020617] text-white">
      <Sidebar onSelectTicket={setActiveTicket} />

      <div className="flex flex-col flex-1">
        <ChatWindow messages={messages} />
        <ChatInput onSend={sendMessage} />
      </div>
    </div>
  );
}
