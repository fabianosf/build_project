# Orquestrador de Fragmentos

Aplicação local: catálogo de fragmentos, **seleção determinística**, pipeline em duas etapas com LLM (**Prompt Forger** → revisão humana → **especialista**).

## Diferença entre as etapas

| Etapa | O que faz | Usa LLM? |
|-------|-----------|----------|
| Sugestão (regras) | Ranqueia fragmentos por intenção/stack/keywords | Não |
| Sugestão (híbrida) | Se o pedido for ambíguo/score baixo, interpreta a intenção e reordena | +1 chamada (opcional) |
| Prompt Forger (`/api/forge/`) | Produz um draft/instrução estruturada | Sim (1ª) ou prévia |
| Especialista (`/api/run/`) | Responde ao draft aprovado | Sim (2ª) ou prévia |

Pedidos claros (ex.: Django + React) tendem a ficar só nas regras. Pedidos vagos (“melhorar meu sistema”) disparam interpretação se `LLM_*` estiver configurado.

A interpretação de intenção usa só metadados do catálogo (`id`, `name`, `function`, `category`, `keywords`) — **sem** corpos `.md`. No forge/run: só o Forger na 1ª chamada e só o especialista escolhido na 2ª. Os demais fragmentos não vão ao modelo.

## Estrutura

```
build_project/
  fragmentos/     # arquivos .md (allowlist no catálogo)
  backend/        # Django + DRF
  frontend/       # React + TypeScript + Vite
  .env.example
  README.md
```

## Instalação (Linux)

```bash
cd build_project/backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp ../.env.example ../.env
python manage.py migrate --run-syncdb
python manage.py runserver 8000
```

Em outro terminal:

```bash
cd build_project/frontend
npm install
npm run dev
```

Abra http://127.0.0.1:5173

## Instalação (Windows)

```bat
cd build_project\backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy ..\.env.example ..\.env
python manage.py migrate --run-syncdb
python manage.py runserver 8000
```

```bat
cd build_project\frontend
npm install
npm run dev
```

## Fragmentos (.md)

Coloque os arquivos em `build_project/fragmentos/` com extensão `.md`.

- Entradas **curadas** ficam em `backend/orchestrator/catalog.py` (allowlist base).
- Arquivos **novos** são detectados automaticamente (GET `/api/fragments/`, health ou botão **Atualizar catálogo** / `POST /api/catalog/resync/`) e gravados em `backend/orchestrator/data/catalog_discovered.json` com categoria **Outros**, badge **Auto** e metadados mínimos do cabeçalho.
- Se o mesmo filename existir no `catalog.py`, a entrada curada **prevalece**.
- Confira ausentes/novos:

```bash
curl -s http://127.0.0.1:8000/api/health/ | python -m json.tool
```

Campos úteis: `missing`, `discovered_new`, `auto_count`. Ajuste `FRAGMENTOS_DIR` ou `CATALOG_DISCOVERED_PATH` no `.env` se necessário. Forjador canônico: `Prompt_Forger_v1.0.md`.

O conteúdo dos `.md` **nunca** é executado como código — só lido como texto/contexto.

## Configurar provedor LLM (opcional)

No `.env` (nunca no frontend):

```
LLM_BASE_URL=https://api.openai.com/v1
LLM_API_KEY=sk-...
LLM_MODEL=gpt-4o-mini
LLM_TIMEOUT=60
LLM_MAX_PROMPT_CHARS=120000
LLM_MAX_FRAGMENT_CHARS=8000
MAX_REQUEST_CHARS=20000
MAX_DRAFT_CHARS=100000
```

### Exemplos de troca de provedor

**OpenAI**

```
LLM_BASE_URL=https://api.openai.com/v1
LLM_API_KEY=sk-...
LLM_MODEL=gpt-4o-mini
```

**Groq** (OpenAI-compatible)

```
LLM_BASE_URL=https://api.groq.com/openai/v1
LLM_API_KEY=gsk_...
LLM_MODEL=openai/gpt-oss-20b
```

Reinicie o `runserver` após mudar o `.env`. O badge **LLM · modelo** no topo da UI vem de `GET /api/health/` (`llm.model`, `llm.base_host`). Sem as três variáveis (`BASE_URL`, `API_KEY`, `MODEL`), a API responde em `mode: "preview"` com `ai_executed: false` (sem cobrança).

Trocar Groq por **ChatGPT/OpenAI** (chave `sk-…` + plano/créditos) **não deixa o código mais enxuto** — a app já usa o mesmo adapter OpenAI-compatible. O que melhora é qualidade, cota e estabilidade do modelo. Com plano pago você pode subir `LLM_MAX_FRAGMENT_CHARS` (ex.: `24000`) se quiser mais contexto do `.md`; o restante (agente, workspace, diffs, confirmação humana) permanece igual.

### Chave paga ajuda? Gasta menos tokens?

- **Ajuda mais na qualidade/estabilidade** (menos 429, modelos consistentes como `gpt-4o-mini`), não porque a app muda.
- **Não gasta menos tokens automaticamente.** Token ≈ tamanho do prompt + da resposta. A chave paga não comprime o pedido. Mesmo texto ≈ mesmos tokens de entrada; modelo mais verboso pode **aumentar** a saída; subir `LLM_MAX_FRAGMENT_CHARS` ou `@pasta/` grande **aumenta** a entrada.
- **Dinheiro ≠ tokens:** custo em US$ = tokens × preço do modelo. `gpt-4o-mini` costuma ser bom custo/benefício; modelos “flagship” cobram mais pelo mesmo volume.

Para gastar menos de verdade (qualquer provedor): pedidos curtos; poucos anexos; `@arquivo`/`@pasta/` pontual; histórico curto (a UI já limita turnos); `LLM_MAX_FRAGMENT_CHARS` razoável (8000–16000); preferir modelo barato para tarefas simples.

### Custo aproximado por turno

O app **não** calcula preço em dinheiro (varia por provedor). No chat, após cada resposta, aparece uma estimativa:

- `~4 caracteres ≈ 1 token` (mistura PT/EN)
- Tokens ≈ prompt + conclusão do turno

Use isso para controlar volume de anexos/histórico. Erros comuns:

| Código | Significado | O que fazer |
|--------|-------------|-------------|
| 429 | Rate limit / créditos | Esperar e **Tentar de novo**; verificar saldo |
| 413 | Prompt grande demais | Reduzir anexos/histórico; compactação/RAG já ajuda |
| 401 | Chave inválida | Conferir `LLM_API_KEY` |
| 404 | Modelo/URL errados | Conferir `LLM_MODEL` / `LLM_BASE_URL` |

CORS padrão: apenas `http://127.0.0.1:5173` e `http://localhost:5173` (`CORS_ALLOW_ALL_ORIGINS=False`). Em produção: `DJANGO_DEBUG=false`, `DJANGO_SECRET_KEY` forte e `CORS_ORIGINS` restrito.

## Testar sem pagar API (FakeLLM)

```bash
cd backend
source .venv/bin/activate   # Windows: .venv\Scripts\activate
python manage.py test orchestrator -v 2
```

Os testes usam `FakeLLMProvider` (sem internet). Frontend:

```bash
cd frontend
npm run build
```

## API

| Método | Rota | Body |
|--------|------|------|
| GET | `/api/health/` | — (`llm_configured`, `llm.model`, `llm.base_host`) |
| GET | `/api/fragments/` | — (faz sync de novos `.md`) |
| POST | `/api/catalog/resync/` | força sync + lista categorias |
| POST | `/api/suggest/` | `{"request":"...", "attachments":[]}` |
| POST | `/api/forge/` | `{"request","fragment_id","attachments"}` |
| POST | `/api/run/` | `{"request","fragment_id","approved_draft"}` |
| POST | `/api/chat/` | chat JSON (`web_search`, `suggest_diff` opcionais) |
| POST | `/api/chat/stream/` | chat SSE (mesmos flags) |
| POST | `/api/sandbox/python/` | `{"code":"..."}` |
| GET | `/api/workspace/` | status do WORKSPACE_ROOT |
| GET | `/api/workspace/file/?path=` | lê arquivo texto |
| GET | `/api/workspace/search/?q=` | busca lexical |
| POST | `/api/workspace/apply-diff/` | `{"patches":[{"path","unified_diff"}]}` |
| POST | `/api/workspace/run/` | `{"recipe":"pytest\|manage_test\|npm_build\|…"}` (allowlist) |

## Busca web, pasta local e workspace

No chat (e no pedido), marque **Buscar na web** para injetar resultados externos no contexto do turno (DuckDuckGo HTML por padrão; opcional `BRAVE_SEARCH_API_KEY` no `.env`). Desligue com `WEB_SEARCH_ENABLED=false`.

**Pasta local** (browser) usa `webkitdirectory`: filtra `node_modules`/`.git`/etc., anexa até 16 arquivos e ativa **Sugerir diffs**.

**Workspace no servidor** (independente do Cursor): no `.env` defina

```
WORKSPACE_ROOT=/caminho/absoluto/do/seu/projeto
```

Reinicie o backend. O badge **Workspace · nome** aparece no topo; se estiver off, um aviso no hero orienta o `WORKSPACE_ROOT`. O toggle **Usar workspace** injeta arquivos relevantes do disco no turno. No chat: digite **`@`** para **arquivo** ou **pasta/** (ex.: `@backend/`); há um painel de árvore com preview só leitura e botão **+@**. Pastas expandem até 8 ficheiros no contexto. No painel de diffs, **Aplicar** grava patches após confirmação (cria `.bak`) e oferece **Verificar agora**. Paths sensíveis (`.env`, chaves) são bloqueados.

**Verificação**: com workspace ativo, a barra **Verificar** no chat roda receitas allowlist (`pytest`, `manage.py test/check`, `compileall`, `npm test/build`) com timeout (`WORKSPACE_RUN_TIMEOUT_SEC`). O log aparece na thread; **Enviar log ao especialista** cola no composer. Sem shell livre.

**Git (somente leitura)**: barra **Git** com `status` / `diff` / `log`; **Sugerir commit** monta uma mensagem no composer (sem `git commit`). Toggle **Incluir Git** injeta resumo no prompt do turno. Sem `commit`/`push`. Exige `.git` em `WORKSPACE_ROOT`.

**Agente (mini tool-loop)**: toggle **Agente** (precisa de workspace). Até `AGENT_MAX_ROUNDS` (padrão 5) rodadas; até 2 tools por rodada (`workspace_search`, `workspace_read`, `workspace_list`, `workspace_run`). Eventos SSE `tool` saem em tempo real durante o loop. Use **Parar** para cancelar. Apply de diff continua só com confirmação humana (por arquivo ou todos).

## Fluxo na UI

1 Pedido (exemplos + anexos/pasta) → 2 Sugestões → 3 Especialista → 4 Prompt Forger → 5 Revisão → 6 Resposta (chat + agente + Git + verificação + painel de diffs).

No topo, **Especialistas (N)** abre o catálogo completo (filtro por nome/id/arquivo). Dá para escolher à mão no passo Pedido e clicar **Preparar com este**, sem depender só da sugestão automática.

Exemplos preenchíveis, chips de stack/seção/arquivo, aviso de até 2 chamadas (sem preço monetário inventado), copiar draft/resposta. Sem histórico sensível em localStorage por padrão.

## Limitações

- Shell/git de escrita não estão disponíveis (só status/diff/log, sugestão de mensagem de commit e receitas de verificação)
- Agente não aplica patches sozinho (máx. rodadas configuráveis; até 2 tools/rodada)
- Apply de diff exige unified diff alinhado ao arquivo atual
- Busca web depende de rede/provedor e pode retornar vazio
- APIs LLM externas só são exercidas se você configurar e chamar manualmente; os testes automatizados **não** cobram provedor real
