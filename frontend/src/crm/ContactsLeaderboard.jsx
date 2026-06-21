export default function ContactsLeaderboard({ contacts, selectedId, onSelect }) {
  return (
    <div className="overflow-hidden rounded-lg border border-white/10">
      {contacts.map((contact) => (
        <button
          key={contact.id}
          onClick={() => onSelect?.(contact.id)}
          className={`grid w-full gap-3 border-b border-white/10 p-4 text-left last:border-0 md:grid-cols-[1fr_160px_120px] ${
            selectedId === contact.id ? "bg-cyan-400/10" : "hover:bg-white/[0.03]"
          }`}
        >
          <div className="min-w-0">
            <p className="truncate font-medium">{contact.name || contact.email}</p>
            <p className="truncate text-sm text-slate-400">{contact.email}</p>
          </div>
          <p className="text-sm text-slate-300">{contact.company || "Independent"}</p>
          <p className="text-sm text-slate-400">{contact.sentiment}</p>
        </button>
      ))}
    </div>
  );
}
