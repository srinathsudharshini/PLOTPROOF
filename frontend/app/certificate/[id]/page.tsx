'use client';

import React, { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { 
  ShieldCheck, 
  Printer, 
  Download, 
  ArrowLeft, 
  QrCode, 
  CheckCircle2, 
  ExternalLink,
  Award,
  Lock,
  Building
} from 'lucide-react';
import { apiService, VerificationReport } from '@/services/api';

export default function CertificatePage() {
  const params = useParams();
  const verificationId = params.id as string;

  const [report, setReport] = useState<VerificationReport | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!verificationId) return;

    const load = async () => {
      try {
        setLoading(true);
        const data = await apiService.getVerificationDetails(verificationId);
        setReport(data);
      } catch (e) {
        console.error(e);
      } finally {
        setLoading(false);
      }
    };

    load();
  }, [verificationId]);

  if (loading) {
    return (
      <div className="min-h-[60vh] flex flex-col items-center justify-center space-y-3">
        <div className="w-12 h-12 rounded-full border-4 border-emerald-500/20 border-t-emerald-500 animate-spin"></div>
        <p className="text-sm font-mono text-slate-400">Rendering Digital Land Certificate...</p>
      </div>
    );
  }

  if (!report) {
    return (
      <div className="text-center py-12">
        <h2 className="text-xl font-bold text-white">Certificate Not Found</h2>
      </div>
    );
  }

  const handlePrint = () => {
    window.print();
  };

  const isVerified = report.overall_status === 'VERIFIED';

  // A certificate should never be presented as a clean, issued document for a
  // record that the backend has not actually marked VERIFIED. Show the real
  // status and why, instead of a document that looks official either way.
  if (!isVerified) {
    const reasons: string[] = [];
    if (report.spatial?.overlap_detail?.collision_detected) {
      reasons.push(
        `Boundary overlap detected against survey ${
          report.spatial.overlap_detail.affected_surveys?.join(', ') || 'a registered parcel'
        } (${report.spatial.overlap_detail.overlap_area_sqm ?? '?'} m² overlap).`
      );
    }
    if (report.authenticity?.is_tampered) {
      reasons.push('Document fingerprint does not match the registered hash — possible tampering.');
    }
    if (report.document?.ocr_confidence !== undefined && report.document.ocr_confidence < 0.7) {
      reasons.push('OCR extraction confidence was too low for automated approval.');
    }
    if (reasons.length === 0) {
      reasons.push('This record has not yet cleared all automated verification checks.');
    }

    return (
      <div className="max-w-2xl mx-auto space-y-6 pb-16">
        <Link
          href={`/verification/${verificationId}`}
          className="inline-flex items-center text-xs font-mono text-slate-400 hover:text-emerald-400 transition"
        >
          <ArrowLeft className="w-4 h-4 mr-1.5" />
          <span>Back to Forensic Report</span>
        </Link>

        <div className="glass-panel p-8 rounded-2xl border border-amber-500/40 text-center space-y-4">
          <ShieldCheck className="w-12 h-12 text-amber-400 mx-auto" />
          <h2 className="text-xl font-bold text-white">Certificate Not Available</h2>
          <p className="text-xs text-slate-400">
            Current status: <span className="font-mono text-amber-400">{report.overall_status}</span>
          </p>
          <p className="text-xs text-slate-400">
            A PlotProof certificate can only be issued once a document is fully VERIFIED.
            This record was not, for the following reason(s):
          </p>
          <ul className="text-xs text-slate-300 text-left list-disc list-inside space-y-1 bg-slate-950/60 p-4 rounded-xl border border-slate-800">
            {reasons.map((r, i) => (
              <li key={i}>{r}</li>
            ))}
          </ul>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto space-y-6 pb-16">
      
      {/* Top Bar Actions (Hidden in Print) */}
      <div className="flex items-center justify-between print:hidden">
        <Link
          href={`/verification/${verificationId}`}
          className="inline-flex items-center text-xs font-mono text-slate-400 hover:text-emerald-400 transition"
        >
          <ArrowLeft className="w-4 h-4 mr-1.5" />
          <span>Back to Forensic Report</span>
        </Link>

        <div className="flex items-center space-x-3">
          <button
            onClick={handlePrint}
            className="flex items-center space-x-1.5 px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold shadow transition active:scale-95"
          >
            <Printer className="w-4 h-4" />
            <span>Print Official Certificate</span>
          </button>
        </div>
      </div>

      {/* Official Certificate Layout */}
      <div className="relative bg-gradient-to-b from-slate-900 via-slate-900 to-slate-950 p-8 sm:p-12 rounded-2xl border-4 border-double border-emerald-500/40 shadow-2xl text-slate-100 print:border-emerald-700 print:text-black print:bg-white overflow-hidden">
        
        {/* Certificate Watermark Background */}
        <div className="absolute inset-0 flex items-center justify-center opacity-5 pointer-events-none">
          <ShieldCheck className="w-[450px] h-[450px] text-emerald-500" />
        </div>

        {/* Certificate Header */}
        <div className="text-center space-y-2 border-b-2 border-slate-800 pb-6 relative z-10">
          <div className="flex items-center justify-center space-x-3">
            <div className="w-12 h-12 rounded-xl bg-emerald-500/20 border border-emerald-500/40 flex items-center justify-center text-emerald-400">
              <Award className="w-7 h-7" />
            </div>
          </div>

          <h1 className="text-xl sm:text-2xl font-black tracking-widest text-emerald-400 uppercase font-mono mt-2">
            PLOTPROOF DIGITAL LAND TITLE CERTIFICATE
          </h1>
          <p className="text-xs text-slate-400 tracking-wider uppercase font-mono">
            Government Cadastral Verification & Immutable Blockchain Registry
          </p>
        </div>

        {/* Main Certificate Content */}
        <div className="py-8 space-y-6 relative z-10">
          
          <div className="text-center space-y-1">
            <span className="text-xs text-slate-400 uppercase tracking-widest font-mono">THIS IS TO ATTEST AND CERTIFY THAT</span>
            <h2 className="text-lg font-bold text-white">
              Land Parcel Survey Number: <span className="text-emerald-400 font-mono">{report.document.extracted_fields.survey_number}</span>
            </h2>
            <p className="text-xs text-slate-300">
              Located in {report.document.extracted_fields.village}, {report.document.extracted_fields.taluk} Taluk, {report.document.extracted_fields.district} District
            </p>
          </div>

          {/* Key Metrics Grid */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 p-4 rounded-xl bg-slate-950/60 border border-slate-800 text-xs">
            <div className="space-y-0.5">
              <span className="text-[10px] font-mono text-slate-500 uppercase">Verification ID</span>
              <div className="font-mono font-bold text-emerald-400">{report.verification_id}</div>
            </div>
            <div className="space-y-0.5">
              <span className="text-[10px] font-mono text-slate-500 uppercase">Area Extent</span>
              <div className="font-mono font-bold text-white">{report.document.extracted_fields.area_sqft} sq.ft</div>
            </div>
            <div className="space-y-0.5">
              <span className="text-[10px] font-mono text-slate-500 uppercase">Spatial Status</span>
              <div className="font-mono font-bold text-emerald-400">
                {report.spatial.overlap_detail.collision_detected ? '⚠ Overlap Detected' : '✓ 0 Overlaps (Clean)'}
              </div>
            </div>
            <div className="space-y-0.5">
              <span className="text-[10px] font-mono text-slate-500 uppercase">Integrity Verdict</span>
              <div className="font-mono font-bold text-emerald-400">
                {report.authenticity.is_tampered ? '⚠ Tamper Detected' : '✓ Authentic Title'}
              </div>
            </div>
          </div>

          {/* Boundaries Table */}
          <div className="border border-slate-800 rounded-xl p-4 bg-slate-950/40 text-xs space-y-2">
            <span className="font-bold text-slate-300 font-mono text-[11px] uppercase">Registered Cadastral Boundaries:</span>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-slate-300 text-[11px]">
              <div><strong>North:</strong> {report.document.extracted_fields.boundaries.north}</div>
              <div><strong>South:</strong> {report.document.extracted_fields.boundaries.south}</div>
              <div><strong>East:</strong> {report.document.extracted_fields.boundaries.east}</div>
              <div><strong>West:</strong> {report.document.extracted_fields.boundaries.west}</div>
            </div>
          </div>

          {/* Cryptographic Seal & QR Verification Section */}
          <div className="flex flex-col sm:flex-row items-center justify-between gap-6 pt-4 border-t-2 border-slate-800">
            
            {/* Blockchain Details */}
            <div className="space-y-2 flex-1 text-xs">
              <div className="flex items-center space-x-1.5 text-emerald-400 font-bold font-mono">
                <Lock className="w-4 h-4" />
                <span>Cryptographic Document Fingerprint:</span>
              </div>
              <div className="font-mono text-[11px] text-slate-400 bg-slate-950 p-2 rounded border border-slate-800 break-all select-all">
                {report.authenticity.document_hash}
              </div>

              <div className="text-[11px] text-slate-400 space-y-0.5 font-mono">
                <div>Polygon Tx: <span className="text-purple-400">{report.blockchain.transaction_hash}</span></div>
                <div>Block Height: <span className="text-slate-300">#{report.blockchain.block_number}</span></div>
              </div>
            </div>

            {/* Scannable QR Code */}
            <div className="flex flex-col items-center space-y-2 p-3 bg-white rounded-xl shadow-lg border border-slate-300">
              <img
                src={report.qr_code_url || `/static/certificates/qr_${report.verification_id}.png`}
                alt="Verification QR Code"
                className="w-28 h-28 object-contain"
                onError={(e: any) => {
                  e.target.src = `https://api.qrserver.com/v1/create-qr-code/?size=150x150&data=http://localhost:3000/verify/${report.authenticity.document_hash}`;
                }}
              />
              <span className="text-[9px] font-mono font-bold text-slate-900 uppercase">
                Scan to Independently Verify
              </span>
            </div>

          </div>

        </div>

        {/* Certificate Footer */}
        <div className="pt-4 border-t border-slate-800/80 flex items-center justify-between text-[10px] font-mono text-slate-500 relative z-10">
          <span>PLOTPROOF PROTOCOL v1.0 • STATE AUDIT NETWORK</span>
          <span>ISSUED: {new Date(report.created_at).toLocaleDateString()}</span>
        </div>

      </div>

    </div>
  );
}
