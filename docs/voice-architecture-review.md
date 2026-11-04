# Voice architecture review

Researched on 2026-11-04 from official provider documentation and maintained SDKs; links below. "Inference" marks my
judgment, as opposed to documented fact.

## Requirement that decides the design

Voice must be another interface to **the same agent**: same conversation and memory, same tools, same deterministic
analytics, and the same claim validation. The validator runs on the complete answer before anything is shown.
Token-by-token streaming of the final answer is therefore impossible by design, and so is a second model "re-voicing" it.

## Options studied

| | (a) Real-time speech-to-speech | (b) Chained: VAD → STT → our agent → TTS | (c) Browser-only Web Speech |
|---|---|---|---|
| Examples | OpenAI Realtime (WebRTC, ephemeral client secrets, `server_vad`/`semantic_vad`, auto-truncation on barge-in) [1][2][3]; Gemini Live (ephemeral tokens, automatic VAD, `interrupted` events, client-side tool responses) [4][5][6] | Pipecat (Silero VAD + Smart-Turn) [7][8], LiveKit Agents (turn detector, interruption filtering, custom `llm_node`) [9][10]; or a minimal browser-VAD + server-STT pipeline | `SpeechRecognition` + `speechSynthesis` [13] |
| Turn-taking and barge-in | Best in class, built in | Good: Silero VAD in the browser [11][12] plus a barge-in rule | Weaker: recognition stops on silence, echo risk |
| Our agent stays authoritative? | **No.** The voice model becomes a second "brain". Even with a single `ask_agent` tool it re-speaks our validated text, and verbatim output is not guaranteed [3] | **Yes.** The validated text is exactly what is spoken | Yes |
| Keys | Ephemeral client tokens minted by the server | Stay on the server | None |
| Cost | Realtime audio about $32/$64 per 1M tokens (mini $10/$20) [14]; Gemini Live free tier exists [15] | Groq Whisper turbo $0.04 per audio hour [16]; browser TTS free | Free |
| Infrastructure | WebRTC session, sideband channel (an open OpenAI bug with ephemeral keys [17]) | One HTTP endpoint | None |

**Recommendation: (b), chained.** (Inference.) It is the only option where the words you hear are exactly the answer
the validator approved, and where tools, memory and keys stay on our server. Speech-to-speech's main advantage, speaking
while the model thinks, is unavailable to us anyway, because nothing may be said before validation. Pipecat and
LiveKit are excellent, but they add a media server and WebRTC transport that this single-page app does not need.

## What is implemented (`src/airport_agent/voice.py`, `web/app.js`, `/api/voice/*`)

```
mic ─► Silero VAD (browser, vad-web 0.0.31) ─► WAV ─► POST /api/voice/transcribe ─► Groq whisper-large-v3-turbo
   └► (no server STT configured) Web Speech recognition, continuous, partial transcripts ─────────┐
                                                                                                    ▼
             same /api/conversations/{id}/messages (client_turn_id)  ─►  same Agent, tools, validation
                                                                                                    ▼
   speechSynthesis, sentence by sentence  ◄──  structured.spoken (deterministic, from the validated answer)
```

* **Turn detection:**
  * Server-STT mode: Silero VAD v5 (`redemptionMs` 600, `minSpeechMs` 300) decides when you have finished, and clips under 0.4 s are dropped.
  * Browser mode: continuous recognition with interim results.
* **Transcript:** partial (italic) and final transcripts appear in the voice bar, and the final question becomes a normal turn in the conversation.
* **Spoken answer:** the server builds a short spoken version from the rendered, validated answer: headline, judgment, the leading comparisons or rankings, and a pointer to the on-screen evidence. No model rewrites it. The browser speaks it sentence by sentence, so the first audio starts at once and stops cleanly when interrupted.
* **Interruption (barge-in):** speech detected while speaking stops playback immediately. That is VAD speech-start in server-STT mode, or two or more words of new interim speech in browser mode. Esc and "Stop audio" also stop it.
* **Echo rejection:** an utterance whose words are mostly in the text currently being spoken is treated as echo and ignored. Headphones are still recommended.
* **States:** off, connecting, listening, processing (with "next question queued"), speaking, disconnected, error, each shown in the bar.
* **Recovery:** recognition restarts after it ends, with exponential backoff (up to 8 s) after errors. Server STT retries a failed upload once, with the same utterance id, so the server never transcribes it twice.
* **No duplicate turns:** utterance ids are de-duplicated on the client and the server, and `client_turn_id` is de-duplicated by the message endpoint, so a reconnect cannot run a question twice.
* **Text always works:** voice errors never block typing, and voice turns are ordinary turns, so the evidence inspector and charts work exactly as in text chat.
* **Security:** the Groq key lives in the macOS Keychain and is used only by the server. The browser never receives a provider key, so no ephemeral token is needed.

## Language and voices
* Groq Whisper is multilingual, but the app sets `language=en`.
* Groq's text-to-speech (`canopylabs/orpheus-v1-english`) is a **preview, English-only** model: 200 characters per request, WAV only, 100 requests/day on the free tier, and console terms must be accepted first [18][19]. Groq has **no Hebrew text-to-speech**.
* We therefore use browser `speechSynthesis` with an en-US voice (Samantha or Ava on macOS, Google US English in Chrome). The demo language is English; Hebrew voice output is **not** offered.

## Provider setup and cost
* **Default (`AIRPORT_VOICE_STT=browser`):** no key and no server call. Chrome and Safari send audio to their own recognition service [13]. Firefox is not supported.
* **Recommended for the interview:** `AIRPORT_VOICE_STT=groq`. Run `./scripts/configure-groq-key.sh` (the same key as the Groq LLM), set `AIRPORT_VOICE_STT=groq` in `.env`, and restart.
  * Model `whisper-large-v3-turbo`: $0.04 per audio hour, with a 10 s minimum billed per request.
  * Free tier: 20 requests/minute, 2,000/day [16].
  * The app enforces its own daily cap, `AIRPORT_VOICE_MAX_REQUESTS` (default 150), logged in `data/app/voice_usage.jsonl`.
* **No voice API call has been made yet.** Live testing needs your Groq key and your go-ahead.

## Tested and not tested
* **Tested offline (fake transcriber, `tests/test_api.py`):**
  * transcribe endpoint, utterance de-duplication, turn de-duplication;
  * spoken text built from the validated answer;
  * a contextual follow-up through voice;
  * the Groq Whisper multipart request and daily budget.
* **Tested in the browser through the voice code's test hooks** (no microphone in the test browser):
  * spoken question → processing → answer → speaking;
  * duplicate utterance ignored;
  * contextual follow-up ("What about its seat factor?" → ANC);
  * barge-in stops speech and returns to listening;
  * echo rejection;
  * a simulated disconnect recovers;
  * text chat works after voice ends.
* **Not verified:** real microphone capture, real speech recognition, audible playback quality, and Groq Whisper latency. These need a real browser with a microphone (and your Groq key for server STT).

## Sources
[1] https://developers.openai.com/api/reference/resources/realtime/subresources/client_secrets/methods/create ·
[2] https://developers.openai.com/api/docs/guides/realtime-vad ·
[3] https://developers.openai.com/api/docs/guides/realtime-conversations ·
[4] https://aistudio.google.com/docs/live-api/ephemeral-tokens ·
[5] https://aistudio.google.com/docs/live-api/capabilities ·
[6] https://aistudio.google.com/docs/live-api/tools ·
[7] https://docs.pipecat.ai/guides/learn/pipeline ·
[8] https://docs.pipecat.ai/server/utilities/turn-detection/smart-turn-overview ·
[9] https://docs.livekit.io/agents/build/turns/ ·
[10] https://docs.livekit.io/agents/build/nodes/ ·
[11] https://docs.vad.ricky0123.com/user-guide/browser/ ·
[12] https://docs.vad.ricky0123.com/user-guide/algorithm/ ·
[13] https://developer.mozilla.org/en-US/docs/Web/API/SpeechRecognition ·
[14] https://developers.openai.com/api/docs/pricing ·
[15] https://aistudio.google.com/docs/pricing ·
[16] https://console.groq.com/docs/speech-to-text and https://console.groq.com/docs/rate-limits ·
[17] https://community.openai.com/t/ephemeral-keys-trigger-realtime-sideband-404-errors/1396002 ·
[18] https://console.groq.com/docs/text-to-speech ·
[19] https://github.com/langflow-ai/langflow/issues/11120 (terms-acceptance error, third-party report)
