'use client';

import React, { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import {
  ShieldCheck,
  AlertTriangle,
  Lock,
  FileText,
  ArrowLeft,
  CheckCircle2,
  XCircle,
  HelpCircle,
  Info,
} from 'lucide-react';
import { apiService, VerificationReport } from '@/services/api';
import { MapView } from '@/components/MapView';
import { useAuth } from '@/contexts/AuthContext';

type ReviewAction = 'APPROVE' | 'REJECT' | 'MORE_INFO';

export default function HumanReviewPage() {
  const params = useParams();
  const verificationId = params.id as string;
  const { user, isLoading: authLoading, hasRole } = useAuth();

  const [report, setReport] = useState<VerificationReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [actionState, setActionState] = useState<{
    pending: boolean;
    result: 'success' | 'unavailable' | null;
    message: string | null;
  }>({ pending: false, result: null, message: null });

  useEffect(() => {
    if (!verificationId) return;
    const load = async () => {
      try {
        setLoading(true);
        const data = await apiService.getVerificationDetails(verificationId);
        setReport(data);
      } catch (err: any) {
        setError(err.response?.data?.detail || 'Failed to load record for review.');
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [verificationId]);

  // AI assists the authority; it never replaces the authority. This screen is
  // gated to Registrar/Admin roles, matching the backend's own RBAC model.
  if (!authLoading && !hasRole('REGISTRAR', 'ADMIN')) {
    return (
      <div className="max-w-lg mx-auto glass-panel p-8 rounded-2xl border border-amber-500/30 text-center space-y-4">
        <ShieldCheck className="w-10 h-10 text-amber-400 mx-auto" />
        <h2 className="text-lg font-bold text-white">Authority Access Required</h2>
        <p className="text-xs text-slate-400">
          This review workspace is restricted to Sub-Registrar and Administrator accounts.
          Switch roles using the account menu to view it.
        </p>
        <Link href="/dashboard" className="inline-block px-4 py-2 rounded-lg bg-emerald-600 text-white text-xs font-bold">
          Back to Dashboard
        </Link>
      </div>
    );
  }

  const handleDecision = async (action: ReviewAction) => {
    if (!report) return;
    setActionState({ pending: true, result: null, message: null });
    try {
      // The real, persisted review-decision endpoint lives in the Layer 11
      // orchestration API (/api/v1/verifications/{id}/review). Records created
      // through the currently-wired upload flow live in the legacy pipeline's
      // tables, which has no equivalent persisted decision field yet — so we
      // attempt the real call and report exactly what happens, rather than
      // pretending the decision was saved when it may not have been.
      const decision = action === 'APPROVE' ? 'APPROVE' : action === 'REJECT' ? 'REJECT' : 'MORE_INFO';
      await apiService.submitOrchestrationReview(verificationId, decision);
      setActionState({
        pending: false,
        result: 'success',
        message: `Decision "${decision}" recorded by the orchestration backend.`,
      });
    } catch (err: any) {
      setActionState({
        pending: false,
        result: 'unavailable',
        message:
          'This decision could not be persisted: this record was created via the legacy verification pipeline, which does not yet expose a review-decision endpoint. Wiring uploads through the Layer 11 orchestration API (already implemented server-side) would enable this.',
      });
    }
  };

  if (loading) {
    return (
      <div className="min-h-[60vh] flex flex-col items-center justify-center space-y-3">
        <div className="w-12 h-12 rounded-full border-4 border-emerald-500/20 border-t-emerald-500 animate-spin"></div>
        <p className="text-sm font-mono text-slate-400">Loading record for review...</p>
      </div>
    );
  }

  if (error || !report) {
    return (
      <div className="max-w-2xl mx-auto glass-panel p-8 rounded-2xl border border-red-500/30 text-center space-y-4">
        <AlertTriangle className="w-12 h-12 text-red-400 mx-auto" />
        <h2 className="text-xl font-bold text-white">Record Not Found</h2>
        <p className="text-xs text-slate-400">{error}</p>
      </div>
    );
  }

  return (
    <div className="max-w-5xl mx-auto space-y-6 pb-16">
      <Link href="/dashboard" className="inline-flex items-center text-xs font-mono text-slate-400 hover:text-emerald-400 transition">
        <ArrowLeft className="w-4 h-4 mr-1.5" />
        <span>Back to Command Center</span>
      </Link>

      <div className="glass-panel p-5 rounded-xl border border-purple-500/30 bg-purple-950/10 flex items-start gap-3">
        <Info className="w-5 h-5 text-purple-300 shrink-0 mt-0.5" />
        <p className="text-xs text-purple-200">
          This screen surfaces the system's automated findings to assist your decision. It does not
          make the decision for you — approval, rejection, or a request for more information is
          always a human, statutory action.
        </p>
      </div>

      {/* Summary */}
      <div className="glass-panel p-6 rounded-2xl border border-slate-800 space-y-2">
        <div className="flex items-center justify-between flex-wrap gap-2">
          <h1 className="text-xl font-bold text-white">
            Review: {report.document.extracted_fields.survey_number} — {report.verification_id}
          </h1>
          <span className="text-xs font-mono px-3 py-1 rounded-full bg-slate-800 text-slate-300 border border-slate-700">
            {report.overall_status}
          </span>
        </div>
        <p className="text-xs text-slate-400">
          Submitted document: <span className="text-slate-200 font-mono">{report.document.file_name}</span>
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Extracted fields + confidence */}
        <div className="glass-panel p-6 rounded-xl border border-slate-800 space-y-3">
          <h3 className="font-bold text-white text-sm flex items-center gap-2">
            <FileText className="w-4 h-4 text-blue-400" />
            <span>Extracted Fields</span>
          </h3>
          <div className="text-xs space-y-1.5">
            <div className="flex justify-between border-b border-slate-800/60 py-1">
              <span className="text-slate-400">Survey Number</span>
              <span className="font-mono text-white">{report.document.extracted_fields.survey_number}</span>
            </div>
            <div className="flex justify-between border-b border-slate-800/60 py-1">
              <span className="text-slate-400">District / Taluk / Village</span>
              <span className="text-white">
                {report.document.extracted_fields.district}, {report.document.extracted_fields.taluk}, {report.document.extracted_fields.village}
              </span>
            </div>
            <div className="flex justify-between border-b border-slate-800/60 py-1">
              <span className="text-slate-400">Area</span>
              <span className="font-mono text-white">{report.document.extracted_fields.area_sqft} sq.ft</span>
            </div>
            <div className="flex justify-between border-b border-slate-800/60 py-1">
              <span className="text-slate-400">Owner (masked)</span>
              <span className="font-mono text-white">{report.document.extracted_fields.owner_name_masked}</span>
            </div>
            <div className="flex justify-between py-1">
              <span className="text-slate-400">OCR Confidence</span>
              <span className="font-mono text-white">{Math.round(report.document.ocr_confidence * 100)}%</span>
            </div>
          </div>
        </div>

        {/* Integrity + GIS status */}
        <div className="glass-panel p-6 rounded-xl border border-slate-800 space-y-3">
          <h3 className="font-bold text-white text-sm flex items-center gap-2">
            <Lock className="w-4 h-4 text-purple-400" />
            <span>Integrity &amp; Spatial Status</span>
          </h3>
          <div className="text-xs space-y-1.5">
            <div className="flex justify-between border-b border-slate-800/60 py-1">
              <span className="text-slate-400">Document Hash Match</span>
              <span className={`font-mono ${report.authenticity.is_tampered ? 'text-red-400' : 'text-emerald-400'}`}>
                {report.authenticity.is_tampered ? 'MISMATCH' : 'MATCH'}
              </span>
            </div>
            <div className="flex justify-between border-b border-slate-800/60 py-1">
              <span className="text-slate-400">GIS Boundary Check</span>
              <span className={`font-mono ${report.spatial.overlap_detail.collision_detected ? 'text-red-400' : 'text-emerald-400'}`}>
                {report.spatial.overlap_detail.collision_detected ? 'COLLISION' : 'CLEAR'}
              </span>
            </div>
            <div className="flex justify-between border-b border-slate-800/60 py-1">
              <span className="text-slate-400">Overlap Area</span>
              <span className="font-mono text-white">{report.spatial.overlap_detail.overlap_area_sqm ?? 0} m²</span>
            </div>
            <div className="flex justify-between py-1">
              <span className="text-slate-400">Overall Confidence</span>
              <span className="font-mono text-white">{report.confidence_score}%</span>
            </div>
          </div>
        </div>
      </div>

      {/* Map */}
      <div className="glass-panel p-6 rounded-2xl border border-slate-800 space-y-3">
        <h3 className="font-bold text-white text-sm">Cadastral Map</h3>
        <MapView
          cadastralLayer={report.spatial.cadastral_layer_geojson}
          submittedPlot={report.spatial.submitted_plot_geojson}
          collisionPolygon={report.spatial.overlap_detail.collision_polygon_geojson}
          highlightSurvey={report.document.extracted_fields.survey_number}
          height="360px"
        />
      </div>

      {/* Decision actions */}
      <div className="glass-panel p-6 rounded-2xl border border-slate-800 space-y-4">
        <h3 className="font-bold text-white text-sm">Statutory Decision</h3>
        <div className="flex flex-wrap gap-3">
          <button
            onClick={() => handleDecision('APPROVE')}
            disabled={actionState.pending}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white text-xs font-bold transition"
          >
            <CheckCircle2 className="w-4 h-4" />
            <span>Approve</span>
          </button>
          <button
            onClick={() => handleDecision('REJECT')}
            disabled={actionState.pending}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-red-600 hover:bg-red-500 disabled:opacity-50 text-white text-xs font-bold transition"
          >
            <XCircle className="w-4 h-4" />
            <span>Reject</span>
          </button>
          <button
            onClick={() => handleDecision('MORE_INFO')}
            disabled={actionState.pending}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 disabled:opacity-50 text-slate-200 text-xs font-bold transition border border-slate-700"
          >
            <HelpCircle className="w-4 h-4" />
            <span>Request More Information</span>
          </button>
        </div>

        {actionState.message && (
          <div
            className={`p-3 rounded-lg border text-xs flex items-start gap-2 ${
              actionState.result === 'success'
                ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-300'
                : 'bg-amber-500/10 border-amber-500/30 text-amber-300'
            }`}
          >
            <Info className="w-4 h-4 shrink-0 mt-0.5" />
            <span>{actionState.message}</span>
          </div>
        )}
      </div>
    </div>
  );
}
