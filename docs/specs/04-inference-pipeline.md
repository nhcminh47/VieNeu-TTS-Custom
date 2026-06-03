# Inference Pipeline

## Goals
- Provide a clean `TtsEngine` abstraction for server use.
- Reuse existing VieNeu PyTorch and codec code.
- Keep LMDeploy optional and lazy only.

## Non-goals
- No model weight changes.
- No new training path.
- No non-VieNeu model support.

## Constraints
- Default backend is `torch`.
- User-selected model IDs must pass the VieNeu registry.
- Generated audio is saved to a local file.

## Design Decisions
- `VieNeuTorchEngine` wraps the existing `Vieneu` factory.
- Turbo v2 uses the existing non-LMDeploy `turbo_gpu` path for PyTorch model loading.
- Standard models use the existing `standard` path with GGUF disabled for PyTorch inference.
- The engine loads lazily on the first synthesize call.

## Acceptance Criteria
- Server startup does not download models.
- First TTS job loads the selected VieNeu model.
- Failed synthesis marks the job failed and preserves the error message.

## Risks
- Voice cloning support depends on valid reference voice assets or reference audio paths.
- Large PyTorch models may exceed GTX 1070 Ti memory.

## Open Questions
- Whether to expose GGUF as a separate optional backend after the PyTorch MVP.
