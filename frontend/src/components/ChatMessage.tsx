import { Message } from "@/types";

interface Props {
  message: Message;
  isOwn: boolean;
}

function formatTime(timestamp: string): string {
  return new Date(timestamp).toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
  });
}

export default function ChatMessage({ message, isOwn }: Props) {
  return (
    <div className={`flex ${isOwn ? "justify-end" : "justify-start"} mb-3`}>
      <div className="flex max-w-xs flex-col">
        <div
          className={`rounded-2xl px-4 py-2.5 ${
            isOwn
              ? "bg-gradient-to-r from-indigo-500 to-pink-600 text-white"
              : "glass-bubble text-foreground"
          }`}
        >
          <p>{message.text}</p>
        </div>
        <span
          className={`mt-1 text-[10px] text-muted-foreground ${
            isOwn ? "text-right" : "text-left"
          }`}
        >
          {formatTime(message.timestamp)}
        </span>
      </div>
    </div>
  );
}
