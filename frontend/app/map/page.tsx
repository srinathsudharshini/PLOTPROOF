'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { 
  MapPin, 
  Layers, 
  ShieldCheck, 
  AlertTriangle, 
  Search, 
  ArrowLeft, 
  Compass, 
  Filter,
  Info,
  CheckCircle2
} from 'lucide-react';
import { apiService } from '@/services/api';
import { MapView } from '@/components/MapView';

export default function GISMapPage() {
  const [cadastralData, setCadastralData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'all' | 'collision_demo'>('all');
  const [selectedSurvey, setSelectedSurvey] = useState<string>('142/3A');

  useEffect(() => {
    const fetchGISData = async () => {
      try {
        setLoading(true);
        setLoadError(null);
        const data = await apiService.getCadastralLayer();
        setCadastralData(data);
      } catch (e: any) {
        console.error(e);
        setCadastralData(null);
        setLoadError(
          e.response
            ? 'The GIS service returned an error while loading the cadastral layer.'
            : 'Could not reach the backend GIS service.'
        );
      } finally {
        setLoading(false);
      }
    };

    fetchGISData();
  }, []);

  // Demo collision plot geometry for Survey 142/3B
  const collisionSubmittedPlot = {
    type: 'Feature',
    properties: { survey_number: '142/3B (Submitted Encroachment)', status: 'COLLISION' },
    geometry: {
      type: 'Polygon',
      coordinates: [[
        [80.1476, 12.9252],
        [80.1476, 12.9258],
        [80.1482, 12.9258],
        [80.1482, 12.9252],
        [80.1476, 12.9252]
      ]]
    }
  };

  const collisionIntersection = {
    type: 'Polygon',
    coordinates: [[
      [80.1476, 12.9252],
      [80.1476, 12.9255],
      [80.1478, 12.9255],
      [80.1478, 12.9252],
      [80.1476, 12.9252]
    ]]
  };

  return (
    <div className="space-y-6 pb-12">
      
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2 text-xs font-mono text-emerald-400 mb-1">
            <span className="w-2 h-2 rounded-full bg-emerald-400"></span>
            <span>CADASTRAL TOPOLOGICAL INTELLIGENCE LAYER</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-white">
            GIS Cadastral Reference Map
          </h1>
        </div>

        {/* View Mode Toggle */}
        <div className="flex items-center space-x-2 bg-slate-900 p-1 rounded-xl border border-slate-800">
          <button
            onClick={() => setActiveTab('all')}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition ${
              activeTab === 'all'
                ? 'bg-emerald-600 text-white shadow'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            Cadastral Base Map
          </button>
          <button
            onClick={() => setActiveTab('collision_demo')}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center space-x-1.5 transition ${
              activeTab === 'collision_demo'
                ? 'bg-red-600 text-white shadow'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            <AlertTriangle className="w-3.5 h-3.5" />
            <span>Simulate Overlap Collision</span>
          </button>
        </div>
      </div>

      {/* Map + Sidebar Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        
        {/* Main Map View (3 cols) */}
        <div className="lg:col-span-3 space-y-4">
          {loadError && (
            <div className="glass-panel p-4 rounded-xl border border-amber-500/40 bg-amber-950/20 flex items-center gap-3 text-xs text-amber-300">
              <AlertTriangle className="w-5 h-5 shrink-0" />
              <span>{loadError} The map below may be showing an empty base layer.</span>
            </div>
          )}
          <div className="glass-panel p-2 rounded-2xl border border-slate-800 shadow-2xl">
            <MapView
              cadastralLayer={cadastralData}
              submittedPlot={activeTab === 'collision_demo' ? collisionSubmittedPlot : undefined}
              collisionPolygon={activeTab === 'collision_demo' ? collisionIntersection : undefined}
              highlightSurvey={selectedSurvey}
              height="580px"
            />
          </div>

          {activeTab === 'collision_demo' && (
            <div className="glass-panel p-4 rounded-xl border border-red-500/40 bg-red-950/20 flex items-center justify-between gap-4 animate-in fade-in">
              <div className="flex items-center space-x-3">
                <AlertTriangle className="w-6 h-6 text-red-400 animate-pulse" />
                <div>
                  <h3 className="font-bold text-white text-sm">Spatial Collision Intercepted: 17.8 sq.m</h3>
                  <p className="text-xs text-red-300 mt-0.5">
                    Submitted plot for Survey 142/3B infringes upon registered title Survey 142/3A.
                  </p>
                </div>
              </div>
              <Link
                href="/upload?preset=collision"
                className="px-3.5 py-1.5 rounded-lg bg-red-600 hover:bg-red-500 text-white text-xs font-bold whitespace-nowrap transition"
              >
                Run Forensic Report
              </Link>
            </div>
          )}
        </div>

        {/* Sidebar Parcel Inspector (1 col) */}
        <div className="space-y-4">
          
          <div className="glass-panel p-5 rounded-xl border border-slate-800 space-y-4">
            <h3 className="font-bold text-white text-sm flex items-center gap-2">
              <Compass className="w-4 h-4 text-emerald-400" />
              <span>Registered Cadastral Parcels</span>
            </h3>

            <p className="text-xs text-slate-400">
              Select a parcel in Selaiyur village to highlight its bounding polygon on the map.
            </p>

            <div className="space-y-2">
              {[
                { sNo: '142/1', area: '2400 sq.ft', type: 'Residential Property', color: 'border-blue-500' },
                { sNo: '142/2', area: '4800 sq.ft', type: 'Govt 30ft Road', color: 'border-cyan-500' },
                { sNo: '142/3A', area: '2400 sq.ft', type: 'Registered Title', color: 'border-emerald-500' },
                { sNo: '142/4', area: '2400 sq.ft', type: 'Vacant Plot', color: 'border-slate-500' },
                { sNo: '142/5', area: '3000 sq.ft', type: 'Commercial Plot', color: 'border-purple-500' },
              ].map((p) => (
                <button
                  key={p.sNo}
                  onClick={() => setSelectedSurvey(p.sNo)}
                  className={`w-full p-3 rounded-lg border text-left transition text-xs flex items-center justify-between ${
                    selectedSurvey === p.sNo
                      ? 'bg-slate-800 border-emerald-400 text-white shadow-sm'
                      : 'bg-slate-900/60 border-slate-800 hover:border-slate-700 text-slate-300'
                  }`}
                >
                  <div>
                    <div className="font-bold font-mono text-sm text-emerald-400">Survey {p.sNo}</div>
                    <div className="text-[11px] text-slate-400">{p.type}</div>
                  </div>
                  <span className="font-mono text-slate-300 text-[11px]">{p.area}</span>
                </button>
              ))}
            </div>
          </div>

          <div className="glass-panel p-4 rounded-xl border border-slate-800 space-y-2 text-xs text-slate-300">
            <span className="font-bold text-white flex items-center gap-1.5">
              <Info className="w-3.5 h-3.5 text-emerald-400" />
              <span>Topological Standard</span>
            </span>
            <p className="text-[11px] text-slate-400 leading-relaxed">
              Spatial layers adhere to Open Geospatial Consortium (OGC) Simple Feature Access standards with EPSG:4326 coordinate geometry.
            </p>
          </div>

        </div>

      </div>

    </div>
  );
}
