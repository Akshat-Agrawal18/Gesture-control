'use client';


import { Settings, CameraInfo, SystemStatus } from '@/lib/types';

interface ControlPanelProps {
    settings: Settings;
    cameras: CameraInfo[];
    stats: {
        volume: number;
        brightness: number;
    };
    onSettingChange: (key: keyof Settings, value: any) => void;
    onRefreshCameras: () => void;
}


export default function ControlPanel({
    settings,
    cameras,
    stats,
    onSettingChange,
    onRefreshCameras
}: ControlPanelProps) {

    return (
        <div className="bg-black/40 backdrop-blur-xl border border-white/5 rounded-2xl p-6 flex flex-col gap-6">

            {/* Header */}
            <div className="flex items-center justify-between border-b border-white/5 pb-4">
                <h2 className="text-xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-cyan-400 to-purple-500">
                    SYSTEM CONTROLS
                </h2>
                <div className="flex gap-2">
                    <div className="px-2 py-1 bg-white/5 rounded text-xs text-gray-400 font-mono">
                        VOL: {stats.volume}%
                    </div>
                    <div className="px-2 py-1 bg-white/5 rounded text-xs text-gray-400 font-mono">
                        BRI: {stats.brightness}%
                    </div>
                </div>
            </div>

            {/* Camera Selection */}
            <div className="space-y-3">
                <div className="flex items-center justify-between">
                    <label className="text-sm text-gray-400 uppercase tracking-wider font-mono">Video Input</label>
                    <button
                        onClick={onRefreshCameras}
                        className="text-xs text-cyan-400 hover:text-cyan-300 transition-colors"
                    >
                        REFRESH LIST
                    </button>
                </div>
                <select
                    value={settings.selected_camera}
                    onChange={(e) => onSettingChange('selected_camera', e.target.value)}
                    className="w-full bg-black/50 border border-white/10 rounded-lg px-4 py-3 text-sm text-gray-200 focus:outline-none focus:border-cyan-500/50 transition-all font-mono"
                >
                    {cameras.map(cam => (
                        <option key={cam.id} value={cam.source}>
                            {cam.type.toUpperCase()} - {cam.name}
                        </option>
                    ))}
                    {/* If selected camera is not in list (custom IP), show it */}
                    {!cameras.find(c => c.source === settings.selected_camera) && settings.selected_camera.length > 2 && (
                        <option value={settings.selected_camera}>Custom IP: {settings.selected_camera}</option>
                    )}
                </select>

                {/* IP Camera Input */}
                <div className="flex gap-2">
                    <input
                        type="text"
                        placeholder="http://192.168.x.x:4747/video"
                        className="flex-1 bg-black/30 border border-white/10 rounded px-3 py-2 text-xs text-gray-300 font-mono placeholder-gray-600 focus:border-cyan-500/50 outline-none"
                        onKeyDown={(e) => {
                            if (e.key === 'Enter') {
                                onSettingChange('selected_camera', e.currentTarget.value);
                            }
                        }}
                    />
                    <button
                        className="bg-white/5 hover:bg-cyan-500/20 text-cyan-400 px-3 py-2 rounded text-xs transition-colors"
                        onClick={(e) => {
                            const input = e.currentTarget.previousElementSibling as HTMLInputElement;
                            if (input.value) onSettingChange('selected_camera', input.value);
                        }}
                    >
                        CONNECT
                    </button>
                </div>
            </div>

            {/* Toggles Grid */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                {[
                    { key: 'desktop_control', label: 'Desktop', icon: '🖥️' },
                    { key: 'volume_control', label: 'Volume', icon: '🔊' },
                    { key: 'brightness_control', label: 'Brightness', icon: '☀️' },
                ].map((item) => (
                    <button
                        key={item.key}
                        onClick={() => onSettingChange(item.key as keyof Settings, !settings[item.key as keyof Settings])}
                        className={`
              relative p-4 rounded-xl border transition-all duration-300 group
              ${settings[item.key as keyof Settings]
                                ? 'bg-cyan-500/10 border-cyan-500/50 shadow-[0_0_20px_rgba(6,182,212,0.1)]'
                                : 'bg-white/5 border-white/5 hover:bg-white/10'
                            }
            `}
                    >
                        <div className="flex flex-col items-center gap-2">
                            <span className="text-2xl">{item.icon}</span>
                            <span className={`text-xs font-mono uppercase tracking-wider ${settings[item.key as keyof Settings] ? 'text-cyan-400' : 'text-gray-500'
                                }`}>
                                {item.label}
                            </span>
                        </div>
                        {/* Status Dot */}
                        <div className={`absolute top-2 right-2 w-1.5 h-1.5 rounded-full ${settings[item.key as keyof Settings] ? 'bg-cyan-400 shadow-[0_0_10px_rgba(6,182,212,1)]' : 'bg-gray-700'
                            }`}></div>
                    </button>
                ))}
            </div>

            {/* Sliders */}
            <div className="space-y-6 pt-2">
                <div className="space-y-2">
                    <div className="flex justify-between text-xs text-gray-400 font-mono">
                        <span>GESTURE SENSITIVITY</span>
                        <span className="text-cyan-400">{settings.swipe_sensitivity}px</span>
                    </div>
                    <input
                        type="range"
                        min="50"
                        max="300"
                        value={settings.swipe_sensitivity}
                        onChange={(e) => onSettingChange('swipe_sensitivity', parseInt(e.target.value))}
                        className="w-full h-1 bg-white/10 rounded-full appearance-none cursor-pointer [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-4 [&::-webkit-slider-thumb]:h-4 [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-cyan-500 [&::-webkit-slider-thumb]:shadow-[0_0_10px_rgba(6,182,212,0.5)]"
                    />
                </div>

                <div className="space-y-2">
                    <div className="flex justify-between text-xs text-gray-400 font-mono">
                        <span>COOLDOWN TIMER</span>
                        <span className="text-cyan-400">{settings.cooldown}s</span>
                    </div>
                    <input
                        type="range"
                        min="0.2"
                        max="2.0"
                        step="0.1"
                        value={settings.cooldown}
                        onChange={(e) => onSettingChange('cooldown', parseFloat(e.target.value))}
                        className="w-full h-1 bg-white/10 rounded-full appearance-none cursor-pointer [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-4 [&::-webkit-slider-thumb]:h-4 [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-purple-500 [&::-webkit-slider-thumb]:shadow-[0_0_10px_rgba(168,85,247,0.5)]"
                    />
                </div>
            </div>

        </div>
    );
}
