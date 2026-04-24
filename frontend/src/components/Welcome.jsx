const suggestions = [
  { emoji: "🏦", text: "¿Tenpo está regulada?" },
  { emoji: "💰", text: "¿Cuánto vale la UF hoy?" },
  { emoji: "⚠️", text: "Me llegó un SMS sospechoso de mi banco" },
  { emoji: "📋", text: "¿Qué derechos tengo con mi tarjeta de crédito?" },
];

export default function Welcome({ onSelect }) {
  return (
    <div className="flex-1 flex flex-col items-center justify-center p-8">
      <div className="text-center mb-10">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">RegulBot</h1>
        <p className="text-gray-500 text-sm max-w-md">
          Traductor de regulación financiera chilena.
          Conectado en tiempo real con la CMF, SII y BCN.
        </p>
        <div className="flex gap-2 justify-center mt-3">
          <span className="text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded-full">
            MCP Server activo
          </span>
          <span className="text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded-full">
            5 tools disponibles
          </span>
        </div>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 max-w-lg w-full">
        {suggestions.map((s, i) => (
          <button
            key={i}
            onClick={() => onSelect(s.text)}
            className="text-left p-4 bg-white border border-gray-200 rounded-xl
                       hover:border-blue-300 hover:shadow-sm transition-all text-sm cursor-pointer"
          >
            <span className="text-lg mr-2">{s.emoji}</span>
            {s.text}
          </button>
        ))}
      </div>
    </div>
  );
}
