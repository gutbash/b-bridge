#pragma once
// 2026-09-05 (local): lightweight locks for the per-D3D-call hot path. MSVC's std::mutex /
// std::recursive_mutex route through mtx_do_lock (type checks, thread-id bookkeeping, timed-lock
// support) and cost ~30% of GTA IV's render thread at ~70k bridge commands per frame. A raw SRW
// lock is ~10-15 ns uncontended and still parks the thread on contention.
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <intrin.h>
#include <cstdint>

namespace bridge_util {
  // Thread id straight from the TEB: what GetCurrentThreadId() does, minus the import call. The client's
  // kernel32 imports can be redirected by ASI loaders (an Ultimate ASI Loader hook was the single hottest
  // address on the render thread), and this runs 2-4x per D3D command.
  static inline DWORD curTid() {
#if defined(_M_IX86)
    return __readfsdword(0x24);
#elif defined(_M_X64)
    return (DWORD) __readgsqword(0x48);
#else
    return GetCurrentThreadId();
#endif
  }
  // 2026-09-05: import-free spinlock. The SRW locks went through kernel32 imports that the game's ASI loader
  // (Ultimate ASI Loader 9.7) redirects into a wrapper with a process-wide cmpxchg guard and a caller-module
  // lookup on every call: ~15% of the render thread at 70k D3D commands/frame. This lock is one xchg to
  // acquire and a plain store to release; critical sections here are microseconds long and rarely contended.
  class SpinLock {
    volatile long m_flag = 0;
  public:
    SpinLock() = default;
    SpinLock(const SpinLock&) = delete;
    SpinLock& operator=(const SpinLock&) = delete;
    void lock() {
      for (;;) {
        if (_InterlockedExchange(&m_flag, 1) == 0) { return; }
        unsigned spins = 0;
        while (m_flag) {
          _mm_pause();
          if (++spins >= 2048) { SwitchToThread(); spins = 0; }
        }
      }
    }
    bool try_lock() { return _InterlockedExchange(&m_flag, 1) == 0; }
    void unlock() { _ReadWriteBarrier(); m_flag = 0; }   // x86: stores are release; the barrier pins the order
  };
  using SrwLock = SpinLock;

  // Recursive exclusive lock (owner thread + depth on top of the spinlock).
  class SrwRecursiveLock {
    SpinLock m_lock;
    DWORD m_owner = 0;
    uint32_t m_depth = 0;
  public:
    SrwRecursiveLock() = default;
    SrwRecursiveLock(const SrwRecursiveLock&) = delete;
    SrwRecursiveLock& operator=(const SrwRecursiveLock&) = delete;
    void lock() {
      const DWORD me = curTid();
      if (m_owner == me) { ++m_depth; return; }
      m_lock.lock();
      m_owner = me; m_depth = 1;
    }
    bool try_lock() {
      const DWORD me = curTid();
      if (m_owner == me) { ++m_depth; return true; }
      if (!m_lock.try_lock()) return false;
      m_owner = me; m_depth = 1; return true;
    }
    void unlock() {
      if (--m_depth == 0) { m_owner = 0; m_lock.unlock(); }
    }
    // Racy read by design: a thread comparing this with its own id gets a reliable answer
    // (only the owner writes its own id; any other value means "not me").
    DWORD owner() const { return m_owner; }
  };
}
