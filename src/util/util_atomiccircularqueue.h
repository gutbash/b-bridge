/*
 * Copyright (c) 2022-2023, NVIDIA CORPORATION. All rights reserved.
 *
 * Permission is hereby granted, free of charge, to any person obtaining a
 * copy of this software and associated documentation files (the "Software"),
 * to deal in the Software without restriction, including without limitation
 * the rights to use, copy, modify, merge, publish, distribute, sublicense,
 * and/or sell copies of the Software, and to permit persons to whom the
 * Software is furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in
 * all copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.  IN NO EVENT SHALL
 * THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
 * FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
 * DEALINGS IN THE SOFTWARE.
 */
#pragma once

#include "util_common.h"

#include "../tracy/tracy.hpp"

#include <cstdio>
#include <atomic>
#include <assert.h>
#include <vector>
#define WIN32_LEAN_AND_MEAN
#include <windows.h>

namespace bridge_util {

  // Intra/Inter-process thread safe, shared circular queue.
  // Constructed from a shared pool of memory - and synchronized using static atomics
  // Single Producer, Single Consumer ONLY!
  template<typename T, bridge_util::Accessor Accessor>
  class AtomicCircularQueue {
    std::atomic<uint32_t>* m_write;
    std::atomic<uint32_t>* m_read;
    uint32_t m_cachedConsumer = 0;   // producer-local copy of *m_write (see push)
    mutable uint32_t m_cachedProducer = 0;   // consumer-local copy of *m_read (see peek/pull)
    // 2026-09-05 batched publish (producer side). *m_read is the index the consumer polls; storing it on
    // every push hands the cache line (and the entry's line) to the other core once per command, which at
    // ~70k commands/frame is the dominant per-command cost on both sides. The producer now writes entries
    // against a private index and publishes every m_publishBatch pushes or on flush(). flush() MUST run
    // before the producer blocks on anything the consumer has to do first (see flushAllBridgeWriters()).
    uint32_t m_localWrite = 0;     // producer's private write index (>= published *m_read)
    uint32_t m_pending = 0;        // entries written but not yet published
    uint32_t m_publishBatch = 1;   // 1 = publish on every push (original behaviour)
  public:
    void setPublishBatch(uint32_t n) { m_publishBatch = n ? n : 1; }
    uint32_t getPublishBatch() const { return m_publishBatch; }
    void flush() {
      if (m_pending) {
        m_read->store(m_localWrite, std::memory_order_release);
        m_pending = 0;
      }
    }
    // Idle accounting (consumer side): time spent spinning in peek/pull with nothing to read.
    mutable uint64_t m_idleUs = 0;
    mutable uint64_t m_idleEntries = 0;
    static uint64_t nowUs() {
      static LARGE_INTEGER f = [] { LARGE_INTEGER x; QueryPerformanceFrequency(&x); return x; }();
      LARGE_INTEGER c; QueryPerformanceCounter(&c);
      return (uint64_t) (c.QuadPart * 1000000ULL / f.QuadPart);
    }
  private:
    T m_lastPulled = {};

    T* m_data;
    T m_default;

    const size_t m_queueSize;

    static const size_t kAlignment = 128;
    static const size_t kWriteAtomicOffset = 0;
    static const size_t kReadAtomicOffset = kAlignment + kWriteAtomicOffset;
    static const size_t kMemoryPoolOffset = kAlignment + kReadAtomicOffset;

  public:
    static size_t getExtraMemoryRequirements() {
      return kMemoryPoolOffset;
    }

    AtomicCircularQueue(const std::string& name, void* pMemory, const size_t memSize, const size_t queueSize)
      : m_queueSize(queueSize)
      , m_data(nullptr) // INIT
    {
      // Ensure we have enough memory
      assert(memSize > kMemoryPoolOffset);
      assert(memSize - kMemoryPoolOffset >= queueSize * sizeof(T));

      // Writers own the memory, Readers are consumers
      if constexpr(IS_READER(Accessor)) {
        m_data = (T*) ((uintptr_t) pMemory + kMemoryPoolOffset);
        m_write = (std::atomic<uint32_t>*)((uintptr_t) pMemory + kWriteAtomicOffset);
        m_read = (std::atomic<uint32_t>*)((uintptr_t) pMemory + kReadAtomicOffset);
      } else if constexpr (IS_WRITER(Accessor)) {
        m_data = new((void*) ((uintptr_t) pMemory + kMemoryPoolOffset)) T[m_queueSize];
        m_write = new((void*) ((uintptr_t) pMemory + kWriteAtomicOffset)) std::atomic<uint32_t>(0);
        m_read = new((void*) ((uintptr_t) pMemory + kReadAtomicOffset)) std::atomic<uint32_t>(0);
      }

      assert(m_read->is_lock_free() && m_write->is_lock_free()); // Must be runtime check as it's CPU specific
    }

    AtomicCircularQueue(const AtomicCircularQueue& q) = delete;

    ~AtomicCircularQueue() {
    }

    // Push object to queue
    Result push(const T& obj) {
      ULONGLONG start = 0, curTick;
      const DWORD timeoutMS = GlobalOptions::getCommandTimeout();
      do {
        const auto nextWrite = queueIdxInc(m_localWrite);
        // 2026-09-05: the consumer index lives on a cache line the other process writes on every pop;
        // reading it per push cost a cross-core miss per command (58k commands/frame in GTA IV).
        // Keep a producer-local copy and only re-read the shared index when the copy says "full".
        if (nextWrite == m_cachedConsumer) {
          m_cachedConsumer = m_write->load(std::memory_order_acquire);
        }
        if (nextWrite != m_cachedConsumer) {
          m_data[m_localWrite] = obj;
          m_localWrite = nextWrite;
          // The element store is ordered before the index publish by the release store (x86: stores
          // are not reordered with other stores); no full fence needed.
          if (++m_pending >= m_publishBatch) {
            m_read->store(m_localWrite, std::memory_order_release);
            m_pending = 0;
          }
          return Result::Success;
        }

        // Full: publish what we hold so the consumer can drain it, then wait.
        flush();
        std::this_thread::yield();

        curTick = GetTickCount64();
        start = start > 0 ? start : curTick;
      } while (timeoutMS == 0 || start + timeoutMS > curTick);

      return Result::Failure;
    }

    // Does nothing but wait for the next command to come in
    Result try_peek(const DWORD timeoutMS = 0) {
      return Result::Success;
    }

    // Returns a ref to the first element in the queue
    // Note: Blocks if the queue is empty
    const T& peek(Result& result, const DWORD timeoutMS = 0, std::atomic<bool>* const pbEarlyOutSignal = nullptr) const {
      uint64_t idleT0 = 0;
      ULONGLONG start = 0, curTick;
      do {
        const auto currentWrite = m_write->load(std::memory_order_relaxed);
        // Consumer-local copy of the producer index (see push): only touch the shared line when the
        // copy says the queue is empty.
        if (currentWrite == m_cachedProducer) {
          m_cachedProducer = m_read->load(std::memory_order_acquire);
        }
        if (currentWrite != m_cachedProducer) {
          if (idleT0) { m_idleUs += nowUs() - idleT0; }
          result = Result::Success;
          return m_data[currentWrite];
        }
        if (!idleT0) { idleT0 = nowUs(); m_idleEntries++; }

        std::this_thread::yield();

        curTick = GetTickCount64();
        start = start > 0 ? start : curTick;
        
        if (pbEarlyOutSignal && pbEarlyOutSignal->load()) {
          result = Result::Timeout;
          return m_default;
        }
      } while (timeoutMS == 0 || start + timeoutMS > curTick);

      result = Result::Timeout;

      return m_default;
    }

    // Returns a copy to the first element in queue, AND removes it
    // Note: Blocks if queue is empty
    const T& pull(Result& result, const DWORD timeoutMS = 0, std::atomic<bool>* const pbEarlyOutSignal = nullptr) {
      ULONGLONG start = 0, curTick;
      do {
        const auto currentWrite = m_write->load(std::memory_order_relaxed);
        // Consumer-local copy of the producer index (see push): only touch the shared line when the
        // copy says the queue is empty.
        if (currentWrite == m_cachedProducer) {
          m_cachedProducer = m_read->load(std::memory_order_acquire);
        }
        if (currentWrite != m_cachedProducer) {
          // Copy out before publishing the slot back to the producer (the old code returned a
          // reference into a slot the producer could overwrite); a header copy is cheaper than the fence.
          m_lastPulled = m_data[currentWrite];
          m_write->store(queueIdxInc(currentWrite), std::memory_order_release);
          result = Result::Success;
          return m_lastPulled;
        }

        std::this_thread::yield();

        curTick = GetTickCount64();
        start = start > 0 ? start : curTick;

        if (pbEarlyOutSignal && pbEarlyOutSignal->load()) {
          result = Result::Timeout;
          return m_default;
        }
      } while (timeoutMS == 0 || start + timeoutMS > curTick);

      return m_default;
    }

    // Check for queue emptiness. The function may guarantee a correct result
    // ONLY when the queue is stalled on either end and only a single index
    // is advancing.
    bool isEmpty() const {
      const auto currentWrite = m_write->load(std::memory_order_relaxed);
      return currentWrite == m_read->load(std::memory_order_acquire);
    }

    std::vector<Commands::D3D9Command> buildQueueData(int maxQueueElements, int currentIndex) {
      std::vector<Commands::D3D9Command> commandHistory;
      int itemCount = 0;
      while (itemCount < m_queueSize && itemCount < maxQueueElements) {
        // To prevent adding default commands in the Queue to the command list
        if (m_data[currentIndex].command == Commands::Bridge_Invalid)
          break;
        commandHistory.push_back(m_data[currentIndex].command);
        currentIndex = queueIdxDec(currentIndex);
        ++itemCount;
      }
      return commandHistory;
    }

    std::vector<Commands::D3D9Command> getWriterQueueData(int maxQueueElements=10) {
      const auto currentRead = m_localWrite;   // includes entries not yet published
      int currentIndex = queueIdxDec(currentRead);
      return buildQueueData(maxQueueElements, currentIndex);
    }

    std::vector<Commands::D3D9Command> getReaderQueueData(int maxQueueElements = 10) {
      const auto currentWrite = m_write->load(std::memory_order_relaxed);
      int currentIndex = queueIdxDec(currentWrite);
      return buildQueueData(maxQueueElements, currentIndex);
    }

    uint32_t queueIdxInc(uint32_t idx) const {
      return idx + 1 < m_queueSize ? idx + 1 : 0;
    }

    uint32_t queueIdxDec(uint32_t idx) const {
      return idx == 0 ?  m_queueSize - 1 : idx - 1 ;
    }
  };

}