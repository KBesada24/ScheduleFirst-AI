import { useState, useCallback, useEffect } from "react";
import { sendChatMessage, ChatRequest, ChatResponse } from "@/lib/api-endpoints";

export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
  suggestedSchedule?: any;
}

// LocalStorage key for persisting context
const CONTEXT_STORAGE_KEY = "schedule-optimizer-context";
const CONTEXT_EXPIRY_DAYS = 7;

interface PersistedContext {
  semester?: string;
  university?: string;
  timestamp: number;
}

/**
 * Load persisted context from localStorage
 * Returns null if expired or not found
 */
function loadPersistedContext(): PersistedContext | null {
  try {
    const stored = localStorage.getItem(CONTEXT_STORAGE_KEY);
    if (stored) {
      const parsed = JSON.parse(stored) as PersistedContext;
      // Check if expired (7 days)
      const expiryMs = CONTEXT_EXPIRY_DAYS * 24 * 60 * 60 * 1000;
      if (Date.now() - parsed.timestamp < expiryMs) {
        return parsed;
      }
      // Expired - clean up
      localStorage.removeItem(CONTEXT_STORAGE_KEY);
    }
  } catch (e) {
    console.warn("Failed to load persisted context:", e);
  }
  return null;
}

/**
 * Persist context to localStorage
 */
function persistContext(context: { semester?: string; university?: string }): void {
  try {
    const toStore: PersistedContext = {
      ...context,
      timestamp: Date.now(),
    };
    localStorage.setItem(CONTEXT_STORAGE_KEY, JSON.stringify(toStore));
  } catch (e) {
    console.warn("Failed to persist context:", e);
  }
}

export function useChatMessages(initialMessages: Message[] = []) {
  const [messages, setMessages] = useState<Message[]>(initialMessages);
  const [isProcessing, setIsProcessing] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  
  // Persisted context state
  const [persistedContext, setPersistedContext] = useState<PersistedContext | null>(null);
  
  // Load persisted context on mount
  useEffect(() => {
    const loaded = loadPersistedContext();
    if (loaded) {
      setPersistedContext(loaded);
    }
  }, []);

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
   * Fixed: Creates user message before sending to avoid stale closure issues
   */
  const sendMessage = useCallback(
    async (content: string, context?: ChatRequest["context"]) => {
      setIsProcessing(true);
      setError(null);

      // Create user message object FIRST (before any state updates)
      // This avoids React's async state update causing stale closure issues
      const userMessage: Message = {
        id: `user-${Date.now()}`,
        role: "user",
        content,
        timestamp: new Date(),
      };

      try {
        // Build history from current messages state
        // The user message we just created will be sent as 'message', not in history
        const history = messages.map(msg => ({
          role: msg.role,
          content: msg.content
        }));

        // Merge persisted context with provided context
        // Priority: provided context > persisted context
        const mergedContext: ChatRequest["context"] = {
          semester: context?.semester || persistedContext?.semester,
          university: context?.university || persistedContext?.university,
          currentSchedule: context?.currentSchedule,
          preferences: context?.preferences,
        };

        console.log('[useChatMessages] Sending with context:', mergedContext, 'history length:', history.length);

        // Send to backend API
        const response = await sendChatMessage({
          message: content,
          context: mergedContext,
          history,
        });

        // Add user message to state AFTER successful API call
        setMessages(prev => [...prev, userMessage]);

        // Update persisted context from API response
        const responseContext = (response as any).context;
        if (responseContext) {
          const newContext = {
            semester: responseContext.semester || persistedContext?.semester,
            university: responseContext.university || persistedContext?.university,
          };
          // Only persist if we have at least one value
          if (newContext.semester || newContext.university) {
            console.log('[useChatMessages] Persisting context from response:', newContext);
            persistContext(newContext);
            setPersistedContext({ ...newContext, timestamp: Date.now() });
          }
        }

        // Add AI response
        const aiMessage = addAIMessage(response);

        return aiMessage;
      } catch (err) {
        // Still add user message on error so it shows in UI
        setMessages(prev => [...prev, userMessage]);
        const error = err instanceof Error ? err : new Error("Failed to send message");
        setError(error);
        throw error;
      } finally {
        setIsProcessing(false);
      }
    },
    [addAIMessage, messages, persistedContext]
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
  
  /**
   * Clear persisted context
   */
  const clearPersistedContext = useCallback(() => {
    localStorage.removeItem(CONTEXT_STORAGE_KEY);
    setPersistedContext(null);
  }, []);
  
  /**
   * Update persisted context manually
   */
  const updateContext = useCallback((context: { semester?: string; university?: string }) => {
    const newContext = {
      semester: context.semester || persistedContext?.semester,
      university: context.university || persistedContext?.university,
    };
    persistContext(newContext);
    setPersistedContext({ ...newContext, timestamp: Date.now() });
  }, [persistedContext]);

  return {
    messages,
    isProcessing,
    error,
    sendMessage,
    addUserMessage,
    addAIMessage,
    clearMessages,
    removeMessage,
    // New exports for context persistence
    persistedContext: persistedContext ? {
      semester: persistedContext.semester,
      university: persistedContext.university,
    } : null,
    clearPersistedContext,
    updateContext,
  };
}
