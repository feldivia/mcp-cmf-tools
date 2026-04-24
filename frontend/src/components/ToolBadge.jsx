const TOOL_LABELS = {
  cmf_verificar_institucion: { icon: "🏦", label: "Verificando en CMF" },
  cmf_indicadores: { icon: "📊", label: "Indicadores CMF" },
  cmf_alertas: { icon: "🚨", label: "Alertas de fraude" },
  chile_indicadores_economicos: { icon: "💹", label: "Indicadores Chile" },
  chile_consultar_ley: { icon: "📜", label: "Consultando ley" },
};

export default function ToolBadge({ name, input, compact = false }) {
  const info = TOOL_LABELS[name] || { icon: "🔧", label: name };

  if (compact) {
    return (
      <span className="inline-flex items-center gap-1 text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded-full">
        {info.icon} {info.label}
      </span>
    );
  }

  return (
    <div className="inline-flex items-center gap-2 text-xs bg-amber-50 text-amber-700 border border-amber-200 px-3 py-1.5 rounded-lg animate-pulse">
      {info.icon} {info.label}
      {input && Object.keys(input).length > 0 && (
        <span className="text-amber-500">
          ({Object.values(input).join(", ")})
        </span>
      )}
    </div>
  );
}
