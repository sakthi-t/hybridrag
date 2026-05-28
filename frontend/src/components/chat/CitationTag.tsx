interface CitationTagProps {
  page: number | string;
  text: string;
}

export default function CitationTag({ page }: CitationTagProps) {
  return (
    <span className="inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium bg-purple-600/20 text-purple-300 ml-1 cursor-help" title={`From page ${page}`}>
      p.{page}
    </span>
  );
}
