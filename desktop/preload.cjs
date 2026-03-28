const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("labjDesktop", {
  getRuntimeStatus: () => ipcRenderer.invoke("runtime:getStatus"),
  restartRuntime: () => ipcRenderer.invoke("runtime:restartServices"),
  openLogsFolder: () => ipcRenderer.invoke("runtime:openLogsFolder"),
});
