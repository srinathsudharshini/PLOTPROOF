'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { 
  ShieldCheck, 
  AlertTriangle, 
  Clock, 
  Lock, 
  UploadCloud, 
  MapPin, 
  FileCheck, 
  ArrowUpRight, 
  RefreshCw,
  Search,
  ExternalLink,
  ChevronRight
} from 'lucide-react';
import { apiService } from '@/services/api';
import { useAuth } from '@/contexts/AuthContext';

export default function DashboardPage() {
  const { hasRole } = useAuth();
  // No hardcoded/mock starting values: null means "not yet loaded from the backend".
  const [stats, setStats] = useState<any>(null);
  const [statsError, setStatsError] = useState<string | null>(null);

  const [recentList, setRecentList] = useState<any[]>([]);
  const [recentListError, setRecentListError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchDashboardData = async () => {
    try {
      setLoading(true);
      setStatsError(null);
      setRecentListError(null);

      const [statsResult, listResult] = await Promise.allSettled([
        apiService.getStatsSummary(),
        apiService.getRecentVerifications(),
      ]);

      if (statsResult.status === 'fulfilled') {
        setStats(statsResult.value);
      } else {
        setStats(null);
        setStatsError('Statistics service is currently unavailable.');
      }

      if (listResult.status === 'fulfilled') {
        setRecentList(listResult.value || []);
      } else {
        setRecentList([]);
        setRecentListError('Recent verifications could not be loaded.');
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'VERIFIED':
        return (
          <span className="inline-flex items-center px-2.5 py-1 rounded-md text-xs font-bold bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">
            ✓ VERIFIED
          </span>
        );
      case 'SPATIAL_COLLISION':
        return (
          <span className="inline-flex items-center px-2.5 py-1 rounded-md text-xs font-bold bg-red-500/15 text-red-400 border border-red-500/30">
            ⚠ COLLISION
          </span>
        );
      case 'TAMPER_ALERT':
        return (
          <span className="inline-flex items-center px-2.5 py-1 rounded-md text-xs font-bold bg-purple-500/15 text-purple-400 border border-purple-500/30">
            ⚠ TAMPER ALERT
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center px-2.5 py-1 rounded-md text-xs font-bold bg-amber-500/15 text-amber-400 border border-amber-500/30">
            ● REVIEW REQUIRED
          </span>
        );
    }
  };

  return (
    <div className="space-y-8">
      
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2 text-xs font-mono text-emerald-400 mb-1">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
            <span>NATIONAL LAND RECORD MODERNIZATION AUDIT STREAM</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
            Land Verification Command Center
          </h1>
        </div>

        <div className="flex items-center space-x-3">
          <button
            onClick={fetchDashboardData}
            className="flex items-center space-x-1.5 px-3 py-2 rounded-lg glass-panel hover:bg-slate-800 text-slate-300 text-xs font-medium border border-slate-700 transition"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </button>
          
          <Link
            href="/upload"
            className="flex items-center space-x-2 px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold shadow-lg shadow-emerald-600/20 transition active:scale-95"
          >
            <UploadCloud className="w-4 h-4" />
            <span>Verify New Deed</span>
          </Link>
        </div>
      </div>

      {statsError && (
        <div className="p-3 rounded-lg bg-amber-500/10 border border-amber-500/30 text-amber-300 text-xs flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 shrink-0" />
          <span>{statsError} Figures below are omitted rather than estimated.</span>
        </div>
      )}

      {/* 4 Stat Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        
        {/* Verified Card */}
        <div className="glass-panel p-5 rounded-xl border border-emerald-500/30 bg-emerald-950/10 relative overflow-hidden">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Verified Titles</span>
            <div className="p-2 rounded-lg bg-emerald-500/20 text-emerald-400">
              <ShieldCheck className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-3">
            <div className="text-3xl font-black text-white">{stats ? stats.verified_count : '—'}</div>
            <p className="text-xs text-emerald-400 mt-1 flex items-center gap-1 font-medium">
              <span>Passed integrity, GIS &amp; OCR checks</span>
            </p>
          </div>
        </div>

        {/* Collisions Card */}
        <div className="glass-panel p-5 rounded-xl border border-red-500/30 bg-red-950/10 relative overflow-hidden">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Boundary Collisions</span>
            <div className="p-2 rounded-lg bg-red-500/20 text-red-400">
              <AlertTriangle className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-3">
            <div className="text-3xl font-black text-white">{stats ? stats.collision_count : '—'}</div>
            <p className="text-xs text-red-400 mt-1 flex items-center gap-1 font-medium">
              <span>Overlaps intercepted</span>
            </p>
          </div>
        </div>

        {/* Pending Review Card */}
        <div className="glass-panel p-5 rounded-xl border border-amber-500/30 bg-amber-950/10 relative overflow-hidden">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Pending Review</span>
            <div className="p-2 rounded-lg bg-amber-500/20 text-amber-400">
              <Clock className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-3">
            <div className="text-3xl font-black text-white">{stats ? stats.pending_count : '—'}</div>
            <p className="text-xs text-amber-400 mt-1 font-medium">
              <span>Awaiting manual surveyor signoff</span>
            </p>
          </div>
        </div>

        {/* Tamper Alerts Card */}
        <div className="glass-panel p-5 rounded-xl border border-purple-500/30 bg-purple-950/10 relative overflow-hidden">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Tamper Interceptions</span>
            <div className="p-2 rounded-lg bg-purple-500/20 text-purple-400">
              <Lock className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-3">
            <div className="text-3xl font-black text-white">{stats ? stats.tamper_count : '—'}</div>
            <p className="text-xs text-purple-300 mt-1 font-medium">
              <span>SHA-256 Hash Mismatches</span>
            </p>
          </div>
        </div>

      </div>

      {/* Main Table + Quick Visualizer Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Recent Verifications Stream (2 cols) */}
        <div className="lg:col-span-2 glass-panel rounded-xl border border-slate-800 shadow-xl overflow-hidden">
          <div className="p-5 border-b border-slate-800 flex items-center justify-between">
            <div>
              <h2 className="text-base font-bold text-white flex items-center gap-2">
                <FileCheck className="w-4 h-4 text-emerald-400" />
                <span>Recent Land Title Verifications</span>
              </h2>
              <p className="text-xs text-slate-400 mt-0.5">Real-time cadastral verification stream and blockchain timestamps</p>
            </div>
            <span className="text-xs font-mono text-slate-400">Live Audit Queue</span>
          </div>

          <div className="overflow-x-auto">
            {recentListError && (
              <div className="p-3 m-4 rounded-lg bg-amber-500/10 border border-amber-500/30 text-amber-300 text-xs flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 shrink-0" />
                <span>{recentListError}</span>
              </div>
            )}
            {!recentListError && !loading && recentList.length === 0 && (
              <div className="p-8 text-center text-xs text-slate-500">
                No verifications have been run yet. Upload a deed to see it appear here.
              </div>
            )}
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-900/80 text-slate-400 uppercase font-mono text-[10px] border-b border-slate-800">
                <tr>
                  <th className="py-3 px-4">Verification ID</th>
                  <th className="py-3 px-4">Survey No</th>
                  <th className="py-3 px-4">Location</th>
                  <th className="py-3 px-4">Area (sq.ft)</th>
                  <th className="py-3 px-4">Verdict Status</th>
                  <th className="py-3 px-4 text-right">Confidence</th>
                  <th className="py-3 px-4 text-center">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-medium">
                {recentList.map((item) => (
                  <tr key={item.verification_id} className="hover:bg-slate-800/40 transition-colors">
                    <td className="py-3.5 px-4 font-mono text-emerald-400 font-bold">
                      {item.verification_id}
                    </td>
                    <td className="py-3.5 px-4 text-white font-semibold">
                      {item.survey_number}
                    </td>
                    <td className="py-3.5 px-4 text-slate-300">
                      {item.district || 'Chennai'}
                    </td>
                    <td className="py-3.5 px-4 font-mono text-slate-300">
                      {item.area_sqft} sq.ft
                    </td>
                    <td className="py-3.5 px-4">
                      {getStatusBadge(item.status)}
                    </td>
                    <td className="py-3.5 px-4 text-right font-mono text-slate-200">
                      {item.confidence_score}%
                    </td>
                    <td className="py-3.5 px-4 text-center">
                      <div className="flex items-center justify-center gap-3">
                        <Link
                          href={`/verification/${item.verification_id}`}
                          className="inline-flex items-center text-xs font-semibold text-emerald-400 hover:text-emerald-300 transition"
                        >
                          <span>Audit</span>
                          <ChevronRight className="w-3.5 h-3.5 ml-0.5" />
                        </Link>
                        {hasRole('REGISTRAR', 'ADMIN') && (
                          <Link
                            href={`/review/${item.verification_id}`}
                            className="inline-flex items-center text-xs font-semibold text-purple-300 hover:text-purple-200 transition"
                          >
                            <span>Review</span>
                            <ChevronRight className="w-3.5 h-3.5 ml-0.5" />
                          </Link>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Sidebar Mini Action Panel (1 col) */}
        <div className="space-y-5">
          
          {/* Quick GIS Map Card */}
          <div className="glass-panel p-5 rounded-xl border border-slate-800 shadow-xl space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="font-bold text-white text-sm flex items-center gap-2">
                <MapPin className="w-4 h-4 text-emerald-400" />
                <span>Cadastral GIS Explorer</span>
              </h3>
              <Link href="/map" className="text-xs text-emerald-400 hover:underline flex items-center gap-1">
                <span>Full Map</span>
                <ExternalLink className="w-3 h-3" />
              </Link>
            </div>
            
            <p className="text-xs text-slate-300 leading-relaxed">
              Explore Selaiyur village cadastral parcels, examine bounding polygons, and visualize real-time collision boundaries.
            </p>

            <div className="p-3 bg-slate-900 rounded-lg border border-slate-800 text-xs font-mono space-y-1.5 text-slate-300">
              <div className="flex justify-between">
                <span className="text-slate-400">Total Registered Plots:</span>
                <span className="text-white font-bold">5 Parcels</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Cadastral Cluster:</span>
                <span className="text-emerald-400">Survey 142/1-5</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Topology Integrity:</span>
                <span className="text-emerald-400">99.8%</span>
              </div>
            </div>

            <Link
              href="/map"
              className="w-full py-2.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold flex items-center justify-center space-x-2 border border-slate-700 transition"
            >
              <span>Launch Cadastral Viewer</span>
              <ArrowUpRight className="w-4 h-4 text-emerald-400" />
            </Link>
          </div>

          {/* Trust Guarantee Banner */}
          <div className="glass-panel p-5 rounded-xl border border-emerald-500/20 bg-emerald-950/20 space-y-3">
            <div className="flex items-center space-x-2 text-emerald-400 font-bold text-sm">
              <ShieldCheck className="w-4 h-4" />
              <span>Immutable Audit Trail</span>
            </div>
            <p className="text-xs text-slate-300 leading-relaxed">
              Every verification generates a canonical SHA-256 fingerprint anchored to Polygon blockchain smart contracts. No citizen PII is ever exposed publicly.
            </p>
          </div>

        </div>

      </div>

    </div>
  );
}
