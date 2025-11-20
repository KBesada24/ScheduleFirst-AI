import { useState, useCallback } from "react";
import { sendChatMessage, ChatRequest, ChatResponse } from "@/lib/api-endpoints";

export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
  suggestedSchedule?: any;
}

export function useChatMessages(initialMessages: Message[] = []) {
  const [messages, setMessages] = useState<Message[]>(initialMessages);
  const [isProcessing, setIsProcessing] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  /**
   * Add a user message to chat history
   */
  const addUserMessage = useCallback((content: string): Message => {
    const message: Message = {
      id: `user-${Date.now()}`,
      role: "user",
      content,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, message]);
    return message;
  }, []);

  /**
   * Add an AI response to chat history
   */
  const addAIMessage = useCallback((response: ChatResponse): Message => {
    const message: Message = {
      id: `ai-${Date.now()}`,
      role: "assistant",
      content: response.message,
      timestamp: new Date(),
      suggestedSchedule: response.suggestedSchedule,
    };

    setMessages((prev) => [...prev, message]);
    return message;
  }, []);

  /**
   * Send a message and get AI response
   */
  const sendMessage = useCallback(
    async (content: string, context?: ChatRequest["context"]) => {
      setIsProcessing(true);
      setError(null);

      // Add user message immediately
      addUserMessage(content);

      try {
        // Send to backend API
        const response = await sendChatMessage({
          message: content,
          context,
        });

        // Add AI response
        const aiMessage = addAIMessage(response);

        return aiMessage;
      } catch (err) {
        const error = err instanceof Error ? err : new Error("Failed to send message");
        setError(error);
        throw error;
      } finally {
        setIsProcessing(false);
      }
    },
    [addUserMessage, addAIMessage]
  );

  /**
   * Clear all messages
   */
  const clearMessages = useCallback(() => {
    setMessages([]);
    setError(null);
  }, []);

  /**
   * Remove a specific message
   */
  const removeMessage = useCallback((messageId: string) => {
    setMessages((prev) => prev.filter((msg) => msg.id !== messageId));
  }, []);

  return {
    messages,
    isProcessing,
    error,
    sendMessage,
    addUserMessage,
    addAIMessage,
    clearMessages,
    removeMessage,
  };
}
