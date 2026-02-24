export interface User {
  userId: string;
  username: string;
  firstName: string;
  lastName: string;
  nativeLanguage: string;
}

export interface Chat {
  chatId: string;
  otherUsername: string;
  otherUserId: string;
  lastMessagePreview?: string;
  updatedAt?: string;
}

export interface Message {
  messageId: string;
  text: string;
  fromUserId: string;
  language: string;
  timestamp: string;
}
