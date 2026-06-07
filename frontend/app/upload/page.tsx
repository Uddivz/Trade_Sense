/**
 * TradeSense — Upload Page Placeholder
 * Full drag-and-drop upload implementation built during Week 4.
 */
export const metadata = {
  title: "Upload Trade History",
};

export default function UploadPage() {
  return (
    <div className="min-h-screen bg-slate-900 flex items-center justify-center">
      <div className="text-center max-w-md px-6">
        <div className="text-6xl mb-6">📤</div>
        <h1 className="text-3xl font-bold text-white mb-3">Upload Trade History</h1>
        <p className="text-slate-400">
          CSV upload with drag-and-drop — implemented in Week 2 backend + Week 4 frontend.
        </p>
      </div>
    </div>
  );
}
