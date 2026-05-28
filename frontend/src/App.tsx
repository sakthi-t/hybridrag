import { ClerkProvider, SignedIn, SignedOut } from "@clerk/clerk-react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import MainLayout from "./components/layout/MainLayout";
import SignInPage from "./pages/SignInPage";
import SignUpPage from "./pages/SignUpPage";
import ChatPage from "./pages/ChatPage";
import AdminPage from "./pages/AdminPage";
import AdminGuard from "./components/auth/AdminGuard";

const CLERK_KEY = import.meta.env.VITE_CLERK_PUBLISHABLE_KEY;

function App() {
  return (
    <ClerkProvider publishableKey={CLERK_KEY}>
      <BrowserRouter>
        <SignedIn>
          <Routes>
            <Route element={<MainLayout />}>
              <Route path="/" element={<ChatPage />} />
              <Route path="/chat/:threadId" element={<ChatPage />} />
              <Route
                path="/admin"
                element={
                  <AdminGuard>
                    <AdminPage />
                  </AdminGuard>
                }
              />
            </Route>
            <Route path="*" element={<Navigate to="/" />} />
          </Routes>
        </SignedIn>
        <SignedOut>
          <Routes>
            <Route path="/sign-in" element={<SignInPage />} />
            <Route path="/sign-up" element={<SignUpPage />} />
            <Route path="*" element={<Navigate to="/sign-in" />} />
          </Routes>
        </SignedOut>
      </BrowserRouter>
    </ClerkProvider>
  );
}

export default App;
