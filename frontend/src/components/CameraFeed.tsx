'use client';

import { useEffect, useRef, useState } from 'react';
import { Gesture, WebSocketMessage } from '@/lib/types';

interface CameraFeedProps {
    wsUrl: string;
    isConnected: boolean;
    onStatsUpdate: (stats: { fps: number; gestures: Gesture[] }) => void;
}

export default function CameraFeed({ wsUrl, isConnected, onStatsUpdate }: CameraFeedProps) {
    const [imageSrc, setImageSrc] = useState<string | null>(null);
    const canvasRef = useRef<HTMLCanvasElement>(null);
    const wsRef = useRef<WebSocket | null>(null);

    useEffect(() => {
        if (!isConnected) {
            setImageSrc(null);
            return;
        }

        const ws = new WebSocket(wsUrl);
        wsRef.current = ws;

        ws.onmessage = (event) => {
            try {
                const data: WebSocketMessage = JSON.parse(event.data);

                if (data.type === 'frame' && data.frame) {
                    setImageSrc(`data:image/jpeg;base64,${data.frame}`);

                    if (data.fps !== undefined) {
                        onStatsUpdate({
                            fps: data.fps,
                            gestures: data.gestures || []
                        });
                    }
                }
            } catch (e) {
                console.error('Error parsing WS message:', e);
            }
        };

        return () => {
            ws.close();
        };
    }, [wsUrl, isConnected, onStatsUpdate]);

    return (
        <div className="relative w-full aspect-video bg-black/50 rounded-2xl overflow-hidden border border-white/10 shadow-2xl shadow-cyan-500/10">
            {imageSrc ? (
                <img
                    src={imageSrc}
                    alt="Camera Feed"
                    className="w-full h-full object-cover transform scale-x-[-1]" // Mirror effect
                />
            ) : (
                <div className="absolute inset-0 flex items-center justify-center flex-col gap-4">
                    <div className="w-16 h-16 border-4 border-cyan-500/30 border-t-cyan-500 rounded-full animate-spin"></div>
                    <p className="text-cyan-500/50 font-mono text-sm uppercase tracking-widest">
                        {isConnected ? 'Connecting to Neural Interface...' : 'System Offline'}
                    </p>
                </div>
            )}

            {/* HUD Overlay */}
            <div className="absolute inset-0 pointer-events-none">
                <div className="absolute top-4 left-4 flex gap-2">
                    <div className="bg-black/60 backdrop-blur border border-white/10 px-3 py-1 rounded text-xs font-mono text-cyan-400">
                        REC
                    </div>
                    <div className="bg-black/60 backdrop-blur border border-white/10 px-3 py-1 rounded text-xs font-mono text-green-400">
                        LIVE
                    </div>
                </div>

                {/* Reticle Lines */}
                <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-32 h-32 border border-white/5 opacity-50"></div>
                <div className="absolute top-1/2 left-0 w-full h-px bg-cyan-500/10"></div>
                <div className="absolute top-0 left-1/2 w-px h-full bg-cyan-500/10"></div>

                {/* Corner Brackets */}
                <div className="absolute top-4 right-4 w-8 h-8 border-t-2 border-r-2 border-cyan-500/50 rounded-tr-lg"></div>
                <div className="absolute bottom-4 left-4 w-8 h-8 border-b-2 border-l-2 border-cyan-500/50 rounded-bl-lg"></div>
            </div>
        </div>
    );
}
