'use client';

import { useState, useEffect } from 'react';
import CameraFeed from '@/components/CameraFeed';
import ControlPanel from '@/components/ControlPanel';
import { Settings, Gesture } from '@/lib/types';
import { CameraInfo } from '@/lib/types';

const API_URL = 'http://localhost:8000';
const WS_URL = 'ws://localhost:8000/ws/gestures';

export default function Home() {
  const [isRunning, setIsRunning] = useState(false);
  const [isConnected, setIsConnected] = useState(false);
  const [cameras, setCameras] = useState<CameraInfo[]>([]);
  const [stats, setStats] = useState({
    fps: 0,
    volume: 50,
    brightness: 50
  });
  const [lastGesture, setLastGesture] = useState<Gesture | null>(null);

  const [settings, setSettings] = useState<Settings>({
    desktop_control: true,
    volume_control: true,
    brightness_control: true,
    swipe_sensitivity: 100,
    cooldown: 0.75,
    selected_camera: "0"
  });

  // Fetch initial state
  useEffect(() => {
    fetchCameras();
    fetchSettings();
    checkStatus();

    // Poll status every 2 seconds
    const interval = setInterval(checkStatus, 2000);
    return () => clearInterval(interval);
  }, []);

  const fetchCameras = async () => {
    try {
      const res = await fetch(`${API_URL}/cameras`);
      const data = await res.json();
      setCameras(data.cameras);
    } catch (e) {
      console.error('Failed to fetch cameras', e);
    }
  };

  const fetchSettings = async () => {
    try {
      const res = await fetch(`${API_URL}/settings`);
      const data = await res.json();
      setSettings(data);
    } catch (e) {
      console.error('Failed to fetch settings', e);
    }
  };

  const checkStatus = async () => {
    try {
      const res = await fetch(`${API_URL}/stats`);
      const data = await res.json();
      setIsRunning(data.is_running);
      setIsConnected(true);
      setStats(prev => ({
        ...prev,
        volume: data.volume,
        brightness: data.brightness
      }));
    } catch (e) {
      setIsConnected(false);
    }
  };

  const toggleSystem = async () => {
    try {
      const endpoint = isRunning ? 'stop' : 'start';
      await fetch(`${API_URL}/${endpoint}`, { method: 'POST' });
      setIsRunning(!isRunning);
    } catch (e) {
      console.error('Failed to toggle system', e);
    }
  };

  const updateSetting = async (key: keyof Settings, value: any) => {
    const newSettings = { ...settings, [key]: value };
    setSettings(newSettings);

    try {
      await fetch(`${API_URL}/settings`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newSettings)
      });
    } catch (e) {
      console.error('Failed to update settings', e);
    }
  };

  const handleStatsUpdate = (newStats: { fps: number; gestures: Gesture[] }) => {
    setStats(prev => ({ ...prev, fps: newStats.fps }));
    if (newStats.gestures.length > 0) {
      setLastGesture(newStats.gestures[0]);

      // Clear gesture after animation
      setTimeout(() => setLastGesture(null), 2000);
    }
  };

  return (
    <main className="min-h-screen bg-[#050505] text-white p-4 md:p-8 font-sans selection:bg-cyan-500/30">
      <div className="max-w-7xl mx-auto space-y-8">

        {/* Navbar */}
        <header className="flex items-center justify-between py-4 border-b border-white/5">
          <div className="flex items-center gap-4">
            <h1 className="text-3xl font-black tracking-tighter bg-clip-text text-transparent bg-gradient-to-r from-cyan-400 via-purple-500 to-pink-500">
              EYES
            </h1>
            <div className="px-3 py-1 bg-white/5 rounded-full border border-white/5 flex items-center gap-2">
              <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500 shadow-[0_0_10px_rgba(34,197,94,0.8)]' : 'bg-red-500'}`}></div>
              <span className="text-xs font-mono text-gray-400">
                {isConnected ? 'CONNECTED' : 'OFFLINE'}
              </span>
            </div>
          </div>

          <button
            onClick={toggleSystem}
            className={`
              px-8 py-3 rounded-full font-bold tracking-widest text-sm transition-all duration-300
              ${isRunning
                ? 'bg-red-500/10 text-red-500 border border-red-500/50 hover:bg-red-500/20'
                : 'bg-cyan-500 text-black hover:bg-cyan-400 hover:shadow-[0_0_20px_rgba(6,182,212,0.5)]'
              }
            `}
          >
            {isRunning ? 'STOP SYSTEM' : 'INITIALIZE'}
          </button>
        </header>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">

          {/* Left Column: Camera Feed */}
          <div className="lg:col-span-2 space-y-6">
            <div className="relative group">
              <CameraFeed
                wsUrl={WS_URL}
                isConnected={isRunning}
                onStatsUpdate={handleStatsUpdate}
              />

              {/* FPS Counter */}
              <div className="absolute top-6 right-6 bg-black/60 backdrop-blur px-3 py-1 rounded text-xs font-mono text-cyan-400 border border-white/10">
                {Math.round(stats.fps)} FPS
              </div>
            </div>

            {/* Recent Gestures Log */}
            <div className="bg-white/5 rounded-2xl p-6 border border-white/5 min-h-[200px]">
              <h3 className="text-sm font-mono text-gray-400 mb-4 uppercase tracking-wider">Neural Activity Log</h3>
              <div className="space-y-2">
                {lastGesture && (
                  <div className="animate-in slide-in-from-left fade-in duration-300 flex items-center justify-between p-3 bg-cyan-500/10 border border-cyan-500/20 rounded-lg">
                    <div className="flex items-center gap-3">
                      <span className="text-2xl">
                        {lastGesture.gesture.includes('swipe') ? '✋' : '🤏'}
                      </span>
                      <div>
                        <div className="font-bold text-cyan-400">{lastGesture.gesture.toUpperCase().replace('_', ' ')}</div>
                        <div className="text-xs text-gray-400 font-mono">CONFIDENCE: {Math.round(lastGesture.confidence * 100)}%</div>
                      </div>
                    </div>
                    <div className="text-xs font-mono text-gray-500">JUST NOW</div>
                  </div>
                )}
                <div className="p-3 border border-white/5 rounded-lg text-gray-600 text-sm font-mono flex justify-center">
                  Waiting for input...
                </div>
              </div>
            </div>
          </div>

          {/* Right Column: Controls */}
          <div className="space-y-6">
            <ControlPanel
              settings={settings}
              cameras={cameras}
              stats={stats}
              onSettingChange={updateSetting}
              onRefreshCameras={fetchCameras}
            />

            {/* Supabase / Sheets Status Card (Placeholder for now) */}
            <div className="p-6 rounded-2xl bg-gradient-to-br from-purple-900/20 to-pink-900/20 border border-purple-500/20">
              <div className="flex items-center gap-3 mb-2">
                <span className="text-2xl">☁️</span>
                <h3 className="font-bold text-purple-300">Cloud Sync</h3>
              </div>
              <p className="text-sm text-purple-200/60 mb-4">
                Supabase & Google Sheets integration ready for configuration.
              </p>
              <button className="w-full py-2 rounded-lg bg-purple-500/20 border border-purple-500/50 text-purple-300 text-sm hover:bg-purple-500/30 transition-colors">
                CONFIGURE SYNC
              </button>
            </div>
          </div>

        </div>
      </div>
    </main>
  );
}
