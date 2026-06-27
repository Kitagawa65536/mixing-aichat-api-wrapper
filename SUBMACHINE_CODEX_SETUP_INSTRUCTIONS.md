# サブマシン用 Codex 指示書: start-test-env-lite 相当の構築

この指示書は、サブマシン上で Codex に渡して、`start-test-env-lite.bat` 相当のローカル実行環境を構築させるためのものです。

重要: ここに書かれた現行PCの情報は参考です。サブマシンでは必ず実ファイル、GPU、ポート、上流README、GitHub latest release をその場で確認してください。確認していないことを `HANDOFF.md` や完了報告に「確認済み」と書かないでください。

## ユーザーから一緒に渡す入力

Codex にこの指示書を渡すとき、次の値も渡してください。

```text
STACK_ROOT=<この一式を置く親フォルダ>
GEMMA_GGUF=<Gemma4 Actor/Router 用 gguf の絶対パス>
QWEN_GGUF=<Qwen Director 用 gguf の絶対パス>
QWEN_CHAT_TEMPLATE=<Qwen 用 chat_template_thinkoff.jinja 等の絶対パス。なければ空>
REFERENCE_VOICE=<Irodori に使う参照音声 wav の絶対パス。あとで渡す場合は空>
PUBLIC_LAN_MODE=true または false
```

`PUBLIC_LAN_MODE=true` のときは、Gateway / SillyTavern WebUI / Kokoro dev server を `0.0.0.0` bind にして、別PCから `http://<サブマシンのLAN IPv4>:8000/` で開ける構成を目標にします。Gemma / Qwen / Irodori TTS は原則 `127.0.0.1` bind のままにします。

## 目標フォルダ構成

`STACK_ROOT` の下に、依存先を横並びで置いてください。

```text
<STACK_ROOT>/
  mixing-aichat-api-wrapper/
  EasyCharacterChatWebUI/
  llama.cpp/
    release/
  Irodori-TTS_v3/
    Irodori-TTS/
    Irodori-TTS-Server/
    Irodori-TTS-Lite/
    models/
    voices/
    outputs/
    scripts/
```

`mixing-aichat-api-wrapper/local-work/` は gitignore 対象のローカル接続フォルダにし、必要に応じて上記フォルダへの junction または相対パス参照を置いてください。個人環境の絶対パスは追跡対象ファイルにコミットしないでください。

## clone / upstream の基本方針

- `mixing-aichat-api-wrapper`: `https://github.com/Kitagawa65536/mixing-aichat-api-wrapper.git`
- `EasyCharacterChatWebUI`: `https://github.com/Kitagawa65536/EasyCharacterChatWebUI.git`
- `llama.cpp`: `https://github.com/ggml-org/llama.cpp`
- `Irodori-TTS-Server`: `https://github.com/Aratako/Irodori-TTS-Server`
- `Irodori-TTS-Lite`: `https://github.com/kizuna-intelligence/Irodori-TTS-Lite`

`llama.cpp` は最新版を使ってください。構築時に `https://github.com/ggml-org/llama.cpp/releases/latest` を確認し、Windows + NVIDIA なら `llama-*-bin-win-cuda-12.4-x64.zip` と対応する `cudart-llama-bin-win-cuda-12.4-x64.zip` を優先してください。GPUドライバが十分新しく CUDA 13 系を使う根拠がある場合だけ `cuda-13.3` 系を選んでください。NVIDIA GPU が使えない場合は CPU / Vulkan / HIP など現地ハードに合わせて選び、LLM実用速度の見込みを明記してください。

この指示書作成時点では latest release は `b9826` でしたが、サブマシン構築時には古くなっている可能性があります。必ず latest を再確認してください。

## サブマシン上の Codex への指示本文

以下をそのまま Codex に渡してください。

```text
この Windows マシンに、mixing-aichat-api-wrapper の start-test-env-lite.bat 相当の起動環境を構築してください。

入力:
- STACK_ROOT=<ユーザー指定>
- GEMMA_GGUF=<ユーザー指定>
- QWEN_GGUF=<ユーザー指定>
- QWEN_CHAT_TEMPLATE=<ユーザー指定または空>
- REFERENCE_VOICE=<ユーザー指定または空>
- PUBLIC_LAN_MODE=<true/false>

守ること:
1. まず現地環境を確認してください。`git`, `python`, `py`, `node`, `npm`, `uv`, `ffmpeg`, `nvidia-smi`, PowerShell version, 空き容量、GPU名、VRAM、現在listen中の `8000,8001,5173,8088,1234,1235` を確認し、結果を短く記録してください。
2. 未確認のことを確認済みとして書かないでください。特に WebUI / LLM / TTS / 音声再生 / LAN別PCアクセスは、実際に試したものだけ確認済みにしてください。
3. `STACK_ROOT` の下に `mixing-aichat-api-wrapper`, `EasyCharacterChatWebUI`, `llama.cpp`, `Irodori-TTS_v3` を作ってください。既に存在する場合は、上書きや削除の前に状態を確認してください。
4. `llama.cpp` は GitHub の latest release を確認して最新版を入れてください。Windows + NVIDIA CUDA なら、まず `llama-*-bin-win-cuda-12.4-x64.zip` と `cudart-llama-bin-win-cuda-12.4-x64.zip` を `llama.cpp\release\` に展開する方針で進めてください。展開後、`llama-server.exe --version` または `.\llama-server.exe --help` が動くことを確認してください。
5. `GEMMA_GGUF` と `QWEN_GGUF` は既にダウンロード済みなので再ダウンロードしないでください。ファイル存在、サイズ、拡張子、読み取り可能性だけ確認してください。
6. Qwen 用 chat template は、ユーザーが `QWEN_CHAT_TEMPLATE` を渡していればそれを使ってください。空の場合は、同等の `think off` 用テンプレートが既存ファイルやモデル配布元にあるか確認し、なければ Qwen の起動から `--chat-template-file` を外すか、根拠を示してテンプレートを作成してください。推測で既存確認済みにしないでください。
7. `mixing-aichat-api-wrapper` は venv を作り、`requirements.txt` と必要なら `requirements-dev.txt` を入れてください。`config.webui.local.yaml` を作り、Router/Actor/Formatter は Gemma `http://127.0.0.1:1234/v1`、Director は Qwen `http://127.0.0.1:1235/v1` に向けてください。Formatter は現行に合わせて `formatter_enabled=false` でよいです。
8. `EasyCharacterChatWebUI` は README と実ファイルを確認してセットアップしてください。SillyTavern と Kokoro dev server が必要です。既存の `Start-KokoroSillyTavern.ps1` がある場合は内容を読んで使ってください。
9. Irodori は `Irodori-TTS_v3` というローカル作業フォルダを作り、その中に `Irodori-TTS-Server` をベースとして構築してください。ハードウェア的に相性が悪くなさそうなら `Irodori-TTS-Lite` も入れて、Lite OpenAI互換サーバを `scripts\launch_lite_server.bat --host 127.0.0.1 --port 8088` で起動できるようにしてください。
10. Lite を使う判断基準は、少なくとも `nvidia-smi` が通る NVIDIA CUDA GPU、十分なVRAM、PyTorch CUDA が有効、Lite の依存が現地OSで解決できることです。Windows native で Triton が難しい場合は、既存PCと同じような pure-torch / compatibility fallback が作れるかを確認してください。難しければ base server を使い、Lite は未完了として理由を残してください。
11. `REFERENCE_VOICE` が渡されていれば、`Irodori-TTS_v3\voices\generated\` にコピーまたは junction してください。APIの voice id は通常、拡張子なしファイル名で使えるようにしてください。未指定なら `voices\generated\` だけ作り、参照音声待ちと明記してください。
12. `mixing-aichat-api-wrapper\local-work\start-test-env.ps1` と `start-test-env-lite.bat` 相当を作ってください。gitignore 対象の `local-work` 配下で構いません。現行PCの挙動に合わせ、次を満たしてください。
    - `-CheckOnly` で必要パスだけ検査してサーバを起動しない。
    - `-TtsMode lite` で `Irodori-TTS_v3\scripts\launch_lite_server.bat --host 127.0.0.1 --port 8088` を起動する。
    - base TTS の場合は `launch_server.bat --host 127.0.0.1 --port 8088` を起動する。
    - Gemma を `127.0.0.1:1234/v1`、Qwen を `127.0.0.1:1235/v1` で起動する。
    - Gateway を `:8001`、SillyTavern を `:8000`、Kokoro を `:5173` で起動する。
    - `PUBLIC_LAN_MODE=true` の場合、Gateway / SillyTavern / Kokoro は `0.0.0.0` bind にする。Gemma / Qwen / TTS は `127.0.0.1` bind のままにする。
    - 既に該当ポートが起動している場合はスキップするが、LAN公開モードで既存プロセスが localhost bind の可能性があるときは警告する。
    - 起動完了後に `Gateway`, `SillyTavern`, `Kokoro`, `TTS`, `WebUI LAN` のURLを表示する。
13. `start-test-env-lite.bat` はダブルクリック用の薄い wrapper にしてください。例: `powershell.exe -NoProfile -ExecutionPolicy Bypass -File ".\start-test-env.ps1" -TtsMode lite -GatewayHost 0.0.0.0 -WebUiHost 0.0.0.0 -KokoroHost 0.0.0.0 -OpenBrowser`
14. SillyTavern を LAN公開する場合は、現行PCと同じく `--listen --listenAddressIPv4 0.0.0.0 --no-whitelist --basicAuthMode` を使う方針で確認してください。basic auth のユーザー/パスワードは SillyTavern の設定ファイルで必ず確認し、既定値のまま公開しないよう警告してください。信頼できるLAN/VPN内だけで使う前提です。
15. Kokoro avatar iframe が別PCから開いたときに `127.0.0.1:5173` を指して壊れる場合は、EasyCharacterChatWebUI 側の現在の実装を確認し、必要なら SillyTavern を開いた host に avatar URL host を差し替える runtime 補正を入れてください。変更したら `node --check` などで確認してください。
16. Windows Firewall は管理者権限が必要です。`PUBLIC_LAN_MODE=true` で別PCアクセスする場合は、TCP `8000,5173,8001` の許可が必要か確認し、Codexが権限不足なら「管理者PowerShellで実行するコマンド」を提示してください。
17. 受け入れ確認は段階的に行ってください。
    - `.\local-work\start-test-env.ps1 -CheckOnly -TtsMode lite -GatewayHost 0.0.0.0 -WebUiHost 0.0.0.0 -KokoroHost 0.0.0.0`
    - `http://127.0.0.1:1234/v1/models`
    - `http://127.0.0.1:1235/v1/models`
    - `http://127.0.0.1:8088/health`
    - `http://127.0.0.1:8088/v1/models`
    - `http://127.0.0.1:8001/v1/models`
    - `http://127.0.0.1:5173/kokoro/avatar.html`
    - `http://127.0.0.1:8000/`
    - Gateway の `POST /v1/chat/completions`
    - TTS の `POST /v1/audio/speech`
    - WebUI から Gateway 応答表示
    - Kokoro / TTS 音声再生
    - `PUBLIC_LAN_MODE=true` なら別PCから `http://<LAN IPv4>:8000/`
18. 作業後、`mixing-aichat-api-wrapper\HANDOFF.md` を更新してください。構成は `全体の概要`、`現在の作業段階`、`次のステップの作業` を維持し、確認済み/未確認、実際に使ったパス、ポート、起動オプション、未解決事項を短く残してください。引き継ぎ書は `HANDOFF.md` 1枚だけにしてください。
```

## start-test-env-lite 相当の起動仕様

現行PCでの `start-test-env-lite.bat` は、次の PowerShell 呼び出しの薄い wrapper です。

```bat
@echo off
setlocal
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File ".\start-test-env.ps1" -TtsMode lite -GatewayHost 0.0.0.0 -WebUiHost 0.0.0.0 -KokoroHost 0.0.0.0 -OpenBrowser
pause
```

サブマシン側でも、bat 自体はこの程度に薄くして、実際の分岐、パス検査、起動、待機、URL表示は `start-test-env.ps1` に寄せてください。

ポートと役割:

```text
1234  Gemma Actor/Router/Formatter llama.cpp server, localhost only
1235  Qwen Director llama.cpp server, localhost only
8088  Irodori TTS OpenAI-compatible server, localhost only
8001  mixing-aichat-api-wrapper Gateway
8000  SillyTavern WebUI
5173  Kokoro avatar Vite dev server
```

LLM起動オプションの現行ベースライン:

```powershell
# Gemma :1234
llama-server.exe `
  --model "<GEMMA_GGUF>" `
  --alias gemma-4-e2b `
  --host 127.0.0.1 --port 1234 `
  --ctx-size 65536 `
  --cache-type-k q8_0 --cache-type-v q8_0 `
  --no-kv-offload --no-mmproj `
  --parallel 1 --flash-attn on --n-gpu-layers all `
  --reasoning off

# Qwen :1235
llama-server.exe `
  --model "<QWEN_GGUF>" `
  --alias qwen3.6-27b-script `
  --host 127.0.0.1 --port 1235 `
  --ctx-size 65536 `
  --cache-type-k q8_0 --cache-type-v q8_0 `
  --no-kv-offload --no-mmproj `
  --parallel 1 --flash-attn on --n-gpu-layers all `
  --jinja `
  --chat-template-file "<QWEN_CHAT_TEMPLATE>" `
  --reasoning off `
  --spec-type draft-mtp
```

サブマシンのVRAMが足りない場合は、`--ctx-size`、KV cache、`--n-gpu-layers`、MTP、Qwen側モデルを現地で調整してください。調整した場合は `HANDOFF.md` に実際の起動オプションを残してください。

## Irodori TTS の構築方針

`Irodori-TTS_v3` は、単一のローカル作業フォルダに base server と Lite server をまとめる方針にします。

```text
Irodori-TTS_v3/
  Irodori-TTS/
  Irodori-TTS-Server/
  Irodori-TTS-Lite/
  models/
    shared/
  voices/
    generated/
    references/
  outputs/
  scripts/
```

base server:

- 上流 `Aratako/Irodori-TTS-Server` の README を読んで構築する。
- `scripts\launch_server.bat --host 127.0.0.1 --port 8088` で OpenAI互換 API を起動できる状態にする。
- CORS は Kokoro 用に `IRODORI_CORS_ORIGINS=["http://127.0.0.1:5173","http://localhost:5173"]` を設定する。

Lite server:

- NVIDIA CUDA + PyTorch CUDA が使えるなら `kizuna-intelligence/Irodori-TTS-Lite` を導入する。
- `scripts\launch_lite_server.bat --host 127.0.0.1 --port 8088` で OpenAI互換 API を起動できる状態にする。
- Windows native で upstream の Triton 系依存がそのまま通らない場合は、pure-torch fallback で運用可能かを検証する。無理に成功扱いにしない。
- `GET /health`, `GET /v1/models`, `GET /v1/audio/voices`, `POST /v1/audio/speech` まで確認する。

参照音声:

- ユーザーが渡す WAV を `Irodori-TTS_v3\voices\generated\<voice_id>.wav` に置く。
- `/v1/audio/voices` で voice id が見えることを確認する。
- 音声が出ない場合は、まず CORS / proxy / browser autoplay / `Enable Voice` / `Replay` / voice id / output device の順に確認する。

## 完了条件

最低限の完了条件:

- `mixing-aichat-api-wrapper\local-work\start-test-env-lite.bat` が存在する。
- `.\local-work\start-test-env.ps1 -CheckOnly -TtsMode lite -GatewayHost 0.0.0.0 -WebUiHost 0.0.0.0 -KokoroHost 0.0.0.0` が通る。Lite未採用の場合は、base TTS で通したコマンドと Lite未採用理由を残す。
- `llama-server.exe` が latest release 由来で、Gemma `:1234` と Qwen `:1235` の `/v1/models` が返る。
- Gateway `:8001/v1/models` が返る。
- TTS `:8088/health` と `/v1/models` が返る。
- WebUI `:8000` と Kokoro `:5173/kokoro/avatar.html` がローカルで開く。
- WebUI から Gateway 経由の通常会話を1回確認する。
- TTS音声再生を1回確認する。ブラウザ autoplay 制限で止まった場合は `Enable Voice` / `Replay` 後の結果を書く。
- `PUBLIC_LAN_MODE=true` なら、別PCから `http://<サブマシンLAN IPv4>:8000/` を開けたか、開けない場合は firewall / network profile / VPN route のどこまで確認したかを書く。
- `HANDOFF.md` に、確認済み、未確認、実際の起動コマンド、ポート、次の作業が残っている。

## 参考URL

- llama.cpp releases: https://github.com/ggml-org/llama.cpp/releases/latest
- Irodori-TTS-Server: https://github.com/Aratako/Irodori-TTS-Server
- Irodori-TTS-Lite: https://github.com/kizuna-intelligence/Irodori-TTS-Lite
