#pragma once
// Client-side wait accounting (2026-09-05, local): how long the game's threads block inside the
// bridge, per call site, dumped every few seconds from Present(). Header-only so it needs no
// build-file change. Cheap enough to leave on: one mutex + map insert per *waited* call only.
#include <windows.h>
#include <cstdint>
#include <map>
#include <mutex>
#include <string>
#include <sstream>
#include <vector>
#include <algorithm>
#include "util_commands.h"

namespace bridge_util {
  struct WaitStats {
    struct Entry { uint64_t n = 0, us = 0, maxUs = 0; };
    std::mutex m;
    std::map<std::string, Entry> waits;   // WAIT_FOR_SERVER_RESPONSE sites
    std::map<std::string, Entry> stalls;  // command pushes that took > 100 us (queue full / server behind)
    uint64_t cmds = 0;                    // commands pushed since last dump
    static const size_t kHistSize = 512;
    uint32_t hist[kHistSize] = {};        // commands per D3D9Command id since last dump (unlocked, approximate)
    uint64_t frames = 0;
    uint64_t lastDumpUs = 0;

    static WaitStats& get() { static WaitStats s; return s; }

    static uint64_t nowUs() {
      static LARGE_INTEGER f = [] { LARGE_INTEGER x; QueryPerformanceFrequency(&x); return x; }();
      LARGE_INTEGER c; QueryPerformanceCounter(&c);
      return (uint64_t) (c.QuadPart * 1000000ULL / f.QuadPart);
    }

    void record(std::map<std::string, Entry>& tbl, const char* key, uint64_t us) {
      std::lock_guard<std::mutex> l(m);
      auto& e = tbl[key]; e.n++; e.us += us; if (us > e.maxUs) e.maxUs = us;
    }

    // Returns a non-empty summary once every `periodUs`; caller logs it.
    std::string tick(uint64_t periodUs = 5000000) {
      const uint64_t now = nowUs();
      std::lock_guard<std::mutex> l(m);
      frames++;
      if (lastDumpUs == 0) { lastDumpUs = now; return {}; }
      if (now - lastDumpUs < periodUs) return {};
      const double secs = (now - lastDumpUs) / 1e6;
      std::ostringstream s;
      s << "[waitstats] " << frames << " frames in " << secs << " s (" << (frames / secs) << " fps), "
        << cmds << " cmds (" << (cmds / (double) (frames ? frames : 1)) << "/frame)";
      uint64_t totalWait = 0;
      for (auto& kv : waits) totalWait += kv.second.us;
      s << ", waited " << (totalWait / 1000.0) << " ms total = " << (totalWait / 1000.0 / (frames ? frames : 1)) << " ms/frame";
      for (auto& kv : waits) {
        s << "\n    wait  " << kv.first << " n=" << kv.second.n << " total=" << (kv.second.us / 1000.0) << "ms avg=" << (kv.second.us / (double) kv.second.n) << "us max=" << kv.second.maxUs << "us";
      }
      for (auto& kv : stalls) {
        s << "\n    stall " << kv.first << " n=" << kv.second.n << " total=" << (kv.second.us / 1000.0) << "ms max=" << kv.second.maxUs << "us";
      }
      // top command types
      std::vector<std::pair<uint32_t, size_t>> top;
      for (size_t i = 0; i < kHistSize; ++i) if (hist[i]) top.emplace_back(hist[i], i);
      std::sort(top.begin(), top.end(), [](auto& a, auto& b) { return a.first > b.first; });
      for (size_t i = 0; i < top.size() && i < 14; ++i) {
        s << "\n    cmd   " << Commands::toString((Commands::D3D9Command) top[i].second) << " n=" << top[i].first << " (" << (top[i].first / (double) (frames ? frames : 1)) << "/frame)";
      }
      for (auto& h : hist) h = 0;
      waits.clear(); stalls.clear(); cmds = 0; frames = 0; lastDumpUs = now;
      return s.str();
    }
  };
}
