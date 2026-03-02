"use client";

import ReactMarkdown from "react-markdown";
import { Message as MessageType } from "@/lib/api";
import CaseCard from "./CaseCard";

interface MessageProps {
  message: MessageType;
  isStreaming?: boolean;
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

export default function Message({ message, isStreaming = false }: MessageProps) {
  const isUser = message.role === "user";

  // Extract case IDs from tool calls if any search was performed
  const searchResults = message.toolCalls?.find(
    (tc) => tc.tool === "search_legal_cases" || tc.tool === "search_by_pdf"
  );

  let caseResults: Array<{ case_id: string; score: number; snippet: string }> = [];
  if (searchResults) {
    try {
      const parsed = JSON.parse(searchResults.result.replace(/\.\.\.$/,''));
      if (Array.isArray(parsed)) {
        caseResults = parsed;
      } else if (parsed.results && Array.isArray(parsed.results)) {
        caseResults = parsed.results;
      }
    } catch {
      // Result was truncated or invalid, ignore
    }
  }

  if (isUser) {
    return (
      <div className="flex justify-end animate-fade-in">
        <div className="max-w-[75%] bg-legal-navy text-white rounded-2xl rounded-br-md px-4 py-2.5 shadow-sm">
          <p className="text-[15px] leading-relaxed">{message.content}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex items-start gap-3 animate-fade-in">
      {/* Assistant avatar - scales of justice */}
      <div className="w-8 h-8 rounded-full bg-legal-navy flex items-center justify-center flex-shrink-0">
        <ScalesIcon className="w-4 h-4 text-legal-gold" />
      </div>

      {/* Message content */}
      <div className="flex-1 min-w-0 space-y-3">
        {/* Tool usage indicator */}
        {message.toolCalls && message.toolCalls.length > 0 && (
          <div className="flex items-center gap-2 text-xs text-legal-gold font-medium">
            <svg
              className="w-3.5 h-3.5"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
              />
            </svg>
            <span>Searched {caseResults.length} cases</span>
          </div>
        )}

        {/* Main response card */}
        <div className="bg-legal-parchment rounded-2xl rounded-tl-md px-4 py-3 shadow-sm border border-gray-100">
          <div className="prose prose-sm prose-slate max-w-none">
            <ReactMarkdown>{message.content}</ReactMarkdown>
            {isStreaming && (
              <span className="inline-block w-0.5 h-4 bg-legal-gold animate-cursor ml-0.5 align-middle" />
            )}
          </div>
        </div>

        {/* Case cards */}
        {caseResults.length > 0 && (
          <div className="space-y-2 mt-3">
            {caseResults.slice(0, 3).map((result) => (
              <CaseCard
                key={result.case_id}
                caseId={result.case_id}
                score={result.score}
                snippet={result.snippet}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
