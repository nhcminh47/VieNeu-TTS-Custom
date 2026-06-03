# Product Scope

## Goals
- Provide a backend-only VieNeu TTS API server.
- Run VieNeu Hugging Face models locally with a PyTorch-first backend.
- Support NVIDIA GPUs from compute capability sm_61 upward, including GTX 1070 Ti.
- Provide HTTP job APIs, WebSocket job events, local audio output, runtime diagnostics, and tests.

## Non-goals
- No Next.js, PWA, Gradio, or browser UI.
- No training, fine-tuning, payment, authentication, cloud inference, or distributed queue.
- No non-VieNeu TTS providers or unrelated Hugging Face models.

## Constraints
- User-facing model IDs must be restricted to VieNeu repositories.
- LMDeploy, FlashAttention, Triton, XFormers, and torch.compile must not be required.
- The default server backend is PyTorch/local inference.

## Design Decisions
- Add a new `vieneu_server` package instead of replacing the existing SDK.
- Keep demo/UI code available but outside the backend MVP.
- Store generated files in a local output directory.

## Acceptance Criteria
- Server can start without LMDeploy installed.
- Health, runtime, model list, job creation, job status, audio download, and WebSocket endpoints exist.
- Setup docs clearly describe sm_61 and GTX 1070 Ti support.

## Risks
- Full PyTorch inference may need large memory on 8 GB GPUs.
- Existing docs contain mojibake in terminal output and should be edited carefully.

## Open Questions
- Whether future releases should expose authentication or persistent job storage.
