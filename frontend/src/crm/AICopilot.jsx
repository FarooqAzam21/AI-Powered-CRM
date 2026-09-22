import { useState, useEffect, useRef } from "react";
import {
  Bot,
  Sparkles,
  Send,
  Plus,
  Trash2,
  CheckCircle2,
  XCircle,
  AlertCircle,
  Layers,
  ArrowRight,
  Database,
  Cpu,
  RefreshCw,
  Clock,
  Check,
} from "lucide-react";
import {
  getCopilotStatus,
  listCopilotConversations,
  createCopilotConversation,
  getCopilotConversation,
  deleteCopilotConversation,
  sendCopilotMessage,
  confirmCopilotAction,
  rejectCopilotAction,
} from "./api";

export default function AICopilot() {
  const [conversations, setConversations] = useState([]);
  const [activeConvId, setActiveConvId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [inputText, setInputText] = useState("");
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState(null);
  const [actionLoadingId, setActionLoadingId] = useState(null);
  const messagesEndRef = useRef(null);

  const loadStatus = async () => {
    try {
      const data = await getCopilotStatus();
      setStatus(data);
    } catch (e) {
      console.warn("Could not load copilot status", e);
    }
  };

  const loadConversations = async () => {
    try {
      const list = await listCopilotConversations();
      setConversations(list);
      if (list.length > 0 && !activeConvId) {
        selectConversation(list[0].id);
      }
    } catch (e) {
      console.warn("Could not list conversations", e);
    }
  };

  const selectConversation = async (convId) => {
    setActiveConvId(convId);
    try {
      const data = await getCopilotConversation(convId);
      setMessages(data.messages || []);
    } catch (e) {
      console.warn("Could not load conversation messages", e);
    }
  };

  useEffect(() => {
    loadStatus();
    loadConversations();
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const handleNewChat = async () => {
    try {
      const conv = await createCopilotConversation({ title: "New Conversation" });
      setConversations([conv, ...conversations]);
      setActiveConvId(conv.id);
      setMessages([]);
    } catch (e) {
      console.error("Failed to create conversation", e);
    }
  };

  const handleDeleteConv = async (e, convId) => {
    e.stopPropagation();
    try {
      await deleteCopilotConversation(convId);
      const updated = conversations.filter((c) => c.id !== convId);
      setConversations(updated);
      if (activeConvId === convId) {
        if (updated.length > 0) {
          selectConversation(updated[0].id);
        } else {
          setActiveConvId(null);
          setMessages([]);
        }
      }
    } catch (e) {
      console.error("Failed to delete conversation", e);
    }
  };

  const handleSend = async (customPrompt) => {
    const textToSend = customPrompt || inputText;
    if (!textToSend.trim() || loading) return;

    setInputText("");
    const tempUserMsg = {
      id: Date.now(),
      role: "user",
      content: textToSend,
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, tempUserMsg]);
    setLoading(true);

    try {
      const res = await sendCopilotMessage({
        query: textToSend,
        conversation_id: activeConvId,
      });

      if (!activeConvId) {
        setActiveConvId(res.conversation_id);
        loadConversations();
      }

      const assistantMsg = {
        id: res.message_id || Date.now() + 1,
        role: "assistant",
        agent: res.agent,
        content: res.reply,
        proposed_actions: res.proposed_actions,
        action_status: res.proposed_actions?.length ? "proposed" : null,
        references: res.references,
        created_at: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, assistantMsg]);
      loadStatus();
    } catch (e) {
      const errDetail = e?.response?.data?.detail;
      const errMsg = typeof errDetail === "string" ? errDetail : "Failed to get response from AI Copilot.";
      setMessages((prev) => [
        ...prev,
        {
          id: Date.now() + 2,
          role: "assistant",
          content: `⚠️ ${errMsg}`,
          created_at: new Date().toISOString(),
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleConfirmAction = async (msgId, action) => {
    setActionLoadingId(msgId);
    try {
      await confirmCopilotAction({
        message_id: msgId,
        action_type: action.action_type,
        params: action.params || {},
      });
      setMessages((prev) =>
        prev.map((m) => (m.id === msgId ? { ...m, action_status: "executed" } : m))
      );
    } catch (e) {
      console.error("Failed to execute action", e);
    } finally {
      setActionLoadingId(null);
    }
  };

  const handleRejectAction = async (msgId) => {
    setActionLoadingId(msgId);
    try {
      await rejectCopilotAction({ message_id: msgId });
      setMessages((prev) =>
        prev.map((m) => (m.id === msgId ? { ...m, action_status: "rejected" } : m))
      );
    } catch (e) {
      console.error("Failed to reject action", e);
    } finally {
      setActionLoadingId(null);
    }
  };

  const quickStarters = [
    "Show my hot leads with high buying intent.",
    "Which deals need immediate attention this week?",
    "Summarize today's sales pipeline health and KPIs.",
    "Create a follow-up task for recent outreach.",
  ];

  return (
    <div className="flex flex-col h-[calc(100vh-5rem)] max-w-7xl mx-auto pb-4">
      {/* Top Bar: Model & Quota Telemetry */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-white/10 pb-4 mb-4">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-cyan-500/10 border border-cyan-500/30 text-cyan-400">
            <Bot size={22} />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-xl font-bold text-white">AI Copilot</h2>
              <span className="flex items-center gap-1.5 text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded-full bg-cyan-400/10 text-cyan-300 border border-cyan-400/20">
                <Cpu size={11} />
                {status?.model || "Ollama (qwen2.5:1.5b)"}
              </span>
            </div>
            <p className="text-xs text-slate-400">
              Workspace-isolated CRM Copilot with multi-agent orchestration & RAG memory
            </p>
          </div>
        </div>

        {/* Quota Indicator */}
        <div className="flex items-center gap-3 bg-slate-900/80 border border-white/10 px-3.5 py-1.5 rounded-xl text-xs">
          <div className="flex items-center gap-1.5 text-slate-400">
            <Database size={13} className="text-cyan-400" />
            <span>AI Quota:</span>
          </div>
          <span className="font-semibold text-white">
            {status?.quota?.used ?? 0} / {status?.quota?.unlimited ? "∞" : status?.quota?.limit ?? 100}
          </span>
          <span className="text-[10px] text-emerald-400 font-medium">Active Plan</span>
        </div>
      </div>

      {/* Main Copilot Shell: Split View (Conversations Sidebar + Chat Thread) */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 flex-1 min-h-0">
        {/* Left Sidebar: Conversations History */}
        <div className="hidden md:flex flex-col rounded-2xl border border-white/10 bg-[#0c111d] p-3 space-y-3">
          <button
            onClick={handleNewChat}
            className="flex items-center justify-center gap-2 w-full rounded-xl bg-cyan-400 py-2.5 text-xs font-bold text-slate-950 hover:bg-cyan-300 transition shadow"
          >
            <Plus size={15} />
            New Chat
          </button>

          <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider px-2 pt-2">
            History
          </div>

          <div className="flex-1 overflow-y-auto space-y-1 pr-1">
            {conversations.map((c) => (
              <div
                key={c.id}
                onClick={() => selectConversation(c.id)}
                className={`group flex items-center justify-between gap-2 px-3 py-2 rounded-xl text-xs cursor-pointer transition ${
                  activeConvId === c.id
                    ? "bg-cyan-400/15 border border-cyan-400/30 text-cyan-200 font-semibold"
                    : "text-slate-400 hover:bg-white/5 hover:text-white"
                }`}
              >
                <div className="truncate flex-1">{c.title || "Conversation"}</div>
                <button
                  onClick={(e) => handleDeleteConv(e, c.id)}
                  className="opacity-0 group-hover:opacity-100 hover:text-rose-400 transition"
                  title="Delete chat"
                >
                  <Trash2 size={13} />
                </button>
              </div>
            ))}
            {conversations.length === 0 && (
              <p className="text-xs text-slate-500 text-center py-6">No previous chats.</p>
            )}
          </div>
        </div>

        {/* Right Chat Panel */}
        <div className="md:col-span-3 flex flex-col rounded-2xl border border-white/10 bg-[#0c111d] p-4 min-h-0">
          {/* Messages Scroll Area */}
          <div className="flex-1 overflow-y-auto space-y-4 pr-2">
            {messages.length === 0 && (
              <div className="flex flex-col items-center justify-center h-full text-center p-6 space-y-6">
                <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-cyan-400/10 border border-cyan-400/30 text-cyan-400 shadow-xl">
                  <Sparkles size={32} />
                </div>
                <div className="max-w-md space-y-2">
                  <h3 className="text-lg font-bold text-white">How can I assist you today?</h3>
                  <p className="text-xs text-slate-400 leading-relaxed">
                    I have access to your workspace contacts, active pipeline deals, email communications, and knowledge base.
                  </p>
                </div>

                {/* Quick Prompts */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 w-full max-w-xl">
                  {quickStarters.map((prompt, i) => (
                    <button
                      key={i}
                      onClick={() => handleSend(prompt)}
                      className="text-left rounded-xl border border-white/10 bg-white/[0.03] p-3 text-xs text-slate-300 hover:border-cyan-400/40 hover:bg-cyan-400/5 transition flex items-center justify-between group"
                    >
                      <span className="line-clamp-2">{prompt}</span>
                      <ArrowRight size={13} className="text-cyan-400 opacity-0 group-hover:opacity-100 transition shrink-0 ml-2" />
                    </button>
                  ))}
                </div>
              </div>
            )}

            {messages.map((m) => {
              const isUser = m.role === "user";
              return (
                <div key={m.id} className={`flex gap-3 ${isUser ? "justify-end" : "justify-start"}`}>
                  {!isUser && (
                    <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-cyan-500/10 text-cyan-400 border border-cyan-500/30">
                      <Bot size={16} />
                    </div>
                  )}

                  <div className={`space-y-2 max-w-2xl ${isUser ? "items-end" : "items-start"}`}>
                    <div
                      className={`rounded-2xl px-4 py-3 text-xs leading-relaxed ${
                        isUser
                          ? "bg-cyan-500 text-slate-950 font-medium"
                          : "border border-white/10 bg-white/[0.03] text-slate-200"
                      }`}
                    >
                      <div className="whitespace-pre-wrap">{m.content}</div>

                      {/* Source References */}
                      {m.references && m.references.length > 0 && (
                        <div className="mt-3 pt-2.5 border-t border-white/10 flex flex-wrap items-center gap-1.5 text-[10px]">
                          <span className="text-slate-400 flex items-center gap-1">
                            <Layers size={11} />
                            Sources:
                          </span>
                          {m.references.map((ref, idx) => (
                            <span
                              key={idx}
                              className="px-2 py-0.5 rounded-md bg-white/5 border border-white/10 text-cyan-300"
                            >
                              {ref.type}: {ref.name || ref.title || ref.preview || "CRM data"}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>

                    {/* Proposed Action Confirmation Card */}
                    {m.proposed_actions && m.proposed_actions.length > 0 && (
                      <div className="w-full space-y-2 pt-1">
                        {m.proposed_actions.map((act, actIdx) => (
                          <div
                            key={actIdx}
                            className="rounded-xl border border-amber-500/30 bg-amber-500/10 p-3 text-xs space-y-2"
                          >
                            <div className="flex items-center justify-between">
                              <span className="font-bold text-amber-300 uppercase text-[10px] tracking-wider">
                                Proposed Action: {act.action_type.replace(/_/g, " ")}
                              </span>
                              {m.action_status === "executed" ? (
                                <span className="flex items-center gap-1 text-emerald-400 font-semibold text-[11px]">
                                  <CheckCircle2 size={13} /> Executed
                                </span>
                              ) : m.action_status === "rejected" ? (
                                <span className="flex items-center gap-1 text-slate-400 text-[11px]">
                                  <XCircle size={13} /> Dismissed
                                </span>
                              ) : null}
                            </div>
                            <p className="text-white font-medium">{act.summary}</p>

                            {m.action_status === "proposed" && (
                              <div className="flex items-center gap-2 pt-1">
                                <button
                                  onClick={() => handleConfirmAction(m.id, act)}
                                  disabled={actionLoadingId === m.id}
                                  className="flex items-center gap-1.5 rounded-lg bg-emerald-500 px-3 py-1.5 font-bold text-slate-950 hover:bg-emerald-400 transition"
                                >
                                  <Check size={13} />
                                  Confirm & Execute
                                </button>
                                <button
                                  onClick={() => handleRejectAction(m.id)}
                                  disabled={actionLoadingId === m.id}
                                  className="rounded-lg border border-white/10 px-3 py-1.5 text-slate-400 hover:bg-white/5 transition"
                                >
                                  Dismiss
                                </button>
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              );
            })}

            {loading && (
              <div className="flex items-center gap-3 text-cyan-400 text-xs py-2">
                <RefreshCw size={14} className="animate-spin" />
                <span>AI Copilot is analyzing CRM context...</span>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Prompt Input Form */}
          <div className="mt-4 pt-3 border-t border-white/10">
            <form
              onSubmit={(e) => {
                e.preventDefault();
                handleSend();
              }}
              className="flex items-center gap-2"
            >
              <input
                type="text"
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
                placeholder="Ask AI Copilot about leads, deals, tasks, or request an action..."
                disabled={loading}
                className="flex-1 rounded-xl border border-white/10 bg-black/30 px-4 py-3 text-xs text-white placeholder-slate-500 focus:border-cyan-400 focus:outline-none"
              />
              <button
                type="submit"
                disabled={loading || !inputText.trim()}
                className="flex items-center justify-center rounded-xl bg-cyan-400 p-3 text-slate-950 hover:bg-cyan-300 transition disabled:opacity-40"
              >
                <Send size={16} />
              </button>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
}
