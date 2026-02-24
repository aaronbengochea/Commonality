import { Chat } from "@/types";

interface Props {
  chats: Chat[];
}

export default function ChatList({ chats }: Props) {
  if (chats.length === 0) {
    return <p className="text-gray-500">No conversations yet.</p>;
  }

  return (
    <ul className="divide-y divide-gray-200">
      {chats.map((chat) => (
        <li key={chat.chatId}>
          <a
            href={`/chat/${chat.chatId}`}
            className="block px-4 py-3 hover:bg-gray-50"
          >
            <p className="font-medium">{chat.otherUsername}</p>
            {chat.lastMessagePreview && (
              <p className="truncate text-sm text-gray-500">
                {chat.lastMessagePreview}
              </p>
            )}
          </a>
        </li>
      ))}
    </ul>
  );
}
