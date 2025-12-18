export interface Gesture {
    gesture: string;
    hand: string;
    confidence: number;
}

export interface Settings {
    desktop_control: boolean;
    volume_control: boolean;
    brightness_control: boolean;
    swipe_sensitivity: number;
    cooldown: number;
    selected_camera: string;
}

export interface CameraInfo {
    id: string;
    name: string;
    type: string;
    source: string;
}

export interface SystemStatus {
    is_running: boolean;
    camera: string;
    fps: number;
    volume: number;
    brightness: number;
    connected_clients: number;
}

export interface WebSocketMessage {
    type: string;
    frame?: string;
    fps?: number;
    gestures?: Gesture[];
    volume?: number;
    brightness?: number;
}
