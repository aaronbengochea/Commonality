import { Message } from "@/types";

interface Props {
  message: Message;
  isOwn: boolean;
}

export default function ChatMessage({ message, isOwn }: Props) {
  return (
    <div className={`flex ${isOwn ? "justify-end" : "justify-start"} mb-2`}>
      <div
        className={`max-w-xs rounded-lg px-4 py-2 ${
          isOwn ? "bg-blue-600 text-white" : "bg-gray-200 text-gray-900"
        }`}
      >
        <p>{message.text}</p>
      </div>
    </div>
  );
}
