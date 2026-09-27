---
name: orus-skill-posts-visuais
description: >
  Sistema completo de geração de posts visuais para projetos editoriais no Instagram.
  Use esta skill sempre que o usuário pedir para criar, gerar, ajustar ou referenciar
  posts, capas, slides ou imagens no padrão ORUS. Cobre: seleção de estilo visual (24 estilos
  catalogados em 6 categorias), geração de prompts de imagem completos com especificações
  técnicas de cores, tipografia e layout, distribuição estratégica de estilos por série de posts,
  e verificação de qualidade (checklist ORUS). Acione também quando o usuário mencionar
  "Edição XX", "badge", "prompt base", "estilo visual", "série Primeiros Passos",
  ou qualquer código de estilo (ex: FUJI35, VNOIR, PSYCHO, NEONOIR, etc.).

  ⚠️ INSTRUÇÃO OBRIGATÓRIA PARA A IA: Quando esta skill for carregada ou quando o arquivo
  for enviado pelo usuário, a IA deve IMEDIATAMENTE listar os temas e estilos disponíveis
  antes de qualquer outra ação. Ver seção "0. PROTOCOLO DE INICIALIZAÇÃO" para o formato correto.
---

# ORUS — KNOWLEDGE SKILL DE POSTS VISUAIS (UNIFICADA)

> **Hash de referência:** `orus.posts.visuais.sistema.completo.backup.20250713`
> **Versão consolidada** a partir dos 5 documentos do ecossistema ORUS.

---

## 0. PROTOCOLO DE INICIALIZAÇÃO (OBRIGATÓRIO)

> **Para a IA:** Sempre que este arquivo for enviado ou carregado pelo usuário, execute este protocolo **antes de qualquer outra resposta**.

### O que fazer ao receber este arquivo

Ao detectar o carregamento desta skill, responda com a seguinte estrutura:

```
✅ Skill ORUS de Posts Visuais carregada com sucesso!

📚 ESTILOS DISPONÍVEIS — 24 estilos em 6 categorias:

🎞️ CATEGORIA 1 — FILM & PHOTOGRAPHY
  • FUJI35   → Fuji 35mm Film          (nostalgia, autenticidade)
  • VNOIR    → Vintage Film Noir        (sofisticação, drama)
  • DOCSOC   → Documentary Social       (credibilidade, dados)
  • STREET   → Street Photography       (autenticidade urbana)

🏢 CATEGORIA 2 — CORPORATE & TECH
  • CORPMIN  → Corporate Minimalist     (negócios, home office)
  • TECHMAG  → Tech Magazine            (tecnologia, startups)
  • CORPTECH → Corporate Tech           (inovação empresarial)
  • DATAVIZ  → Data Visualization       (estatísticas, análises)

🔪 CATEGORIA 3 — PSYCHOLOGICAL & THRILLER
  • PSYCHO   → Psychological Thriller   (provocativo, impacto)
  • NPSYCHO  → Noir Psycho Thriller     (conflitos, relacionamentos)
  • HORROR   → Horror Warning           (alertas, crises)
  • NEONOIR  → Neo-Noir Detective       (investigações, revelações)

🎨 CATEGORIA 4 — ARTISTIC & CREATIVE
  • STREETART → Street Art Underground  (criatividade, juventude)
  • VINTALE   → Vintage Storytelling    (histórias, legado)
  • FASHION   → Fashion Magazine        (marca pessoal, estilo)
  • CREATIVE  → Creative Magazine       (inovação, arte)

⚙️ CATEGORIA 5 — SPECIALIZED STYLES
  • SURVIVAL  → Survival Warning        (crises empresariais)
  • MILITARY  → Military Tactical       (disciplina, estratégia)
  • LUXURY    → Luxury Service          (serviços premium)
  • RETRO     → Retrowave Neon          (nostalgia tech, inovação)

💼 CATEGORIA 6 — BUSINESS SPECIALIZED
  • INDUSTRIAL → Industrial Blueprint   (processos, metodologias)
  • FINANCE    → Financial Professional (finanças, investimentos)
  • ALLIANCE   → Corporate Alliance     (parcerias, networking)
  • MINIMAL    → Japanese Minimal       (simplicidade, clareza)

📌 6 ESTILOS EDITORIAIS PRINCIPAIS (produção em série):
  1. Magazine Futurista       (Posts 1–10)
  2. Cinematográfico Editorial (Posts 11–20)
  3. Neo-Noir Editorial        (Posts 21–30)
  4. Sci-Fi Distópico          (Posts 31–40)
  5. Mentor Realista           (uso especial, 2-3x/mês)
  6. Thriller Psicológico      (uso especial, 1-2x/mês)

💬 Como posso te ajudar? Me diga o tema do post e, se quiser, o estilo preferido.
   Ou peça "ajuda na seleção" e responderei algumas perguntas para indicar o melhor estilo.
```

### Gatilhos que ativam este protocolo

- Usuário envia este arquivo `.md` diretamente
- Usuário digita: `carregar skill`, `iniciar skill`, `ativar posts visuais`
- Usuário menciona código de estilo pela primeira vez na conversa (ex: `FUJI35`, `PSYCHO`)

---

## 1. PADRÃO UNIVERSAL DE LAYOUT (OBRIGATÓRIO EM TODOS OS POSTS)

Todo post, independentemente do estilo visual, deve respeitar esta estrutura fixa:

| Elemento | Especificação |
|---|---|
| **Dimensões** | 1080 × 1350 px (formato Instagram) |
| **Badge Edição** | `EDIÇÃO XX` — canto superior esquerdo, 40px do topo, 30px da esquerda; fundo laranja `#FF8A65`; texto branco; Montserrat SemiBold 12pt |
| **Logo do Projeto** | `[NOME_DO_PROJETO]` — centralizado no topo, 80px do topo; branco `#F8F8F8`; Montserrat ExtraBold; tamanho fixo proporcional ao slide |
| **Título Principal** | 200px do topo, 40px da margem esquerda; Montserrat Bold 30pt; branco `#F8F8F8` |
| **Subtítulo** | 280px do topo, 40px da esquerda; Open Sans Regular 20pt; branco `#F8F8F8` |
| **Corpo de Texto** | 360px do topo, 40px da esquerda; Open Sans Regular 16pt; branco `#F8F8F8` |
| **Rodapé** | 1250px do topo, centralizado; Open Sans Regular 12pt; cinza `#3C3C3C`; texto fixo: `"Revista do Empreendedor Raiz"` |
| **Código de Rastreamento** | `` — canto inferior direito, Open Sans 18px, 20px das bordas |

### 1.1 Regras de Destaque em Laranja `#FF8A65`

Os seguintes elementos **sempre** recebem cor laranja:

- Números e porcentagens (ex: `73%`, `8 MESES`)
- Palavras de ação em caixa alta (COMEÇAR, GANHAR, FAZER)
- Valores monetários (R$ amounts)
- Conceitos-chave do tema
- Calls-to-action

---

## 2. PALETA DE CORES OFICIAL ORUS

### Paleta Base Universal

| Nome | Hex | Uso |
|---|---|---|
| Preto Base | `#0B0B0B` | Fundos principais |
| Azul Profundo | `#1A2B3D` | Elementos secundários |
| Branco Puro | `#F8F8F8` | Textos principais |
| Cinza Neutro | `#3C3C3C` | Textos secundários / rodapé |
| **Laranja Claro** | **`#FF8A65`** | **Destaques e palavras-chave** |

### Paleta Alternativa (Prompts Base Completos)

| Nome | Hex | Uso |
|---|---|---|
| Azul Escuro | `#2C3E50` | Fundo principal alternativo |
| Laranja | `#E67E22` | Destaques alternativos |
| Branco | `#FFFFFF` | Tipografia principal |

---

## 3. TIPOGRAFIA PADRÃO

### Fontes Oficiais

| Elemento | Fonte | Peso |
|---|---|---|
| Logo do Projeto | Montserrat | ExtraBold |
| Títulos | Montserrat | Bold |
| Subtítulos | Montserrat | SemiBold |
| Corpo de Texto | Open Sans | Regular |
| Destaques | Open Sans | Bold |

### Hierarquia de Tamanhos

| Elemento | Tamanho |
|---|---|
| Logo | Proporcional ao slide (fixo) |
| Título Principal | 28–32pt |
| Subtítulo | 18–22pt |
| Corpo | 14–16pt |
| Rodapé | 12pt |

---

## 4. PROMPT BASE UNIVERSAL

Use este template como esqueleto para qualquer post. Substitua os campos em `[COLCHETES]`:

```
Create Instagram carousel slide 1080x1350px, [ESTILO_VISUAL] aesthetic
with authentic film grain.
IMPORTANT: Pay special attention to Portuguese accents and special
characters in all text elements (ã, ç, é, í, ó, ú, etc.).
SCENE: [DESCRIÇÃO_ESPECÍFICA_DO_CENÁRIO]
VISUAL ELEMENTS:
- Film grain texture matching the chosen style
- Orange highlight color #FF8A65 for key terms and impact words
- [ELEMENTOS_VISUAIS_ESPECÍFICOS_DO_ESTILO]
FIXED LAYOUT STRUCTURE:
1. TOP LEFT BADGE: "EDIÇÃO [NÚMERO]" in small rounded rectangle
background, positioned 40px from top, 30px from left, orange #FF8A65
background, white text, Montserrat SemiBold 12pt
2. CENTERED LOGO: "[NOME_DO_PROJETO]" positioned center-top, 80px from top,
white #F8F8F8, Montserrat ExtraBold, fixed size proportional to slide
3. MAGAZINE-STYLE TEXT POSITIONING (left-aligned with line breaks):
- MAIN TITLE: 200px from top, 40px from left margin, white #F8F8F8
Montserrat Bold 30pt — Text: "[TÍTULO_PRINCIPAL]"
- SUBTITLE: 280px from top, 40px from left margin, white #F8F8F8
Open Sans Regular 20pt — Text: "[SUBTÍTULO]"
- BODY TEXT: 360px from top, 40px from left margin, white #F8F8F8
Open Sans Regular 16pt — Text: "[TEXTO_CORPO]"
- FOOTER: 1250px from top, center-aligned, gray #3C3C3C Open Sans
Regular 12pt — Text: "Revista do Empreendedor Raiz"
TEXT HIGHLIGHTING RULES:
- Numbers and percentages in orange #FF8A65
- Action words (COMEÇAR, GANHAR, FAZER) in orange #FF8A65
- Money values (R$ amounts) in orange #FF8A65
- Key concepts related to theme in orange #FF8A65
STYLE: [ESTILO_ESPECÍFICO] with magazine editorial layout, professional
typography hierarchy, consistent brand positioning.
```

---

## 5. CATÁLOGO COMPLETO DE ESTILOS VISUAIS (24 ESTILOS)

### CATEGORIA 1 — FILM & PHOTOGRAPHY

| Código | Estilo | Características Visuais | Uso Recomendado |
|---|---|---|---|
| `FUJI35` | Fuji 35mm Film | Granulação analógica autêntica, tons vintage quentes, leve desbotamento, texturas de filme | Nostalgia, autenticidade, histórias pessoais, casos reais inspiradores |
| `VNOIR` | Vintage Film Noir | P&B dramático, contrastes altos, iluminação de sombras pronunciadas, estética cinema clássico | Sofisticação, drama, investigação, temas sérios, storytelling profundo |
| `DOCSOC` | Documentary Social | Fotojornalismo realista, cores neutras, composição espontânea, credibilidade jornalística | Credibilidade, casos reais, pesquisas, estatísticas, reportagens |
| `STREET` | Street Photography | Cenas urbanas cruas, luz natural, capturas espontâneas, texturas de concreto e grafite | Autenticidade urbana, vida real, movimento social, cultura de rua |

### CATEGORIA 2 — CORPORATE & TECH

| Código | Estilo | Características Visuais | Uso Recomendado |
|---|---|---|---|
| `CORPMIN` | Corporate Minimalist | Layout limpo, espaços brancos generosos, tipografia sans-serif, geometria simples | Negócios, home office, corporativo, profissionalismo |
| `TECHMAG` | Tech Magazine | Interfaces digitais, dados visualizados, layout clean tech, elementos UI/UX | Tecnologia, inovação, startups, ferramentas tech |
| `CORPTECH` | Corporate Tech | Fusão entre negócios e tecnologia, interfaces híbridas, profissionalismo digital | Inovação empresarial, transformação digital, business tech |
| `DATAVIZ` | Data Visualization | Gráficos limpos, infográficos claros, charts profissionais, estatísticas visuais | Estatísticas, pesquisas, análises, relatórios, dados científicos |

### CATEGORIA 3 — PSYCHOLOGICAL & THRILLER

| Código | Estilo | Características Visuais | Uso Recomendado |
|---|---|---|---|
| `PSYCHO` | Psychological Thriller | Suspense visual, tensão psicológica, contrastes dramáticos, profundidade emocional | Temas provocativos, conflitos internos, decisões difíceis, impacto emocional |
| `NPSYCHO` | Noir Psycho Thriller | Combinação noir clássico + psicológico, sombras dramáticas, tensão familiar | Conflitos familiares, sabotagem emocional, relacionamentos complexos |
| `HORROR` | Horror Warning | Elementos de alerta, cores de perigo, atmosfera de urgência, impacto visual forte | Avisos importantes, alertas, crises, situações de risco |
| `NEONOIR` | Neo-Noir Detective | Noir moderno, investigação contemporânea, mistério urbano, atmosfera de descoberta | Investigações, revelações, casos empresariais, descobertas importantes |

### CATEGORIA 4 — ARTISTIC & CREATIVE

| Código | Estilo | Características Visuais | Uso Recomendado |
|---|---|---|---|
| `STREETART` | Street Art Underground | Arte de rua, grafite, texturas urbanas, cores vibrantes, estética underground | Juventude, criatividade, inovação, movimento cultural, autenticidade |
| `VINTALE` | Vintage Storytelling | Narrativa clássica, tons sépia, nostalgia, elementos retrô, storytelling visual | Histórias inspiradoras, tradição, valores familiares, legado |
| `FASHION` | Fashion Magazine | Editorial de moda, sofisticação visual, estilização profissional, composição elegante | Marca pessoal, estilo, sofisticação, imagem profissional |
| `CREATIVE` | Creative Magazine | Layouts artísticos, cores vibrantes, composições experimentais, criatividade livre | Conteúdo criativo, inovação, arte, expressão, originalidade |

### CATEGORIA 5 — SPECIALIZED STYLES

| Código | Estilo | Características Visuais | Uso Recomendado |
|---|---|---|---|
| `SURVIVAL` | Survival Warning | Estética de emergência, alertas críticos, atmosfera de preparação | Crises empresariais, preparação, situações extremas |
| `MILITARY` | Military Tactical | Visual tático, disciplina militar, cores sóbrias, tipografia bold, organização rígida | Disciplina, estratégia, planejamento, organização |
| `LUXURY` | Luxury Service | Sofisticação premium, elegância, cores douradas e pretas, acabamento refinado | Serviços premium, qualidade superior, excelência |
| `RETRO` | Retrowave Neon | Estética anos 80, gradientes neon, cores vibrantes roxo/rosa, futurismo retrô | Nostalgia tech, inovação, modernidade vintage |

### CATEGORIA 6 — BUSINESS SPECIALIZED

| Código | Estilo | Características Visuais | Uso Recomendado |
|---|---|---|---|
| `INDUSTRIAL` | Industrial Blueprint | Esquemas técnicos, linhas precisas, estética de engenharia, plantas industriais | Processos, sistemas, metodologias, estruturas |
| `FINANCE` | Financial Professional | Cores sóbrias, gráficos financeiros, profissionalismo bancário, confiabilidade | Finanças, investimentos, economia, contabilidade |
| `ALLIANCE` | Corporate Alliance | Parcerias visuais, conexões empresariais, networking, tons azuis corporativos | Parcerias, networking, alianças estratégicas |
| `MINIMAL` | Japanese Minimal | Minimalismo japonês, espaços brancos, linhas finas, simplicidade elegante | Simplicidade, clareza, foco, zen empresarial |

---

## 6. PROMPTS BASE COMPLETOS — 6 ESTILOS EDITORIAIS PRINCIPAIS

Estes 6 estilos são os **estilos de produção** da série principal. Cada um tem especificações visuais únicas.

---

### ESTILO 1 — MAGAZINE FUTURISTA (Posts 1–10)

**Bases:** Fuji 35mm Film + Elementos Editoriais Premium

**Paleta:** Fundo `#2C3E50` · Destaque `#E67E22` · Texto `#FFFFFF`
**Tipografia:** Montserrat Bold (títulos) + Open Sans (corpo)

```
Create Instagram carousel cover 1080x1350px, premium futuristic magazine
design for [NOME_DO_PROJETO] edition.
MANDATORY LAYOUT:
- Top left: "EDIÇÃO XX" in orange #E67E22 rounded box, size 24px, subtle glow effect
- Header: "[NOME_DO_PROJETO]" in white Montserrat Bold 72px, positioned 120px from top, centered
- Main title: "[TÍTULO CENTRALIZADO]" in white Montserrat Bold 48px, center-positioned
- Bottom right: ".LPxxxx" in white Open Sans 18px, 20px from edges
- Background: Deep blue #2C3E50 with premium magazine texture
VISUAL STYLE:
- Base: Authentic Fuji 35mm film photography with pronounced grain
- Texture: Professional magazine paper with subtle fiber details
- Film elements: Light leaks in upper corners, natural vignette edges
- Lighting: Dramatic editorial lighting with orange #E67E22 accent highlights
FUTURISTIC ELEMENTS:
- Holographic line accents along edges
- Subtle digital interface overlays
- Orange #E67E22 neon highlighting key areas
- Magazine spine design on left edge
- QR code element in bottom left corner (small, integrated)
TEXTURES & EFFECTS:
- 35mm film grain overlay at 30% opacity
- Subtle paper texture for magazine feel
- Light leak effects in corners
- Soft glow on orange elements
- Professional depth of field
TYPOGRAPHY DETAILS:
- [NOME_DO_PROJETO]: Montserrat Bold, 72px, letter-spacing 2px
- Edition badge: Open Sans Bold, 24px, all caps
- Main title: Montserrat Bold, 48px, line-height 1.2
- Code: Open Sans Regular, 18px, 70% opacity
ATMOSPHERE: Premium editorial magazine with futuristic sophistication,
balanced between analog nostalgia and digital innovation.
KEYWORDS: authentic, film, 35mm, vintage, Brazilian, analog, warm, natural, grain
```

---

### ESTILO 2 — CINEMATOGRÁFICO EDITORIAL (Posts 11–20)

**Bases:** Drama Corporativo + Layout Magazine

**Paleta:** Fundo `#1A2332` · Destaque âmbar `#D4A628` · Texto `#FFFFFF` · Accent `#7F8C8D`
**Tipografia:** Playfair Display (títulos) + Source Sans Pro (corpo)

```
Create Instagram carousel cover 1080x1350px, cinematic magazine design for [NOME_DO_PROJETO] edition.
MANDATORY LAYOUT:
- Top left: "EDIÇÃO XX" in orange #E67E22 cinematic box, size 24px, film-style border
- Header: "[NOME_DO_PROJETO]" in white Montserrat Bold 72px, positioned 120px from top
- Main title: "[TÍTULO CENTRALIZADO]" in white Montserrat Bold 48px, dramatic positioning
- Bottom right: ".LPxxxx" in white Open Sans 18px, 20px from edges
- Background: Deep blue #1A2332 with cinematic lighting setup
CINEMATIC STYLE:
- Lighting: Professional 3-point lighting system with dramatic shadows
- Environment: Modern business/corporate setting
- Atmosphere: Authoritative and professional with film drama
- Composition: Cinematic framing with rule of thirds
VISUAL ELEMENTS:
- Dramatic chiaroscuro lighting effects
- Amber (#D4A628) key lighting creating focal points
- Subtle business graphics integrated (charts, documents)
- Corporate environment elements
- Film-quality depth of field
TEXTURES & EFFECTS:
- Digital film grain at 25% opacity
- Subtle motion blur effects
- Professional color grading (blue-orange scheme)
- Dramatic shadow gradients
TYPOGRAPHY DETAILS:
- [NOME_DO_PROJETO]: Playfair Display Bold, 72px, cinematic styling
- Edition badge: Source Sans Pro Bold, 24px, film border effect
- Main title: Playfair Display Bold, 48px, dramatic weight
ATMOSPHERE: Cinematic business drama with editorial authority,
professional corporate environment with film-quality visual storytelling.
KEYWORDS: cinematic, corporate, professional, executive, dramatic, film-quality, sophisticated
```

---

### ESTILO 3 — NEO-NOIR EDITORIAL (Posts 21–30)

**Bases:** Thriller Psicológico + Magazine Design

**Paleta:** Fundo `#1C1C1C` · Destaque `#FF6B35` · Texto `#FFFFFF` · Accent `#2C2C2C`
**Tipografia:** Oswald (títulos) + Lato (corpo)

```
Create Instagram carousel cover 1080x1350px, neo-noir magazine design for [NOME_DO_PROJETO] edition.
MANDATORY LAYOUT:
- Top left: "EDIÇÃO XX" in orange #FF6B35 noir-style box, size 24px, dramatic glow
- Header: "[NOME_DO_PROJETO]" in white Montserrat Bold 72px, positioned 120px from top, noir typography
- Main title: "[TÍTULO CENTRALIZADO]" in white Oswald Bold 48px, dramatic emphasis
- Bottom right: ".LPxxxx" in white Open Sans 18px, 20px from edges
- Background: Deep noir black #1C1C1C with dramatic lighting
NEO-NOIR CHARACTERISTICS:
- Lighting: Dramatic chiaroscuro with harsh directional lighting
- Shadows: Sharp, intentional shadow play creating mystery
- Contrast: High contrast between light and dark areas
- Atmosphere: Controlled tension and sophisticated suspense
VISUAL STYLE:
- Film noir aesthetic with modern editorial sophistication
- Orange #FF6B35 spotlight effects creating dramatic focal points
- Venetian blind shadow effects
- Urban night atmosphere elements
TEXTURES & EFFECTS:
- High contrast film grain at 35% opacity
- Dramatic shadow gradients
- Spotlight beam effects
- Subtle smoke/fog atmospheric elements
TYPOGRAPHY DETAILS:
- [NOME_DO_PROJETO]: Oswald Bold, 72px, dramatic weight with subtle shadow
- Edition badge: Lato Bold, 24px, noir styling
- Main title: Oswald Bold, 48px, high contrast emphasis
ATMOSPHERE: Modern film noir with editorial sophistication, mysterious
and compelling visual narrative perfect for revelations and provocative content.
KEYWORDS: noir, mysterious, sophisticated, urban, dramatic, revelation, tension, shadows
```

---

### ESTILO 4 — SCI-FI DISTÓPICO EDITORIAL (Posts 31–40)

**Bases:** Elementos Tecnológicos + Magazine Futurista

**Paleta:** Fundo `#0D1117` · Destaque cyan `#00D4FF` · Texto `#F0F6FC` · Accent roxo `#8B5CF6`
**Tipografia:** Orbitron (títulos) + Exo 2 (corpo)

```
Create Instagram carousel cover 1080x1350px, dystopian sci-fi magazine design for [NOME_DO_PROJETO] edition.
MANDATORY LAYOUT:
- Top left: "EDIÇÃO XX" in orange #E67E22 tech box, size 24px, digital glow effect
- Header: "[NOME_DO_PROJETO]" in white Montserrat Bold 72px, positioned 120px from top, futuristic
- Main title: "[TÍTULO CENTRALIZADO]" in white Orbitron Bold 48px, cyberpunk emphasis
- Bottom right: ".LPxxxx" in white Open Sans 18px, 20px from edges
- Background: Cyber dark blue #0D1117 with digital circuit patterns
SCI-FI ELEMENTS:
- Holographic interface overlays
- Digital circuit board patterns
- Neon cyan (#00D4FF) lighting effects with orange #E67E22 highlights
- Cyberpunk atmospheric elements
- Futuristic technological interfaces
VISUAL STYLE:
- High-tech dystopian aesthetic
- Digital noise and glitch effects
- Holographic projections and data streams
- Tech purple (#8B5CF6) accent elements
TEXTURES & EFFECTS:
- Digital noise overlay at 40% opacity
- Holographic shimmer effects
- Neon glow on technological elements
- Circuit board texture patterns
TYPOGRAPHY DETAILS:
- [NOME_DO_PROJETO]: Orbitron Bold, 72px, futuristic styling with digital effects
- Edition badge: Exo 2 Bold, 24px, tech border with glow
- Main title: Orbitron Bold, 48px, cyberpunk emphasis
ATMOSPHERE: Dystopian cyberpunk with editorial sophistication,
high-tech futuristic aesthetic perfect for technology and digital transformation.
KEYWORDS: cyberpunk, futuristic, technology, digital, neon, holographic, innovation, sci-fi
```

---

### ESTILO 5 — MENTOR REALISTA EDITORIAL (Uso Especial — 2-3 posts/mês)

**Bases:** Educacional + Clareza Visual

**Paleta:** Fundo `#34495E` · Destaque teal `#16A085` · Texto `#FFFFFF` · Accent `#BDC3C7`
**Tipografia:** Roboto Slab (títulos) + Roboto (corpo)

```
Create Instagram carousel cover 1080x1350px, educational magazine design for [NOME_DO_PROJETO] edition.
MANDATORY LAYOUT:
- Top left: "EDIÇÃO XX" in orange #E67E22 clean box, size 24px, professional styling
- Header: "[NOME_DO_PROJETO]" in white Montserrat Bold 72px, positioned 120px from top, educational clarity
- Main title: "[TÍTULO CENTRALIZADO]" in white Roboto Slab Bold 48px, clear emphasis
- Bottom right: ".LPxxxx" in white Open Sans 18px, 20px from edges
- Background: Professional navy #34495E with clean educational elements
EDUCATIONAL STYLE:
- Clean, organized visual hierarchy
- Professional educational environment
- Clear information architecture
- Accessible and welcoming atmosphere
VISUAL ELEMENTS:
- Uniform professional lighting
- Educational iconography (books, charts, tools)
- Teal (#16A085) highlighting key information areas
- Clean geometric organization
TEXTURES & EFFECTS:
- Minimal grain overlay at 15% opacity
- Clean paper texture for educational feel
- Subtle organizational grid patterns
TYPOGRAPHY DETAILS:
- [NOME_DO_PROJETO]: Roboto Slab Bold, 72px, clear and professional
- Edition badge: Roboto Bold, 24px, educational styling
- Main title: Roboto Slab Bold, 48px, maximum readability
ATMOSPHERE: Professional educational magazine with clear information delivery,
accessible and authoritative. Perfect for tutorials, explanations, and learning content.
KEYWORDS: educational, mentoring, learning, professional, clear, organized, accessible, authority
```

---

### ESTILO 6 — THRILLER PSICOLÓGICO EDITORIAL (Uso Especial — 1-2 posts/mês)

**Bases:** Tensão Psicológica + Urgência Visual

**Paleta:** Fundo `#8B0000` · Destaque `#FFD700` · Texto `#FFFFFF` · Accent `#696969`
**Tipografia:** Bebas Neue (títulos) + Nunito Sans (corpo)

```
Create Instagram carousel cover 1080x1350px, psychological thriller magazine design for [NOME_DO_PROJETO].
MANDATORY LAYOUT:
- Top left: "EDIÇÃO XX" in yellow #FFD700 warning box, size 24px, intense styling
- Header: "[NOME_DO_PROJETO]" in white Montserrat Bold 72px, positioned 120px from top, psychological
- Main title: "[TÍTULO CENTRALIZADO]" in white Bebas Neue 48px, intense dramatic weight
- Bottom right: ".LPxxxx" in white Open Sans 18px, 20px from edges
- Background: Intense dark red #8B0000 with psychological tension elements
PSYCHOLOGICAL THRILLER ELEMENTS:
- Dramatic overhead lighting creating psychological pressure
- Intentional visual discomfort for emphasis
- Controlled claustrophobic atmosphere
- Harsh shadow contrasts
- Tension-building visual metaphors
VISUAL STYLE:
- Psychological intensity with editorial sophistication
- Warning yellow (#FFD700) creating breakthrough tension moments
- Dramatic lighting with psychological impact
TEXTURES & EFFECTS:
- Intense grain overlay at 45% opacity
- Dramatic shadow effects
- High contrast emotional impacts
- Warning-level visual intensity
TYPOGRAPHY DETAILS:
- [NOME_DO_PROJETO]: Bebas Neue, 72px, psychological weight
- Edition badge: Nunito Sans Bold, 24px, warning emphasis
- Main title: Bebas Neue, 48px, maximum dramatic impact
ATMOSPHERE: Intense psychological thriller with editorial authority,
serious warning aesthetic. Perfect for crisis content, urgent alerts, and critical warnings.
KEYWORDS: psychological, intense, mental, pressure, breakthrough, tension, transformation, thriller
```

---

## 7. DISTRIBUIÇÃO ESTRATÉGICA — SÉRIE "PRIMEIROS PASSOS" (40 Posts)

| Bloco | Posts | Estilo | Propósito | Frequência |
|---|---|---|---|---|
| 1 | 1–10 | Magazine Futurista | Base / Introdução à série | 25% |
| 2 | 11–20 | Cinematográfico Editorial | Corporativo / Estratégia | 25% |
| 3 | 21–30 | Neo-Noir Editorial | Provocativo / Revelações | 25% |
| 4 | 31–40 | Sci-Fi Distópico | Tecnologia / Futuro | 25% |
| Especial | Variável | Mentor Realista | Educacional / Tutoriais | 5–8% |
| Especial | Variável | Thriller Psicológico | Urgência / Crises | 2–5% |

### 7.1 Critérios de Ajuste por Tema

- **Temas Educacionais** → Mentor Realista (independente do bloco)
- **Alertas Críticos** → Thriller Psicológico (substituição pontual)
- **Inovação Tech** → Sci-Fi Distópico (reforço temático)
- **Análises Corporativas** → Cinematográfico (intensificação)

### 7.2 Regra Anti-Fadiga Visual

- **Paleta Unificada:** `#2C3E50` e `#E67E22` presentes em todos os estilos
- **Variação Controlada:** 70% estilo do bloco + 30% elementos de outros estilos
- **Transições Suaves:** elementos visuais conectivos entre blocos

---

## 8. GUIA DE SELEÇÃO RÁPIDA DE ESTILO

| Objetivo do Post | Estilo Recomendado | Código(s) |
|---|---|---|
| Nostalgia / Autenticidade | Fuji 35mm / Vintage Storytelling | `FUJI35`, `VINTALE` |
| Sofisticação / Drama | Vintage Film Noir / Neo-Noir | `VNOIR`, `NEONOIR` |
| Credibilidade / Dados | Documentary Social / Data Viz | `DOCSOC`, `DATAVIZ` |
| Corporativo / Negócios | Corporate Minimalist / Finance | `CORPMIN`, `FINANCE` |
| Tecnologia / Inovação | Tech Magazine / Corporate Tech | `TECHMAG`, `CORPTECH` |
| Urgência / Alerta | Horror Warning / Survival | `HORROR`, `SURVIVAL` |
| Investigação / Revelação | Neo-Noir / Psychological | `NEONOIR`, `PSYCHO` |
| Educacional / Tutorial | Corporate Minimalist / Data Viz | `CORPMIN`, `DATAVIZ` |
| Arte / Criatividade | Street Art / Creative Magazine | `STREETART`, `CREATIVE` |
| Lifestyle / Cultura | Street Photography / Fashion | `STREET`, `FASHION` |

### Combinações Eficazes

| Combinação | Resultado |
|---|---|
| `FUJI35` + `PSYCHO` | Nostalgia com tensão |
| `VNOIR` + `CORPMIN` | Sofisticação profissional |
| `STREETART` + `CREATIVE` | Energia jovem criativa |
| `DOCSOC` + `DATAVIZ` | Credibilidade científica |
| `PSYCHO` + `HORROR` | Alerta com impacto máximo |

---

## 9. CHECKLIST DE QUALIDADE (OBRIGATÓRIO)

Antes de finalizar qualquer prompt ou validar qualquer imagem gerada, verificar:

### ✅ Estrutura
- [ ] Badge `EDIÇÃO X` posicionado corretamente (canto sup. esquerdo)
- [ ] Logo do projeto centralizado e fixo (topo)
- [ ] Layout tipo revista aplicado
- [ ] Hierarquia tipográfica respeitada

### ✅ Tipografia
- [ ] Fontes padrão especificadas para o estilo escolhido
- [ ] Tamanhos proporcionais definidos
- [ ] Alinhamento à esquerda com quebras de linha
- [ ] Destaques em laranja `#FF8A65`

### ✅ Cores
- [ ] Paleta ORUS aplicada ao estilo
- [ ] Palavras-chave e números em laranja claro
- [ ] Contraste adequado para leitura
- [ ] Fundo escuro mantido

### ✅ Técnico
- [ ] Resolução 1080×1350px especificada
- [ ] Aviso sobre acentos portugueses incluído no prompt
- [ ] Estilo visual especificado
- [ ] Grain de filme autêntico mencionado

---

## 10. TABELA COMPARATIVA DE ESPECIFICAÇÕES POR ESTILO

### Cores por Estilo

| Estilo | Background | Highlights | Texto | Accent |
|---|---|---|---|---|
| Magazine Futurista | `#2C3E50` | `#E67E22` | `#FFFFFF` | — |
| Cinematográfico | `#1A2332` | `#D4A628` | `#FFFFFF` | `#7F8C8D` |
| Neo-Noir | `#1C1C1C` | `#FF6B35` | `#FFFFFF` | `#2C2C2C` |
| Sci-Fi Distópico | `#0D1117` | `#00D4FF` | `#F0F6FC` | `#8B5CF6` |
| Mentor Realista | `#34495E` | `#16A085` | `#FFFFFF` | `#BDC3C7` |
| Thriller Psicológico | `#8B0000` | `#FFD700` | `#FFFFFF` | `#696969` |
| Fuji 35mm (deploy) | `#2C3E50` | `#E67E22` | `#FAF9F6` | `#8B4513` |

### Tipografia por Estilo

| Estilo | Headlines | Body Text | Característica |
|---|---|---|---|
| Magazine Futurista | Montserrat Bold | Open Sans | Sofisticação editorial |
| Cinematográfico | Playfair Display | Source Sans Pro | Elegância corporativa |
| Neo-Noir | Oswald | Lato | Impacto urbano |
| Sci-Fi Distópico | Orbitron | Exo 2 | Futurismo tecnológico |
| Mentor Realista | Roboto Slab | Roboto | Clareza educacional |
| Thriller Psicológico | Bebas Neue | Nunito Sans | Intensidade psicológica |
| Fuji 35mm (deploy) | Merriweather | Open Sans | Autenticidade vintage |

---

## 11. EXEMPLOS PRÁTICOS DE APLICAÇÃO

### Exemplo 1 — Tema: "Você Não Está Pronto Para Empreender"
- **Estilo:** PSYCHO + HORROR
- **Título:** `VOCÊ NÃO ESTÁ **PRONTO** PARA **EMPREENDER**`
- **Subtítulo:** `**6 SINAIS** que você deve parar antes de **PERDER TUDO**`
- **Corpo:** `**73%** dos brasileiros empreendem **SEM PREPARO** e quebram em **8 MESES**`
- **Destaques em laranja:** PRONTO, EMPREENDER, 6 SINAIS, PERDER TUDO, 73%, SEM PREPARO, 8 MESES

### Exemplo 2 — Tema: "IA no Empreendedorismo"
- **Estilo:** Sci-Fi Distópico
- **Headline:** `IA NO EMPREENDEDORISMO` (Orbitron Bold)
- **Supporting:** `O Futuro dos Negócios Já Chegou` (Exo 2)
- **Background:** `#0D1117` · Highlights: `#00D4FF`

### Exemplo 3 — Tema: "A Mentira dos R$ 50 Mil"
- **Estilo:** Neo-Noir
- **Headline:** `A MENTIRA DOS R$ 50 MIL` (Oswald Bold)
- **Supporting:** `O Que Ninguém Te Conta Sobre Este Valor` (Lato)
- **Background:** `#1C1C1C` · Highlights: `#FF6B35`

### Exemplo 4 — Tema: "Primeiros Passos no Negócio"
- **Estilo:** Fuji 35mm
- **Headline:** `PRIMEIROS PASSOS NO NEGÓCIO` (Merriweather Bold)
- **Supporting:** `O Guia Definitivo Para Começar` (Open Sans)
- **Background:** `#2C3E50` · Highlights: `#E67E22`

---

## 12. COMANDOS DE GERAÇÃO

```
# Criar novo post
orus.posts.criar.[TEMA].[CÓDIGO_ESTILO].padrao

# Aplicar padrão visual
orus.visual.padrao.apply

# Verificar conformidade
orus.quality.check

# Por estilo com parâmetros
.prompt.cinematografico --tema="[TEMA]" --tipografia=playfair_source
.prompt.fuji35mm        --tema="[TEMA]" --tipografia=merriweather_opensans
.prompt.mentor          --tema="[TEMA]" --tipografia=robotoslab_roboto
.prompt.noir            --tema="[TEMA]" --tipografia=oswald_lato
.prompt.scifi           --tema="[TEMA]" --tipografia=orbitron_exo2
.prompt.thriller        --tema="[TEMA]" --tipografia=bebas_nunito
```

---

*Skill consolidada a partir de:*
*① Catálogo Completo de Estilos Visuais · ② ORUS Visual Extraction Core · ③ Deploy Completo dos Prompts Base Estruturados · ④ Prompts Base Completos · ⑤ Distribuição de Estilos Visuais*
