import { AlertCircle, RefreshCcw, WifiOff, Lock, FileWarning } from "lucide-react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { categorizeError, ErrorCategory, getUserFriendlyMessage } from "@/lib/error-handler";
import { APIClientError } from "@/lib/api-client";

interface ErrorDisplayProps {
    error: Error | APIClientError;
    onRetry?: () => void;
    className?: string;
}

export function ErrorDisplay({ error, onRetry, className = "" }: ErrorDisplayProps) {
    const category = categorizeError(error);
    const message = getUserFriendlyMessage(error);

    const getIcon = () => {
        switch (category) {
            case ErrorCategory.NETWORK:
                return <WifiOff className="h-4 w-4" />;
            case ErrorCategory.AUTH:
                return <Lock className="h-4 w-4" />;
            case ErrorCategory.NOT_FOUND:
            case ErrorCategory.VALIDATION:
                return <FileWarning className="h-4 w-4" />;
            default:
                return <AlertCircle className="h-4 w-4" />;
        }
    };

    const getTitle = () => {
        switch (category) {
            case ErrorCategory.NETWORK:
                return "Connection Error";
            case ErrorCategory.AUTH:
                return "Authentication Error";
            case ErrorCategory.NOT_FOUND:
                return "Not Found";
            case ErrorCategory.VALIDATION:
                return "Validation Error";
            case ErrorCategory.SERVER:
                return "Server Error";
            default:
                return "Error";
        }
    };

    return (
        <Alert variant="destructive" className={className}>
            {getIcon()}
            <AlertTitle className="ml-2">{getTitle()}</AlertTitle>
            <AlertDescription className="mt-2 flex flex-col gap-3">
                <p>{message}</p>
                {onRetry && (
                    <Button
                        variant="outline"
                        size="sm"
                        onClick={onRetry}
                        className="w-fit bg-white text-destructive hover:bg-destructive/10 border-destructive/20"
                    >
                        <RefreshCcw className="mr-2 h-3 w-3" />
                        Try Again
                    </Button>
                )}
            </AlertDescription>
        </Alert>
    );
}
