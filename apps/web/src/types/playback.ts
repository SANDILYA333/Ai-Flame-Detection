export type TimeWindow = "1H" | "6H" | "24H" | "48H" | "7D" | "ALL";
export type PlaybackSpeed = 1 | 2 | 4 | 8;
export type PlaybackMode = "LIVE" | "PLAYBACK";

export interface PlaybackRange {
  start: number;
  end: number;
  durationMs: number;
}

export interface PlaybackState {
  mode: PlaybackMode;
  selectedWindow: TimeWindow;
  playbackTime: number;
  range: PlaybackRange;
  isPlaying: boolean;
  playbackSpeed: PlaybackSpeed;
  progress: number; // 0.0 to 1.0
  activeEventCount: number;
  totalCatalogCount: number;
}
