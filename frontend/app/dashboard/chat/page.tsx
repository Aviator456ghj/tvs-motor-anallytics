"use client";

import { useEffect, useState } from "react";
import { PageHeader, Spinner, EmptyState } from "@/components/ui";
import { api } from "@/lib/api";

interface ChatThread {
  id: string;
  customer_id: string;
  business_id: string;
  booking_id: string | null;
  created_at: string;
}

interface ChatMessage {
  id: string;
  thread_id: string;
  sender_id: string;
  message: string;
  created_at: string;
}

export default function CustomerChatPage() {
  const [threads, setThreads] = useState<ChatThread[] | null>(null);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [draft, setDraft] = useState("");

  useEffect(() => {
    api.get<ChatThread[]>("/chat/threads").then((t) => {
      setThreads(t);
      if (t.length > 0) setActiveId(t[0].id);
    });
  }, []);

  useEffect(() => {
    if (!activeId) return;
    api.get<ChatMessage[]>(`/chat/threads/${activeId}/messages`).then(setMessages);
  }, [activeId]);

  async function send() {
    if (!draft.trim() || !activeId) return;
    await api.post(`/chat/threads/${activeId}/messages?message=${encodeURIComponent(draft)}`);
    setDraft("");
    const updated = await api.get<ChatMessage[]>(`/chat/threads/${activeId}/messages`);
    setMessages(updated);
  }

  if (!threads) return <Spinner />;

  return (
    <div>
      <PageHeader title="Chat" description="Messages with your service providers." />
      {threads.length === 0 ? (
        <EmptyState message="No conversations yet. Message a provider from their profile page." />
      ) : (
        <div className="card grid grid-cols-1 gap-0 overflow-hidden p-0 sm:grid-cols-[220px_1fr]">
          <div className="border-b border-slate-200 sm:border-b-0 sm:border-r">
            {threads.map((t) => (
              <button
                key={t.id}
                onClick={() => setActiveId(t.id)}
                className={`block w-full px-4 py-3 text-left text-sm ${activeId === t.id ? "bg-brand-50 text-brand-700" : "hover:bg-slate-50"}`}
              >
                Thread #{t.id.slice(0, 8)}
              </button>
            ))}
          </div>
          <div className="flex h-96 flex-col">
            <div className="flex-1 space-y-2 overflow-y-auto p-4">
              {messages.map((m) => (
                <div key={m.id} className="rounded-lg bg-slate-100 px-3 py-2 text-sm text-slate-700">
                  {m.message}
                </div>
              ))}
            </div>
            <div className="flex gap-2 border-t border-slate-200 p-3">
              <input className="input flex-1" value={draft} onChange={(e) => setDraft(e.target.value)} placeholder="Type a message…" />
              <button className="btn-primary" onClick={send}>
                Send
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
