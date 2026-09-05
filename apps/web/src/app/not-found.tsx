import Link from "next/link";

export default function NotFound() {
  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-[#07090d] text-white p-6">
      <div className="text-center max-w-md space-y-4">
        <h1 className="text-4xl font-bold tracking-tight text-amber-500 font-mono">404</h1>
        <h2 className="text-xl font-semibold text-gray-200">Page Not Found</h2>
        <p className="text-sm text-gray-400">
          The requested tactical intelligence coordinate or view could not be located.
        </p>
        <div className="pt-4">
          <Link
            href="/"
            className="inline-flex items-center justify-center px-4 py-2 text-xs font-mono font-medium text-black bg-amber-400 hover:bg-amber-300 rounded transition-colors"
          >
            RETURN TO COMMAND CENTER
          </Link>
        </div>
      </div>
    </div>
  );
}
