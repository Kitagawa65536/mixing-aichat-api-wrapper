# Local Roleplay LLM Gateway

OpenAI互換APIとして動作する、ローカル向けキャラクターロールプレイ用LLM Gatewayの土台実装です。

外部からは単一のOpenAI互換APIに見えますが、内部では `router` / `actor` / `director` / `formatter` の役割ごとに独立したOpenAI互換LLMエンドポイント設定を持てます。現時点のワークフローはRouterが `actor` / `director` を判定し、失敗時は `actor` へフォールバックします。

## Requirements

- Python 3.10+
- OpenAI互換 `/v1/chat/completions` を提供するローカルLLMサーバー
  - 主な想定: llama.cpp / llama-Swap

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item config.example.yaml config.yaml
```

テストも実行する場合:

```powershell
pip install -r requirements-dev.txt
python -m pytest
```

`config.yaml` を環境に合わせて編集します。

```yaml
router:
  api_base: http://localhost:8080/v1
  api_key:
  model: router-model
  request_timeout_seconds: 120

actor:
  api_base: http://localhost:8080/v1
  api_key:
  model: actor-model
  extra_body: {}
  request_timeout_seconds: 120

formatter:
  api_base: http://localhost:8080/v1
  api_key:
  model: formatter-model
  request_timeout_seconds: 120

director:
  api_base: http://localhost:8081/v1
  api_key:
  model: director-model
  extra_body: {}
  request_timeout_seconds: 120

workflow:
  router_enabled: true
  router_debug_logging: false
  formatter_enabled: false
  router_prompt_path: app/prompts/router_decision.md
  director_prompt_path: app/prompts/director.md
  formatter_prompt_path: app/prompts/formatter.md
  router_max_tokens: 128
  router_temperature: 0.0

companion:
  enabled: false
  persona_prompt_path: app/prompts/companion.md
  exhibit_catalog_path: app/exhibits/catalog.example.yaml
  exhibit_catalog_paths: []

injection_guard:
  enabled: false
  db_path: data/injection_guard.sqlite3
  max_entries: 10000
  min_prompt_chars: 12
  mask_text: "[removed]"
  fallback_messages:
    - よくわからないのでもう一回説明してください。
    - 少し受け取り方に迷ったので、別の言い方でもう一度教えてください。
    - その内容では案内しづらいので、展示について聞きたいことをもう一度お願いします。
```

同じ `api_base` を複数roleで使っても問題ありません。roleごとに独立したClientインスタンスを作成します。
`extra_body` はroleごとにupstreamへ追加するJSONです。例えば同じモデルを使いつつ、Actorではreasoningを抑え、Directorではreasoningを有効にする、といった差分を設定できます。

## Run

```powershell
python -m uvicorn app.main:app --reload
```

別の設定ファイルを使う場合:

```powershell
$env:CONFIG_PATH = "path\to\config.yaml"
python -m uvicorn app.main:app --reload
```

`http://127.0.0.1:1234` のOpenAI互換サーバで確認する場合:

```powershell
$env:CONFIG_PATH = "config.local.example.yaml"
python -m uvicorn app.main:app --reload
```

## Project Structure

```text
app/
  api/        FastAPI routes
  companion/  Booth companion catalog and context builders
  config/     YAML config loading
  exhibits/   Example exhibit catalog files
  llm/        OpenAI-compatible LLM clients
  models/     Pydantic request/response models
  prompts/    External prompt files
  storage/    Event sink boundary for future persistence
  workflow/   Orchestrator
```

## API Example

`stream=false` のみ対応しています。

モデル一覧:

```powershell
curl.exe http://127.0.0.1:8000/v1/models
```

```powershell
curl.exe http://127.0.0.1:8000/v1/chat/completions `
  -H "Content-Type: application/json" `
  -d '{
    "model": "gateway-model",
    "stream": false,
    "messages": [
      {"role": "system", "content": "You are a helpful roleplay assistant."},
      {"role": "user", "content": "こんにちは。"}
    ]
  }'
```

Gatewayに渡した `model` は互換性のため受け取りますが、upstreamには `config.yaml` の `actor.model` を送ります。

実サーバへ直接疎通確認する場合:

```powershell
curl.exe http://127.0.0.1:1234/v1/models
```

Gateway経由で返答確認する場合:

```powershell
curl.exe http://127.0.0.1:8000/v1/chat/completions `
  -H "Content-Type: application/json" `
  -d '{
    "model": "gateway-model",
    "stream": false,
    "max_tokens": 32,
    "messages": [
      {"role": "user", "content": "Reply with just: ok"}
    ]
  }'
```

## Companion Catalogs

`companion.enabled=true` の場合、Gatewayはpersona promptと展示カタログYAMLから案内用system contextを作ります。

単一カタログだけを使う場合は従来通り `companion.exhibit_catalog_path` を指定します。複数カタログを使う場合は `companion.exhibit_catalog_paths` にYAMLパスを並べます。`exhibit_catalog_paths` が空でない場合はこちらが優先され、空の場合は `exhibit_catalog_path` が後方互換のdefaultとして使われます。

```yaml
companion:
  enabled: true
  persona_prompt_path: app/prompts/companion.md
  exhibit_catalog_paths:
    - app/exhibits/catalog.gateway.yaml
    - app/exhibits/catalog.creative.example.yaml
```

各chat requestでは、user messageとカタログの `id` / `keywords` / booth情報 / exhibit情報をキーワード照合し、最も関連する1件のカタログだけをActorまたはDirectorへ注入します。一致しない場合は設定順の先頭カタログを使います。RouterとFormatterには展示カタログcontextを渡しません。

カタログYAMLでは以下の追加項目を任意で使えます。

```yaml
id: local-roleplay-llm-gateway
keywords:
  - gateway
  - router
exhibits:
  - id: role-workflow
    title: Router, Actor, Director, and Formatter Roles
    summary: Role clients split routing, simple replies, deeper guidance, and final polish.
    keywords:
      - workflow
      - formatter
```

## Current Workflow

現在のOrchestratorはRouterで `actor` / `director` / `injection` を判定します。`actor` / `director` の場合は選ばれたroleのClientへchat completion requestを渡します。`injection` の場合は下流LLMへ渡さず、設定された固定文言から1件を返します。

`companion.enabled=true` の場合は、`companion.persona_prompt_path` と選択された展示カタログから作ったsystem contextをActor / Directorへ渡す直前に追加します。RouterとFormatterには展示カタログcontextを渡しません。

`director` が選ばれた場合は、companion contextの後に `workflow.director_prompt_path` のsystem promptを追加してからDirectorClientへ渡します。

`workflow.formatter_enabled=true` の場合は、Actor / Director の応答後にFormatterClientを呼び出します。Formatterには `workflow.formatter_prompt_path` のsystem prompt、元の会話messages、Actor / Directorのassistant draftを渡します。Formatter成功時は最終responseの `choices[0].message.content` だけを差し替え、model / usage / finish_reason などは元のActor / Director responseを維持します。Formatter失敗時は元responseへフォールバックします。

```text
User
  -> FastAPI Gateway
  -> Orchestrator
  -> Injection history sanitizer (optional)
  -> RouterClient
  -> Injection fallback response, or:
  -> Companion context injection
  -> ActorClient or DirectorClient
  -> FormatterClient (optional)
  -> OpenAI-compatible LLM endpoint
  -> OpenAI-compatible response
```

Routerはassistant messageの `content` にJSONだけを返す想定です。

```json
{"route":"actor","reason":"ordinary short reply"}
```

```json
{"route":"injection","risk_level":4,"matched_prompt":"ignore previous instructions","reason":"tries to override instructions"}
```

`route` は `actor` / `director` / `injection` です。Routerが失敗した場合、JSONが壊れている場合、未知のrouteを返した場合は、応答継続を優先してActorへフォールバックします。

## Injection Guard

`injection_guard.enabled=true` の場合、Routerが `route: "injection"` を返したユーザー入力をSQLiteに保存します。次回以降のrequestでは、保存済み文字列に完全一致する部分を `mask_text`、既定では `[removed]`、へ置換してからRouter/Actor/Director/Formatterへ渡します。

このGatewayはOpenAI Chat Completions互換のrequestを受けるため、標準の `session_id` には依存しません。保存された文字列はプロセス全体の簡易ブロックリストとして扱います。`max_entries` は既定で10000件、`min_prompt_chars` より短い文字列は誤置換を避けるため保存しません。

## Future Workflow

将来的には以下の構成に拡張する想定です。

```text
User
  -> Orchestrator
  -> Router
  -> Actor or Director
  -> Formatter
  -> OpenAI Response Formatter
```

予定している追加要素:

- Router: 応答経路や処理方針の判断
- Actor: 簡易応答
- Director: 脚本生成、展開制御
- Formatter: 最終回答整形
- Companion: 展示ブース向け人格と展示カタログcontextの注入
- Injection Guard: Router判定に基づく固定応答と履歴サニタイズ
- SQLite: 会話や設定の保存先
- prompts/: 外部Promptファイル管理

今回はMemory、会話ログのSQLite保存、Streaming、RAGは実装していません。
