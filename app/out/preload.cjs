"use strict";

// src/preload/preload.ts
var import_electron = require("electron");
var invoke = (channel) => (...args) => import_electron.ipcRenderer.invoke(channel, ...args);
var subscribe = (channel) => (listener) => {
  const handler = (_event, payload) => listener(payload);
  import_electron.ipcRenderer.on(channel, handler);
  return () => {
    import_electron.ipcRenderer.removeListener(channel, handler);
  };
};
var api = {
  status: invoke("status"),
  chooseProjectsRoot: invoke("choose-projects-root"),
  recent: invoke("recent"),
  pickVideo: invoke("pick-video"),
  pickCvpFolder: invoke("pick-cvp-folder"),
  scanCvpPacks: invoke("scan-cvp-packs"),
  createFromFile: invoke("create-from-file"),
  createFromYoutube: invoke("create-from-youtube"),
  createFromCvp: invoke("create-from-cvp"),
  pickSceneFolder: invoke("pick-scene-folder"),
  createFromScene: invoke("create-from-scene"),
  open: invoke("open"),
  openPicker: invoke("open-picker"),
  save: invoke("save"),
  relink: invoke("relink"),
  prepareMedia: invoke("prepare-media"),
  importSubtitles: invoke("import-subtitles"),
  readSubtitles: invoke("read-subtitles"),
  analyse: invoke("analyse"),
  build: invoke("build"),
  readCues: invoke("read-cues"),
  cancel: invoke("cancel"),
  exportDub: invoke("export-dub"),
  openUploadPage: invoke("open-upload-page"),
  openDub: invoke("open-dub"),
  pendingDub: invoke("pending-dub"),
  showInFolder: invoke("show-in-folder"),
  fileUrl: invoke("file-url"),
  updateYtdlp: invoke("update-ytdlp"),
  sourceSuggestions: invoke("source-suggestions"),
  licenses: invoke("licenses"),
  updateStatus: invoke("update-status"),
  installUpdate: invoke("install-update"),
  openUpdateDownload: invoke("open-update-download"),
  pathForFile: (file) => import_electron.webUtils.getPathForFile(file),
  onProgress: subscribe("progress"),
  onMenu: subscribe("menu"),
  onUpdate: subscribe("update")
};
import_electron.contextBridge.exposeInMainWorld("editor", api);
//# sourceMappingURL=preload.cjs.map
