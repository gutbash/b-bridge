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
#include "pch.h"
#include "d3d9_lss.h"
#include <cstring>
#include <type_traits>


/*
 * Direct3DStateBlock9_LSS Interface Implementation
 */

HRESULT Direct3DStateBlock9_LSS::QueryInterface(REFIID riid, LPVOID* ppvObj) {
  LogFunctionCall();
  if (ppvObj == nullptr)
    return E_POINTER;

  *ppvObj = nullptr;

  if (riid == __uuidof(IUnknown)
    || riid == __uuidof(IDirect3DStateBlock9)) {
    *ppvObj = bridge_cast<IDirect3DStateBlock9*>(this);
    AddRef();
    return S_OK;
  }

  return E_NOINTERFACE;
}

ULONG Direct3DStateBlock9_LSS::AddRef() {
  LogFunctionCall();
  // No push since we only care about the last Release call
  return D3DBase::AddRef();
}

ULONG Direct3DStateBlock9_LSS::Release() {
  LogFunctionCall();
  return D3DBase::Release();
}

void Direct3DStateBlock9_LSS::onDestroy() {
  ClientMessage { Commands::IDirect3DStateBlock9_Destroy, getId() };
}

HRESULT Direct3DStateBlock9_LSS::GetDevice(IDirect3DDevice9** ppDevice) {
  LogFunctionCall();
  if (ppDevice == nullptr) {
    return D3DERR_INVALIDCALL;
  }
  m_pDevice->AddRef();
  (*ppDevice) = m_pDevice;
  return S_OK;
}

void Direct3DStateBlock9_LSS::buildPlan() {
  const auto& flags = m_dirtyFlags;
  TransferPlan p;
  auto collect = [](const auto& arr, auto& out, bool& all) {
    using T = typename std::remove_reference_t<decltype(out)>::value_type;
    out.clear();
    for (size_t i = 0; i < arr.size(); i++) {
      if (arr[i]) {
        out.push_back((T) i);
      }
    }
    all = (out.size() == arr.size());
  };
  bool dummy;
  collect(flags.renderStates, p.renderStates, p.allRenderStates);
  collect(flags.transforms, p.transforms, p.allTransforms);
  collect(flags.vertexConstants.fConsts, p.vsF, p.allVsF);
  collect(flags.vertexConstants.iConsts, p.vsI, p.allVsI);
  collect(flags.vertexConstants.bConsts, p.vsB, dummy);
  collect(flags.pixelConstants.fConsts, p.psF, p.allPsF);
  collect(flags.pixelConstants.iConsts, p.psI, p.allPsI);
  collect(flags.pixelConstants.bConsts, p.psB, dummy);
  collect(flags.streams, p.streams, dummy);
  collect(flags.streamOffsetsAndStrides, p.streamOffsetsAndStrides, dummy);
  collect(flags.streamFreqs, p.streamFreqs, dummy);
  collect(flags.textures, p.textures, dummy);
  collect(flags.clipPlanes, p.clipPlanes, dummy);
  size_t total = 0;
  for (size_t i = 0; i < flags.samplerStates.size(); i++) {
    for (size_t j = 0; j < flags.samplerStates[i].size(); j++) {
      total++;
      if (flags.samplerStates[i][j]) {
        p.samplerStates.push_back((uint16_t) (i * 64 + j));
      }
    }
  }
  p.allSamplerStates = (p.samplerStates.size() == total);
  total = 0;
  for (size_t i = 0; i < flags.textureStageStates.size(); i++) {
    for (size_t j = 0; j < flags.textureStageStates[i].size(); j++) {
      total++;
      if (flags.textureStageStates[i][j]) {
        p.textureStageStates.push_back((uint16_t) (i * 64 + j));
      }
    }
  }
  p.allTextureStageStates = (p.textureStageStates.size() == total);
  p.built = true;
  m_plan = std::move(p);
}

void Direct3DStateBlock9_LSS::StateTransfer(const BaseDirect3DDevice9Ex_LSS::StateCaptureDirtyFlags& flags, BaseDirect3DDevice9Ex_LSS::State& src, BaseDirect3DDevice9Ex_LSS::State& dst) {
  if (!m_plan.built) {
    buildPlan();
  }
  const TransferPlan& p = m_plan;
  if (p.allRenderStates) {
    dst.renderStates = src.renderStates;
  } else {
    for (uint16_t i : p.renderStates) {
      dst.renderStates[i] = src.renderStates[i];
    }
  }
  if (flags.vertexDecl) {
    dst.vertexDecl = src.vertexDecl;
  }
  if (flags.indices) {
    dst.indices = src.indices;
  }
  if (p.allSamplerStates) {
    dst.samplerStates = src.samplerStates;
  } else {
    for (uint16_t k : p.samplerStates) {
      dst.samplerStates[k >> 6][k & 63] = src.samplerStates[k >> 6][k & 63];
    }
  }
  for (uint8_t i : p.streams) {
    dst.streams[i] = src.streams[i];
  }
  for (uint8_t i : p.streamOffsetsAndStrides) {
    dst.streamOffsets[i] = src.streamOffsets[i];
    dst.streamStrides[i] = src.streamStrides[i];
  }
  for (uint8_t i : p.streamFreqs) {
    dst.streamFreqs[i] = src.streamFreqs[i];
  }
  for (uint8_t i : p.textures) {
    dst.textures[i] = src.textures[i];
    dst.textureTypes[i] = src.textureTypes[i];
  }
  if (flags.vertexShader) {
    dst.vertexShader = src.vertexShader;
  }
  if (flags.pixelShader) {
    dst.pixelShader = src.pixelShader;
  }
  if (flags.material) {
    dst.material = src.material;
  }
  for (const auto& [key, value] : flags.lights) {
    dst.lights[key] = src.lights[key];
  }
  for (const auto& [key, value] : flags.bLightEnables) {
    dst.bLightEnables[key] = src.bLightEnables[key];
  }
  if (p.allTransforms) {
    dst.transforms = src.transforms;
  } else {
    for (uint16_t i : p.transforms) {
      dst.transforms[i] = src.transforms[i];
    }
  }
  if (p.allTextureStageStates) {
    dst.textureStageStates = src.textureStageStates;
  } else {
    for (uint16_t k : p.textureStageStates) {
      dst.textureStageStates[k >> 6][k & 63] = src.textureStageStates[k >> 6][k & 63];
    }
  }
  if (flags.viewport) {
    dst.viewport = src.viewport;
  }
  if (flags.scissorRect) {
    dst.scissorRect = src.scissorRect;
  }
  for (uint8_t i : p.clipPlanes) {
    for (int j = 0; j < 4; j++) {
      dst.clipPlanes[i][j] = src.clipPlanes[i][j];
    }
  }
  if (p.allVsF) {
    memcpy(dst.vertexConstants.fConsts, src.vertexConstants.fConsts, sizeof(dst.vertexConstants.fConsts));
  } else {
    for (uint16_t i : p.vsF) {
      dst.vertexConstants.fConsts[i] = src.vertexConstants.fConsts[i];
    }
  }
  if (p.allVsI) {
    memcpy(dst.vertexConstants.iConsts, src.vertexConstants.iConsts, sizeof(dst.vertexConstants.iConsts));
  } else {
    for (uint16_t i : p.vsI) {
      dst.vertexConstants.iConsts[i] = src.vertexConstants.iConsts[i];
    }
  }
  for (uint16_t i : p.vsB) {
    const size_t dwordIndex = i / 32;
    const uint32_t bitMask = 1u << (i % 32);
    dst.vertexConstants.bConsts[dwordIndex]
      = (src.vertexConstants.bConsts[dwordIndex] & bitMask) ? dst.vertexConstants.bConsts[dwordIndex] | bitMask : dst.vertexConstants.bConsts[dwordIndex] & ~bitMask;
  }
  if (p.allPsF) {
    memcpy(dst.pixelConstants.fConsts, src.pixelConstants.fConsts, sizeof(dst.pixelConstants.fConsts));
  } else {
    for (uint16_t i : p.psF) {
      dst.pixelConstants.fConsts[i] = src.pixelConstants.fConsts[i];
    }
  }
  if (p.allPsI) {
    memcpy(dst.pixelConstants.iConsts, src.pixelConstants.iConsts, sizeof(dst.pixelConstants.iConsts));
  } else {
    for (uint16_t i : p.psI) {
      dst.pixelConstants.iConsts[i] = src.pixelConstants.iConsts[i];
    }
  }
  for (uint16_t i : p.psB) {
    const size_t dwordIndex = i / 32;
    const uint32_t bitMask = 1u << (i % 32);
    dst.pixelConstants.bConsts[dwordIndex]
      = (src.pixelConstants.bConsts[dwordIndex] & bitMask) ? dst.pixelConstants.bConsts[dwordIndex] | bitMask : dst.pixelConstants.bConsts[dwordIndex] & ~bitMask;
  }
}

void Direct3DStateBlock9_LSS::LocalCapture() {
  StateTransfer(m_dirtyFlags, m_pDevice->m_state, m_captureState);
}

HRESULT Direct3DStateBlock9_LSS::Capture() {
  LogFunctionCall();
  if (m_pDevice->m_stateRecording) {
    return D3DERR_INVALIDCALL;
  }
  LocalCapture();
  {
    ClientMessage { Commands::IDirect3DStateBlock9_Capture, getId() };
  }
  return S_OK;
}

HRESULT Direct3DStateBlock9_LSS::Apply() {
  LogFunctionCall();
  StateTransfer(m_dirtyFlags, m_captureState, m_pDevice->m_state);
  {
    ClientMessage { Commands::IDirect3DStateBlock9_Apply, getId() };
  }
  return S_OK;
}
