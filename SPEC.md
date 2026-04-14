# Especificação do sistema de detecção de oportunidades para criptomoedas

## Visão geral

O sistema deve funcionar como um **assistente inteligente de operações**, monitorando automaticamente pares de criptomoedas nas exchanges NovaDAX, Mercado Bitcoin e Binance. Ele deve coletar dados de mercado em tempo quase real, aplicar filtros de volatilidade/volume/liquidez, classificar as oportunidades conforme a capacidade de execução e notificar o operador via Telegram e painel web. Também deve manter histórico e permitir evolução futura para integração de IA e automação de ordens.


## 1. Integração com APIs

A infraestrutura deve abstrair as diferenças entre as APIs das exchanges para permitir coleta unificada. As classes `NovaDaxProvider`, `MercadoBitcoinProvider` e `BinanceProvider` deverão fornecer interface comum:

```python
class ExchangeProvider:
    async def get_ticker(self, pair): ...
    async def get_order_book(self, pair): ...
    async def get_trades(self, pair, limit): ...
    async def get_klines(self, pair, interval, limit): ...
```

### 1.1 NovaDAX
- **Base URL**: `https://api.novadax.com/v1/`.
- **Autenticação**: algumas rotas públicas (ticker, depth, trades) não exigem autenticação; rotas privadas exigem chave/secret e header HMAC.
- **Endpoints importantes**:
  - `market/ticker?symbol=BTC_BRL` – retorna preço atual.
  - `market/depth?symbol=BTC_BRL` – retorna order book.
  - `market/trades?symbol=BTC_BRL&limit=100` – últimas negociações.
  - `market/kline?symbol=BTC_BRL&period=5min&size=100` – candles OHLCV.
- **Cuidados**: a documentação oficial indica limites de requisições por minuto e possíveis erros de timestamp; prever tratamento de exceções e backoff.

### 1.2 Mercado Bitcoin
- **Base URL**: `https://www.mercadobitcoin.net/api/`.
- **Endpoints importantes**:
  - `/ticker/<pair>/` – retorna preço, volume e variação (ex.: `ticker/BTCBRL/`).
  - `/orderbook/<pair>/` – livro de ordens.
  - `/trades/<pair>/<since>/` – lista de trades após `since` (timestamp unix).
  - `/candles/<pair>/?period=5m` – candles (dependendo da interface REST v4). As rotas para candles podem exigir autenticação via token da API v3 (chave/secret).
- **Limitações**: muitos dados são públicos, mas há quotas e a latência pode variar.

### 1.3 Binance
- **Base URL**: `https://api.binance.com/api/v3/` (pública) e `https://api.binance.com/api/v3/` (privada).
- **Endpoints importantes**:
  - `ticker/price?symbol=BTCUSDT` – preço atual.
  - `ticker/24hr?symbol=BTCUSDT` – estatísticas de 24 h.
  - `depth?symbol=BTCUSDT&limit=100` – order book.
  - `trades?symbol=BTCUSDT&limit=1000` – últimos trades.
  - `klines?symbol=BTCUSDT&interval=5m&limit=500` – candles OHLCV.
- **Autenticação**: rotas públicas não exigem chave; rotas privadas exigem `X‑Mbx‑APIKey` e assinatura HMAC.

### 1.4 Implementação do módulo de API
- **Dependências**: `httpx` ou `aiohttp` para chamadas assíncronas; `tenacity` para retry/backoff.
- **Funcionalidades**:
  - Configurar sessões HTTP com timeouts, headers e proxies.
  - Tratar limites de rate limit (status 429) com backoff exponencial.
  - Registrar erros e latência.

## 2. Módulos essenciais

### 2.5 Painel web
- **Tecnologia**: Next.js/React com TypeScript; shadcn/ui para componentes; Tailwind CSS. 
- **Layout**:
  - **Dashboard principal**: cards coloridos com KPIs (nº de oportunidades, pares monitorados, volumetria total). 
  - **Tabela de oportunidades**: listagem das melhores oportunidades com filtros (corretora, par, score, tipo). Linhas destacadas conforme a cor do score (verde intenso = excelente, amarelo = moderado). 
  - **Detalhes do sinal**: ao clicar, modal com gráfico de preço recente (recharts), volume, liquidez, spread, tempo de vida. 
  - **Filtros**: controles para ajustar thresholds de volume/volatilidade, escolher corretoras, intervalos de tempo.
- **Interatividade**: WebSockets (Ex. `socket.io`) para atualizações em tempo real; charts com zoom; dark/light mode.
- **Design system**: basear‑se em fintechs modernas (Nubank, C6) com paleta de cores suaves, tipografia clara, ícones simples. Evitar gridlines; usar cards com bordas arredondadas (radius 2xl), sombras suaves, emojis nos KPIs para enfatizar alegria/urgência (ex.: 📈, ⚠️).

### 2.6 Histórico e analytics
- Registrar cada oportunidade detectada com timestamp, exchange, par, score, volume, liquidez, tipo de movimento, spread, duração. 
- Permitir relatórios: “top moedas por oportunidades boas”, “horários com mais sinais”, “distribuição de scores”. 
- Persistir no banco para análise futura e ajuste de parâmetros.

### 2.7 Configurações e parâmetros
- Interface de administração para ajustar thresholds (volume mínimo, variação mínima, limite de alertas) sem alterar código. 
- Permitir ativar/desativar exchanges ou pares individuais.

## 3. Módulos de evolução (versões futuras)

### 3.1 Componente de inteligência adaptativa
Implementar algoritmos que ajustem automaticamente os thresholds com base no histórico de sucesso. Possibilidades:
- **Aprendizado supervisionado**: treinar modelo (e.g., Random Forest, Gradient Boosted Trees) com features calculadas (volatilidade, volume, liquidez, spread, tipo de movimento, horários) e rótulos (operação deu lucro ou não). A saída seria um score refinado.
- **Modelos de previsão de volatilidade**: usar GARCH/ARCH ou redes neurais (LSTM) para estimar volatilidade futura. 
- **Classificação de armadilhas**: usar clustering (DBSCAN, k‑means) com features de profundidade de livro e variação para separar sinais falsos.

### 3.2 Análise cross‑exchange
- Verificar se um movimento ocorre apenas em uma exchange ou em várias. 
- Calcular arbitragem simples (diferença de preço). 
- Ajustar score se houver convergência divergente (movimento só local → menor score). 

### 3.3 Sinais de deterioração
- Monitorar sinais em curso; enviar aviso quando volume cair, liquidez diminuir, spread piorar ou o tempo de vida ultrapassar limite (ex.: 2 horas). 
- Recomendar saída ou pausa.

### 3.4 Execução assistida
- Integração parcial com APIs privadas para enviar ordens (somente após validação legal). 
- Implementar “botão de teste” no painel que aciona ordem mínima via API, com confirmação. 
- Calcular valor de entrada sugerido com base em liquidez e perfil do usuário. 

### 3.5 App móvel e notificações push
- Desenvolver versão móvel (React Native ou Flutter). 
- Integrar com notificações push (OneSignal, Firebase). 

### 3.6 Customização de perfis
- Permitir múltiplos usuários com parâmetros diferentes. 
- Permitir definir perfil “conservador” (prioriza liquidez) ou “agressivo” (aceita spikes). 

## 4. Tecnologias e algoritmos úteis

- **Linguagem**: Python 3.11 para backend e algoritmos.
- **Bibliotecas**: `pandas` e `numpy` para manipulação de dados; `statsmodels` para modelos GARCH; `ta` (Technical Analysis library) para indicadores; `scikit‑learn` para modelos supervisionados; `sqlalchemy` para ORM; `aiohttp` ou `httpx` para HTTP assíncrono; `python-telegram-bot` para integração com Telegram.
- **Banco de dados**: Supabase (PostgreSQL) com Row Level Security para isolar dados por usuário; pgbouncer para pooling; triggers para limpeza de dados antigos.
- **Infraestrutura**: deploy no Railway ou Render para backend Python; Vercel para front end; monitoramento com Logtail e Sentry; containerização com Docker.
- **Design**: usar design system inspirado em fintechs; cores suaves (#121212 para fundo escuro, roxo/azul para destaques); tipografia consistente; ícones da lucide‑react; layout grid; componentes do shadcn/ui; variação de tamanhos de fonte (headline `text-2xl`, texto `text-base`); animações com Framer Motion.

## 5. Resumo de funcionalidades do MVP

| Módulo | Descrição | Observações |
|-------|-----------|------------|
| **Coletor de dados** | Consome APIs de NovaDAX, Mercado Bitcoin e Binance (públicas) para obter preço, candles, volume e liquidez em intervalos curtos. | Implementar controle de rate limit e cache. |
| **Filtro de volatilidade** | Calcula variação percentual de preço nas últimas `n` velas. | Threshold ≥ 2 % (ajustável). |
| **Filtro de volume** | Exige volume financeiro mínimo por par (R$ 10k grandes, R$ 3k–5k pequenas). | Parâmetro ajustável via painel. |
| **Filtro de liquidez** | Exige quantidade mínima de unidades negociadas (≥ 1000 para teste, ≥ 3000 para operações maiores). | Baseado em valor relatado pelo usuário. |
| **Filtro de spread** | Calcula diferença entre melhor compra e melhor venda; rejeita sinais com spread elevado. | Spread máximo 1 % (ajustável). |
| **Classificação do movimento** | Determina se o movimento é range forte, spike, fraco ou armadilha. | Usa sequência de candles e padrões. |
| **Cálculo de score** | Combina volatilidade, volume, liquidez, repetição e spread em nota 0–100. | Peso configurável. |
| **Painel web (Next.js)** | Mostra top oportunidades, detalhes do sinal e histórico, com filtros e dark mode. | Usar Tailwind + shadcn/ui. |
| **Alertas no Telegram** | Envia mensagens com melhores sinais, mostrando exchange, par, volatilidade, volume, liquidez e score. | Usar bot com envio de mensagens proativas. |
| **Histórico** | Registra cada sinal, permitindo análises futuras e ajuste fino. | Tabelas de logging no banco. |
| **Configurações** | Permite modificar thresholds sem alterar código. | Interface no painel web. |

## 6. Considerações finais

Este documento serve como base para implementação por ferramentas de code generation (Codex/Claude Code). Algumas referências de design e ambiente de pesquisa foram registradas【505120507351886†screenshot】. Para detalhes específicos dos endpoints das exchanges, consulte a documentação oficial de cada API na fase de desenvolvimento. 

A arquitetura sugerida oferece flexibilidade para evoluir de um scanner simples para um **assistente operacional inteligente**, com possibilidade de automação gradual, aprendizado de máquina e integração com corretoras. O foco inicial deverá ser a **utilidade imediata para o usuário**, priorizando detecção de oportunidades reais, filtros robustos e experiência de uso fluida.
