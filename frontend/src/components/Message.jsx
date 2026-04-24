import ToolBadge from "./ToolBadge";

export default function Message({ msg }) {
  const isUser = msg.role === "user";

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[85%] rounded-2xl px-4 py-3 text-sm leading-relaxed ${
          isUser
            ? "bg-blue-600 text-white"
            : msg.error
              ? "bg-red-50 text-red-800 border border-red-200"
              : "bg-white border border-gray-200 text-gray-800"
        }`}
      >
        {/* Render content */}
        <div className="whitespace-pre-wrap">{msg.content}</div>

        {/* Tools used */}
        {msg.tools && msg.tools.length > 0 && (
          <div className="mt-3 pt-2 border-t border-gray-100 flex flex-wrap gap-1.5">
            {msg.tools.map((t, i) => (
              <ToolBadge key={i} name={t.name} compact />
            ))}
          </div>
        )}

        {/* Token usage */}
        {msg.usage && (
          <div className="mt-1 text-xs text-gray-400">
            {msg.usage.input_tokens + msg.usage.output_tokens} tokens
          </div>
        )}
      </div>
    </div>
  );
}
