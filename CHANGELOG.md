# Changelog

## 0.1.0 - 2026-09-07

First public build. Fork point: NVIDIAGameWorks/bridge-remix `7dbbd37` (2025-05-02).

### Client (`GTAIV\d3d9.dll`, x86)
- Frame pacer: high-resolution waitable timer plus a short spin, `clientFrameCap` in bridge.conf.
- State blocks: TransferPlan with precomputed dirty index lists.
- StateBatch: hot device setters and shader constants packed into one record per flush;
  flushed under the channel lock (`clientStateBatch`).
- Batched command index publish (`clientCmdPublishBatch = 32`).
- Merged device/channel lock; import-free spinlock (`util_fastlock.h`).
- Wait statistics per window (`util_waitstats.h`), printed to `bridge32.log`.
- Assert logger no longer touches a dead writer channel.
- Redundant setter elimination on by default.

### Server (`.trex\NvRemixBridge.exe`, x64)
- StateBatch replay.
- Vanilla DXVK mode is the supported configuration; DXVK pinned to 3.0.2 (3.1 fails
  `CreateDevice` with this server).
- `sendAllServerResponses = False`; responses only for calls that return data.

### Measured (RTX 2070, 2560x1440, GTA IV CE 1.2.0.59 + FusionFix)
- In-process DXVK 17.6 ms -> bridged 13.6 ms mean frame time on the same route after the
  batching work (uncapped, view and detail distance 100).
- About 880 MB more free address space in the game process; largest free hole 735-819 MB with
  a 5 GB texture-pack stack loaded.

### Known issues
- Intermittent startup desync (~1 in 10 launches): server never starts, client exits at 12 s.
- Overlays injected on the server side (ReShade Vulkan layer) have no input.
