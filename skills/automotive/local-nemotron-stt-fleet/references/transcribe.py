#!/usr/bin/env python3
"""Transcribe audio using cache-aware FastConformer-RNNT (3 ONNX graphs).

Reference copy of the working runner deployed at /home/itadmin/nemotron-stt/transcribe.py.
Drives encoder.onnx / decoder.onnx / joint.onnx directly via onnxruntime (CPU).
CLI contract (matches the Hermes local_command template):
  transcribe.py <input_audio> --output_dir <dir> [--model <ignored>] [--language en]
Writes <stem>.txt into <output_dir> and prints the transcript.
"""
import argparse
import os
import subprocess
import sys
import tempfile

import numpy as np
import onnxruntime as ort

MODEL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "model")
FFMPEG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bin", "ffmpeg")

# Hyperparams (from the model's genai_config.json / audio_processor_config.json)
SR = 16000
N_FFT = 512
HOP = 160
WIN = 400
N_MELS = 128
FMIN = 0
FMAX = 8000
PREEMPH = 0.97
LOG_EPS = 1e-10
SUBSAMPLE = 8
PRE_ENCODE_CACHE = 9
CHUNK_SAMPLES = 8960  # 56 new mel frames -> 7 encoded frames
NEW_FRAMES = CHUNK_SAMPLES // HOP  # 56
WINDOW_FRAMES = NEW_FRAMES + PRE_ENCODE_CACHE  # 65
BLANK_ID = 13087
MAX_SYMBOLS = 10

LANG_MAP = {"en": 0, "en-us": 0}


def load_audio(path):
    """Convert any audio to 16k mono float32 wav using ffmpeg, then read it."""
    import soundfile as sf
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tf:
        tmp = tf.name
    try:
        subprocess.run(
            [FFMPEG, "-y", "-i", path, "-ac", "1", "-ar", str(SR),
             "-f", "wav", "-acodec", "pcm_s16le", tmp],
            check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        audio, sr = sf.read(tmp, dtype="float32")
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)
    if audio.ndim > 1:
        audio = audio.mean(axis=1)
    return audio.astype(np.float32)


def compute_logmel(audio):
    """NeMo-style log-mel filterbank features -> [T_frames, N_MELS]."""
    import librosa
    if PREEMPH and PREEMPH > 0:
        audio = np.concatenate([audio[:1], audio[1:] - PREEMPH * audio[:-1]])
    stft = librosa.stft(
        audio, n_fft=N_FFT, hop_length=HOP, win_length=WIN,
        window="hann", center=True, pad_mode="reflect",
    )
    power = np.abs(stft) ** 2.0  # mag_power=2.0
    mel_fb = librosa.filters.mel(
        sr=SR, n_fft=N_FFT, n_mels=N_MELS, fmin=FMIN, fmax=FMAX, norm="slaney", htk=False
    )
    mel = mel_fb @ power
    logmel = np.log(mel + LOG_EPS)
    return logmel.T.astype(np.float32)  # [T, N_MELS]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input_audio")
    ap.add_argument("--output_dir", required=True)
    ap.add_argument("--model", default="base")
    ap.add_argument("--language", default="en")
    args = ap.parse_args()

    lang_id = LANG_MAP.get(args.language.lower(), 0)
    os.makedirs(args.output_dir, exist_ok=True)

    audio = load_audio(args.input_audio)
    feats = compute_logmel(audio)  # [T, 128]
    T = feats.shape[0]

    pad = np.zeros((PRE_ENCODE_CACHE, N_MELS), dtype=np.float32)
    feats_p = np.concatenate([pad, feats], axis=0)

    so = ort.SessionOptions()
    so.intra_op_num_threads = max(1, os.cpu_count() or 1)
    enc = ort.InferenceSession(os.path.join(MODEL_DIR, "encoder.onnx"),
                               sess_options=so, providers=["CPUExecutionProvider"])
    dec = ort.InferenceSession(os.path.join(MODEL_DIR, "decoder.onnx"),
                               sess_options=so, providers=["CPUExecutionProvider"])
    joint = ort.InferenceSession(os.path.join(MODEL_DIR, "joint.onnx"),
                                 sess_options=so, providers=["CPUExecutionProvider"])

    cache_ch = np.zeros((1, 24, 56, 1024), dtype=np.float32)
    cache_tm = np.zeros((1, 24, 1024, 8), dtype=np.float32)
    cache_ch_len = np.zeros((1,), dtype=np.int64)
    lang = np.array([lang_id], dtype=np.int64)

    encoded_all = []
    n_chunks = (T + NEW_FRAMES - 1) // NEW_FRAMES
    for ci in range(n_chunks):
        start = ci * NEW_FRAMES
        win = feats_p[start:start + WINDOW_FRAMES]
        if win.shape[0] < WINDOW_FRAMES:
            win = np.concatenate(
                [win, np.zeros((WINDOW_FRAMES - win.shape[0], N_MELS), dtype=np.float32)],
                axis=0)
        audio_signal = win[None, :, :].astype(np.float32)  # [1,65,128]
        length = np.array([WINDOW_FRAMES], dtype=np.int64)
        out = enc.run(None, {
            "audio_signal": audio_signal,
            "length": length,
            "cache_last_channel": cache_ch,
            "cache_last_time": cache_tm,
            "cache_last_channel_len": cache_ch_len,
            "lang_id": lang,
        })
        enc_out, enc_len, cache_ch, cache_tm, cache_ch_len = out
        valid = int(enc_len[0])
        encoded_all.append(enc_out[0, :valid, :])

    encoder_frames = np.concatenate(encoded_all, axis=0)  # [Ttot, 1024]
    valid_frames = (T + SUBSAMPLE - 1) // SUBSAMPLE
    encoder_frames = encoder_frames[:valid_frames]

    # RNNT greedy decode
    h = np.zeros((2, 1, 640), dtype=np.float32)
    c = np.zeros((2, 1, 640), dtype=np.float32)
    last_token = BLANK_ID  # SOS = blank
    tokens = []

    Ttot = encoder_frames.shape[0]
    for t in range(Ttot):
        enc_t = encoder_frames[t:t + 1][None, :, :]  # [1,1,1024]
        n_emit = 0
        while n_emit < MAX_SYMBOLS:
            targets = np.array([[last_token]], dtype=np.int64)
            dout, h_out, c_out = dec.run(None, {
                "targets": targets, "h_in": h, "c_in": c})
            dec_feat = np.transpose(dout, (0, 2, 1))  # [1,640,1] -> [1,1,640]
            jout = joint.run(None, {
                "encoder_output": enc_t, "decoder_output": dec_feat})[0]
            logits = jout[0, 0, 0, :]  # [13088]
            k = int(np.argmax(logits))
            if k == BLANK_ID:
                break
            tokens.append(k)
            last_token = k
            h, c = h_out, c_out
            n_emit += 1

    import json
    with open(os.path.join(MODEL_DIR, "tokenizer.json")) as f:
        tk = json.load(f)
    vocab = [p[0] for p in tk["model"]["vocab"]]
    pieces = [vocab[i] for i in tokens if 0 <= i < len(vocab)]
    text = "".join(pieces).replace("\u2581", " ").strip()

    stem = os.path.splitext(os.path.basename(args.input_audio))[0]
    out_path = os.path.join(args.output_dir, stem + ".txt")
    with open(out_path, "w") as f:
        f.write(text + "\n")
    print(text)


if __name__ == "__main__":
    main()
