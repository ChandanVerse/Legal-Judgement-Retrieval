"use client";

import { useState, useRef } from "react";
import ChatWindow from "@/components/ChatWindow";
import MessageInput from "@/components/MessageInput";
import { streamChat, searchByPdf, getCase, sendMessage, Message, ToolCall } from "@/lib/api";

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

const EXAMPLE_PROMPTS = [
  "Find cases about cheque bounce under Section 138",
  "Cases related to property disputes between siblings",
  "Consumer protection cases involving e-commerce",
];

export default function Home() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamingContent, setStreamingContent] = useState("");
  const streamingToolCallsRef = useRef<ToolCall[]>([]);
  const streamingContentRef = useRef("");

  const handleSend = async (text: string) => {
    if (!text.trim() || isStreaming) return;

    const userMessage: Message = {
      role: "user",
      content: text,
    };

    setMessages((prev) => [...prev, userMessage]);
    setIsStreaming(true);
    setStreamingContent("");
    streamingContentRef.current = "";
    streamingToolCallsRef.current = [];

    try {
      await streamChat(
        text,
        messages,
        (chunk) => {
          streamingContentRef.current += chunk;
          setStreamingContent(streamingContentRef.current);
        },
        (tool, input) => {
          console.log("Tool call:", tool, input);
        },
        (tool, result) => {
          streamingToolCallsRef.current.push({
            tool,
            input: {},
            result,
          });
        },
        (toolCalls) => {
          const finalContent = streamingContentRef.current || "I apologize, but I couldn't generate a response.";
          setMessages((prev) => [
            ...prev,
            {
              role: "assistant",
              content: finalContent,
              toolCalls: toolCalls.length > 0 ? toolCalls : streamingToolCallsRef.current,
            },
          ]);
          setStreamingContent("");
          setIsStreaming(false);
        },
        (error) => {
          console.error("Stream error:", error);
          setMessages((prev) => [
            ...prev,
            {
              role: "assistant",
              content: "Sorry, there was an error processing your request. Please try again.",
            },
          ]);
          setStreamingContent("");
          setIsStreaming(false);
        }
      );
    } catch (error) {
      console.error("Error sending message:", error);
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: "Sorry, there was an error processing your request. Please try again.",
        },
      ]);
      setStreamingContent("");
      setIsStreaming(false);
    }
  };

  const handlePdfUpload = async (file: File, userPrompt: string) => {
    if (isStreaming) return;

    const displayPrompt = userPrompt
      ? `${userPrompt} [Uploaded: ${file.name}]`
      : `Find similar cases for: ${file.name}`;

    const userMessage: Message = {
      role: "user",
      content: displayPrompt,
    };

    setMessages((prev) => [...prev, userMessage]);
    setIsStreaming(true);
    setStreamingContent("");

    try {
      const searchResponse = await searchByPdf(file, 5);

      if (searchResponse.results.length === 0) {
        setMessages((prev) => [
          ...prev,
          {
            role: "assistant",
            content: `No similar cases found for **${searchResponse.filename}**. Try uploading a different document.`,
          },
        ]);
        setIsStreaming(false);
        return;
      }

      const topCases = searchResponse.results.slice(0, 3);
      const fullCases = await Promise.all(
        topCases.map(async (result) => {
          try {
            const caseDetails = await getCase(result.case_id);
            return {
              ...result,
              full_text: caseDetails.full_text.slice(0, 8000),
            };
          } catch {
            return { ...result, full_text: result.snippet };
          }
        })
      );

      const resultsForAI = fullCases
        .map(
          (r, i) =>
            `--- CASE ${i + 1}: ${r.case_id.replace(/_/g, " ")} (Similarity: ${(r.score * 100).toFixed(1)}%) ---\n\n${r.full_text}\n`
        )
        .join("\n\n");

      const remainingCases = searchResponse.results.slice(3);
      const remainingList =
        remainingCases.length > 0
          ? `\n\nOther similar cases (not shown in full):\n${remainingCases.map((r, i) => `${i + 4}. ${r.case_id.replace(/_/g, " ")} (${(r.score * 100).toFixed(1)}%)`).join("\n")}`
          : "";

      let analysisPrompt: string;

      if (userPrompt) {
        analysisPrompt = `I uploaded a legal document "${searchResponse.filename}" with this request: "${userPrompt}"

Here are the top 3 similar cases with their FULL TEXT:

${resultsForAI}
${remainingList}

Based on the user's specific request "${userPrompt}", please:

1. **Address the User's Request**: Directly respond to what they asked for.
2. **Relevant Analysis**: Provide analysis specifically tailored to their request.
3. **Case Comparisons**: Compare the cases in the context of what the user is looking for.
4. **Recommendations**: Based on their specific need, which case(s) would be most useful and why?`;
      } else {
        analysisPrompt = `I uploaded a legal document "${searchResponse.filename}" and found similar cases. Here are the top 3 cases with their FULL TEXT:

${resultsForAI}
${remainingList}

Based on the full text of these cases, please provide:

1. **Document Analysis**: What type of legal matter does my uploaded document likely concern?
2. **Key Legal Issues**: What are the main legal issues, statutes, or principles that connect these cases?
3. **Case Summaries**: For each of the top 3 cases, provide a brief summary.
4. **Relevance Assessment**: Which case is most relevant to my document and why?
5. **Key Precedents**: Any important legal precedents from these cases that might apply.`;
      }

      // Use streaming for the analysis
      streamingContentRef.current = "";

      await streamChat(
        analysisPrompt,
        [],
        (chunk) => {
          streamingContentRef.current += chunk;
          setStreamingContent(streamingContentRef.current);
        },
        () => {},
        () => {},
        () => {
          setMessages((prev) => [
            ...prev,
            {
              role: "assistant",
              content: streamingContentRef.current,
              toolCalls: [
                {
                  tool: "search_by_pdf",
                  input: { filename: file.name, prompt: userPrompt || "general search" },
                  result: JSON.stringify(searchResponse.results),
                },
              ],
            },
          ]);
          setStreamingContent("");
          setIsStreaming(false);
        },
        (error) => {
          console.error("Stream error:", error);
          // Fallback to non-streaming if streaming fails
          sendMessage(analysisPrompt, []).then((response) => {
            setMessages((prev) => [
              ...prev,
              {
                role: "assistant",
                content: response.response,
                toolCalls: [
                  {
                    tool: "search_by_pdf",
                    input: { filename: file.name, prompt: userPrompt || "general search" },
                    result: JSON.stringify(searchResponse.results),
                  },
                ],
              },
            ]);
            setStreamingContent("");
            setIsStreaming(false);
          });
        }
      );
    } catch (error) {
      console.error("Error searching by PDF:", error);
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: "Sorry, there was an error processing your PDF. Please try again.",
        },
      ]);
      setStreamingContent("");
      setIsStreaming(false);
    }
  };

  const handleClear = () => {
    setMessages([]);
    setStreamingContent("");
    setIsStreaming(false);
  };

  const handleExampleClick = (example: string) => {
    handleSend(example);
  };

  const hasMessages = messages.length > 0 || isStreaming;

  // Centered welcome layout when no messages
  if (!hasMessages) {
    return (
      <main className="flex flex-col h-screen">
        {/* Minimal header */}
        <header className="flex items-center px-6 py-4">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-legal-navy flex items-center justify-center">
              <ScalesIcon className="w-5 h-5 text-legal-gold" />
            </div>
            <div>
              <h1 className="text-lg font-serif font-semibold text-legal-navy">
                Legal Assistant
              </h1>
              <div className="h-0.5 w-12 bg-legal-gold rounded-full mt-0.5" />
            </div>
          </div>
        </header>

        {/* Centered content */}
        <div className="flex-1 flex flex-col items-center justify-center px-4 -mt-16">
          {/* Welcome section */}
          <div className="text-center mb-8">
            <div className="w-20 h-20 mx-auto mb-6 bg-legal-navy rounded-full flex items-center justify-center">
              <ScalesIcon className="w-10 h-10 text-legal-gold" />
            </div>
            <h2 className="text-2xl font-serif font-semibold text-legal-navy mb-2">
              How can I help with your legal research?
            </h2>
            <p className="text-gray-500">
              Search through Indian court judgments or ask me about legal topics
            </p>
          </div>

          {/* Centered input */}
          <div className="w-full max-w-2xl mb-8">
            <MessageInput
              onSend={handleSend}
              onPdfUpload={handlePdfUpload}
              isLoading={isStreaming}
              showClear={false}
            />
          </div>

          {/* Example prompts */}
          <div className="w-full max-w-2xl space-y-3">
            {EXAMPLE_PROMPTS.map((example, i) => (
              <button
                key={i}
                onClick={() => handleExampleClick(example)}
                className="w-full text-left px-4 py-3 bg-white border border-legal-gold/30 hover:border-legal-gold hover:bg-legal-parchment rounded-xl text-legal-slate text-sm transition-all duration-200 group"
              >
                <span className="flex items-center gap-3">
                  <span className="w-6 h-6 rounded-full bg-legal-gold/10 flex items-center justify-center flex-shrink-0 group-hover:bg-legal-gold/20 transition-colors">
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
                        d="M8 12h.01M12 12h.01M16 12h.01"
                      />
                    </svg>
                  </span>
                  <span className="flex-1">{example}</span>
                  <svg
                    className="w-4 h-4 text-gray-300 group-hover:text-legal-gold transition-colors"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M9 5l7 7-7 7"
                    />
                  </svg>
                </span>
              </button>
            ))}
          </div>
        </div>
      </main>
    );
  }

  // Normal chat layout with messages
  return (
    <main className="flex flex-col h-screen">
      {/* Header */}
      <header className="flex items-center justify-between px-6 py-4 bg-white border-b border-gray-200">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg bg-legal-navy flex items-center justify-center">
            <ScalesIcon className="w-5 h-5 text-legal-gold" />
          </div>
          <div>
            <h1 className="text-lg font-serif font-semibold text-legal-navy">
              Legal Assistant
            </h1>
            <div className="h-0.5 w-12 bg-legal-gold rounded-full mt-0.5" />
          </div>
        </div>
      </header>

      {/* Chat Window */}
      <ChatWindow
        messages={messages}
        isStreaming={isStreaming}
        streamingContent={streamingContent}
      />

      {/* Message Input at bottom */}
      <MessageInput
        onSend={handleSend}
        onPdfUpload={handlePdfUpload}
        onClear={handleClear}
        isLoading={isStreaming}
        showClear={messages.length > 0}
      />
    </main>
  );
}
