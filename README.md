# BrokerBridge

**64-bit out-of-process Direct3D 9 rendering for Grand Theft Auto IV: The Complete Edition.**

GTA IV is a 32-bit game. Every texture, shadow map and render target the driver allocates
lands in the same 4 GB of address space as the game itself, and a heavily modded install
runs out of that space long before it runs out of RAM or VRAM. BrokerBridge moves the whole
Direct3D 9 device into a separate 64-bit process. The game keeps a thin 32-bit `d3d9.dll`
that brokers every call across a shared-memory channel to a 64-bit server, which renders
through [DXVK](https://github.com/doitsujin/dxvk) on Vulkan.

Measured on this project's install: about **880 MB of address space returned** to the game,
frame time at parity with in-process DXVK, and a six-pack texture stack (HQ Vanilla Textures,
Higher Resolution Vehicle and Misc packs, RDR2 vegetation, More Visible Interiors,
LibertyCityPlates) running with a 800 MB largest free hole where the unmodified layout crashed
in minutes.

It is a fork of NVIDIA's [bridge-remix](https://github.com/NVIDIAGameWorks/bridge-remix),
the IPC layer of RTX Remix, with the Remix runtime removed and the client tuned for a game
that issues tens of thousands of D3D9 calls per frame.

## What it is not

- **Not path tracing.** GTA IV is a deferred renderer and Remix's ray-traced path does not
  work with it. BrokerBridge runs the raster path only.
- **Not a CPU fix.** Every D3D9 call still crosses the process boundary. A scene that is
  bound on the game's render thread will not get faster. The win is memory, and the frame
  time is held at parity by batching, not eliminated.
- **Not a Remix install.** The server executable keeps NVIDIA's name because the client looks
  for it, but it loads plain DXVK. None of the Remix runtime DLLs are needed or shipped.

## How it works

```
GTAIV.exe (32-bit)                         NvRemixBridge.exe (64-bit)
  game code                                   BrokerBridge server
    |                                            |
  d3d9.dll  (BrokerBridge client)   ===IPC===>   command replay
    - frame pacer                    shared     |
    - state-block transfer plans     memory   d3d9vk_x64.dll (DXVK 3.0.2)
    - StateBatch (hot setters in     channel     |
      one record per frame)                    Vulkan driver
```

Changes against upstream bridge-remix, all in `src/`:

| Area | Change | bridge.conf key |
|---|---|---|
| Client | Frame pacer (waitable timer + spin) so the *game* is paced, not the server | `clientFrameCap` |
| Client | State-block TransferPlan: precomputed dirty lists for `D3DSBT_ALL` blocks GTA IV applies ~475x per frame | - |
| Client | StateBatch: render/sampler/stage state, textures, shaders, streams, constants packed into one 64 KB record | `clientStateBatch` |
| Client | Batched command index publish | `clientCmdPublishBatch` |
| Client | Merged device/channel lock; import-free spinlock (ASI loaders that hook kernel32 cannot re-enter it) | - |
| Client | Wait statistics per window in `bridge32.log`; assert logger fixed | - |
| Server | StateBatch replay; vanilla-DXVK mode is the supported path | `server.useVanillaDxvk` |
| Both | Server responses only when required | `sendAllServerResponses = False` |

## Requirements

- Grand Theft Auto IV: The Complete Edition, 1.2.0.59 (Steam or Rockstar)
- [FusionFix](https://github.com/ThirteenAG/GTAIV.EFLC.FusionFix), loaded through an ASI
  loader (Ultimate ASI Loader as `dinput8.dll`) rather than through its own `d3d9.dll`
- A Vulkan 1.3 GPU and driver (DXVK 3.0.2 requirement)
- Windows 10 or 11, 64-bit

See [INSTALL.md](INSTALL.md) for the steps and [CHANGELOG.md](CHANGELOG.md) for the history.

## Known limits

- **Startup desync (about 1 launch in 10).** The server never comes up, `bridge64.log` is not
  written, and the client exits after 12 seconds. Relaunch. Under investigation.
- **Overlays that hook the window from the server side cannot see input.** ReShade as a Vulkan
  layer renders fine but its overlay and hotkeys are dead, because the window belongs to the
  game process. Configure it by file.
- **DXVK 3.0.2 is the tested version** and is what ships. Newer DXVK releases have not been
  validated with this server.
- Only tested on one machine: RTX 2070, driver of September 2026, 2560x1440 borderless.

## Building

Meson + ninja with MSVC 14.42. `build_x86_release.cmd` builds the client, `build_x64_release.cmd`
the server. `b_ndebug=true` is required: without it `bridge_cast` falls back to `dynamic_cast`
with live asserts and the client is several milliseconds slower per frame.

## License

MIT, same as upstream. See `LICENSE-MIT` and `ThirdPartyLicenses.txt`. DXVK is zlib-licensed
and redistributed unmodified.

The name is the Broker Bridge in Liberty City. The client brokers the calls; the bridge is the shape.
