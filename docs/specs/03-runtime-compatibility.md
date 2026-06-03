# Runtime Compatibility

## Goals
- Detect CUDA capability explicitly.
- Support NVIDIA sm_61 and newer GPUs.
- Fall back to CPU when CUDA is unavailable or unsupported.

## Non-goals
- No automatic CUDA driver installation.
- No requirement for BF16, FlashAttention, Triton, XFormers, or torch.compile.

## Constraints
- FP16 is preferred on supported CUDA.
- FP32 is preferred on CPU.
- GPU lower than sm_61 must not be selected.

## Design Decisions
- `get_runtime_device()` returns device, torch device, CUDA availability, GPU name, compute capability, dtype, and reason.
- `VIENEU_DEVICE=auto` selects CUDA only when capability is supported.
- Explicit `VIENEU_DEVICE=cpu` always uses CPU.

## Acceptance Criteria
- Runtime tests cover CPU, sm_61, below-sm_61, newer CUDA GPUs, and dtype selection.
- `/runtime` exposes the selected runtime and fallback reason.

## Risks
- Installed PyTorch CUDA wheels can be incompatible with older GPUs even when hardware is sm_61.

## Open Questions
- Whether to add a hard startup warning for known incompatible CUDA wheel versions.
