# BrokerBridge

**Out-of-process Direct3D 9 rendering for Grand Theft Auto IV: The Complete Edition.**
A research release. Fork of NVIDIA's [bridge-remix](https://github.com/NVIDIAGameWorks/bridge-remix).

## Abstract

GTA IV is a 32-bit process. Every resource the graphics driver allocates on the game's behalf
(textures, shadow maps, render targets, staging buffers) is mapped into the same 4 GB address
space as the game's own data, and a heavily modded install exhausts that space long before it
exhausts RAM or VRAM. BrokerBridge moves the entire Direct3D 9 device into a separate 64-bit
process. The game keeps a thin 32-bit `d3d9.dll` that forwards every call over a shared-memory
channel to a 64-bit server, which renders through DXVK on Vulkan. On the test system this
returned about 880 MB of address space to the game and held frame time at parity with
in-process DXVK, allowing a 5 GB texture-pack stack to run where the same install previously
crashed within minutes.

## Problem

The address-space wall, not memory, is the practical ceiling on GTA IV modding. Prior
approaches (large-address-aware flags, streaming-budget tuning, the `-nomemrestrict` family,
texture-memory caps in DXVK) reduce pressure but cannot change the fact that driver
allocations and game allocations share one 32-bit space. Measured on the reference install
before this work: largest contiguous free region as low as 5 MB with view distance at 100,
and a streaming-allocator crash band at 2.8 to 3.0 GB committed.

## Method

The IPC layer of NVIDIA RTX Remix already marshals D3D9 across processes; its purpose there is
to feed a path tracer. BrokerBridge keeps the transport and discards the renderer: the server
loads an unmodified DXVK 3.0.2 instead of the Remix runtime, and the client is tuned for a game
that issues 15,000 to 70,000 D3D9 calls per frame.

Changes against upstream (all in `src/`):

| Area | Change | Config key |
|---|---|---|
| Client | Frame pacer: waitable timer plus spin, so pacing happens in the game process rather than the server | `clientFrameCap` |
| Client | State-block transfer plans: precomputed dirty index lists for the `D3DSBT_ALL` blocks GTA IV applies ~475 times per frame | - |
| Client | StateBatch: render, sampler and stage state, textures, shaders, streams and shader constants packed into one record per flush | `clientStateBatch` |
| Client | Batched command index publish | `clientCmdPublishBatch` |
| Client | Merged device/channel lock; import-free spinlock, so ASI loaders that hook `kernel32` cannot re-enter it | - |
| Client | Per-window wait statistics in `bridge32.log`; assert logger no longer dereferences a dead channel | - |
| Server | StateBatch replay with the same resource lookups as the individual commands | - |
| Server | Vanilla-DXVK mode as the supported configuration | `server.useVanillaDxvk` |
| Both | Server responses only for calls that return data | `sendAllServerResponses` |

## Results

Reference system: Intel i7-9700K, NVIDIA GeForce RTX 2070 (8 GB), driver 610.74, 2560x1440 borderless,
GTA IV CE 1.2.0.59 with FusionFix. Frame times are means over a fixed 60-second scripted drive
(uncapped, view and detail distance 100), memory figures from an in-process address-space monitor.

| Configuration | Mean frame time | Largest free region |
|---|---|---|
| In-process DXVK, same route | 17.6 ms | 5 to 65 MB at view 100 |
| BrokerBridge, upstream client | ~19 ms | 800 MB |
| BrokerBridge, this client | 13.6 ms | 800 MB |
| BrokerBridge, this client, 5 GB texture-pack stack | 16.4 ms | 735 to 819 MB |

The batching work is what brings the bridged frame time below the in-process figure; the
transport itself costs time, and the client hides it by sending fewer, larger messages.

## Limitations

These are the boundaries of what was tested. Nothing outside them should be assumed to work.

- **NVIDIA only.** Every measurement was taken on one RTX 2070 with one driver version. No AMD
  or Intel GPU has run this build. DXVK itself is vendor-neutral, but the bridge server's device
  creation and swapchain path have not been exercised on any other Vulkan driver.
- **One machine, one configuration.** One CPU, one resolution and refresh rate, borderless
  windowed only. Exclusive fullscreen is disabled by the shipped `dxvk.conf` because the mode
  switch loses the device across the process boundary.
- **One game build and one mod stack.** GTA IV CE 1.2.0.59 with FusionFix loaded through an
  ASI loader. Other patch levels (1.0.7.0, 1.0.8.0), the unpatched Complete Edition, and
  FusionFix loaded through its own `d3d9.dll` are untested.
- **Raster only.** GTA IV is a deferred renderer and the Remix path-traced pipeline does not
  produce a usable image with it. That pipeline is not shipped.
- **CPU-bound scenes do not improve.** Every D3D9 call still crosses the process boundary.
  The gain is address space; frame time is held at parity, not reduced, in scenes limited by
  the game's render thread.
- **Startup desync, about one launch in ten.** The server process never comes up, its log is
  not written, and the client exits after 12 seconds. Relaunching succeeds. The cause is in
  process launch or the initial channel handshake and is not yet isolated.
- **First device creation fails on every launch.** `bridge64.log` shows one failed `CreateDevice`
  (0x8876086c) before the real device is created. This is the game probing with a zero refresh
  rate and is harmless; it is listed here so it is not reported as a fault.
- **Overlays on the server side get no input.** A ReShade Vulkan layer in the server renders
  correctly but its overlay and hotkeys are dead, because the window belongs to the game
  process. Such tools must be configured by file.
- **DXVK 3.0.2 only.** Newer DXVK releases have not been validated with this server.
- **Session length.** The longest single measured session is about 25 minutes. Multi-hour
  stability has not been characterised.

## Reproducibility

The benchmark route, the address-space monitor and the census scripts used for the results are
part of the reference install's tooling rather than this repository; the numbers above should be
read as one system's measurements, not as a specification. Anyone reproducing them should
report GPU, driver, resolution, the mean and 1% low over a fixed route, and the minimum largest
free region over the session.

## Future work

- Isolate and fix the startup desync.
- Validate on AMD and Intel Vulkan drivers.
- Reduce per-call client overhead further; the render thread still spends a measurable share
  of its time in the client wrapper.
- Characterise multi-hour sessions.

## Installation

See [INSTALL.md](INSTALL.md). Changes by version are in [CHANGELOG.md](CHANGELOG.md).

## Building

Meson and ninja with MSVC 14.42. `build_x86_release.cmd` builds the client, `build_x64_release.cmd`
the server. `b_ndebug=true` is required: without it `bridge_cast` falls back to `dynamic_cast`
with live asserts and the client is several milliseconds slower per frame.

## License

MIT, as upstream. See `LICENSE-MIT` and `ThirdPartyLicenses.txt`. DXVK is zlib-licensed and
redistributed unmodified. The upstream README is preserved as `README.upstream.md`.

The name is the Broker Bridge in Liberty City. The client brokers the calls; the bridge is the shape.
