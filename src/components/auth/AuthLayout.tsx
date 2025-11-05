import React from "react";

interface AuthLayoutProps {
  children?: React.ReactNode;
  title?: string;
  subtitle?: string;
}

export default function AuthLayout({
  children,
  title = "Welcome to ScheduleFirst AI",
  subtitle = "Create an account or sign in to continue",
}: AuthLayoutProps) {
  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-purple-50 p-6">
      <div className="max-w-7xl mx-auto">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-gray-900">{title}</h1>
          <p className="text-gray-600 mt-1">{subtitle}</p>
        </div>
        <div className="flex justify-center">
          {children}
        </div>
      </div>
    </div>
  );
}
