"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/hooks/useAuth";
import { api } from "@/lib/api";
import { Chat } from "@/types";
import ChatList from "@/components/ChatList";
import Navbar from "@/components/Navbar";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Alert } from "@/components/ui/alert";
import { Plus, X } from "lucide-react";

export default function ChatListPage() {
  const { user, loading, logout } = useAuth("/");
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

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <p className="text-muted-foreground">Loading...</p>
      </div>
    );
  }
  if (!user) return null;

  return (
    <div className="flex min-h-screen flex-col">
      <Navbar
        username={user.username}
        firstName={user.firstName}
        onLogout={logout}
      />

      <main className="mx-auto w-full max-w-2xl flex-1 p-4">
        <div className="mb-4 flex items-center justify-between">
          <h1 className="text-2xl font-bold">Chats</h1>
          <Button
            onClick={() => setShowNewChat(!showNewChat)}
            size="sm"
          >
            {showNewChat ? (
              <X className="mr-1.5 h-4 w-4" />
            ) : (
              <Plus className="mr-1.5 h-4 w-4" />
            )}
            {showNewChat ? "Cancel" : "New Chat"}
          </Button>
        </div>

        {showNewChat && (
          <Card className="mb-4">
            <form onSubmit={handleNewChat} className="space-y-3">
              <p className="text-sm text-muted-foreground">
                Start a conversation with another user
              </p>
              {error && <Alert variant="destructive">{error}</Alert>}
              <div className="flex gap-2">
                <Input
                  type="text"
                  placeholder="Enter username..."
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  required
                  className="py-2"
                />
                <Button type="submit" disabled={creating} size="sm" className="px-6">
                  {creating ? "Creating..." : "Start"}
                </Button>
              </div>
            </form>
          </Card>
        )}

        {!showNewChat && error && (
          <Alert variant="destructive" className="mb-4">{error}</Alert>
        )}

        <Card className="p-0 overflow-hidden">
          <ChatList chats={chats} />
        </Card>
      </main>
    </div>
  );
}
