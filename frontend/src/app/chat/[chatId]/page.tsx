"use client";

import { useParams } from "next/navigation";

export default function ChatConversationPage() {
  const { chatId } = useParams<{ chatId: string }>();

  return (
    <main className="flex h-screen flex-col">
      <header className="border-b p-4">
        <h1 className="text-lg font-semibold">Chat {chatId}</h1>
      </header>
      <div className="flex-1 overflow-y-auto p-4">
        {/* TODO: Message list in Phase 3 */}
      </div>
      <div className="border-t p-4">
        {/* TODO: Chat input in Phase 3 */}
      </div>
    </main>
  );
}
