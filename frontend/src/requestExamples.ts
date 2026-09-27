/** One-click starter prompts for the Pedido step. */

export type RequestExample = {
  id: string;
  label: string;
  text: string;
  suggestDiff?: boolean;
  webSearch?: boolean;
};

export const REQUEST_EXAMPLES: RequestExample[] = [
  {
    id: "django-react-debug",
    label: "Debug Django + React",
    text:
      "Tenho um erro num projeto Django (DRF) + React/Vite. Ajude a diagnosticar a causa provável, o que checar no backend/frontend e um plano de correção passo a passo. Se eu anexar logs ou arquivos, use-os.",
  },
  {
    id: "refactor",
    label: "Refactor legado",
    text:
      "Quero refatorar código legado anexado: melhorar legibilidade e estrutura sem mudar comportamento. Sugira diffs (unified) por arquivo e explique cada mudança em 1–2 frases.",
    suggestDiff: true,
  },
  {
    id: "activate-specialist",
    label: "Ativar especialista",
    text:
      "Reconheça e ative o documento/especialista anexado (cite nome e hash se houver), declare-se pronto e aguarde minhas perguntas no papel desse especialista.",
  },
  {
    id: "folder-diffs",
    label: "Diffs na pasta",
    text:
      "Analise os arquivos da pasta anexada e sugira diffs (unified) para corrigir ou melhorar. Não afirme ter aplicado nada no disco — só sugira o patch.",
    suggestDiff: true,
  },
];
