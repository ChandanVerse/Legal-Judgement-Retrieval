"use client";

import { useState } from "react";
import { getCase, getDownloadUrl, CaseDetails } from "@/lib/api";

interface CaseCardProps {
  caseId: string;
  score: number;
  snippet: string;
}

export default function CaseCard({ caseId, score, snippet }: CaseCardProps) {
  const [expanded, setExpanded] = useState(false);
  const [fullCase, setFullCase] = useState<CaseDetails | null>(null);
  const [loading, setLoading] = useState(false);

  const handleExpand = async () => {
    if (expanded) {
      setExpanded(false);
      return;
    }

    if (!fullCase) {
      setLoading(true);
      try {
        const data = await getCase(caseId);
        setFullCase(data);
      } catch (error) {
        console.error("Error fetching case:", error);
      } finally {
        setLoading(false);
      }
    }
    setExpanded(true);
  };

  const scorePercent = Math.round(score * 100);
  const scoreColor =
    scorePercent >= 80
      ? "text-legal-gold bg-legal-gold/10 border-legal-gold/30"
      : scorePercent >= 60
      ? "text-amber-600 bg-amber-50 border-amber-200"
      : "text-gray-600 bg-gray-50 border-gray-200";

  return (
    <div className="bg-legal-parchment rounded-xl border-l-4 border-legal-gold overflow-hidden shadow-sm">
      {/* Header */}
      <div className="px-4 py-3 flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <h4 className="font-medium text-legal-navy text-sm truncate">
            {caseId.replace(/_/g, " ")}
          </h4>
          <p className="text-xs text-gray-500 mt-1 line-clamp-2">{snippet}</p>
        </div>
        <span
          className={`text-xs font-semibold px-2.5 py-1 rounded-full border flex-shrink-0 ${scoreColor}`}
        >
          {scorePercent}%
        </span>
      </div>

      {/* Expanded content */}
      {expanded && fullCase && (
        <div className="px-4 py-3 border-t border-gray-200 bg-white">
          <div className="flex items-center gap-4 text-xs text-gray-500 mb-3">
            <span className="flex items-center gap-1">
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
                  d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                />
              </svg>
              {fullCase.page_count} pages
            </span>
            <span className="flex items-center gap-1">
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
                  d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z"
                />
              </svg>
              {fullCase.filename}
            </span>
          </div>
          <div className="bg-legal-parchment rounded-lg border border-gray-200 p-3 max-h-64 overflow-y-auto">
            <pre className="text-xs text-legal-slate whitespace-pre-wrap font-mono leading-relaxed">
              {fullCase.full_text.slice(0, 5000)}
              {fullCase.full_text.length > 5000 && "..."}
            </pre>
          </div>
        </div>
      )}

      {/* Actions */}
      <div className="px-4 py-2 border-t border-gray-200 flex items-center gap-3 bg-white/50">
        <button
          onClick={handleExpand}
          disabled={loading}
          className="text-xs text-legal-navy hover:text-legal-gold font-medium disabled:opacity-50 flex items-center gap-1 transition-colors"
        >
          {loading ? (
            <>
              <svg
                className="w-3.5 h-3.5 animate-spin"
                fill="none"
                viewBox="0 0 24 24"
              >
                <circle
                  className="opacity-25"
                  cx="12"
                  cy="12"
                  r="10"
                  stroke="currentColor"
                  strokeWidth="4"
                />
                <path
                  className="opacity-75"
                  fill="currentColor"
                  d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                />
              </svg>
              Loading...
            </>
          ) : expanded ? (
            <>
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
                  d="M5 15l7-7 7 7"
                />
              </svg>
              Hide Full Text
            </>
          ) : (
            <>
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
                  d="M19 9l-7 7-7-7"
                />
              </svg>
              View Full Text
            </>
          )}
        </button>
        <span className="text-gray-300">|</span>
        <a
          href={getDownloadUrl(caseId)}
          target="_blank"
          rel="noopener noreferrer"
          className="text-xs text-legal-navy hover:text-legal-gold font-medium flex items-center gap-1 transition-colors"
        >
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
              d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"
            />
          </svg>
          Download PDF
        </a>
      </div>
    </div>
  );
}
