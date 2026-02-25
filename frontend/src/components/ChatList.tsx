import Link from "next/link";
import { Chat } from "@/types";
import { MessageSquare } from "lucide-react";

function formatRelativeTime(dateStr?: string): string {
  if (!dateStr) return "";
  const now = Date.now();
  const then = new Date(dateStr).getTime();
  const diffSec = Math.floor((now - then) / 1000);

  if (diffSec < 60) return "just now";
  if (diffSec < 3600) return `${Math.floor(diffSec / 60)}m ago`;
  if (diffSec < 86400) return `${Math.floor(diffSec / 3600)}h ago`;
  if (diffSec < 604800) return `${Math.floor(diffSec / 86400)}d ago`;
  return new Date(dateStr).toLocaleDateString();
}

interface Props {
  chats: Chat[];
}

export default function ChatList({ chats }: Props) {
  if (chats.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
        <MessageSquare className="mb-3 h-10 w-10 opacity-40" />
        <p>No conversations yet.</p>
        <p className="text-sm">Start a new chat to begin!</p>
      </div>
    );
  }

  return (
    <ul className="divide-y divide-white/5">
      {chats.map((chat) => (
        <li key={chat.chatId}>
          <Link
            href={`/chat/${chat.chatId}`}
            className="flex items-center justify-between px-5 py-4 transition-colors hover:bg-white/5"
          >
            <div className="min-w-0 flex-1">
              <p className="font-medium text-foreground">
                {chat.otherUsername}
              </p>
              {chat.lastMessagePreview && (
                <p className="truncate text-sm text-muted-foreground">
                  {chat.lastMessagePreview}
                </p>
              )}
            </div>
            {chat.updatedAt && (
              <span className="ml-4 shrink-0 text-xs text-muted-foreground">
                {formatRelativeTime(chat.updatedAt)}
              </span>
            )}
          </Link>
        </li>
      ))}
    </ul>
  );
}
