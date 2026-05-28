import { SignUp } from "@clerk/clerk-react";

export default function SignUpPage() {
  return (
    <div className="flex min-h-screen">
      <div className="hidden md:flex w-1/2 bg-gradient-to-br from-gray-900 to-gray-800 flex-col justify-center px-16">
        <h1 className="text-4xl font-bold text-white mb-4">Get Started</h1>
        <p className="text-gray-400">
          Create your account to start uploading documents and chatting with them using Hybrid RAG.
        </p>
      </div>
      <div className="w-full md:w-1/2 flex items-center justify-center bg-gray-950 p-8">
        <SignUp signInUrl="/sign-in" />
      </div>
    </div>
  );
}
