/**
 * Loading Indicators
 * 
 * Various loading indicators for different use cases
 */

import { Loader2 } from "lucide-react";

// ============================================
// SPINNER
// ============================================

interface SpinnerProps {
  size?: "sm" | "md" | "lg";
  className?: string;
}

export function Spinner({ size = "md", className = "" }: SpinnerProps) {
  const sizeClasses = {
    sm: "h-4 w-4",
    md: "h-8 w-8",
    lg: "h-12 w-12",
  };

  return (
    <Loader2 className={`animate-spin ${sizeClasses[size]} ${className}`} />
  );
}

// ============================================
// SKELETON LOADER
// ============================================

interface SkeletonProps {
  className?: string;
  variant?: "text" | "circular" | "rectangular";
  width?: string;
  height?: string;
}

export function Skeleton({
  className = "",
  variant = "rectangular",
  width,
  height,
}: SkeletonProps) {
  const variantClasses = {
    text: "h-4 rounded",
    circular: "rounded-full",
    rectangular: "rounded-md",
  };

  const style: React.CSSProperties = {};
  if (width) style.width = width;
  if (height) style.height = height;

  return (
    <div
      className={`animate-pulse bg-gray-200 ${variantClasses[variant]} ${className}`}
      style={style}
    />
  );
}

// ============================================
// PROGRESS BAR
// ============================================

interface ProgressBarProps {
  value: number; // 0-100
  className?: string;
  showLabel?: boolean;
  color?: "blue" | "green" | "purple" | "red";
}

export function ProgressBar({
  value,
  className = "",
  showLabel = false,
  color = "blue",
}: ProgressBarProps) {
  const colorClasses = {
    blue: "bg-blue-600",
    green: "bg-green-600",
    purple: "bg-purple-600",
    red: "bg-red-600",
  };

  const clampedValue = Math.min(100, Math.max(0, value));

  return (
    <div className={`w-full ${className}`}>
      <div className="w-full bg-gray-200 rounded-full h-2.5">
        <div
          className={`${colorClasses[color]} h-2.5 rounded-full transition-all duration-300`}
          style={{ width: `${clampedValue}%` }}
        />
      </div>
      {showLabel && (
        <div className="text-sm text-gray-600 mt-1 text-center">
          {clampedValue}%
        </div>
      )}
    </div>
  );
}

// ============================================
// DOTS LOADER
// ============================================

interface DotsLoaderProps {
  className?: string;
  color?: "blue" | "gray" | "white";
}

export function DotsLoader({ className = "", color = "blue" }: DotsLoaderProps) {
  const colorClasses = {
    blue: "bg-blue-600",
    gray: "bg-gray-600",
    white: "bg-white",
  };

  return (
    <div className={`flex gap-1 ${className}`}>
      <div
        className={`w-2 h-2 ${colorClasses[color]} rounded-full animate-bounce`}
        style={{ animationDelay: "0ms" }}
      />
      <div
        className={`w-2 h-2 ${colorClasses[color]} rounded-full animate-bounce`}
        style={{ animationDelay: "150ms" }}
      />
      <div
        className={`w-2 h-2 ${colorClasses[color]} rounded-full animate-bounce`}
        style={{ animationDelay: "300ms" }}
      />
    </div>
  );
}

// ============================================
// PULSE LOADER
// ============================================

interface PulseLoaderProps {
  className?: string;
  size?: "sm" | "md" | "lg";
}

export function PulseLoader({ className = "", size = "md" }: PulseLoaderProps) {
  const sizeClasses = {
    sm: "h-8 w-8",
    md: "h-12 w-12",
    lg: "h-16 w-16",
  };

  return (
    <div className={`relative ${sizeClasses[size]} ${className}`}>
      <div className="absolute inset-0 rounded-full bg-blue-400 animate-ping opacity-75" />
      <div className="absolute inset-0 rounded-full bg-blue-600" />
    </div>
  );
}

// ============================================
// CARD SKELETON
// ============================================

export function CardSkeleton() {
  return (
    <div className="border border-gray-200 rounded-lg p-4 space-y-3">
      <Skeleton variant="text" width="60%" height="24px" />
      <Skeleton variant="text" width="100%" height="16px" />
      <Skeleton variant="text" width="100%" height="16px" />
      <Skeleton variant="text" width="80%" height="16px" />
      <div className="flex gap-2 mt-4">
        <Skeleton variant="rectangular" width="80px" height="32px" />
        <Skeleton variant="rectangular" width="80px" height="32px" />
      </div>
    </div>
  );
}

// ============================================
// TABLE SKELETON
// ============================================

interface TableSkeletonProps {
  rows?: number;
  columns?: number;
}

export function TableSkeleton({ rows = 5, columns = 4 }: TableSkeletonProps) {
  return (
    <div className="space-y-2">
      {/* Header */}
      <div className="flex gap-4 pb-2 border-b">
        {Array.from({ length: columns }).map((_, i) => (
          <Skeleton key={i} variant="text" width="100px" height="20px" />
        ))}
      </div>
      {/* Rows */}
      {Array.from({ length: rows }).map((_, rowIndex) => (
        <div key={rowIndex} className="flex gap-4 py-2">
          {Array.from({ length: columns }).map((_, colIndex) => (
            <Skeleton key={colIndex} variant="text" width="100px" height="16px" />
          ))}
        </div>
      ))}
    </div>
  );
}

// ============================================
// FULL PAGE LOADER
// ============================================

interface FullPageLoaderProps {
  message?: string;
}

export function FullPageLoader({ message = "Loading..." }: FullPageLoaderProps) {
  return (
    <div className="fixed inset-0 bg-white bg-opacity-90 flex items-center justify-center z-50">
      <div className="text-center">
        <Spinner size="lg" className="mx-auto mb-4 text-blue-600" />
        <p className="text-gray-600 text-lg">{message}</p>
      </div>
    </div>
  );
}

// ============================================
// INLINE LOADER
// ============================================

interface InlineLoaderProps {
  message?: string;
  className?: string;
}

export function InlineLoader({ message, className = "" }: InlineLoaderProps) {
  return (
    <div className={`flex items-center gap-2 ${className}`}>
      <Spinner size="sm" />
      {message && <span className="text-sm text-gray-600">{message}</span>}
    </div>
  );
}
