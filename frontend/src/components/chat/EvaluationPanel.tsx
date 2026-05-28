interface EvalMetric {
  label: string;
  score: number;
  key: string;
}

interface EvalRecord {
  query: string;
  metrics: EvalMetric[];
  overall: number;
  at: string;
}

interface EvaluationPanelProps {
  metrics: EvalMetric[];
  overall: number;
  history?: EvalRecord[];
  latencyMs?: number;
  chunksRetrieved?: number;
  visible: boolean;
  onToggle: () => void;
}

export default function EvaluationPanel({ metrics, overall, history, latencyMs, chunksRetrieved, visible, onToggle }: EvaluationPanelProps) {
  const getColor = (score: number) => {
    if (score >= 80) return "bg-green-500";
    if (score >= 60) return "bg-yellow-500";
    return "bg-red-500";
  };

  const getTextColor = (score: number) => {
    if (score >= 80) return "text-green-400";
    if (score >= 60) return "text-yellow-400";
    return "text-red-400";
  };

  const allRecords = history && history.length > 0 ? history : [];

  return (
    <>
      <button
        onClick={onToggle}
        className="absolute right-0 top-1/2 -translate-y-1/2 z-10 bg-gray-800 border border-gray-700 rounded-l-lg px-1.5 py-3 text-gray-400 hover:text-white hover:bg-gray-700 transition-colors"
        title="Toggle evaluation panel"
      >
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d={visible ? "M9 5l7 7-7 7" : "M15 19l-7-7 7-7"} />
        </svg>
      </button>

      {visible && (
        <div className="w-80 border-l border-gray-800 bg-gray-900/50 flex flex-col flex-shrink-0">
          <div className="p-4 overflow-y-auto flex-1">
            <h3 className="text-sm font-semibold text-gray-300 mb-4">Evaluation Metrics</h3>

            <div className="mb-6">
              <div className="flex justify-between items-center mb-2">
                <span className="text-sm text-gray-400">Session Average</span>
                <span className={`text-lg font-bold ${getTextColor(overall)}`}>{overall}</span>
              </div>
              <div className="w-full bg-gray-700 rounded-full h-2">
                <div
                  className={`h-2 rounded-full transition-all duration-500 ${getColor(overall)}`}
                  style={{ width: `${overall}%` }}
                />
              </div>
            </div>

            {metrics.length > 0 && (
              <>
                <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">Latest Response</h4>
                {metrics.map((metric) => (
                  <div key={metric.key} className="mb-3">
                    <div className="flex justify-between items-center mb-1">
                      <span className="text-xs text-gray-400">{metric.label}</span>
                      <span className={`text-xs font-medium ${getTextColor(metric.score)}`}>{metric.score}</span>
                    </div>
                    <div className="w-full bg-gray-700 rounded-full h-1.5">
                      <div
                        className={`h-1.5 rounded-full transition-all duration-500 ${getColor(metric.score)}`}
                        style={{ width: `${metric.score}%` }}
                      />
                    </div>
                  </div>
                ))}
              </>
            )}

            {allRecords.length > 0 && (
              <>
                <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3 mt-4 pt-4 border-t border-gray-800">
                  History ({allRecords.length})
                </h4>
                <div className="space-y-3">
                  {allRecords.map((record, idx) => (
                    <div key={idx} className="bg-gray-800/50 rounded-lg p-3">
                      <p className="text-xs text-gray-400 truncate mb-2">"{record.query}"</p>
                      <div className="flex items-center gap-2 mb-1">
                        <div className="w-full bg-gray-700 rounded-full h-1">
                          <div
                            className={`h-1 rounded-full ${getColor(record.overall)}`}
                            style={{ width: `${record.overall}%` }}
                          />
                        </div>
                        <span className={`text-xs font-medium ${getTextColor(record.overall)}`}>{record.overall}</span>
                      </div>
                      <div className="grid grid-cols-4 gap-1 text-[10px] text-gray-500">
                        {record.metrics.map((m) => (
                          <span key={m.key} className={getTextColor(m.score)}>
                            {m.label.slice(0, 4)}:{m.score}
                          </span>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </>
            )}

            {metrics.length === 0 && allRecords.length === 0 && (
              <p className="text-xs text-gray-500 mb-4">Send a message to see evaluation scores</p>
            )}

            <div className="border-t border-gray-800 pt-4 mt-4 space-y-2">
              {latencyMs !== undefined && (
                <div className="flex justify-between text-xs">
                  <span className="text-gray-500">Latency</span>
                  <span className="text-gray-400">{(latencyMs / 1000).toFixed(1)}s</span>
                </div>
              )}
              {chunksRetrieved !== undefined && (
                <div className="flex justify-between text-xs">
                  <span className="text-gray-500">Chunks Retrieved</span>
                  <span className="text-gray-400">{chunksRetrieved}</span>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </>
  );
}
