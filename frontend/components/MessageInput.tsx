"use client";

import { useState, KeyboardEvent, useRef, useEffect } from "react";

interface MessageInputProps {
  onSend: (message: string) => void;
  onPdfUpload: (file: File, prompt: string) => void;
  onClear?: () => void;
  isLoading: boolean;
  showClear?: boolean;
}

export default function MessageInput({
  onSend,
  onPdfUpload,
  onClear,
  isLoading,
  showClear = false,
}: MessageInputProps) {
  const [input, setInput] = useState("");
  const [attachedFile, setAttachedFile] = useState<File | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 120)}px`;
    }
  }, [input]);

  const handleSubmit = () => {
    if (isLoading) return;

    if (attachedFile) {
      onPdfUpload(attachedFile, input.trim());
      setAttachedFile(null);
      setInput("");
    } else if (input.trim()) {
      onSend(input.trim());
      setInput("");
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file && file.type === "application/pdf") {
      setAttachedFile(file);
    }
    e.target.value = "";
  };

  const handleRemoveAttachment = () => {
    setAttachedFile(null);
  };

  const canSubmit = attachedFile || input.trim();

  return (
    <div className="p-4">
      <div className="max-w-3xl mx-auto bg-white rounded-xl shadow-md border border-gray-200">
        {/* Attachment Badge */}
        {attachedFile && (
          <div className="px-4 py-2 border-b border-gray-100">
            <div className="inline-flex items-center gap-2 px-2 py-1 bg-legal-parchment border border-legal-gold/30 rounded text-xs text-legal-navy">
              <svg
                className="w-3.5 h-3.5 text-legal-gold"
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
              <span className="max-w-[180px] truncate font-medium">{attachedFile.name}</span>
              <button
                onClick={handleRemoveAttachment}
                disabled={isLoading}
                className="p-0.5 hover:bg-legal-gold/10 rounded transition-colors disabled:opacity-50"
                title="Remove attachment"
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
                    d="M6 18L18 6M6 6l12 12"
                  />
                </svg>
              </button>
            </div>
          </div>
        )}

        <div className="flex items-center gap-2 p-2">
          {/* Left buttons */}
          {showClear && onClear && (
            <button
              onClick={onClear}
              disabled={isLoading}
              className="p-2 text-gray-400 hover:text-legal-navy hover:bg-gray-100 rounded-lg transition-colors disabled:opacity-50"
              title="New conversation"
            >
              <svg
                className="w-5 h-5"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 4v16m8-8H4"
                />
              </svg>
            </button>
          )}

          <button
            onClick={() => fileInputRef.current?.click()}
            disabled={isLoading || attachedFile !== null}
            className={`p-2 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed ${
              attachedFile
                ? "text-legal-gold bg-legal-gold/10"
                : "text-gray-400 hover:text-legal-navy hover:bg-gray-100"
            }`}
            title={attachedFile ? "PDF attached" : "Attach PDF"}
          >
            <svg
              className="w-5 h-5"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13"
              />
            </svg>
          </button>

          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf"
            onChange={handleFileChange}
            className="hidden"
          />

          {/* Text Input */}
          <textarea
            ref={textareaRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={
              attachedFile
                ? "Add a prompt for your PDF search..."
                : "Ask about legal cases..."
            }
            disabled={isLoading}
            rows={1}
            className="flex-1 px-2 py-2 bg-transparent border-0 focus:ring-0 focus:outline-none resize-none text-legal-slate placeholder-gray-400 text-sm"
            style={{ minHeight: "36px", maxHeight: "120px" }}
          />

          {/* Send Button */}
          <button
            onClick={handleSubmit}
            disabled={!canSubmit || isLoading}
            className={`p-2 rounded-lg transition-all disabled:opacity-40 disabled:cursor-not-allowed ${
              canSubmit && !isLoading
                ? "bg-legal-navy text-white hover:bg-legal-navy/90"
                : "bg-gray-100 text-gray-400"
            }`}
            title="Send message"
          >
            {isLoading ? (
              <svg
                className="w-5 h-5 animate-spin"
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
            ) : (
              <svg
                className="w-5 h-5"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M5 10l7-7m0 0l7 7m-7-7v18"
                />
              </svg>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
