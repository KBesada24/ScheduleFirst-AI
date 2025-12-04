import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Send, Loader2 } from "lucide-react";
import { sendChatMessage, ChatRequest, ChatResponse } from "@/lib/api-endpoints";
import { useToast } from "@/components/ui/use-toast";

export interface ChatContext {
  currentSchedule?: any;
  preferences?: any;
  semester?: string;
  university?: string;
}

interface ChatButtonProps {
  message: string;
  context?: ChatContext;
  onResponse: (response: ChatResponse) => void;
  onError?: (error: Error) => void;
  disabled?: boolean;
  className?: string;
}

export function ChatButton({
  message,
  context,
  onResponse,
  onError,
  disabled = false,
  className = "",
}: ChatButtonProps) {
  const [loading, setLoading] = useState(false);
  const { toast } = useToast();

  const validateMessage = (): boolean => {
    if (!message || message.trim() === "") {
      toast({
        title: "Empty Message",
        description: "Please enter a message before sending.",
        variant: "destructive",
      });
      return false;
    }
    return true;
  };

  const handleSend = async () => {
    if (!validateMessage()) {
      return;
    }

    setLoading(true);

    try {
      const request: ChatRequest = {
        message: message.trim(),
        context,
      };

      const response = await sendChatMessage(request);
      onResponse(response);

      toast({
        title: "Message Sent",
        description: "AI is processing your request...",
      });
    } catch (error) {
      const err = error instanceof Error ? error : new Error("Failed to send message");
      
      if (onError) {
        onError(err);
      }

      toast({
        title: "Error",
        description: err.message || "Failed to send message. Please try again.",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <Button
      onClick={handleSend}
      disabled={disabled || loading || !message.trim()}
      className={`bg-blue-600 hover:bg-blue-700 ${className}`}
    >
      {loading ? (
        <>
          <Loader2 className="mr-2 h-4 w-4 animate-spin" />
          Sending...
        </>
      ) : (
        <>
          <Send className="mr-2 h-4 w-4" />
          Send
        </>
      )}
    </Button>
  );
}
