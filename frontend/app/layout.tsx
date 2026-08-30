import './globals.css';
import type { Metadata } from 'next';
import { Navbar } from '@/components/Navbar';
import { AuthProvider } from '@/contexts/AuthContext';
import { AuthModal } from '@/components/AuthModal';

export const metadata: Metadata = {
  title: 'PlotProof — Digital Land Verification Platform',
  description: 'Forensic-grade automated land title deed verification powered by Document OCR, GIS Cadastral Overlap Analysis, SHA-256 Blockchain Registry, and ZK Privacy.',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="bg-[#0a0f1d] text-slate-100 min-h-screen flex flex-col antialiased selection:bg-emerald-500/30 selection:text-emerald-200 font-sans">
        <AuthProvider>
          <Navbar />
          <AuthModal />
          <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6">
            {children}
          </main>
          
          {/* Footer */}
          <footer className="border-t border-slate-800/80 bg-slate-950/60 py-6 text-center text-xs text-slate-500 font-mono">
            <div className="max-w-7xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-4">
              <div className="flex items-center space-x-2">
                <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
                <span>PlotProof Land Registry & Forensic Trust Engine • Hackathon MVP</span>
              </div>
              <div className="flex items-center space-x-4 text-slate-400">
                <span>FastAPI</span>
                <span>•</span>
                <span>PostGIS</span>
                <span>•</span>
                <span>Solidity Blockchain</span>
                <span>•</span>
                <span>ZK Privacy</span>
              </div>
            </div>
          </footer>
        </AuthProvider>
      </body>
    </html>
  );
}
