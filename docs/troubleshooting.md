# VieNeu Server Troubleshooting

## CUDA Not Detected

Run:

```bash
python scripts/check_runtime.py
```

Install a CUDA-enabled PyTorch wheel that matches your driver. For GTX 1070 Ti, prefer the documented CUDA 11.8 PyTorch install.

## GPU Too Old

The server requires NVIDIA compute capability sm_61 or newer for CUDA inference. Older GPUs automatically fall back to CPU.

## Out of Memory

GTX 1070 Ti has 8 GB VRAM. Use the smallest supported VieNeu model first, keep `VIENEU_MAX_CONCURRENT_JOBS=1`, and close other GPU workloads.

## Torch CUDA Wheel Mismatch

If CUDA is available but inference fails immediately, reinstall PyTorch with the CUDA 11.8 wheel documented in `docs/setup-sm61.md`.

## LMDeploy Import Errors

The backend server does not require LMDeploy. Keep:

```bash
VIENEU_DISABLE_LMDEPLOY=true
```

If an LMDeploy error appears during server startup, it is coming from a legacy entrypoint, not `vieneu-server`.

## Slow CPU Generation

CPU fallback is expected to be slower. Use CUDA when supported or reduce input length.

## Long Text Sounds Unstable

Long scripts are generated as multiple chunks. If voice quality drifts or chunk joins sound rough:

- Prefer `pnnbao-ump/VieNeu-TTS-v2` for quality when hardware allows it.
- Reduce `VIENEU_TTS_MAX_CHARS` to `140`-`180`.
- Lower `VIENEU_TTS_TEMPERATURE` to `0.30`-`0.40`.
- Keep punctuation and paragraph breaks clean before synthesis.
- Increase `VIENEU_TTS_SILENCE_SECONDS` slightly for narration.
- Use a preset voice or a clean 5-10 second reference with matching language/style.

## WebSocket Connection Issues

Create the job first with `POST /tts/jobs`, then connect to `WS /ws/jobs/{job_id}` using the returned job ID.

## Cloudflare Tunnel Token Not Found

Run the Docker Compose Cloudflare profile from the repository root and pass the root `.env` explicitly:

```powershell
docker compose --env-file .env -f docker/docker-compose.pwa.yml --profile frontend-tunnel up --build
```

`env_file` passes variables into containers after Compose has parsed the file. The `cloudflared` command uses `${TUNNEL_TOKEN}`, so Compose must receive the variable during parsing through `--env-file .env` or a PowerShell environment variable.
