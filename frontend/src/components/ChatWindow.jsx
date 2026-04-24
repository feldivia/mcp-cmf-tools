import { useState, useEffect, useRef } from "react";
import Message from "./Message";
import ToolBadge from "./ToolBadge";

export default function ChatWindow({ initialQuestion }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [activeTools, setActiveTools] = useState([]);
  const bottomRef = useRef(null);

  useEffect(() => {
    if (initialQuestion) sendMessage(initialQuestion);
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, activeTools]);

  async function sendMessage(text) {
    const userMsg = { role: "user", content: text };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setLoading(true);
    setActiveTools([]);

    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: text,
          history: messages.slice(-10),
        }),
      });

      const reader = res.body.getReader();
      const decoder = new TextDecoder();

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        const lines = chunk.split("\n").filter((l) => l.startsWith("data: "));

        for (const line of lines) {
          try {
            const data = JSON.parse(line.slice(6));

            if (data.type === "tool") {
              setActiveTools((prev) => [...prev, data]);
            }

            if (data.type === "response") {
              setMessages((prev) => [
                ...prev,
                {
                  role: "assistant",
                  content: data.content,
                  tools: data.tools_used || [],
                  usage: data.usage,
                },
              ]);
              setActiveTools([]);
            }

            if (data.type === "error") {
              setMessages((prev) => [
                ...prev,
                { role: "assistant", content: `Error: ${data.message}`, error: true },
              ]);
            }
          } catch {}
        }
      }
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: "Error de conexión.", error: true },
      ]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex-1 flex flex-col max-w-2xl mx-auto w-full">
      {/* Header */}
      <div className="px-4 py-3 border-b bg-white flex items-center gap-3">
        <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center text-white text-sm font-bold">
          R
        </div>
        <div>
          <div className="font-semibold text-sm">RegulBot</div>
          <div className="text-xs text-gray-400">
            MCP: CMF · mindicador · BCN
          </div>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((msg, i) => (
          <Message key={i} msg={msg} />
        ))}

        {/* Tool activity */}
        {activeTools.length > 0 && (
          <div className="flex flex-wrap gap-2">
            {activeTools.map((t, i) => (
              <ToolBadge key={i} name={t.name} input={t.input} />
            ))}
          </div>
        )}

        {loading && activeTools.length === 0 && (
          <div className="text-gray-400 text-sm animate-pulse">
            Pensando...
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="p-4 border-t bg-white">
        <div className="flex gap-2">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && !loading && input.trim() && sendMessage(input.trim())}
            placeholder="Pregunta sobre regulación financiera..."
            className="flex-1 px-4 py-2.5 border border-gray-200 rounded-xl text-sm
                       focus:outline-none focus:border-blue-400"
            disabled={loading}
          />
          <button
            onClick={() => input.trim() && sendMessage(input.trim())}
            disabled={loading || !input.trim()}
            className="px-4 py-2.5 bg-blue-600 text-white rounded-xl text-sm font-medium
                       disabled:opacity-40 hover:bg-blue-700 transition-colors cursor-pointer"
          >
            Enviar
          </button>
        </div>
      </div>
    </div>
  );
}
