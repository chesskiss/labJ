/// <reference types="vite/client" />

interface LabJDesktopRuntimeServiceStatus {
  pid: number | null;
  running: boolean;
  port: number;
}

interface LabJDesktopRuntimeStatus {
  state: string;
  services: Record<string, LabJDesktopRuntimeServiceStatus>;
  serviceHealth: Record<string, boolean>;
  pendingServices: string[];
  lastError: string | null;
  logsDir: string;
}

interface Window {
  labjDesktop?: {
    getRuntimeStatus: () => Promise<LabJDesktopRuntimeStatus>;
    restartRuntime: () => Promise<LabJDesktopRuntimeStatus>;
    openLogsFolder: () => Promise<string>;
  };
}
