"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/hooks/useAuth";
import { useWebSocket } from "@/hooks/useWebSocket";
import { api } from "@/lib/api";
import { Message, Chat } from "@/types";
import ChatMessage from "@/components/ChatMessage";
import ChatInput from "@/components/ChatInput";
import Navbar from "@/components/Navbar";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { ArrowLeft, Phone } from "lucide-react";

export default function ChatConversationPage() {
  const { chatId } = useParams<{ chatId: string }>();
  const { user, loading, logout } = useAuth("/login");
  const [messages, setMessages] = useState<Message[]>([]);
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState("");
  const [otherName, setOtherName] = useState("");
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

  // Fetch other user's name from chat list
  useEffect(() => {
    if (!user || !chatId) return;
    api
      .get("/api/chats")
      .then((data) => {
        const chat = data.find(
          (c: Record<string, string>) => c.chat_id === chatId
        );
        if (chat) setOtherName(chat.other_username);
      })
      .catch(() => {});
  }, [user, chatId]);

  // Load message history
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

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <p className="text-muted-foreground">Loading...</p>
      </div>
    );
  }
  if (!user) return null;

  return (
    <div className="flex h-screen flex-col">
      <Navbar
        username={user.username}
        firstName={user.firstName}
        onLogout={logout}
      />

      {/* Chat sub-header */}
      <div className="flex items-center justify-between border-b border-white/5 px-4 py-3">
        <Link
          href="/chat"
          className="flex items-center gap-1 text-sm text-muted-foreground transition-colors hover:text-foreground"
        >
          <ArrowLeft className="h-4 w-4" />
          Back
        </Link>
        <h2 className="font-semibold">
          {otherName || "Chat"}
        </h2>
        <Link href={`/voice/${chatId}`}>
          <Button variant="outline" size="sm">
            <Phone className="mr-1.5 h-4 w-4" />
            Call
          </Button>
        </Link>
      </div>

      {/* Messages area */}
      <div className="flex-1 overflow-y-auto p-4">
        {error && (
          <Alert variant="destructive" className="mb-4">{error}</Alert>
        )}
        {nextCursor && (
          <button
            onClick={loadMore}
            disabled={loadingMore}
            className="mb-4 w-full text-center text-sm text-muted-foreground transition-colors hover:text-foreground disabled:opacity-50"
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

      {/* Input area */}
      <div className="border-t border-white/5 p-4">
        <ChatInput onSend={handleSend} />
      </div>
    </div>
  );
}
