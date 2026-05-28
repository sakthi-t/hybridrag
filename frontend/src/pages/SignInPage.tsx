import { useState, useEffect } from "react";
import { SignIn } from "@clerk/clerk-react";

const slides = [
  {
    title: "Traditional RAG",
    description:
      "Classic retrieval-augmented generation using vector similarity search. Upload documents and chat with them using semantic search powered by OpenAI embeddings and Chroma vector database.",
    image: "https://picsum.photos/seed/rag1/800/1024",
  },
  {
    title: "Hybrid RAG",
    description:
      "The best of both worlds — combines vector search with knowledge graph traversal. Get precise, context-aware answers that understand relationships between entities in your documents.",
    image: "https://picsum.photos/seed/rag2/800/1024",
  },
  {
    title: "Graph RAG",
    description:
      "Advanced knowledge graph-based retrieval that maps entity relationships. Perfect for complex documents with interconnected concepts, hierarchical data, and cross-referenced information.",
    image: "https://picsum.photos/seed/rag3/800/1024",
  },
];

export default function SignInPage() {
  const [current, setCurrent] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => {
      setCurrent((prev) => (prev + 1) % slides.length);
    }, 5000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="flex min-h-screen">
      {/* Left: Carousel */}
      <div className="hidden md:flex w-1/2 bg-gradient-to-br from-gray-900 to-gray-800 flex-col justify-center px-16 relative overflow-hidden">
        <div className="mb-12">
          <h1 className="text-4xl font-bold text-white mb-2">Hybrid RAG</h1>
          <p className="text-gray-400 text-sm">Intelligent Document Understanding</p>
        </div>

        <div className="relative min-h-[420px]">
          {slides.map((slide, idx) => (
            <div
              key={idx}
              className={`absolute inset-0 transition-all duration-700 ease-in-out ${
                idx === current
                  ? "opacity-100 translate-y-0"
                  : "opacity-0 translate-y-4 pointer-events-none"
              }`}
            >
              <img
                src={slide.image}
                alt={slide.title}
                className="w-full h-48 object-cover rounded-xl mb-6"
              />
              <div className="flex items-center gap-3 mb-4">
                <div className="w-10 h-10 rounded-lg bg-purple-600/20 flex items-center justify-center">
                  <svg className="w-5 h-5 text-purple-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                  </svg>
                </div>
                <h2 className="text-2xl font-semibold text-white">{slide.title}</h2>
              </div>
              <p className="text-gray-300 leading-relaxed">{slide.description}</p>
            </div>
          ))}
        </div>

        {/* Dots */}
        <div className="flex gap-2 mt-8">
          {slides.map((_, idx) => (
            <button
              key={idx}
              type="button"
              onClick={() => setCurrent(idx)}
              className={`w-2.5 h-2.5 rounded-full transition-all ${
                idx === current ? "bg-purple-500 w-8" : "bg-gray-600 hover:bg-gray-500"
              }`}
            />
          ))}
        </div>
      </div>

      {/* Right: Clerk SignIn */}
      <div className="w-full md:w-1/2 flex items-center justify-center bg-gray-950 p-8">
        <div className="w-full max-w-md">
          <div className="md:hidden mb-8 text-center">
            <h1 className="text-3xl font-bold text-white mb-2">Hybrid RAG</h1>
            <p className="text-gray-400 text-sm">Intelligent Document Understanding</p>
          </div>
          <SignIn signUpUrl="/sign-up" />
        </div>
      </div>
    </div>
  );
}
