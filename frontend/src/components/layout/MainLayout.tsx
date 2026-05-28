import { useState, useCallback } from "react";
import { Outlet, useParams } from "react-router-dom";
import Sidebar from "./Sidebar";
import UploadModal from "../documents/UploadModal";

export default function MainLayout() {
  const [uploadOpen, setUploadOpen] = useState(false);
  const { threadId } = useParams();

  const handleUploadClick = useCallback(() => setUploadOpen(true), []);
  const handleUploadClose = useCallback(() => setUploadOpen(false), []);

  return (
    <div className="flex h-screen bg-gray-950">
      <Sidebar onUploadClick={handleUploadClick} activeThreadId={threadId} />
      <main className="flex-1 flex overflow-hidden">
        <Outlet />
      </main>
      <UploadModal open={uploadOpen} onClose={handleUploadClose} />
    </div>
  );
}
