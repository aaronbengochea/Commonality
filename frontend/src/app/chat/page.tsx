"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/hooks/useAuth";
import { api } from "@/lib/api";
import { Chat } from "@/types";
import ChatList from "@/components/ChatList";

export default function ChatListPage() {
  const { user, loading } = useAuth("/");
  const router = useRouter();
  const [chats, setChats] = useState<Chat[]>([]);
  const [showNewChat, setShowNewChat] = useState(false);
  const [username, setUsername] = useState("");
  const [error, setError] = useState("");
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    if (!user) return;
    api
      .get("/api/chats")
      .then((data) => {
        setChats(
          data.map((c: Record<string, string>) => ({
            chatId: c.chat_id,
            otherUsername: c.other_username,
            otherUserId: c.other_user_id,
            lastMessagePreview: c.last_message_preview,
            updatedAt: c.updated_at,
          }))
        );
      })
      .catch((err) => {
        setError(err instanceof Error ? err.message : "Failed to load chats");
      });
  }, [user]);

  async function handleNewChat(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setCreating(true);
    try {
      const data = await api.post("/api/chats", { username });
      router.push(`/chat/${data.chat_id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create chat");
    } finally {
      setCreating(false);
    }
  }

  if (loading) return <div className="p-8 text-center text-gray-500">Loading...</div>;
  if (!user) return null;

  return (
    <main className="mx-auto max-w-2xl p-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Chats</h1>
        <button
          onClick={() => setShowNewChat(!showNewChat)}
          className="rounded-lg bg-blue-600 px-4 py-2 text-sm text-white hover:bg-blue-700"
        >
          New Chat
        </button>
      </div>

      {showNewChat && (
        <form onSubmit={handleNewChat} className="mt-4 space-y-2">
          {error && (
            <div className="rounded-lg bg-red-50 p-2 text-sm text-red-600">{error}</div>
          )}
          <div className="flex gap-2">
            <input
              type="text"
              placeholder="Enter username..."
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
              className="flex-1 rounded-lg border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none"
            />
            <button
              type="submit"
              disabled={creating}
              className="rounded-lg bg-blue-600 px-4 py-2 text-sm text-white hover:bg-blue-700 disabled:opacity-50"
            >
              {creating ? "Creating..." : "Start"}
            </button>
          </div>
        </form>
      )}

      <div className="mt-4">
        <ChatList chats={chats} />
      </div>
    </main>
  );
}
