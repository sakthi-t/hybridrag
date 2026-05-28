import { useState, useCallback } from "react";
import { useDropzone } from "react-dropzone";
import { useAuth } from "@clerk/clerk-react";
import { useDocuments } from "../../hooks/useDocuments";
import { apiFetch } from "../../lib/api";

interface UploadModalProps {
  open: boolean;
  onClose: () => void;
}

export default function UploadModal({ open, onClose }: UploadModalProps) {
  const { getToken } = useAuth();
  const { fetchDocuments } = useDocuments();
  const [files, setFiles] = useState<File[]>([]);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const onDrop = useCallback((accepted: File[]) => {
    setFiles((prev) => {
      const combined = [...prev, ...accepted];
      if (combined.length > 5) return combined.slice(0, 5);
      return combined;
    });
    setError(null);
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      "application/pdf": [".pdf"],
      "text/csv": [".csv"],
      "text/plain": [".txt"],
      "text/markdown": [".md"],
    },
    maxSize: 100 * 1024 * 1024,
    maxFiles: 5,
  });

  const removeFile = (idx: number) => {
    setFiles((prev) => prev.filter((_, i) => i !== idx));
  };

  const handleUpload = async () => {
    if (files.length === 0) return;
    setUploading(true);
    setError(null);

    try {
      const token = await getToken();
      const fileMetas = files.map((f) => ({
        filename: f.name,
        content_type: f.type || "application/pdf",
        size_bytes: f.size,
      }));

      const batchRes = await apiFetch("/api/documents/upload-batch", {
        method: "POST",
        body: JSON.stringify({ files: fileMetas }),
      }, token);

      const presigned = batchRes.presigned_urls as Array<{
        filename: string; upload_url: string; object_key: string; document_id: string;
      }>;

      await Promise.all(
        presigned.map(async (pu) => {
          const file = files.find((f) => f.name === pu.filename);
          if (!file) return;
          const resp = await fetch(pu.upload_url, {
            method: "PUT",
            body: file,
            headers: { "Content-Type": file.type || "application/pdf" },
          });
          if (!resp.ok) throw new Error(`Upload failed for ${pu.filename}`);
        })
      );

      await apiFetch("/api/documents/confirm-batch", {
        method: "POST",
        body: JSON.stringify({
          batch_id: batchRes.batch_id,
          files: presigned.map((pu) => ({
            object_key: pu.object_key,
            title: pu.filename,
          })),
        }),
      }, token);

      await fetchDocuments();
      setFiles([]);
      onClose();
    } catch (err: any) {
      setError(err.message || "Upload failed");
    } finally {
      setUploading(false);
    }
  };

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
      <div className="bg-gray-900 border border-gray-700 rounded-2xl w-full max-w-lg p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-white">Upload Documents</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-white">
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div
          {...getRootProps()}
          className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-colors ${
            isDragActive ? "border-purple-500 bg-purple-500/10" : "border-gray-600 hover:border-gray-500"
          }`}
        >
          <input {...getInputProps()} />
          <svg className="w-10 h-10 text-gray-500 mx-auto mb-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
          </svg>
          <p className="text-sm text-gray-300">Drag & drop files here, or click to browse</p>
          <p className="text-xs text-gray-500 mt-1">PDF, CSV, TXT, MD — up to 5 files, 100MB total</p>
        </div>

        {files.length > 0 && (
          <ul className="mt-4 space-y-2 max-h-48 overflow-y-auto">
            {files.map((f, idx) => (
              <li key={idx} className="flex items-center justify-between bg-gray-800 rounded-lg px-3 py-2 text-sm text-gray-300">
                <span className="truncate">{f.name}</span>
                <button onClick={() => removeFile(idx)} className="text-gray-500 hover:text-red-400 ml-2">
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </li>
            ))}
          </ul>
        )}

        {error && <p className="mt-3 text-sm text-red-400">{error}</p>}

        <div className="flex justify-end gap-3 mt-6">
          <button onClick={onClose} disabled={uploading} className="px-4 py-2 text-sm text-gray-400 hover:text-white transition-colors">
            Cancel
          </button>
          <button
            onClick={handleUpload}
            disabled={files.length === 0 || uploading}
            className="px-4 py-2 bg-purple-600 hover:bg-purple-500 disabled:bg-gray-700 disabled:text-gray-500 text-white rounded-lg text-sm font-medium transition-colors"
          >
            {uploading ? "Uploading..." : `Upload ${files.length} file${files.length !== 1 ? "s" : ""}`}
          </button>
        </div>
      </div>
    </div>
  );
}
