---
name: local-nemotron-stt-fleet
description: Stand up NVIDIA Nemotron 3.5 ASR (streaming, CPU ONNX) as the shared speech-to-text backend for every Hermes agent on this machine, replacing the broken faster-whisper/libcublas path. Use when voice messages arrive untranscribed or when asked to enable local speech recognition for the agent fleet.
triggers:
  - install local speech recognition for the agents
  - voice messages arrive blank / libcublas error
  - nemotron asr or parakeet local install
  - replace whisper with a local ASR model
  - enable voice transcription fleet-wide
---

# Local Nemotron 3.5 ASR for the whole agent fleet

Make every Hermes agent transcribe voice messages locally on CPU. The box has **no GPU**,
and the default `stt.provider: local` (faster-whisper) dies on a missing `libcublas.so.12`
CUDA library. The fix uses Hermes' built-in **`local_command`** STT provider pointed at a
CPU ONNX runner — no edits to the hermes-agent code.

The full working deployment is already on disk at `/home/itadmin/nemotron-stt/` (model/, venv/,
bin/ffmpeg, transcribe.py, nemotron-stt.sh) — copy from there. A reference copy of the inference
script also lives at `references/transcribe.py` in this skill. Literal copy-paste setup commands
(hf download, pip, systemd drop-ins, config edits) are recoverable from the 2026-06-18 session
transcript via session_search if needed.

## Hard-won lessons (read first — these cost the most time)
- **Model id**: the real model is `nvidia/nemotron-3.5-asr-streaming-0.6b` (note `-asr-`).
  Its official repo is a `.nemo` needing NeMo+CUDA — wrong for CPU. Use the community CPU build
  `onnx-community/nemotron-3.5-asr-streaming-0.6b-onnx-int4` (encoder/decoder/joint `.onnx` +
  silero_vad + tokenizer; ~757 MB on disk despite the "int4" label).
- **Shared-path trap**: Jay's `~` resolves to `.../profiles/jay/home`, but each agent runs with a
  different HOME. Install fleet assets to the REAL path `/home/itadmin/nemotron-stt/` so all agents
  resolve them identically. Never park shared assets under a profile `~`.
- **onnxruntime-genai does NOT drive this model** even though the model card says so — the
  `genai_config.json` is a custom `nemotron_speech` descriptor it can't execute. Drive the three
  ONNX graphs directly with plain `onnxruntime` (see `references/transcribe.py`).
- **ffmpeg**: not installed, and sudo is password-gated. The Playwright-bundled ffmpeg is
  `--disable-everything` (no audio codecs — useless). Use a johnvansickle **static** build dropped
  at `/home/itadmin/nemotron-stt/bin/ffmpeg`, and put that dir first on each gateway's PATH —
  Hermes pre-converts non-WAV audio (voice msgs are `.ogg`/Opus) and needs ffmpeg discoverable.
- **Provider must be explicit**: if `stt.provider` is absent, Hermes auto-detects and picks the
  broken `local` (faster-whisper present). Set `local_command` explicitly in the base config AND
  every profile config.
- **Restart safety**: restarting the gateways bounces all agents. Restart the OTHER agents first,
  verify healthy, then base + your own last. (A live one-shot session usually survives its own
  gateway bounce, but do yourself last to be safe — and finish all other work first.)
- Performance: ~2x realtime, ~1.1 GB peak RAM (fits a ~3 GB-free box).

## Procedure
1. Confirm the real model id via the HF API; pick the `onnx-community ...-onnx-int4` build.
2. Create `/home/itadmin/nemotron-stt/{model,bin}`; download the model into `model/`.
3. Place a static ffmpeg at `bin/ffmpeg` (chmod +x).
4. Make a dedicated venv in `nemotron-stt/`; install `onnxruntime numpy librosa soundfile`.
5. Drop in `transcribe.py` (copy from `references/transcribe.py`) and a one-line wrapper
   `nemotron-stt.sh` that execs the venv python + transcribe.py "$@".
6. Per gateway service, add a systemd drop-in `*.service.d/stt-nemotron.conf` that sets
   `HERMES_LOCAL_STT_COMMAND` to the wrapper template
   (`... {input_path} --output_dir {output_dir} --model {model} --language {language}`) and a PATH
   that prepends `/home/itadmin/nemotron-stt/bin`.
7. Set `stt.provider: local_command` in the base config and in every profile config.
8. Reload the user systemd manager and restart the gateways (others first, base+self last).
9. Confirm the env var is live in a running gateway, then run the end-to-end check.

## Verify
- All gateways report active.
- From the hermes-agent venv with the env set:
  `from tools.transcription_tools import transcribe_audio; transcribe_audio('<some .ogg>')`
  returns `success True`, `provider local_command`, correct text, and NO libcublas error.
- A real voice message on Slack/Telegram now transcribes instead of arriving blank.

## Model I/O (for rebuilding transcribe.py)
Encoder in: audio_signal[1,65,128] (65 log-mel frames x 128 mels), length[1], cache_last_channel
[1,24,56,1024], cache_last_time[1,24,1024,8], cache_last_channel_len[1], lang_id[1] (0=English).
Encoder out: outputs[1,7,1024] + the three cache_*_next + encoded_lengths. Streaming: front-pad 9
zero frames, slide a 65-frame window advancing 56 per chunk, carry cache_*_next back in.
Decoder in: targets[b,L], h_in/c_in[2,b,640]; out decoder_output[b,640,L] (transpose to [b,L,640]
before the joint), h_out/c_out. Joint(encoder_output[b,T,1024], decoder_output[b,L,640]) ->
logits[b,T,L,13088]. RNNT greedy: blank_id 13087, SOS=blank, update LSTM state only on non-blank
emits, max 10 symbols/step. Detokenize from tokenizer.json unigram vocab; replace U+2581 with space.
Mel: n_fft512 hop160 win400 hann center, 128 mels 0-8000Hz slaney, preemph0.97, log(x+1e-10).
