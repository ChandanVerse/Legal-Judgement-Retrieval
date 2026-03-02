"use client";

import { useEffect, useRef } from "react";
import { Message as MessageType } from "@/lib/api";
import Message from "./Message";

interface ChatWindowProps {
  messages: MessageType[];
  isStreaming: boolean;
  streamingContent: string;
}

// Scales of Justice icon component
function ScalesIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M12 3v18" />
      <path d="M5 7l7-4 7 4" />
      <path d="M5 7l-1 7h4l-1-7" />
      <path d="M19 7l-1 7h4l-1-7" />
      <circle cx="12" cy="3" r="1" fill="currentColor" />
    </svg>
  );
}

export default function ChatWindow({
  messages,
  isStreaming,
  streamingContent,
}: ChatWindowProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streamingContent]);

  return (
    <div className="flex-1 overflow-y-auto">
      <div className="max-w-3xl mx-auto p-4 space-y-6">
        {messages.map((message, index) => (
          <Message key={index} message={message} />
        ))}

        {/* Streaming message */}
        {isStreaming && streamingContent && (
          <Message
            message={{ role: "assistant", content: streamingContent }}
            isStreaming={true}
          />
        )}

        {/* Loading indicator when waiting for first chunk */}
        {isStreaming && !streamingContent && (
          <div className="flex items-start gap-3 animate-fade-in">
            <div className="w-8 h-8 rounded-full bg-legal-navy flex items-center justify-center flex-shrink-0">
              <ScalesIcon className="w-4 h-4 text-legal-gold" />
            </div>
            <div className="bg-legal-parchment rounded-2xl rounded-tl-md px-4 py-3 shadow-sm border border-gray-100">
              <div className="flex items-center gap-2">
                <div className="flex gap-1">
                  <div className="w-2 h-2 bg-legal-gold rounded-full animate-bounce" />
                  <div
                    className="w-2 h-2 bg-legal-gold rounded-full animate-bounce"
                    style={{ animationDelay: "0.1s" }}
                  />
                  <div
                    className="w-2 h-2 bg-legal-gold rounded-full animate-bounce"
                    style={{ animationDelay: "0.2s" }}
                  />
                </div>
                <span className="text-sm text-gray-500">Searching cases...</span>
              </div>
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>
    </div>
  );
}
