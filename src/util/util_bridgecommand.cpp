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
#include "util_bridgecommand.h"
#include "log/log_strings.h"

namespace {
  DWORD get_default_timeout() {
    const auto timeout = GlobalOptions::getCommandTimeout();
    const auto retries = GlobalOptions::getCommandRetries();
    const auto default = timeout * retries;
    // Catch overflow and return infinite in that case
    return ((timeout != 0) && (default / timeout != retries)) ? INFINITE : default;
  }
}

#define DECL_BRIDGE_FUNC(RETURN_T, NAME, ...) \
  template<typename BridgeId> \
  RETURN_T Bridge<BridgeId>::NAME(__VA_ARGS__)

DECL_BRIDGE_FUNC(void, init,
    const std::string baseName,
    const size_t writerChannelMemSize, const size_t writerChannelCmdQueueSize,
    const size_t writerChannelDataQueueSize, const size_t readerChannelMemSize,
    const size_t readerChannelCmdQueueSize, const size_t readerChannelDataQueueSize) {
  static bool bIsInit = false;
  if (bIsInit) {
    Logger::warn("Re-Init'ing Bridge type. May be sign of problem code.");
    return;
  }
  s_pWriterChannel = new WriterChannel(
    baseName + kWriterChannelName,
    writerChannelMemSize, writerChannelCmdQueueSize, writerChannelDataQueueSize);
  s_pReaderChannel = new ReaderChannel(
    baseName + kReaderChannelName,
    readerChannelMemSize, readerChannelCmdQueueSize, readerChannelDataQueueSize);
  bIsInit = true;
}

DECL_BRIDGE_FUNC(void, syncDataQueue, size_t expectedMemUsage, bool posResetOnLastIndex) {
  // 2026-09-05: *serverDataPos is written by the other process on every pull; reading it on every
  // data push was a cross-core miss per push. Use a local copy (always <= the true position, i.e.
  // conservative) and refresh it every 64 pushes or whenever the copy suggests an overwrite.
  static int s_cachedServerPos = -1;
  static uint32_t s_cachedServerPosAge = 0;
  if (++s_cachedServerPosAge >= 64) {
    s_cachedServerPos = (int) *s_pWriterChannel->serverDataPos;
    s_cachedServerPosAge = 0;
  }
  int serverCount = s_cachedServerPos;
  size_t currClientDataPos = s_pWriterChannel->get_data_pos();
  size_t expectedClientDataPos = currClientDataPos + ((expectedMemUsage != 0) ? expectedMemUsage : 1) - 1;
  size_t totalSize = s_pWriterChannel->data->get_total_size();

  auto handleOverwriteCondition = [&]() {
    // Below variable is set to let the server know that a particular position
    // in the queue not yet accessed by it is going to be used
    *s_pWriterChannel->clientDataExpectedPos = s_curBatchStartPos - 1;
    Logger::warn("Data Queue overwrite condition triggered");
    // Check to see if there is even enough space to ever succeed in pushing all the data
    if ((expectedMemUsage + (currClientDataPos >= s_curBatchStartPos ? currClientDataPos - s_curBatchStartPos : currClientDataPos + totalSize - s_curBatchStartPos)) > totalSize) {
      Logger::errLogMessageBoxAndExit(std::string(logger_strings::OutOfBufferMemory) + std::string(logger_strings::OutOfBufferMemory1) + logger_strings::bufferNameToOption(s_pWriterChannel->data->getName()));
    }
    // Wait for the server to access the data at the above postion
    const auto maxRetries = GlobalOptions::getCommandRetries();
    size_t numRetries = 0;
    Logger::warn("Waiting on server to process enough data from data queue to prevent overwrite...");
    // The server can only consume data for commands it can see: publish everything batched first.
    flushAllBridgeWriters();
    while (RESULT_FAILURE(s_pWriterChannel->dataSemaphore->wait()) && numRetries++ < maxRetries) {
    }
    if (numRetries >= maxRetries) {
      Logger::err("Max retries reached waiting on the server to process enough data to prevent a overwrite!");
    }
    *s_pWriterChannel->clientDataExpectedPos = -1;
    *s_pWriterChannel->serverResetPosRequired = false;
    Logger::info("DataQueue overwrite condition resolved");
  };

  if (expectedClientDataPos >= totalSize) {
    if (*s_pWriterChannel->serverResetPosRequired == true) {
      // Double Overflow Condition Detected, mitigate by stalling and waiting for a response
      handleOverwriteCondition();
    }
    if (posResetOnLastIndex) {
      // Reset index pos to 0 if the size is larger than the remaining buffer
      expectedClientDataPos = expectedMemUsage - 1;
    } else {
      // Evaluate the respective pos when the end of the queue is reached
      expectedClientDataPos = expectedClientDataPos - totalSize;
    }
    // Below variable is set when the server needs to complete a loop to get to
    // the client's expected position. When this is set on pull we check if
    // m_pos is reset and toggle this variable if it is
    *s_pWriterChannel->serverResetPosRequired = true;
  }

  /*
    * overwrite conditions
    * 1. client < server, expectedClient >= server
    * 2. client > server, expectedClient >= server, expectedClient < client
    */
  auto wouldOverwrite = [&](int sc) {
    return expectedClientDataPos >= sc &&
      ((s_curBatchStartPos < sc)
       || (s_curBatchStartPos > sc && expectedClientDataPos < s_curBatchStartPos)
       || ((s_curBatchStartPos <= sc) && *s_pWriterChannel->serverResetPosRequired));
  };
  if (wouldOverwrite(serverCount)) {
    // Re-check against the live position before stalling.
    serverCount = (int) *s_pWriterChannel->serverDataPos;
    s_cachedServerPos = serverCount;
    s_cachedServerPosAge = 0;
    if (wouldOverwrite(serverCount)) {
      handleOverwriteCondition();
    }
  }
}

DECL_BRIDGE_FUNC(Header, pop_front) {
  ZoneScoped;
  Result result;
  // No retries, but wait the same amount of time
  const auto response = getReaderChannel().commands->pull(result, get_default_timeout());
  if (RESULT_FAILURE(result)) {
    // For now just log when things go wrong, but could use some robustness improvements
    Logger::err("CommandQueue get_response: Failed to retrieve the command response!");
  }
  return response;
}

DECL_BRIDGE_FUNC(bridge_util::Result, ensureQueueEmpty) {
  flushAllBridgeWriters();
  if (getReaderChannel().commands->isEmpty()) {
    return bridge_util::Result::Success;
  }

  const uint32_t maxAttempts = GlobalOptions::getCommandRetries();
  uint32_t attemptNum = 0;
  do {
    Result result;
    getReaderChannel().commands->peek(result, 1);

    if (result != Result::Timeout) {
      // Give the server some time to process the commands
      Sleep(8);
    } else {
      // Timeout from peek() means the queue is empty
      return bridge_util::Result::Success;
    }
  } while (attemptNum++ <= maxAttempts && gbBridgeRunning);

  return bridge_util::Result::Timeout;
}

DECL_BRIDGE_FUNC(bridge_util::Result, waitForCommand, const Commands::D3D9Command& command,
                                                      DWORD overrideTimeoutMS,
                                                      std::atomic<bool>* const pbEarlyOutSignal, bool verifyUID, UID uidToVerify) {
  ZoneScoped;
  // Anything we are about to wait for can only arrive once the other side has seen everything we queued.
  flushAllBridgeWriters();
  DWORD peekTimeoutMS = overrideTimeoutMS > 0 ? overrideTimeoutMS : GlobalOptions::getCommandTimeout();
  uint32_t maxAttempts = GlobalOptions::getCommandRetries();
#ifdef ENABLE_WAIT_FOR_COMMAND_TRACE
  if (command != Commands::Any) {
    Logger::trace(format_string("Waiting for command %s for %d ms up to %d times...", Commands::toString(command).c_str(), peekTimeoutMS, maxAttempts));
  }
#endif
#if defined(_DEBUG) || defined(DEBUGOPT)
  if (GlobalOptions::getLogAllCommands()) {
    Logger::info("waitForCommand Command:" + toString(command) + (verifyUID ? " UID: " + std::to_string(uidToVerify) : ""));
  }
#endif
  bool infiniteRetries = false;
  bool bEarlyOut = false;
  uint32_t attemptNum = 0;
  do {
    Result result;
    Header header = getReaderChannel().commands->peek(result, peekTimeoutMS, pbEarlyOutSignal);

    switch (result) {

    case Result::Success:
    {
      bool uidVerified = true;
      if (verifyUID) {
        if (header.pHandle != uidToVerify) {
          uidVerified = false;
        }
      }
      if ((command == Commands::Bridge_Any) || (header.command == command) && uidVerified) {
#ifdef ENABLE_WAIT_FOR_COMMAND_TRACE
        if (command != Commands::Bridge_Any) {
          Logger::trace(format_string("...success, command %s received!", Commands::toString(command).c_str()));
        }
#endif
        return Result::Success;
      } else {
#if defined(_DEBUG) || defined(DEBUGOPT)
        if (GlobalOptions::getLogAllCommands()) {
          Logger::info(format_string("Different instance of a command detected: %s with UID: %s , Expected: %s with UID: %s. ", Commands::toString(header.command).c_str(), std::to_string(header.pHandle).c_str(),
                                     Commands::toString(command).c_str(), std::to_string(uidToVerify).c_str()));
        }
#endif
        // If we see the incorrect command, we want to give the other side of
        // the bridge ample time to make an attempt to process it first
        Sleep(peekTimeoutMS);
      }
      break;
    }

    case Result::Timeout:
    {
      if (GlobalOptions::getInfiniteRetries()) {
        // Infinite retries requested, the application might be alt-tabbed and sleeping, and so we need to wait too.

        // Set timeout for consecutive peeks to 1ms to relieve spin-waits.
        peekTimeoutMS = 1;
        // Decrease the attempt counter so it won't overrun maxAttempts in case it did not capture infinite retries.
        if (attemptNum > 0) {
          --attemptNum;
        }
        // Set the flag so that the consecutive peek 1ms-timeout would not generate a failure in case if
        // infinite retries are revoked in the process.
        infiniteRetries = true;

        // Sleep for default OS period
        Sleep(1);
      } else if (infiniteRetries) {
        // A timeout in infinite retries loop but infinite retries have been revoked (app restored from alt-tab).

        // Restore peek timeout interval and continue.
        peekTimeoutMS = overrideTimeoutMS > 0 ? overrideTimeoutMS : GlobalOptions::getCommandTimeout();
        // Drop the flag - we're in the normal loop now.
        infiniteRetries = false;
      }
      Logger::trace(format_string("Peek timeout while waiting for command: %s.", Commands::toString(command).c_str()));
      break;
    }

    case Result::Failure:
    {
      Logger::trace(format_string("Peek failed while waiting for command: %s.", Commands::toString(command).c_str()));
      return Result::Failure;
    }

    }
    if (pbEarlyOutSignal) {
      bEarlyOut = pbEarlyOutSignal->load();
    }
  } while (!bEarlyOut &&
            attemptNum++ <= maxAttempts &&
            gbBridgeRunning);
  return Result::Timeout;
}

#define DECL_COMMAND_FUNC(RETURN_T, NAME, ...) \
  template<typename BridgeId> \
  RETURN_T Bridge<BridgeId>::Command::NAME(__VA_ARGS__)

#ifdef REMIX_BRIDGE_CLIENT
bool g_stateBatchPending = false;
void (*g_stateBatchFlush)() = nullptr;
#endif

DECL_COMMAND_FUNC(,Command,const Commands::D3D9Command command,
                           uintptr_t pHandle,
                           const Commands::Flags commandFlags)
  : m_command(command)
  , m_handle((uint32_t) (size_t) pHandle)
  , m_commandFlags(commandFlags) {
#ifdef REMIX_BRIDGE_CLIENT
  if (g_stateBatchPending && command != Commands::IDirect3DDevice9Ex_StateBatch && g_stateBatchFlush) {
    // The batch buffer is device state guarded by the (recursive) channel lock; a Draw from a thread
    // that does not hold the device lock must not flush while another thread appends.
    s_pWriterChannel->m_mutex.lock();
    if (g_stateBatchPending) {
      g_stateBatchPending = false;
      g_stateBatchFlush();   // runs a complete StateBatch Command (ctor+dtor) before this one starts
    }
    s_pWriterChannel->m_mutex.unlock();
  }
#endif
  // If the assert or exception gets triggered it means that there is more than one Command
  // instance in a function or command block with overlapping object lifecycles. Only one instance
  // can be alive at a time to ensure data integrity on the command and data buffers. To resolve
  // this issue I recommend enclosing the Command object in its own scope block, and make
  // sure there is no command nesting happening either.

#if defined(_DEBUG) || defined(DEBUGOPT)
  if (GlobalOptions::getLogAllCommands()) {
#ifdef REMIX_BRIDGE_CLIENT
    Logger::info("Requesting: " +toString(command) + " UID: " + std::to_string(s_cmdUID));
#else
    Logger::info("Responding: " + toString(command) + " UID: " + std::to_string(pHandle));
#endif
  }
#endif

#ifdef REMIX_BRIDGE_CLIENT
  s_pWriterChannel->m_mutex.lock();   // recursive: free when the caller already holds the device lock
#endif

  assert(!s_pWriterChannel->pbCmdInProgress->load(std::memory_order_relaxed));
  if (s_pWriterChannel->pbCmdInProgress->load(std::memory_order_relaxed)) {
    Logger::errLogMessageBoxAndExit(logger_strings::MultipleActiveCommands);
  }
  // Only start a data batch if the bridge is actually enabled, otherwise this becomes a no-op
  if (gbBridgeRunning) {
    s_pWriterChannel->data->begin_batch();
  }
  s_pWriterChannel->pbCmdInProgress->store(true, std::memory_order_relaxed);   // same-thread guard under the channel lock; no fence needed
  s_curBatchStartPos = (int32_t) s_pWriterChannel->data->get_pos();
  s_cmdCounter++;
  // 2026-09-05: the command UID is no longer pushed through the data ring. The queue is a strict FIFO, so
  // the server derives the same UID by counting the headers it pulls (see ProcessDeviceCommandQueue /
  // processModuleCommandQueue); the client only advances s_cmdUID for headers that were actually pushed.
}

DECL_COMMAND_FUNC(,~Command) {
  // Only actually send the command if the bridge is enabled, otherwise this becomes a no-op
  bool headerSent = false;
  if (gbBridgeRunning) {
    s_pWriterChannel->data->end_batch();
    s_curBatchStartPos = -1;
    uint32_t numRetries = 0;
    Result result;
    // We check if the bridge is enabled for each loop iteration in case it
    // was disabled externally by the server process exit callback.
    do {
      result = s_pWriterChannel->commands->push({ m_command, m_commandFlags, (uint32_t) s_pWriterChannel->data->get_pos(), m_handle });
#if defined(_DEBUG) || defined(DEBUGOPT)
      if (GlobalOptions::getLogAllCommands()) {
        Logger::info("Pushed: " + toString(m_command));
      }
#endif
    } while (
          RESULT_FAILURE(result)
      && numRetries++ < GlobalOptions::getCommandRetries()
      && gbBridgeRunning
#ifdef REMIX_BRIDGE_CLIENT
      && BridgeState::getServerState_NoLock() == BridgeState::ProcessState::Running
#endif
    );
#ifdef REMIX_BRIDGE_CLIENT
    if (BridgeState::getServerState_NoLock() >= BridgeState::ProcessState::DoneProcessing) {
      Logger::warn(format_string("The command %s will not be sent; Server is in the process of or has already shut down. Turning bridge off.", Commands::toString(m_command).c_str()));
      gbBridgeRunning = false;;
    } else
#endif
      if (RESULT_FAILURE(result) && gbBridgeRunning) {
        Logger::err(format_string("The command %s could not be successfully sent, turning bridge off and falling back to client rendering!", Commands::toString(m_command).c_str()));
        gbBridgeRunning = false;
      } else if (RESULT_SUCCESS(result) && numRetries > 1) {
        std::string command = Commands::toString(m_command);
        Logger::debug(format_string("The command %s took %d retries (%d ms)!", command.c_str(), numRetries, numRetries * GlobalOptions::getCommandTimeout()));
      }
    headerSent = RESULT_SUCCESS(result);
  }
  s_pWriterChannel->pbCmdInProgress->store(false, std::memory_order_relaxed);
#ifdef REMIX_BRIDGE_CLIENT
  {
    auto& ws = bridge_util::WaitStats::get();
    ws.cmds++;
    if ((uint16_t) m_command < bridge_util::WaitStats::kHistSize) ws.hist[(uint16_t) m_command]++;
  }
  // UID = number of headers pushed before this one; the server counts pulled headers the same way.
  if (headerSent) {
    ++s_cmdUID;
  }
  s_pWriterChannel->m_mutex.unlock();
#endif
}

template class Bridge<BridgeId::Module>;
template class Bridge<BridgeId::Device>;

void flushAllBridgeWriters() {
  Bridge<BridgeId::Device>::flushWriter();
  Bridge<BridgeId::Module>::flushWriter();
}