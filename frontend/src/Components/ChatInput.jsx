import { useState } from "react";

export default function ChatInput({ onSend }) {
  const [text, setText] = useState("");

  return (
    <div className="flex gap-2 p-2">
      <input
        className="flex-1 bg-slate-800 text-white p-2 rounded"
        value={text}
        onChange={(e) => setText(e.target.value)}
      />
      <button
        className="bg-blue-600 px-4 rounded"
        onClick={() => {
          onSend(text);
          setText("");
        }}
      >
        Send
      </button>
    </div>
  );
}
