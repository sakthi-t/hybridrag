import { useUser } from "@clerk/clerk-react";
import CitationTag from "./CitationTag";

interface MessageBubbleProps {
  role: "user" | "assistant";
  text: string;
  citations?: Array<{ page: number | string; text: string }>;
  createdAt: string;
}

export default function MessageBubble({ role, text, citations, createdAt }: MessageBubbleProps) {
  const { user } = useUser();
  const isUser = role === "user";

  return (
    <div className={`flex gap-3 ${isUser ? "flex-row-reverse" : ""}`}>
      <div className="w-8 h-8 rounded-full flex-shrink-0 flex items-center justify-center text-xs font-medium bg-gray-700 text-gray-300 overflow-hidden">
        {isUser
          ? user?.firstName?.charAt(0) || "U"
          : "AI"}
      </div>
      <div className={`max-w-[75%] ${isUser ? "items-end" : "items-start"}`}>
        <div className={`rounded-2xl px-4 py-2.5 ${
          isUser ? "bg-purple-600 text-white" : "bg-gray-800 text-gray-100"
        }`}>
          <p className="text-sm whitespace-pre-wrap leading-relaxed">{text}</p>
          {citations && citations.length > 0 && (
            <div className="mt-2 flex flex-wrap gap-1">
              {citations.map((c, i) => (
                <CitationTag key={i} page={c.page} text={c.text} />
              ))}
            </div>
          )}
        </div>
        <p className="text-xs text-gray-500 mt-1 px-1">{new Date(createdAt).toLocaleTimeString()}</p>
      </div>
    </div>
  );
}
