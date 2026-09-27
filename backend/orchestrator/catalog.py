"""Versioned allowlist catalog of known fragment files.

Do not invent filenames. Every entry must match a known file under fragmentos/.
Content of .md files is never executed as code.
"""

from __future__ import annotations

from typing import Any, TypedDict

CATALOG_VERSION = "1.1.0"

CATEGORY_CRIACAO = "Criação e desenvolvimento"
CATEGORY_DADOS = "Dados, infraestrutura e design"
CATEGORY_MARKETING = "Marketing e conteúdo"
CATEGORY_ORQUESTRACAO = "Orquestração e conhecimento"
CATEGORY_OUTROS = "Outros"

CATEGORY_ORDER = [
    CATEGORY_CRIACAO,
    CATEGORY_DADOS,
    CATEGORY_MARKETING,
    CATEGORY_ORQUESTRACAO,
    CATEGORY_OUTROS,
]

# Exact on-disk name (NFD Ô): Agente O + U+0302 + mega- Extrator Blueprint.md
_AGENTE_OMEGA_FILENAME = "Agente O\u0302mega- Extrator Blueprint.md"


class Prerequisite(TypedDict):
    code: str
    message: str


class FragmentEntry(TypedDict):
    id: str
    filename: str
    name: str
    function: str
    category: str
    keywords: list[str]
    intents: list[str]
    stacks: list[str]
    prerequisites: list[Prerequisite]
    is_prompt_forger: bool
    selectable_as_specialist: bool


FRAGMENTS: list[FragmentEntry] = [
    {
        "id": "prompt-forger",
        "filename": "Prompt_Forger_v1.0.md",
        "name": "PROMPT FORGER v1.0",
        "function": (
            "Transforma linguagem natural em prompts executáveis; "
            "analisa stacks e gera instruções sem ambiguidade."
        ),
        "category": CATEGORY_CRIACAO,
        "keywords": [
            "forjar prompt",
            "criar prompt",
            "engenhar prompt",
            "prompt engineering",
            "forger",
        ],
        "intents": ["criar_prompt"],
        "stacks": [],
        "prerequisites": [],
        "is_prompt_forger": True,
        "selectable_as_specialist": True,
    },
    {
        "id": "react-native-migrator",
        "filename": "ReactNativeMigrator-yotaia-v1.md",
        "name": "ReactNativeMigrator",
        "function": (
            "Converte aplicações ReactJS (web) para React Native "
            "preservando lógica e reuso."
        ),
        "category": CATEGORY_CRIACAO,
        "keywords": [
            "react native",
            "migração",
            "migrar",
            "mobile",
            "expo",
            "reactjs",
        ],
        "intents": ["frontend", "mobile"],
        "stacks": ["react", "react-native", "expo"],
        "prerequisites": [],
        "is_prompt_forger": False,
        "selectable_as_specialist": True,
    },
    {
        "id": "refactoring-legacy",
        "filename": "Refactoring-Legacy.md",
        "name": "Refactoring Legacy Master v1.0",
        "function": (
            "Especialista em refatorar código legado (Java, C, Python, bancos) "
            "para código moderno preservando semântica."
        ),
        "category": CATEGORY_CRIACAO,
        "keywords": [
            "refatoração",
            "legado",
            "legacy",
            "modernizar",
            "dívida técnica",
        ],
        "intents": ["backend", "arquitetura"],
        "stacks": ["java", "python", "c"],
        "prerequisites": [],
        "is_prompt_forger": False,
        "selectable_as_specialist": True,
    },
    {
        "id": "yota-analista-requisitos",
        "filename": "yota-analista-requisitos.md",
        "name": "Analista de Requisitos Sênior + Arquiteto de Soluções v1.0",
        "function": (
            "Transforma ideias e demandas em especificações técnicas "
            "precisas e executáveis."
        ),
        "category": CATEGORY_CRIACAO,
        "keywords": [
            "requisitos",
            "especificação",
            "user stories",
            "análise",
            "soluções",
        ],
        "intents": ["projeto_novo", "arquitetura", "requisitos"],
        "stacks": [],
        "prerequisites": [],
        "is_prompt_forger": False,
        "selectable_as_specialist": True,
    },
    {
        "id": "yota-arquiteto-software",
        "filename": "yota-arquiteto-software.md",
        "name": "SoftwareArchitectAgent",
        "function": (
            "Converte modelo de domínio em documento de arquitetura técnica; "
            "não gera código de implementação."
        ),
        "category": CATEGORY_CRIACAO,
        "keywords": [
            "arquitetura de software",
            "software architect",
            "documento de arquitetura",
            "staff engineer",
        ],
        "intents": ["arquitetura"],
        "stacks": [],
        "prerequisites": [
            {
                "code": "modelo_dominio_validado",
                "message": (
                    "Este especialista solicita um Modelo de Domínio validado "
                    "como entrada prévia."
                ),
            }
        ],
        "is_prompt_forger": False,
        "selectable_as_specialist": True,
    },
    {
        "id": "orus-fabianosf",
        "filename": "ORUS_FABIANOSF_AGENTE.md",
        "name": "OMEGA FABIANOSF - SUPREME COGNITIVE ENGINEER",
        "function": (
            "Engenheiro cognitivo enterprise (Python/ML/Node/Django/Flask/"
            "frontend/sistemas)."
        ),
        "category": CATEGORY_CRIACAO,
        "keywords": [
            "engenheiro",
            "fullstack",
            "fabianosf",
            "orus",
        ],
        "intents": ["backend", "frontend", "projeto_novo"],
        "stacks": ["python", "django", "flask", "node", "react"],
        "prerequisites": [],
        "is_prompt_forger": False,
        "selectable_as_specialist": True,
    },
    {
        "id": "omega-cartographer",
        "filename": "OMEGA CARTOGRAPHER.md",
        "name": "OMEGA CARTOGRAPHER",
        "function": (
            "Mapeia codebases: endpoints, módulos, padrões e documentação "
            "arquitetural."
        ),
        "category": CATEGORY_CRIACAO,
        "keywords": [
            "mapear",
            "codebase",
            "cartógrafo",
            "cartographer",
            "documentação",
            "endpoints",
        ],
        "intents": ["arquitetura"],
        "stacks": [],
        "prerequisites": [],
        "is_prompt_forger": False,
        "selectable_as_specialist": True,
    },
    {
        "id": "fragmento-typescript",
        "filename": "FRAGMENTO 1 - TYPESCRIPT.md",
        "name": "Fragmento 1 – Fullstack TypeScript React/Node/Tailwind",
        "function": (
            "Matriz cognitiva fullstack TypeScript (React/Node/Tailwind); "
            "não é tutorial de código."
        ),
        "category": CATEGORY_CRIACAO,
        "keywords": [
            "typescript",
            "tailwind",
            "fullstack",
        ],
        "intents": ["frontend", "backend"],
        "stacks": ["typescript", "react", "node", "tailwind"],
        "prerequisites": [],
        "is_prompt_forger": False,
        "selectable_as_specialist": True,
    },
    {
        "id": "fragmento-java-cpp",
        "filename": "FRAGMENTO-JAVA-CPP.md",
        "name": "Fragmento 2 – Java & C++ Systems Architect",
        "function": "Expertise Java/C++ enterprise e sistemas de alto desempenho.",
        "category": CATEGORY_CRIACAO,
        "keywords": ["c++", "cpp", "systems", "alto desempenho"],
        "intents": ["backend", "arquitetura"],
        "stacks": ["java", "cpp"],
        "prerequisites": [],
        "is_prompt_forger": False,
        "selectable_as_specialist": True,
    },
    {
        "id": "pythia",
        "filename": "PYTHIA-PROTOCOL-OMEGA-SUPREME.md",
        "name": "Protocolo PYTHIA - Omega Python Master Supreme v2.0",
        "function": (
            "Python enterprise, CIG-2.0, backend cognitivo/ML e integração "
            "multilíngue."
        ),
        "category": CATEGORY_CRIACAO,
        "keywords": ["pythia", "enterprise"],
        "intents": ["backend"],
        "stacks": ["python"],
        "prerequisites": [],
        "is_prompt_forger": False,
        "selectable_as_specialist": True,
    },
    {
        "id": "iris",
        "filename": "IRIS_Skill_Extraction.md",
        "name": "IRIS — Design Systems Architect",
        "function": (
            "Arquitetura de design systems: tokens, componentes, acessibilidade "
            "e HCD."
        ),
        "category": CATEGORY_DADOS,
        "keywords": [
            "design system",
            "tokens",
            "componentes",
            "acessibilidade",
            "iris",
        ],
        "intents": ["frontend", "design"],
        "stacks": [],
        "prerequisites": [],
        "is_prompt_forger": False,
        "selectable_as_specialist": True,
    },
    {
        "id": "atlas",
        "filename": "ATLAS_Skill_Extraction.md",
        "name": "ATLAS — Cloud Resilience Architect",
        "function": (
            "Infraestrutura cloud, resiliência e observabilidade "
            "(Terraform, Kubernetes, CI/CD)."
        ),
        "category": CATEGORY_DADOS,
        "keywords": [
            "cloud",
            "kubernetes",
            "terraform",
            "infra",
            "resiliência",
            "atlas",
            "deploy",
            "docker",
            "ci/cd",
        ],
        "intents": ["infra", "deploy"],
        "stacks": ["docker", "kubernetes", "terraform"],
        "prerequisites": [],
        "is_prompt_forger": False,
        "selectable_as_specialist": True,
    },
    {
        "id": "athena",
        "filename": "ATHENA_Skill_Extraction.md",
        "name": "ATHENA — Data & Applied AI Architect",
        "function": (
            "Pipelines de dados para IA: ETL, warehouse, ML e RAG."
        ),
        "category": CATEGORY_DADOS,
        "keywords": ["dados", "etl", "warehouse", "rag", "athena"],
        "intents": ["dados", "rag"],
        "stacks": [],
        "prerequisites": [],
        "is_prompt_forger": False,
        "selectable_as_specialist": True,
    },
    {
        "id": "alphaia",
        "filename": "AlphaIA - Especialista em IA.md",
        "name": "AlphaIA — Data Science & AI",
        "function": (
            "Data science, AI/ML, MLOps e engenharia de dados."
        ),
        "category": CATEGORY_DADOS,
        "keywords": [
            "inteligência artificial",
            "machine learning",
            "data science",
            "mlops",
            "alphaia",
        ],
        "intents": ["dados", "rag"],
        "stacks": ["python"],
        "prerequisites": [],
        "is_prompt_forger": False,
        "selectable_as_specialist": True,
    },
    {
        "id": "fragmento-security",
        "filename": "FRAGMENTO-SECURITY.md",
        "name": "Fragmento 3 – Secure & High-Performance Systems Architect",
        "function": (
            "Segurança e performance integradas: threat modeling, crypto e "
            "design resiliente."
        ),
        "category": CATEGORY_DADOS,
        "keywords": [
            "segurança",
            "security",
            "performance",
            "threat modeling",
            "crypto",
        ],
        "intents": ["arquitetura", "backend"],
        "stacks": [],
        "prerequisites": [],
        "is_prompt_forger": False,
        "selectable_as_specialist": True,
    },
    {
        "id": "prometheus-backend",
        "filename": "PROMETHEUS-FRAG-BACKEND-SYSTEMS.md",
        "name": "Fragmento 5 – Scalable Backend Architecture & Systems Design",
        "function": (
            "Backends distribuídos, escala, bancos, filas e IaC "
            "(matriz cognitiva)."
        ),
        "category": CATEGORY_DADOS,
        "keywords": [
            "escala",
            "distribuído",
            "filas",
            "iac",
            "sistemas",
        ],
        "intents": ["backend", "arquitetura", "infra"],
        "stacks": ["django", "python"],
        "prerequisites": [],
        "is_prompt_forger": False,
        "selectable_as_specialist": True,
    },
    {
        "id": "skill-posts-visuais",
        "filename": "skill-posts-visuais.md",
        "name": "ORUS — Knowledge Skill de Posts Visuais",
        "function": (
            "Gera posts, capas e slides no padrão ORUS (estilos e categorias "
            "visuais)."
        ),
        "category": CATEGORY_MARKETING,
        "keywords": [
            "posts",
            "instagram",
            "visual",
            "social media",
            "capa",
            "slides",
        ],
        "intents": ["marketing"],
        "stacks": [],
        "prerequisites": [],
        "is_prompt_forger": False,
        "selectable_as_specialist": True,
    },
    {
        "id": "aurora-prime",
        "filename": "AURORA-PRIME-v2.0-DESIGNER-SOCIALMEDIA-SUPREME.md",
        "name": "AURORA PRIME v2.0 — Designer Gráfico & Social Media",
        "function": (
            "Design gráfico e social media; prompts para IAs generativas e "
            "campanhas visuais."
        ),
        "category": CATEGORY_MARKETING,
        "keywords": [
            "design gráfico",
            "social media",
            "campanha",
            "aurora",
            "visual",
        ],
        "intents": ["marketing", "design"],
        "stacks": [],
        "prerequisites": [],
        "is_prompt_forger": False,
        "selectable_as_specialist": True,
    },
    {
        "id": "traffic-master",
        "filename": "traffic-master-omega-35blocos.md",
        "name": "TRAFFIC MASTER OMEGA",
        "function": (
            "Tráfego pago, conversão e assinaturas SaaS (ads, funil, ROAS/CPA)."
        ),
        "category": CATEGORY_MARKETING,
        "keywords": [
            "tráfego",
            "ads",
            "facebook ads",
            "google ads",
            "funil",
            "roas",
            "conversão",
        ],
        "intents": ["marketing", "prospeccao"],
        "stacks": [],
        "prerequisites": [],
        "is_prompt_forger": False,
        "selectable_as_specialist": True,
    },
    {
        "id": "hefesto-landpage",
        "filename": "HEFESTO _ LANDPAGE_OMEGA.md",
        "name": "OMEGA.HEFESTO.LANDPAGE",
        "function": (
            "Landing pages de alta conversão: design, UX, psicologia e frontend."
        ),
        "category": CATEGORY_MARKETING,
        "keywords": [
            "landing page",
            "landpage",
            "conversão",
            "ux",
            "página de vendas",
        ],
        "intents": ["marketing", "frontend"],
        "stacks": [],
        "prerequisites": [],
        "is_prompt_forger": False,
        "selectable_as_specialist": True,
    },
    {
        "id": "prometheus-prospeccao",
        "filename": "PROMETHEUS-FRAG-PROSPECCAO-FABIANO-SF.md",
        "name": "Fragmento 7 – Prospecção & Conversão Fabiano SF",
        "function": (
            "Prospecção B2B, copy e conversão consultiva para software house."
        ),
        "category": CATEGORY_MARKETING,
        "keywords": [
            "prospecção",
            "copy",
            "b2b",
            "conversão",
            "software house",
            "vendas",
            "comercial",
        ],
        "intents": ["marketing", "prospeccao"],
        "stacks": [],
        "prerequisites": [],
        "is_prompt_forger": False,
        "selectable_as_specialist": True,
    },
    {
        "id": "yotaia",
        "filename": "yotaia.md",
        "name": "YotaIA - Método Universal de Extração de Agentes v1.0",
        "function": (
            "Método ORUS para extrair/criar agentes e entregar fragmento "
            "estruturado."
        ),
        "category": CATEGORY_ORQUESTRACAO,
        "keywords": [
            "extrair agente",
            "criar agente",
            "yotaia",
            "extração",
        ],
        "intents": ["orquestracao", "projeto_novo"],
        "stacks": [],
        "prerequisites": [],
        "is_prompt_forger": False,
        "selectable_as_specialist": True,
    },
    {
        "id": "agente-omega-blueprint",
        "filename": _AGENTE_OMEGA_FILENAME,
        "name": "OMEGA EXTRATOR - BLUEPRINT EXTRACTION MASTER v1.0",
        "function": (
            "Transforma insights em blueprints executáveis com codificação "
            "AlphaLang."
        ),
        "category": CATEGORY_ORQUESTRACAO,
        "keywords": [
            "blueprint",
            "extrator",
            "alphalang",
            "omega extrator",
        ],
        "intents": ["orquestracao", "arquitetura"],
        "stacks": [],
        "prerequisites": [],
        "is_prompt_forger": False,
        "selectable_as_specialist": True,
    },
    {
        "id": "yota-blueprint",
        "filename": "yota-blueprint.md",
        "name": "Yota Blueprint (OMEGA Extrator)",
        "function": (
            "Entrada de catálogo para yota-blueprint.md — mesmo conteúdo do "
            "Extrator Blueprint (duplicata no disco)."
        ),
        "category": CATEGORY_ORQUESTRACAO,
        "keywords": ["blueprint", "yota-blueprint", "extrator"],
        "intents": ["orquestracao", "arquitetura"],
        "stacks": [],
        "prerequisites": [],
        "is_prompt_forger": False,
        "selectable_as_specialist": True,
    },
    {
        "id": "yotaia-ai-eos",
        "filename": "yotaia-AI-EOS-.md",
        "name": "AI-EOS — Multiagent Operating System Specialist",
        "function": (
            "Sistema operacional da engenharia IA: gerencia, coordena e audita "
            "agentes; não escreve código."
        ),
        "category": CATEGORY_ORQUESTRACAO,
        "keywords": [
            "multiagente",
            "orquestração",
            "operating system",
            "ai-eos",
            "coordenar agentes",
        ],
        "intents": ["orquestracao"],
        "stacks": [],
        "prerequisites": [],
        "is_prompt_forger": False,
        "selectable_as_specialist": True,
    },
    {
        "id": "yota-chefe-arquitetura",
        "filename": "yota-chefe-arquitetura.md",
        "name": "ChiefAIArchitect",
        "function": (
            "Orquestra especialistas (CTO/PM); planeja e valida; não executa "
            "tarefas técnicas."
        ),
        "category": CATEGORY_ORQUESTRACAO,
        "keywords": [
            "chief",
            "orquestrar",
            "programa",
            "gestão",
            "cto",
            "pm",
        ],
        "intents": ["orquestracao", "arquitetura", "projeto_novo"],
        "stacks": [],
        "prerequisites": [],
        "is_prompt_forger": False,
        "selectable_as_specialist": True,
    },
    {
        "id": "yotaia-conhecimento",
        "filename": "yotaia-conhecimento.md",
        "name": "KnowledgeAcquisitionAgent",
        "function": (
            "Constrói bases de conhecimento auditáveis; primeiro elo "
            "multiagente."
        ),
        "category": CATEGORY_ORQUESTRACAO,
        "keywords": [
            "conhecimento",
            "knowledge",
            "aquisição",
            "base de conhecimento",
        ],
        "intents": ["orquestracao", "dados"],
        "stacks": [],
        "prerequisites": [],
        "is_prompt_forger": False,
        "selectable_as_specialist": True,
    },
    {
        "id": "yotaia-dominio",
        "filename": "yotaia-dominio.md",
        "name": "DomainExpertAgent",
        "function": (
            "Converte base de conhecimento em modelo de domínio (DDD) sem "
            "inventar regras."
        ),
        "category": CATEGORY_ORQUESTRACAO,
        "keywords": ["domínio", "ddd", "domain", "modelo de domínio"],
        "intents": ["arquitetura", "orquestracao"],
        "stacks": [],
        "prerequisites": [
            {
                "code": "base_conhecimento",
                "message": (
                    "Este especialista solicita uma base de conhecimento "
                    "auditável como entrada prévia."
                ),
            }
        ],
        "is_prompt_forger": False,
        "selectable_as_specialist": True,
    },
    {
        "id": "yota-projeto-conhecimento",
        "filename": "yota-projeto-conhecimento.md",
        "name": "ProjectKnowledgeGraphArchitect",
        "function": (
            "Grafo de conhecimento e memória do projeto; conecta artefatos."
        ),
        "category": CATEGORY_ORQUESTRACAO,
        "keywords": [
            "grafo",
            "knowledge graph",
            "memória do projeto",
            "artefatos",
        ],
        "intents": ["orquestracao", "dados"],
        "stacks": [],
        "prerequisites": [],
        "is_prompt_forger": False,
        "selectable_as_specialist": True,
    },
    {
        "id": "yotaia-platform-evolution",
        "filename": "yotaia-AIPlatformEvolutionArchitect.md",
        "name": "AIPlatformEvolutionArchitect",
        "function": (
            "Pesquisa e propõe evolução da plataforma multiagente; nunca "
            "escreve código nem altera sistemas diretamente."
        ),
        "category": CATEGORY_ORQUESTRACAO,
        "keywords": [
            "plataforma",
            "evolução",
            "multiagente",
            "otimização",
        ],
        "intents": ["orquestracao", "arquitetura"],
        "stacks": [],
        "prerequisites": [],
        "is_prompt_forger": False,
        "selectable_as_specialist": True,
    },
    {
        "id": "prometheus-cognitive",
        "filename": "PROMETHEUS-FRAG-COGNITIVE-ENT.md",
        "name": "Fragmento 4 – Cognitive Systems & Enterprise Architecture",
        "function": (
            "Sistemas cognitivos distribuídos, orquestração de modelos e "
            "arquitetura enterprise."
        ),
        "category": CATEGORY_ORQUESTRACAO,
        "keywords": [
            "cognitivo",
            "enterprise",
            "orquestração de modelos",
        ],
        "intents": ["arquitetura", "orquestracao"],
        "stacks": [],
        "prerequisites": [],
        "is_prompt_forger": False,
        "selectable_as_specialist": True,
    },
    {
        "id": "hefesto-bet-analyst",
        "filename": "HEFESTO-BET-ANALYST-EXTRACTION-v4-ALPHALANG.md",
        "name": "HEFESTO — BET ANALYST",
        "function": (
            "Análise de mercados de apostas: probabilidade, valor e risco."
        ),
        "category": CATEGORY_OUTROS,
        "keywords": ["apostas", "betting", "odds", "probabilidade", "risco"],
        "intents": [],
        "stacks": [],
        "prerequisites": [],
        "is_prompt_forger": False,
        "selectable_as_specialist": True,
    },
    {
        "id": "academia-nutricao",
        "filename": "Academia_Nutrição_Saúde v1.0.md",
        "name": "Academia_Nutrição_Saúde v1.0",
        "function": (
            "Saúde, nutrição, academia/treino e gestão fitness com base em "
            "evidências."
        ),
        "category": CATEGORY_OUTROS,
        "keywords": [
            "nutrição",
            "academia",
            "saúde",
            "treino",
            "fitness",
        ],
        "intents": [],
        "stacks": [],
        "prerequisites": [],
        "is_prompt_forger": False,
        "selectable_as_specialist": True,
    },
]


def get_fragment_by_id(fragment_id: str) -> FragmentEntry | None:
    from orchestrator.services.discovery_service import effective_fragments

    for entry in effective_fragments(sync=False):
        if entry["id"] == fragment_id:
            return entry
    return None


def get_fragment_by_filename(filename: str) -> FragmentEntry | None:
    from orchestrator.services.discovery_service import effective_fragments

    for entry in effective_fragments(sync=False):
        if entry["filename"] == filename:
            return entry
    return None


def get_prompt_forger() -> FragmentEntry:
    for entry in FRAGMENTS:
        if entry["is_prompt_forger"]:
            return entry
    raise RuntimeError("Prompt Forger missing from catalog")


def catalog_public_entry(entry: FragmentEntry, **extra: Any) -> dict[str, Any]:
    from orchestrator.services.discovery_service import is_auto_discovered

    return {
        "id": entry["id"],
        "filename": entry["filename"],
        "name": entry["name"],
        "function": entry["function"],
        "description": entry["function"],
        "category": entry["category"],
        "is_prompt_forger": entry["is_prompt_forger"],
        "selectable_as_specialist": entry["selectable_as_specialist"],
        "prerequisites": list(entry["prerequisites"]),
        "auto_discovered": is_auto_discovered(entry),
        **extra,
    }
