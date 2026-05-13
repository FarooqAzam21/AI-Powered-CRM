export default function ChatWindow({ messages }) {
  return (
    <div className="flex-1 overflow-y-auto p-4">
      {messages.map((msg, i) => (
        <div key={i} className="mb-2 bg-slate-700 p-2 rounded">
          {msg}
        </div>
      ))}
    </div>
  );
}
