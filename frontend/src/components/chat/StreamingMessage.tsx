import CitationTag from "./CitationTag";

interface StreamingMessageProps {
  text: string;
  citations?: Array<{ page: number | string; text: string }>;
}

export default function StreamingMessage({ text, citations }: StreamingMessageProps) {
  return (
    <div className="flex gap-3">
      <div className="w-8 h-8 rounded-full flex-shrink-0 flex items-center justify-center text-xs font-medium bg-gray-700 text-gray-300">
        AI
      </div>
      <div className="max-w-[75%]">
        <div className="rounded-2xl px-4 py-2.5 bg-gray-800 text-gray-100">
          <p className="text-sm whitespace-pre-wrap leading-relaxed">
            {text}
            <span className="inline-block w-1.5 h-4 bg-purple-400 ml-0.5 animate-pulse" />
          </p>
          {citations && citations.length > 0 && (
            <div className="mt-2 flex flex-wrap gap-1">
              {citations.map((c, i) => (
                <CitationTag key={i} page={c.page} text={c.text} />
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
