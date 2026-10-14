"use strict";
const electron = require("electron");
electron.contextBridge.exposeInMainWorld("neeka", {
  health: () => electron.ipcRenderer.invoke("engine:health"),
  request: (request) => electron.ipcRenderer.invoke("api:request", request)
});
