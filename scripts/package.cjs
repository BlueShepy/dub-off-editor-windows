const builder=require('electron-builder');
const path=require('node:path');
const {WineVmManager}=require('app-builder-lib/out/vm/WineVm');
const {UninstallerReader}=require('app-builder-lib/out/targets/nsis/nsisUtil');
const root=process.env.DUB_PORT_WORK_ROOT;
// Use electron-builder's own uninstaller parser, also used by its Mac builds,
// to generate the unsigned uninstaller without a 32-bit Wine installation.
WineVmManager.prototype.exec=async function(file){
 const output=path.join(path.dirname(file),`${path.basename(file,'exe')}__uninstaller.exe`);
 await UninstallerReader.exec(file,output);
};
builder.build({projectDir:root+'/original',config:require(root+'/electron-builder.json'),prepackaged:root+'/windows/Dub-Off Editor',targets:builder.Platform.WINDOWS.createTarget('nsis',builder.Arch.x64),publish:'never'}).catch(e=>{console.error(e);process.exitCode=1;});
