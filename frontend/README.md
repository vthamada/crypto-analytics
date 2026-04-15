# Frontend

Aplicacao Next.js do painel `Crypto Analytics`.

## Responsabilidades

- Exibir dashboard em tempo real com oportunidades detectadas.
- Exibir historico e analytics agregados.
- Permitir ajuste de configuracoes operacionais protegidas por token administrativo.

## Requisitos

- Node.js 20+
- Backend rodando em `http://localhost:8000` por padrao

## Variaveis de ambiente

Crie um arquivo `.env.local` com:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000/api
NEXT_PUBLIC_WS_URL=ws://localhost:8000/ws
```

## Desenvolvimento

Instalacao:

```bash
npm install
```

Subir em modo desenvolvimento:

```bash
npm run dev
```

Aplicacao disponivel em:

```text
http://localhost:3000
```

## Scripts

- `npm run dev`: servidor de desenvolvimento
- `npm run build`: build de producao
- `npm run start`: sobe a build gerada
- `npm run lint`: analise estatico com ESLint

## Estrutura Principal

- `src/app/page.tsx`: dashboard principal
- `src/app/history/page.tsx`: historico e analytics
- `src/app/settings/page.tsx`: configuracoes administrativas
- `src/components/`: componentes de interface
- `src/hooks/use-opportunities.ts`: integracao de dashboard com REST + WebSocket
- `src/lib/api.ts`: cliente HTTP do backend
- `src/lib/websocket.ts`: cliente WebSocket com reconexao

## Observacoes Operacionais

- A pagina de configuracoes exige `ADMIN_TOKEN` configurado no backend.
- O frontend nao recebe de volta segredos armazenados no backend; campos sensiveis sao de escrita pontual.
- O build Docker espera `output: "standalone"` no Next, ja configurado em `next.config.ts`.
