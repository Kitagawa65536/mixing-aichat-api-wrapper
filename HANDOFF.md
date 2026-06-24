# Handoff: Local Roleplay LLM Gateway

## 全体の概要

`mixing-aichat-api-wrapper` は FastAPI 製のローカル向け OpenAI 互換 LLM Gateway です。外からは `/v1/models` と `/v1/chat/completions` を持つ単一APIとして見せつつ、内部では Router / Actor / Director / Formatter の役割別 client に分けて上流の OpenAI 互換 LLM へ渡します。

今回の確認対象は `.\local-work\EasyCharacterChatWebUI` の SillyTavern + Kokoro Avatar WebUI です。WebUI からこの Gateway を呼び出し、キャラクターロール付き会話、プロジェクト説明、Kokoro/TTS 連携まで確認しました。

回答材料として実行時に読まれる主なファイルは `app/prompts/companion.md` と `app/exhibits/*.yaml` です。`app/main.py` が `companion.persona_prompt_path` と `companion.effective_exhibit_catalog_paths()` を読み、`app/prompts/loader.py` と `app/companion/context.py` 経由で Actor / Director へ system context として注入します。Router / Formatter には展示カタログ context を渡しません。

## 現在の作業段階

2026-06-21 の実機確認で、通常系は動作確認済みです。

- Irodori TTS: 既存起動中の `http://127.0.0.1:8088` で `/health` と `/v1/models` 成功
- Gemma4 Actor系 llama.cpp server: `http://127.0.0.1:1234/v1` で起動、直接 chat completion 成功
- Qwen3.6 脚本/Director系 llama.cpp server: `http://127.0.0.1:1235/v1` で起動、MTP付き、直接 chat completion 成功、think本文なし
- Gateway: SillyTavern の既定 `:8000` と衝突するため `http://127.0.0.1:8001/v1` で起動
- WebUI: SillyTavern `http://127.0.0.1:8000/`、kokoro dev server `http://127.0.0.1:5173/kokoro/avatar.html`
- SillyTavern 実ユーザー設定は `custom_url=http://127.0.0.1:8001/v1`、`custom_model=gemma-4-e2b` に更新済み
- WebUI上で「mixing-aichat-api-wrapper と llama-swap-config-editor-gui の関係」を送信し、`custom - gemma-4-e2b` の応答表示を確認
- 応答は `llama-swap-config-editor-gui` を設定GUI、`mixing-aichat-api-wrapper` をOpenAI互換API/Gatewayとして区別して説明できた
- 応答には「私たち」「なんですよ」「ふふっ」など、設定した柔らかいキャラクター口調が反映された
- Kokoro Avatar は `Avatar: Ready`、初回 autoplay 制限後に `Enable Voice` と `Replay` を押して `Synthesizing speech...` から `Speaking` まで確認
- 作業終了時、Codexが起動した Gemma4 `:1234`、Qwen `:1235`、Gateway `:8001`、kokoro `:5173`、SillyTavern `:8000` は停止済み

今回使った Gateway 用のローカル設定は `config.webui.local.yaml` です。環境専用なので `.gitignore` に `config.*.local.yaml` を追加しました。ログと pytest 作業領域用に `.codex-run/` も ignore 済みです。

個人環境の絶対パスは `HANDOFF.md` に残さず、リポジトリ直下の ignored folder `local-work/` に置いた junction 経由の相対パスで記録します。

`config.webui.local.yaml` の方針:

- `router_enabled=false`
- `formatter_enabled=false`
- `injection_guard.enabled=false`
- `actor/router/formatter`: Gemma4 server `http://127.0.0.1:1234/v1`
- `director`: Qwen server `http://127.0.0.1:1235/v1`
- `companion.enabled=true`
- `app/exhibits/catalog.gateway.yaml` を先頭 catalog にする

Router / injection guard は今回の重視対象外なので、正常系のWebUI確認を優先して Actor 直行にしています。必要になったら次回 `router_enabled=true` に戻して確認してください。

使用した llama.cpp server 起動オプション:

```powershell
# Gemma4 Actor系 :1234
llama-server.exe `
  --model ".\local-work\llama-cpp-models\unsloth\gemma-4-E2B-it-GGUF\gemma-4-E2B-it-UD-Q3_K_XL.gguf" `
  --alias gemma-4-e2b `
  --host 127.0.0.1 --port 1234 `
  --ctx-size 65536 `
  --cache-type-k q8_0 --cache-type-v q8_0 `
  --no-kv-offload --no-mmproj `
  --parallel 1 --flash-attn on --n-gpu-layers all `
  --reasoning off

# Qwen3.6 脚本/Director系 :1235
llama-server.exe `
  --model ".\local-work\lm-studio-models\unsloth\Qwen3.6-27B-MTP-GGUF\Qwen3.6-27B-UD-IQ3_XXS.gguf" `
  --alias qwen3.6-27b-script `
  --host 127.0.0.1 --port 1235 `
  --ctx-size 65536 `
  --cache-type-k q8_0 --cache-type-v q8_0 `
  --no-kv-offload --no-mmproj `
  --parallel 1 --flash-attn on --n-gpu-layers all `
  --jinja `
  --chat-template-file ".\local-work\chat-templates\chat_template_thinkoff.jinja" `
  --reasoning off `
  --spec-type draft-mtp
```

ログ上の確認:

- Gemma4: `thinking = 0`, `n_ctx = 65536`
- Qwen3.6: `thinking = 0`, `draft-mtp` 追加、`draft acceptance = 1.00000` の直接疎通ログあり
- どちらも `--no-mmproj` で vision model / mmproj は未読込

検証コマンド:

```powershell
.\.venv\Scripts\python.exe -m pytest --basetemp=.codex-run\pytest-tmp -o cache_dir=.codex-run\pytest-cache
```

結果:

```text
50 passed, 1 warning
```

補足: 通常の `pytest` は既定のユーザー別 temp/cache path と既存 `.pytest_cache` の権限で失敗したため、上記のように temp/cache を明示して通しました。

作業開始時点から残る未コミット差分:

- `.gitignore`
- `HANDOFF.md`
- `app/exhibits/catalog.gateway.yaml`
- `app/prompts/companion.md`
- `AGENTS.md`

`EasyCharacterChatWebUI` 側は SillyTavern の実ユーザー設定を書き換えましたが、同 checkout の git status には差分なしでした。

## 次のステップの作業

通常系の目標は動作確認済みです。次にやるなら、以下を優先してください。

1. 必要なら `router_enabled=true` に戻して、Router 経由でも WebUI 正常系が崩れないか確認する。
2. Qwen/Director を実際に使う会話導線を試す。現確認では Qwen server は起動・直接疎通済みだが、WebUI正常系は Actor 直行で確認した。
3. `app/prompts/companion.md` のキャラクター口調は通っているが、より関西寄りにしたい場合は短く強める。
4. `app/exhibits/catalog.gateway.yaml` の説明内容を展示本番向けに詰める。
5. SillyTavern を手動で再確認するときは、Gateway を `:8001`、SillyTavern を `:8000` に分ける。`HANDOFF.md` の古い `:8000/v1` Gateway例を使わない。
6. Kokoro/TTS の初回音声はブラウザ autoplay 制限で止まることがある。画面内の `Enable Voice` を一度押してから `Replay` する。

再開時の最小手順:

```powershell
# 1. TTS確認。既に起動していなければ launch_server.bat を使う
curl.exe http://127.0.0.1:8088/v1/models

# 2. Gemma4 :1234 と Qwen :1235 を上記オプションで起動

# 3. Gateway :8001
$env:CONFIG_PATH = "config.webui.local.yaml"
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8001

# 4. WebUI
Set-Location .\local-work\EasyCharacterChatWebUI
.\Start-KokoroSillyTavern.ps1
```

確認文:

- `こんにちは。少し話そう`
- `mixing-aichat-api-wrapper ってどんなプロジェクト？`
- `llama-swap-config-editor-gui について説明して`
- `mixing-aichat-api-wrapper と llama-swap-config-editor-gui の関係を、展示向けに短く説明して`
