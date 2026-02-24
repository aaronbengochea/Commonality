"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { useParams } from "next/navigation";
import { useAuth } from "@/hooks/useAuth";
import { useWebSocket } from "@/hooks/useWebSocket";
import { api } from "@/lib/api";
import { Message } from "@/types";
import ChatMessage from "@/components/ChatMessage";
import ChatInput from "@/components/ChatInput";

export default function ChatConversationPage() {
  const { chatId } = useParams<{ chatId: string }>();
  const { user, loading } = useAuth("/");
  const [messages, setMessages] = useState<Message[]>([]);
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);

  // Handle incoming WebSocket messages
  const handleWsMessage = useCallback(
    (raw: string) => {
      try {
        const data = JSON.parse(raw);
        if (data.type === "message" && data.chat_id === chatId) {
          const msg: Message = {
            messageId: data.message.message_id,
            text: data.message.text,
            fromUserId: data.message.from_user_id,
            language: data.message.language,
            timestamp: data.message.timestamp,
          };
          setMessages((prev) => [...prev, msg]);
        }
      } catch {
        // ignore malformed messages
      }
    },
    [chatId]
  );

  const { send } = useWebSocket(handleWsMessage);

  // Load message history — re-runs when chatId changes
  useEffect(() => {
    if (!user || !chatId) return;

    setMessages([]);
    setNextCursor(null);
    setError("");

    api
      .get(`/api/chats/${chatId}/messages?limit=50`)
      .then((data) => {
        const msgs: Message[] = data.messages.map(
          (m: Record<string, string>) => ({
            messageId: m.message_id,
            text: m.text,
            fromUserId: m.from_user_id,
            language: m.language,
            timestamp: m.timestamp,
          })
        );
        // API returns newest-first, reverse for display
        setMessages(msgs.reverse());
        setNextCursor(data.next_cursor);
      })
      .catch((err) => {
        setError(err instanceof Error ? err.message : "Failed to load messages");
      });
  }, [user, chatId]);

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function loadMore() {
    if (!nextCursor || loadingMore) return;
    setLoadingMore(true);
    try {
      const data = await api.get(
        `/api/chats/${chatId}/messages?cursor=${encodeURIComponent(nextCursor)}&limit=50`
      );
      const older: Message[] = data.messages.map(
        (m: Record<string, string>) => ({
          messageId: m.message_id,
          text: m.text,
          fromUserId: m.from_user_id,
          language: m.language,
          timestamp: m.timestamp,
        })
      );
      setMessages((prev) => [...older.reverse(), ...prev]);
      setNextCursor(data.next_cursor);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load messages");
    } finally {
      setLoadingMore(false);
    }
  }

  function handleSend(text: string) {
    send(JSON.stringify({ chat_id: chatId, text }));
  }

  if (loading) return <div className="p-8 text-center text-gray-500">Loading...</div>;
  if (!user) return null;

  return (
    <main className="flex h-screen flex-col">
      <header className="flex items-center justify-between border-b p-4">
        <a href="/chat" className="text-blue-600 hover:underline">
          &larr; Back
        </a>
        <h1 className="text-lg font-semibold">Chat</h1>
        <div className="w-16" />
      </header>
      <div className="flex-1 overflow-y-auto p-4">
        {error && (
          <div className="mb-4 rounded-lg bg-red-50 p-3 text-sm text-red-600">{error}</div>
        )}
        {nextCursor && (
          <button
            onClick={loadMore}
            disabled={loadingMore}
            className="mb-4 w-full text-center text-sm text-blue-600 hover:underline disabled:opacity-50"
          >
            {loadingMore ? "Loading..." : "Load older messages"}
          </button>
        )}
        {messages.map((msg) => (
          <ChatMessage
            key={msg.messageId}
            message={msg}
            isOwn={msg.fromUserId === user.userId}
          />
        ))}
        <div ref={bottomRef} />
      </div>
      <div className="border-t p-4">
        <ChatInput onSend={handleSend} />
      </div>
    </main>
  );
}
