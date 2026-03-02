const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface Message {
  role: "user" | "assistant";
  content: string;
  toolCalls?: ToolCall[];
}

export interface ToolCall {
  tool: string;
  input: Record<string, unknown>;
  result: string;
}

export interface ChatResponse {
  response: string;
  tool_calls: ToolCall[];
}

export interface CaseResult {
  case_id: string;
  score: number;
  snippet: string;
}

export interface CaseDetails {
  case_id: string;
  filename: string;
  page_count: number;
  full_text: string;
}

export interface StreamEvent {
  type: 'text' | 'tool_call' | 'tool_result' | 'done' | 'error';
  content?: string;
  tool?: string;
  input?: Record<string, unknown>;
  result?: string;
  tool_calls?: ToolCall[];
}

export async function streamChat(
  message: string,
  history: Message[],
  onChunk: (text: string) => void,
  onToolCall: (tool: string, input: Record<string, unknown>) => void,
  onToolResult: (tool: string, result: string) => void,
  onDone: (toolCalls: ToolCall[]) => void,
  onError: (error: string) => void
): Promise<void> {
  const response = await fetch(`${API_URL}/api/chat/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      message,
      conversation_history: history.map((msg) => ({
        role: msg.role,
        content: msg.content,
      })),
    }),
  });

  if (!response.ok) {
    throw new Error(`API error: ${response.status}`);
  }

  const reader = response.body!.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop() || '';

    for (const line of lines) {
      if (line.startsWith('data: ')) {
        try {
          const data: StreamEvent = JSON.parse(line.slice(6));
          switch (data.type) {
            case 'text':
              if (data.content) onChunk(data.content);
              break;
            case 'tool_call':
              if (data.tool) onToolCall(data.tool, data.input || {});
              break;
            case 'tool_result':
              if (data.tool && data.result) onToolResult(data.tool, data.result);
              break;
            case 'done':
              onDone(data.tool_calls || []);
              break;
            case 'error':
              if (data.content) onError(data.content);
              break;
          }
        } catch {
          // Ignore parse errors for incomplete JSON
        }
      }
    }
  }
}

export async function sendMessage(
  message: string,
  conversationHistory: Message[]
): Promise<ChatResponse> {
  const response = await fetch(`${API_URL}/api/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      message,
      conversation_history: conversationHistory.map((msg) => ({
        role: msg.role,
        content: msg.content,
      })),
    }),
  });

  if (!response.ok) {
    throw new Error(`API error: ${response.status}`);
  }

  return response.json();
}

export async function searchCases(
  query: string,
  topK: number = 5
): Promise<CaseResult[]> {
  const response = await fetch(
    `${API_URL}/api/search?q=${encodeURIComponent(query)}&top_k=${topK}`
  );

  if (!response.ok) {
    throw new Error(`API error: ${response.status}`);
  }

  const data = await response.json();
  return data.results;
}

export async function getCase(caseId: string): Promise<CaseDetails> {
  const response = await fetch(`${API_URL}/api/case/${encodeURIComponent(caseId)}`);

  if (!response.ok) {
    throw new Error(`API error: ${response.status}`);
  }

  return response.json();
}

export function getDownloadUrl(caseId: string): string {
  return `${API_URL}/api/download/${encodeURIComponent(caseId)}`;
}

export async function listCases(): Promise<{ cases: CaseResult[]; total: number }> {
  const response = await fetch(`${API_URL}/api/cases`);

  if (!response.ok) {
    throw new Error(`API error: ${response.status}`);
  }

  return response.json();
}

export async function searchByPdf(
  file: File,
  topK: number = 5
): Promise<{ filename: string; results: CaseResult[] }> {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("top_k", topK.toString());

  const response = await fetch(`${API_URL}/api/search/pdf`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    throw new Error(`API error: ${response.status}`);
  }

  return response.json();
}
