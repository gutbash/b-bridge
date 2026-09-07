# Installing b-bridge

All paths are relative to the game's `GTAIV` folder (the one containing `GTAIV.exe`).

## 1. Check what owns `d3d9.dll` today

- **FusionFix's wrapper** (about 175 KB, from the FusionFix zip): rename it to `d3d9Hooked.dll`
  and make sure `dinput8.dll` (Ultimate ASI Loader) is present so `plugins\GTAIV.EFLC.FusionFix.asi`
  keeps loading. FusionFix works exactly the same through the ASI loader.
- **DXVK** (several MB): remove it. The server runs DXVK now. Keep your `dxvk.conf` for the
  next step.
- **Nothing / the Windows one**: nothing to do.

## 2. Copy the files

From the zip, copy the `GTAIV` folder over your `GTAIV` folder. You get:

```
GTAIV\d3d9.dll                 b-bridge client (32-bit)
GTAIV\dxvk.conf                settings for the server's DXVK
GTAIV\.trex\NvRemixBridge.exe  b-bridge server (64-bit)
GTAIV\.trex\d3d9vk_x64.dll     DXVK 3.0.2, 64-bit, unmodified
GTAIV\.trex\bridge.conf        bridge settings
```

If you already had a `dxvk.conf`, merge rather than replace, and read step 3.

## 3. Keys that must stay off in `dxvk.conf`

The client paces the game. Anything that paces the *server* fights it:

```
# do not set these while bridged
# dxvk.maxFrameRate = 60
# d3d9.maxFrameLatency = 1     (2 is fine and is what ships)
# dxvk.latencySleep = True
```

Set the frame cap in `.trex\bridge.conf` instead:

```
clientFrameCap = 60      # 0 = uncapped
```

`dxvk.allowFse = false` in the shipped `dxvk.conf` is deliberate: the exclusive-fullscreen
mode switch loses the device across the process boundary. Run borderless.

## 4. Launch

Start the game normally. There is no server window. Logs:

```
GTAIV\rtx-remix\logs\bridge32.log   client (game side)
GTAIV\rtx-remix\logs\bridge64.log   server
```

A healthy start shows `Loading standard Non-RTX DXVK d3d9 dll` in `bridge64.log`. The line
`Unable to resolve QueryFeatureVersion ... loading vanilla DXVK` is expected and harmless.

If the game exits after about 12 seconds and `bridge64.log` was not written, that is the known
startup desync. Launch again.

## 5. Video memory

The server reports the VRAM in `dxgi.maxDeviceMemory` to the game, and GTA IV sizes its texture
streaming from that number. The shipped value is 4096. Under the bridge this costs the game no
address space (the pool lives in the 64-bit process), so raise it if you see distant texture
pop-in with large texture packs.

## Uninstall

Delete `GTAIV\d3d9.dll` and `GTAIV\.trex`, then put back whichever `d3d9.dll` you had
(rename `d3d9Hooked.dll` back if that was FusionFix's).
