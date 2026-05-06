# ESPECIFICACAO_COMPLETA_IMPLEMENTACAO.md

# Especificação Completa para Implementação do Sistema

## 1. Objetivo deste documento

Este documento consolida, de forma completa, todas as instruções necessárias para orientar a implementação do sistema com base:

- no comportamento atual do produto
- no perfil operacional real do usuário final
- nas necessidades práticas levantadas durante as conversas
- nas limitações já identificadas do sistema atual
- na direção refinada de produto desejada

Este documento deve ser tratado como **guia principal de implementação**.

O objetivo do sistema é evoluir para um:

> **scanner de oportunidades operáveis no mercado BRL, com prioridade para liquidez, volume, força de movimento, leitura prática do livro de ofertas e margem real para trade ou continuidade**

---

## 2. Definição do problema que o sistema deve resolver

O sistema **não** deve ser construído como um simples ranking de moedas em alta.

O sistema **não** deve ser orientado apenas por percentual de variação.

O sistema **não** deve priorizar ativos com grandes altas se eles não forem operáveis.

O sistema deve resolver o seguinte problema:

> encontrar, dentro do mercado BRL monitorado, os ativos que estejam apresentando movimento relevante e que, ao mesmo tempo, sejam operacionalmente viáveis para trade ou hold, com liquidez suficiente, volume consistente, baixo risco de aprisionamento e margem real de oportunidade.

---

## 3. Princípio central do produto

A regra mais importante do sistema é:

> **Encontrar bons ativos operáveis**

Essa frase deve orientar:

- arquitetura
- ranking
- filtros
- dashboard
- alertas
- histórico
- score
- leitura de livro
- critérios de descarte

---

## 4. Perfil operacional do usuário final

### 4.1 Como o usuário opera
O usuário final:

- prefere operar em **pares BRL**
- entende que o mercado relevante, nas corretoras nacionais, está em reais
- quer seguir para onde o mercado está indo
- quer identificar oportunidades reais, não apenas movimentos chamativos
- começa pequeno e aumenta posição conforme a liquidez permite
- valoriza fortemente volume e liquidez
- evita moedas com risco de aprisionamento
- aceita movimentos menores com alta liquidez em vez de movimentos explosivos sem saída
- observa o livro de ofertas para encontrar margem operacional entre compra e venda
- diferencia oportunidades para trade e para hold

### 4.2 O que ele valoriza
O usuário final valoriza principalmente:

- liquidez
- volume
- volatilidade útil
- repetição de oscilação
- continuidade do movimento
- capacidade de entrada e saída
- margem operacional de trade
- possibilidade de aumentar tamanho de posição

### 4.3 O que ele rejeita
O usuário rejeita:

- volatilidade sem volume
- alta sem liquidez
- gráfico bonito sem possibilidade real de execução
- ativos onde se corre risco de ficar preso
- sinais médios se existirem movimentos muito mais fortes e líquidos no mercado
- monitoramento excessivamente estreito que deixe passar oportunidades reais do mercado BRL

---

## 5. Universo inicial e escopo de monitoramento

### 5.1 Diretriz refinada
O sistema não deve depender apenas de uma watchlist fixa.

Ele deve operar com duas camadas:

#### Camada A — Mercado BRL
Monitorar **todos os pares BRL relevantes** nas exchanges alvo.

#### Camada B — Shortlist operacional
Dentro desse universo, ranquear e destacar poucos ativos realmente interessantes.

### 5.2 Watchlist
A watchlist ainda deve existir, mas como recurso complementar, não como única fonte de monitoramento.

Ela serve para:
- favoritos
- acompanhamento próximo
- alertas direcionados
- filtro pessoal

### 5.3 Exchanges prioritárias
O sistema deve considerar prioritariamente exchanges compatíveis com o fluxo brasileiro, especialmente:
- NovaDAX
- Mercado Bitcoin

A Binance pode existir como provider complementar, mas deve ficar **desativada por padrão**. O usuário poderá ativá-la manualmente se desejar. O núcleo inicial do produto deve refletir o comportamento do mercado BRL nas exchanges onde o usuário opera: **Mercado Bitcoin e NovaDAX**.

---

## 6. Direção de produto refinada

O sistema deve ser desenhado como:

> **um radar do mercado BRL que descobre onde o fluxo está, filtra o que é operável, diferencia oportunidades de trade e de hold, lê liquidez e livro de ofertas, e destaca as oportunidades com melhor margem prática**

Isso significa que o sistema deve ser capaz de responder:

- onde o mercado BRL está se movendo agora?
- quais pares BRL estão fortes?
- quais têm liquidez suficiente?
- quais têm repetição ou continuidade?
- quais têm livro favorável?
- quais têm margem operacional suficiente?
- quais são bons para trade?
- quais são bons para hold?
- quais devem ser ignorados?

---

## 7. Tipos de oportunidade que o sistema deve reconhecer

### 7.1 Oportunidade de trade por oscilação
Ativo com:
- boa volatilidade
- boa liquidez
- repetição de movimentos
- faixa operacional útil
- margem favorável entre compra e venda

### 7.2 Oportunidade de continuidade / hold
Ativo com:
- disparo forte
- volume crescente
- continuidade do movimento
- chance de persistência por horas ou dias

### 7.3 Oportunidade observável, mas não operável
Ativo que:
- chama atenção
- mas ainda não apresenta qualidade suficiente de execução

### 7.4 Ativo a evitar
Ativo com:
- alta volatilidade sem liquidez
- volume fraco
- spread ruim
- risco de aprisionamento
- falsa aparência de oportunidade

---

## 8. Requisitos funcionais centrais

### 8.1 Monitoramento
O sistema deve:
- monitorar pares BRL relevantes
- permitir configuração de exchanges ativas
- permitir ativar/desativar pares específicos
- permitir watchlist manual
- permitir modo amplo de descoberta de mercado BRL

### 8.2 Filtros mínimos
O sistema deve aplicar filtros mínimos de:
- volume
- liquidez
- spread
- volatilidade
- executabilidade mínima

### 8.3 Ranking
O sistema deve rankear oportunidades usando critérios fortemente orientados a operabilidade.

### 8.4 Alertas
O sistema deve enviar alertas úteis, com baixa frequência e alto valor informativo.

### 8.5 Histórico
O sistema deve guardar histórico suficiente para:
- auditoria
- analytics
- outcome posterior
- aprendizado do ranking

---

## 9. Modelo de scores obrigatório

O sistema não deve depender de um único score genérico.

Deve haver, no mínimo, quatro scores separados:

### 9.1 Score de força do movimento
Objetivo:
medir o quão forte está o movimento atual.

Deve considerar:
- volatilidade atual
- aceleração
- desvio em relação ao comportamento recente
- persistência
- repetição
- continuidade

Pergunta que responde:
> isso está forte de verdade?

### 9.2 Score de liquidez / executabilidade
Objetivo:
medir se o ativo dá para operar na prática.

Deve considerar:
- volume
- liquidez
- profundidade do livro
- spread
- slippage estimado
- capacidade de entrada e saída

Pergunta que responde:
> isso dá para operar?

### 9.3 Score de margem operacional
Objetivo:
medir se existe faixa suficiente entre compra e venda para compensar a operação.

Deve considerar:
- melhor zona provável de compra
- melhor zona provável de venda
- distância percentual entre zonas
- impacto do spread
- impacto do slippage
- margem líquida potencial

Pergunta que responde:
> vale o trade?

### 9.4 Score operacional final
Objetivo:
combinar força, executabilidade e margem, com peso forte para liquidez.

Pergunta que responde:
> isso merece atenção agora?

---

## 10. Liquidez como critério dominante

### 10.1 Regra
Liquidez deve ser critério dominante do sistema.

Um ativo com 3% de movimento e alta liquidez deve ter mais prioridade do que um ativo com 100% de alta e liquidez ruim.

### 10.2 Implementação
O ranking final deve penalizar fortemente:
- pumps sem liquidez
- volatilidade sem volume
- ativos com risco alto de aprisionamento

### 10.3 Faixas operacionais
O sistema deve considerar pelo menos três faixas de operação:

- operação pequena
- operação média
- operação maior

Deve ser possível classificar um ativo como:
- bom para teste pequeno
- bom para operação média
- bom para operação maior

---

## 11. Regras derivadas das respostas do usuário

### 11.1 Liquidez mínima por faixa
Valores iniciais de referência:

- pequena: 3.000
- média: 5.000
- maior: 10.000 por dia

### 11.2 Entrada inicial
- R$ 25 para moedas pequenas

### 11.3 Escalada
- aumentar para R$ 200, R$ 300 ou mais se houver boa liquidez

### 11.4 Operação média
- R$ 1.000 ou mais

### 11.5 Ponto em que liquidez passa a importar muito
- a partir de R$ 1.000

### 11.6 Slippage tolerável
- grandes ativos: 3% a 5%
- ativos menores: 5% a 10%

### 11.7 Fatores de movimento atípico mais importantes
- aumento de volume
- repetição de oscilações

### 11.8 Duração útil do movimento
- horas ou dias

### 11.9 Quando o movimento perde valor
- quando cessam volume e volatilidade

### 11.10 Conteúdo mínimo do alerta
- volatilidade do ativo
- volume de compradores e vendedores

---

## 12. Leitura de livro de ofertas

### 12.1 Importância
O usuário final usa o livro de ofertas para avaliar:
- ponto de compra
- ponto de venda
- margem entre entrada e saída
- viabilidade de trade

### 12.2 Requisito
O sistema deve analisar o livro de ofertas para gerar sinais úteis.

### 12.3 O que deve ser estimado
- zona provável de compra
- zona provável de venda
- profundidade perto da entrada
- profundidade perto da saída
- distância percentual entre zonas
- book pressure
- concentração de ordens
- risco de rompimento da faixa

### 12.4 Métricas sugeridas
- `book_entry_zone`
- `book_exit_zone`
- `book_depth_buy`
- `book_depth_sell`
- `book_pressure_score`
- `estimated_trade_margin_pct`
- `estimated_net_trade_edge_pct`

---

## 13. Margem operacional de trade

### 13.1 Definição
Margem operacional é o espaço útil entre ponto provável de compra e ponto provável de venda, descontando custos estimados.

### 13.2 Requisito
O sistema deve calcular:

> margem operacional estimada = faixa potencial de venda - faixa potencial de compra - custos operacionais estimados

### 13.3 Classificação sugerida
- ruim
- aceitável
- boa
- excelente

### 13.4 Uso no ranking
Ativos sem margem operacional suficiente devem perder prioridade mesmo que tenham movimento e liquidez.

---

## 14. Tipos de classificação que o sistema deve gerar

Cada oportunidade deve poder ser classificada em múltiplas dimensões:

### 14.1 Natureza da oportunidade
- trade
- hold
- observação
- evitar

### 14.2 Nível de operabilidade
- não operável
- operável para teste pequeno
- operável para operação média
- operável para operação maior

### 14.3 Qualidade do movimento
- fraco
- razoável
- forte
- excepcional

### 14.4 Qualidade da margem
- insuficiente
- aceitável
- boa
- excelente

---

## 15. Estrutura arquitetural recomendada

### 15.1 Separação lógica
O sistema deve ser organizado em camadas:

#### A. Market Discovery Engine
Responsável por:
- varrer pares BRL
- descobrir onde o fluxo está
- detectar movimentos relevantes

#### B. Signal Evaluation Engine
Responsável por:
- filtros
- cálculo de scores
- classificação do tipo de oportunidade
- leitura de livro
- margem operacional
- executabilidade

#### C. Projection / Delivery Layer
Responsável por:
- dashboard
- APIs
- alertas
- shortlist
- histórico

### 15.2 Princípio técnico
Separar claramente:
- evento bruto
- sinal avaliado
- sinal publicado
- outcome posterior

---

## 16. Modelo de dados recomendado

### 16.1 Entidades mínimas

#### raw_market_events
Representa a observação bruta do mercado.

Campos sugeridos:
- exchange
- pair
- timestamp
- price
- volume_24h
- spread_pct
- best_bid
- best_ask
- book_snapshot
- volatility_snapshot

#### evaluated_signals
Representa o sinal já avaliado.

Campos sugeridos:
- raw_event_id
- movement_strength_score
- execution_score
- trade_margin_score
- operational_score
- movement_type
- opportunity_type
- operability_level
- book_entry_zone
- book_exit_zone
- estimated_trade_margin_pct
- estimated_slippage_pct
- risk_of_being_trapped
- duration_signal_state

#### published_opportunities
Representa o sinal publicado no sistema.

Campos sugeridos:
- evaluated_signal_id
- exchange
- pair
- rank_position
- alert_sent
- dashboard_visible
- summary_payload

#### signal_outcomes
Representa o que aconteceu depois.

Campos sugeridos:
- signal_id
- return_5m
- return_15m
- return_1h
- return_4h
- movement_persisted
- volume_persisted
- signal_quality_label

---

## 17. Requisitos de analytics

O sistema deve permitir analisar:

- quais pares BRL geram mais oportunidades úteis
- quais sinais performam melhor
- quais tipos de movimento se sustentam mais
- quais oportunidades de trade entregam melhor margem
- quais oportunidades de hold têm mais continuidade
- quais sinais eram bonitos, mas não operáveis
- quais faixas de score realmente funcionam

---

## 18. Requisitos do painel

O painel deve ter pelo menos os seguintes blocos:

### 18.1 Mercado BRL em destaque
Mostrar os pares BRL mais fortes e operáveis do momento.

### 18.2 Oportunidades de trade
Mostrar ativos com:
- oscilação útil
- liquidez
- margem favorável

### 18.3 Oportunidades de hold
Mostrar ativos com:
- força
- volume
- continuidade

### 18.4 Ativos a evitar
Mostrar ativos com:
- alta sem liquidez
- baixa executabilidade
- risco de aprisionamento

### 18.5 Shortlist operacional
Lista pequena de ativos mais relevantes do momento.

---

## 19. Requisitos dos alertas

Os alertas devem ser objetivos e úteis.

Cada alerta deve, no mínimo, conter:
- ativo/par
- exchange
- tipo da oportunidade: trade ou hold
- score operacional
- volatilidade
- volume
- liquidez
- margem estimada
- risco de saída
- leitura resumida do motivo

A frequência deve ser baixa e útil.

O sistema deve priorizar qualidade de alerta, não quantidade.

---

## 20. Requisitos de detecção de movimento atípico

Movimento atípico não deve ser definido apenas como grande alta.

Deve ser entendido como:
- comportamento fora do padrão recente da própria moeda
- acompanhado de liquidez suficiente
- acompanhado de volume útil
- acompanhado de possibilidade real de operação

O sistema deve medir:
- aumento anormal de volume
- aumento anormal de volatilidade
- repetição de oscilações
- mudança de ritmo
- persistência do movimento
- duração útil

---

## 21. Critérios de descarte

Ativos devem ser rebaixados ou descartados quando houver:
- volatilidade sem liquidez
- volume fraco
- spread ruim
- slippage excessivo
- baixa profundidade
- alta chance de aprisionamento
- ausência de margem de trade

---

## 22. Backlog obrigatório para implementação

### 22.1 P0
Implementar primeiro:

- varredura de pares BRL relevantes
- score de força do movimento
- score de liquidez / executabilidade
- score de margem operacional
- score operacional final
- classificação trade vs hold
- classificação observável vs operável
- liquidez por faixa de capital
- slippage estimado
- alerta com volume, liquidez e margem

### 22.2 P1
Implementar depois:

- leitura de zonas do livro
- estimativa de entrada e saída
- duração útil do movimento
- score de repetição / continuidade
- capacidade de escala da operação
- shortlist automática do mercado BRL

### 22.3 P2
Implementar por evolução:

- personalização fina por perfil
- ranking adaptativo por outcome
- aprendizado por histórico real
- análise mais rica de microestrutura

---

## 23. Ordem recomendada de implementação

### Fase 1
- ampliar cobertura para pares BRL relevantes
- manter sistema funcional
- corrigir universo monitorado

### Fase 2
- introduzir score separado de força, executabilidade e margem
- adaptar ranking

### Fase 3
- implementar leitura prática de livro
- estimar zonas de compra/venda

### Fase 4
- melhorar alertas
- melhorar dashboard

### Fase 5
- armazenar outcome e recalibrar ranking

---

## 24. Critérios de aceitação

O sistema será considerado alinhado ao objetivo quando conseguir:

- encontrar movimentos fortes e líquidos no mercado BRL
- não deixar passar ativos relevantes por monitoramento estreito
- priorizar liquidez sobre altas ilusórias
- mostrar diferença entre ativo interessante e ativo operável
- indicar quando um ativo suporta teste pequeno, operação média ou maior
- identificar oportunidade de trade e de hold
- mostrar margem operacional suficiente
- reduzir o risco de ficar preso
- produzir alertas úteis e confiáveis

---

## 25. Instruções explícitas para o agente de codificação

O agente deve:

1. usar este documento como referência principal de implementação
2. validar a arquitetura atual contra esta especificação
3. propor a melhor forma incremental de implementar sem quebrar o sistema existente
4. priorizar P0 antes de refinamentos estruturais de longo prazo
5. manter o foco no mercado BRL
6. tratar liquidez como critério dominante
7. implementar scores separados, não um score genérico único
8. incluir leitura prática de livro e margem operacional
9. preparar o sistema para evolução futura, sem perder aderência ao caso real do usuário

---

## 26. Resumo final para implementação

O sistema deve ser implementado como:

> **um scanner do mercado BRL que descobre onde o fluxo está, identifica ativos com movimento forte ou reaproveitável, filtra por volume e liquidez, estima executabilidade, lê faixas do livro de ofertas, mede margem operacional e destaca oportunidades úteis para trade ou hold**

Esse é o comportamento esperado do produto.

---

## 27. Problema atual de egress no Supabase

### 27.1 Diagnóstico
Foi identificado um problema real de consumo excessivo de **egress/saída de dados** no Supabase.

Contexto observado:
- plano gratuito com cota de 5 GB
- uso no período acima da cota
- cached egress em 0 GB
- consumo concentrado em saída não cacheada

### 27.2 Interpretação
O problema não deve ser tratado como problema principal de storage ou tamanho do banco.

O problema é de **leitura/entrega excessiva de dados**, especialmente em fluxos sem cache.

Na prática, isso significa que o sistema está retirando dados demais do Supabase para frontend, APIs ou tempo real.

### 27.3 Hipóteses mais prováveis no sistema atual
O agente deve investigar prioritariamente:

- polling excessivo no frontend
- refetch duplicado em páginas ou componentes
- queries retornando payload grande demais
- histórico carregado sem paginação
- analytics pesados carregados automaticamente
- leitura direta demais do Supabase pelo frontend
- uso de Realtime/WebSocket com payload grande
- ausência de cache no backend ou frontend
- seleção excessiva de colunas
- múltiplas leituras repetidas das mesmas estruturas

### 27.4 Impacto
Se não for corrigido, esse problema pode:
- aumentar custo operacional rapidamente
- tornar o plano gratuito inviável
- mascarar ineficiências arquiteturais
- dificultar escalar dashboard, histórico e analytics
- criar dependência prematura de upgrade de plano antes da otimização correta

---

## 28. Requisitos obrigatórios para redução de egress

### 28.1 Regra geral
O sistema deve ser redesenhado para **minimizar saída de dados desnecessária do Supabase**.

### 28.2 Diretriz arquitetural
O frontend não deve depender de leitura intensa e repetitiva diretamente do Supabase para telas operacionais.

Sempre que possível:
- o backend deve agregar
- o backend deve resumir
- o backend deve reduzir payload
- o backend deve entregar apenas os dados necessários para a tela

### 28.3 Requisitos técnicos obrigatórios
O agente deve implementar ou revisar:

- paginação de histórico
- limitação explícita de colunas retornadas
- carregamento sob demanda para analytics pesados
- aumento de intervalo de polling onde possível
- eliminação de refetch duplicado
- cache no backend para payloads repetidos
- cache no frontend para estados estáveis
- uso de endpoints agregados para dashboard
- separação entre snapshot atual e histórico pesado
- revisão do uso de Realtime para evitar envio excessivo de dados

---

## 29. Requisitos específicos para frontend

O frontend deve ser auditado para evitar desperdício de egress.

### 29.1 O agente deve verificar
- componentes que fazem fetch ao montar
- componentes que refazem fetch ao trocar de aba
- múltiplas chamadas concorrentes para o mesmo recurso
- polling curto demais
- queries disparadas sem necessidade visível
- analytics carregados automaticamente
- histórico completo carregado sem paginação

### 29.2 Requisitos de implementação
- nenhuma tela deve carregar histórico completo por padrão
- analytics pesados só devem ser carregados sob demanda
- dashboard deve consumir endpoints resumidos
- dados detalhados devem ficar em nível drill-down
- resultados repetidos devem usar cache sempre que possível

---

## 30. Requisitos específicos para backend e APIs

### 30.1 O backend deve assumir maior papel de agregação
O backend deve deixar de atuar apenas como passagem de dados e passar a atuar como camada de otimização.

### 30.2 O agente deve implementar ou revisar
- endpoints específicos para dashboard com payload mínimo
- endpoints separados para histórico resumido e histórico detalhado
- agregações prontas para UI
- serialização enxuta
- remoção de campos desnecessários nas respostas
- políticas de cache para consultas repetidas
- proteção contra consultas amplas demais

### 30.3 Regra de desenho de endpoint
Cada endpoint deve ser pensado para responder exatamente ao que a tela precisa, e não devolver dataset genérico maior do que o necessário.

---

## 31. Estratégia recomendada para correção do problema no Supabase

### P0 — Ações imediatas
- auditar chamadas do frontend
- identificar endpoints e queries mais frequentes
- paginar histórico
- reduzir colunas retornadas
- aumentar intervalos de polling
- remover chamadas duplicadas
- desligar carregamento automático de analytics pesados

### P1 — Correções estruturais
- criar endpoints agregados de dashboard
- mover leitura pesada do frontend para o backend
- introduzir cache backend/frontend
- revisar Realtime e payload de eventos
- separar snapshot operacional de histórico analítico

### P2 — Evolução operacional
- medir consumo por rota e por tela
- introduzir telemetria de payload
- comparar custo de egress por funcionalidade
- decidir conscientemente se faz sentido subir para plano Pro após otimização

---

## 32. Instruções explícitas ao agente sobre Supabase

O agente deve tratar o problema de egress como parte do escopo oficial de implementação.

Ele deve:

1. investigar quais telas, endpoints ou queries mais geram saída de dados
2. identificar desperdícios de polling, payload e refetch
3. propor medidas de redução rápida
4. propor medidas estruturais de redução
5. adaptar frontend e backend para menor dependência de leitura bruta do Supabase
6. manter a experiência do usuário sem sacrificar usabilidade
7. documentar as mudanças feitas para reduzir egress

---

## 33. Critérios de aceitação relacionados ao Supabase

A correção será considerada adequada quando:

- o dashboard deixar de gerar leitura excessiva
- histórico estiver paginado
- analytics pesados não carregarem automaticamente
- houver redução clara de payload nas respostas
- o backend assumir papel de agregação
- o sistema reduzir substancialmente o consumo de egress
- o uso do Supabase se torne sustentável para testes e evolução do produto

---

## 34. Estratégia de monitoramento amplo com menor custo possível

### 34.1 Objetivo

O sistema deve conseguir monitorar o mercado BRL de forma ampla sem explodir custo de:

- chamadas às exchanges
- CPU/memória no backend
- persistência no banco
- egress do Supabase
- payload entregue ao frontend
- alertas desnecessários

A regra central de custo deve ser:

> **Escanear amplo, processar barato, persistir pouco e entregar apenas shortlist qualificada.**

Isso significa que o backend pode observar muitos pares BRL, mas o banco, o frontend e o Telegram só devem receber dados ricos quando houver sinal qualificado.

---

## 35. Scanner em dois estágios

### 35.1 Estágio 1 — Scan leve de mercado

O Estágio 1 deve ser barato e aplicado ao universo amplo de pares BRL.

Para todos os pares BRL relevantes, o sistema deve buscar apenas os dados mínimos necessários para triagem inicial, preferencialmente:

- preço atual
- ticker
- volume 24h
- variação 24h
- melhor compra/venda, se disponível de forma barata
- spread simples, se disponível

O objetivo é eliminar rapidamente a maioria dos pares que não têm potencial operacional.

### 35.2 Dados que não devem ser buscados para todos os pares no Estágio 1

No Estágio 1, o sistema **não deve** consultar de forma pesada para todos os pares:

- order book completo
- candles longos
- histórico extenso
- trades recentes em alta profundidade
- slippage detalhado
- análise de margem operacional detalhada

Esses dados devem ser reservados para candidatos que passaram pela triagem leve.

### 35.3 Filtros baratos de descarte

O Estágio 1 deve descartar rapidamente pares com:

- volume diário abaixo do mínimo
- variação irrelevante
- spread simples muito alto
- ausência de dados confiáveis
- par inativo
- baixa liquidez aparente
- erro recorrente de provider

### 35.4 Resultado do Estágio 1

O Estágio 1 deve produzir uma lista reduzida de candidatos.

Essa lista deve ser pequena o suficiente para permitir análise completa no Estágio 2 sem custo excessivo.

---

## 36. Estágio 2 — Análise completa apenas dos candidatos

### 36.1 Objetivo

O Estágio 2 deve rodar somente para os pares que passaram pela triagem leve.

Para esses candidatos, o sistema deve buscar e calcular:

- order book
- candles/klines
- trades recentes, quando necessário
- slippage estimado
- margem operacional
- repetição
- continuidade
- classificação trade/hold/observe/avoid
- score de força
- score de executabilidade
- score de margem
- score operacional final

### 36.2 Regra de custo

A análise cara deve ser feita apenas para:

- pares com volume suficiente
- pares com movimento relevante
- pares com liquidez mínima
- pares com chance real de virarem oportunidade

### 36.3 Critério de promoção

Um par deve ser promovido do Estágio 1 para o Estágio 2 quando passar em critérios mínimos como:

- volume 24h acima do mínimo configurado
- variação/volatilidade acima do limiar leve
- spread aceitável
- presença de dados válidos
- não estar em blacklist
- não ter falhas recentes recorrentes no provider

---

## 37. Frequência dinâmica de scan

### 37.1 Objetivo

O sistema não deve escanear todos os pares na mesma frequência.

A frequência deve variar conforme o estado operacional do par.

### 37.2 Categorias sugeridas

#### Pares frios

Pares com pouco volume, pouca variação ou baixa atividade.

Frequência sugerida:

- a cada 5 a 10 minutos

#### Pares mornos

Pares com algum volume, alguma variação ou sinais leves de atividade.

Frequência sugerida:

- a cada 1 a 2 minutos

#### Pares quentes

Pares que passaram nos filtros e podem virar oportunidade operacional.

Frequência sugerida:

- a cada 15 a 30 segundos

### 37.3 Requisito

O agente deve implementar ou propor uma estratégia incremental de frequência dinâmica, evitando que todos os pares BRL sejam analisados profundamente em todo ciclo.

---

## 38. Persistência seletiva

### 38.1 Regra principal

O sistema não deve persistir dados detalhados de todos os pares em todos os ciclos.

### 38.2 Não persistir por padrão

Evitar persistir:

- ticker de todos os pares a cada ciclo
- order book completo de todos os pares
- candles completos de todos os pares
- snapshots brutos de todo o mercado
- pares descartados com detalhe excessivo

### 38.3 Persistir apenas quando houver valor

Persistir preferencialmente:

- oportunidades qualificadas
- top candidatos do ciclo
- sinais classificados como trade/hold/observe
- outcomes de sinais relevantes
- agregados por janela
- estatísticas resumidas de descarte

### 38.4 Dados de pares descartados

Para pares descartados, se necessário, armazenar apenas:

- contadores agregados
- motivo de descarte
- último estado resumido
- amostras ocasionais para debug
- métricas agregadas por exchange

### 38.5 Camadas de persistência recomendadas

#### Nível A — Memória/cache

Para dados temporários de todos os pares.

Retenção:

- segundos a minutos

Exemplos:

- ticker atual
- volume atual
- score preliminar
- motivo de descarte

#### Nível B — Banco resumido

Para candidatos bons.

Retenção:

- dias a semanas

Exemplos:

- par
- exchange
- scores
- volume
- liquidez
- margem
- tipo de oportunidade

#### Nível C — Banco detalhado

Somente para sinais realmente relevantes.

Retenção:

- maior

Exemplos:

- book snapshot resumido
- cálculo de slippage
- outcome posterior
- histórico de performance

---

## 39. Entrega seletiva para frontend e Telegram

### 39.1 Regra

O sistema deve ser amplo no backend e seletivo na entrega.

O frontend e o Telegram não devem receber dataset bruto do mercado inteiro.

### 39.2 Frontend

O frontend deve receber:

- shortlist operacional
- top oportunidades
- resumo do mercado BRL
- sinais ativos qualificados
- detalhes apenas sob demanda

Evitar:

- listas completas sem necessidade
- histórico completo
- order book bruto de todos os pares
- analytics automáticos pesados
- payloads grandes em polling

### 39.3 Telegram

O Telegram deve receber apenas:

- oportunidades de alta utilidade
- sinais classificados como trade ou hold relevantes
- no máximo alertas realmente úteis
- resumos compactos quando fizer sentido

O sistema deve evitar alertas de todo sinal `observe`.

### 39.4 Regra operacional

> **Monitorar amplo, entregar seletivo.**

---

## 40. Cache obrigatório

### 40.1 Objetivo

Reduzir chamadas repetidas, CPU, tempo de ciclo, consultas ao banco e egress.

### 40.2 Itens que devem ser cacheados

- catálogo de pares por exchange
- status de disponibilidade de pares
- ticker recente
- métricas preliminares por par
- dashboard summary
- analytics agregados
- resultados de filtros leves
- erros recentes de provider

### 40.3 TTL sugerido

- catálogo de pares: 1h a 6h
- pares frios: 5min
- pares mornos: 1min
- pares quentes: 15s a 30s
- analytics: 5min a 15min
- erros de provider/par: cooldown curto para evitar repetir falhas

---

## 41. Endpoints recomendados para baixo egress

### 41.1 O frontend deve consumir endpoints resumidos

Exemplos:

- `/dashboard/summary`
- `/market/brl/top`
- `/market/brl/summary`
- `/opportunities/active`
- `/opportunities/shortlist`
- `/history/summary`
- `/opportunities/{id}`

### 41.2 Regra

Cada endpoint deve retornar apenas os dados necessários para a tela.

### 41.3 Detalhes sob demanda

Dados pesados, como book detalhado, analytics longos e histórico profundo, devem ser carregados somente quando o usuário pedir explicitamente.

---

## 42. Regras técnicas de menor custo para o agente

O agente deve seguir estas regras:

1. Não consultar order book e klines de todos os pares em todo ciclo.
2. Fazer triagem barata antes de análise completa.
3. Calcular margem operacional e slippage somente para candidatos.
4. Não persistir pares descartados em detalhe.
5. Entregar shortlist ao frontend, não dataset bruto.
6. Manter histórico sempre paginado.
7. Carregar analytics sob demanda.
8. Enviar alertas seletivos.
9. Cachear catálogo de pares e resultados repetidos.
10. Implementar frequência dinâmica ou propor plano incremental para isso.
11. Reduzir consultas diretas ao Supabase pelo frontend.
12. Evitar Realtime com payload grande.

---

## 43. Investigação obrigatória: NovaDAX não retornando moedas

### 43.1 Problema observado

Foi observado que a NovaDAX pode não estar retornando corretamente as moedas/pares esperados no sistema.

O agente deve investigar esse problema como prioridade, pois ele pode comprometer a descoberta ampla do mercado BRL.

### 43.2 Objetivo da investigação

Determinar se o problema está em:

- endpoint incorreto
- parsing incorreto da resposta
- diferença de nomenclatura de símbolos
- cache desatualizado
- filtro interno removendo pares válidos
- erro silencioso no provider
- falha de autenticação, rate limit ou bloqueio
- inconsistência entre catálogo da exchange e pares usados pelo scanner
- falha de normalização entre formatos como `SOL_BRL`, `SOLBRL`, `SOL/BRL`

### 43.3 Verificações obrigatórias

O agente deve verificar:

- qual endpoint da NovaDAX está sendo usado para listar símbolos/pares
- se a resposta bruta da NovaDAX contém os pares esperados
- se o parser está extraindo corretamente base/quote
- se pares BRL estão sendo filtrados por engano
- se há cache persistindo uma lista vazia ou incompleta
- se existe diferença entre pares ativos, pausados, listados e negociáveis
- se o scanner está tentando consultar símbolos no formato aceito pelo provider
- se há logs claros quando o catálogo volta vazio
- se há fallback quando a listagem dinâmica falha

### 43.4 Logs obrigatórios

Adicionar logs estruturados para:

- quantidade de pares retornados pela NovaDAX
- quantidade de pares BRL filtrados
- exemplos dos primeiros pares retornados
- pares descartados e motivo
- erros de parsing
- erros HTTP
- status do cache do catálogo

### 43.5 Critério de aceitação

A correção será considerada adequada quando:

- a NovaDAX retornar lista válida de pares
- pares BRL existentes aparecerem no catálogo interno
- o scanner conseguir avaliar pares BRL da NovaDAX
- falhas de catálogo forem visíveis em logs
- o sistema não falhar silenciosamente quando a NovaDAX não retornar dados

---

## 44. Investigação obrigatória: pares existentes não encontrados nas exchanges

### 44.1 Problema observado

Foi observado que algumas moedas/pares parecem existir nas exchanges, mas o sistema não os encontra ou não os disponibiliza para monitoramento.

### 44.2 Objetivo da investigação

O agente deve investigar por que pares existentes não aparecem no sistema.

Possíveis causas:

- símbolo está em formato diferente do esperado
- par existe visualmente na interface da exchange, mas não está disponível na API pública usada
- par está listado, mas sem negociação ativa
- par usa outro quote além de BRL
- par está com status pausado, suspenso ou somente para conversão
- provider não implementa endpoint de catálogo completo
- catálogo está hardcoded ou incompleto
- cache está desatualizado
- filtro BRL está rígido demais
- normalização está descartando pares válidos
- o par existe em uma exchange, mas não em outra
- a exchange usa nomes comerciais diferentes do símbolo de API

### 44.3 Requisitos de normalização de símbolos

O sistema deve normalizar símbolos entre formatos diferentes.

Exemplos:

- `SOL_BRL`
- `SOLBRL`
- `SOL/BRL`
- `sol-brl`
- `WBTC_BRL`
- `WBTCBRL`

A normalização deve preservar:

- símbolo original da exchange
- símbolo normalizado interno
- base asset
- quote asset
- exchange

### 44.4 Modelo recomendado para catálogo de pares

Criar ou revisar estrutura de catálogo com campos como:

- `exchange`
- `raw_symbol`
- `normalized_symbol`
- `base_asset`
- `quote_asset`
- `is_brl_pair`
- `is_active`
- `is_tradable`
- `source`
- `last_seen_at`
- `last_checked_at`
- `status`
- `error_message`

### 44.5 Requisitos de UI

O frontend deve ajudar a diagnosticar problemas de pares.

Deve ser possível ver:

- pares disponíveis por exchange
- pares BRL detectados
- pares ativos/inativos
- data da última atualização do catálogo
- botão para refresh forçado
- mensagem quando um par buscado não for encontrado
- motivo provável para ausência do par

### 44.6 Fallbacks

Se a listagem dinâmica falhar, o sistema deve ter fallback seguro:

- usar último catálogo válido em cache
- permitir adição manual de par
- marcar par manual como pendente de validação
- testar endpoint do par individualmente
- exibir erro claro se o par não for consultável

### 44.7 Critério de aceitação

A correção será considerada adequada quando:

- pares existentes nas exchanges forem encontrados ou houver motivo claro para não aparecerem
- símbolos forem normalizados corretamente
- o usuário conseguir forçar atualização do catálogo
- o sistema mostrar se o par existe, está ativo e é negociável
- não houver falha silenciosa de catálogo

---

## 45. Critérios de aceitação adicionais de custo e catálogo

O sistema estará adequado quando:

- monitorar mercado BRL amplo sem analisar tudo profundamente em todo ciclo
- usar scan leve antes de análise completa
- persistir apenas sinais qualificados e dados agregados
- reduzir egress do Supabase
- entregar apenas shortlist ao frontend e Telegram
- permitir diagnóstico claro de pares por exchange
- corrigir ou explicar por que a NovaDAX não retorna certos pares
- encontrar pares existentes ou mostrar motivo técnico para ausência
- manter custo operacional controlado mesmo com universo BRL amplo

---

## 46. Status de implementacao - Release I parcial

Implementado em 2026-05-06:

- scan leve por `ticker` antes de buscar `order_book` e `klines`
- promocao de candidatos por exchange antes da analise profunda
- descarte barato por preco invalido, volume abaixo do minimo e movimento preliminar insuficiente
- temperatura de scan em memoria entre pares `hot`, `warm` e `cold`
- cooldown exponencial em memoria para falhas recorrentes de provider/par
- telemetria agregada de triagem em `/api/health`, sem persistir descartes detalhados de todos os pares
- endpoint `GET /api/dashboard/summary` com stats e shortlist operacional em payload reduzido
- endpoints `GET /api/opportunities/active` e `GET /api/opportunities/shortlist`
- cliente frontend tipado para consumir endpoints resumidos
- dashboard principal consumindo payload resumido por padrao
- detalhe completo do sinal carregado sob demanda por `GET /api/opportunities/{id}`
- catalogo de pares com metadados de normalizacao e diagnostico por provider
- UI de configuracoes exibindo status do catalogo por exchange e status tecnico por par

Ainda pendente para completar a Release I:

- cooldown persistente de erros por provider/par
- persistencia opcional da frequencia dinamica entre pares frios, mornos e quentes
- persistencia seletiva de descartes apenas como agregados
- migracao opcional para catalogo persistido em banco caso o cache em memoria nao seja suficiente
- expandir o uso dos endpoints resumidos em outras telas, quando aplicavel

---

## 47. Refinamento de escopo: foco inicial em Mercado Bitcoin e NovaDAX

### 47.1 Decisão de produto

O escopo operacional inicial deve ser focado em:

- Mercado Bitcoin
- NovaDAX
- pares BRL
- principais moedas dessas exchanges
- oportunidades com volume, liquidez e operabilidade

A Binance deve continuar existindo como provider opcional, mas deve ficar **desativada por padrão**.

### 47.2 Justificativa

O usuário final informou que não está operando na Binance no momento e pediu para deixar apenas Mercado Bitcoin e NovaDAX como foco inicial.

Além disso, a lógica operacional observada está fortemente ligada ao mercado brasileiro, especialmente aos pares negociados em reais.

### 47.3 Requisito

O sistema deve permitir:

- habilitar/desabilitar exchanges por configuração
- deixar Mercado Bitcoin e NovaDAX habilitadas por padrão
- deixar Binance desabilitada por padrão
- permitir ativação manual da Binance pelo usuário
- exibir no painel quais exchanges estão ativas
- não permitir que falhas da Binance afetem o funcionamento das exchanges principais

### 47.4 Critério de aceitação

A configuração padrão estará correta quando:

- Mercado Bitcoin estiver ativa por padrão
- NovaDAX estiver ativa por padrão
- Binance estiver inativa por padrão
- o usuário puder ativar Binance manualmente
- o scanner não tentar consultar Binance quando ela estiver desativada
- erros de Binance não contaminarem alertas, dashboard ou health geral do produto quando a exchange estiver desativada

---

## 48. Escopo correto: principais pares BRL das exchanges nacionais

### 48.1 Diretriz

O sistema não deve se limitar a uma pequena watchlist manual.

Também não deve tentar analisar profundamente todos os pares de todas as exchanges sem critério.

A direção correta é:

> **monitorar de forma ampla e barata os principais pares BRL da Mercado Bitcoin e NovaDAX, promover candidatos com potencial e entregar apenas a shortlist operacional.**

### 48.2 O que significa "principais pares"

"Principais pares" não deve significar apenas moedas grandes tradicionais.

Deve significar pares que tenham pelo menos um dos seguintes fatores:

- volume diário mínimo
- liquidez mínima
- atividade recente
- variação relevante
- presença no ranking da exchange
- histórico recente de movimentos úteis
- disponibilidade operacional em BRL

### 48.3 Requisito

O sistema deve construir dinamicamente um universo de pares BRL relevantes por exchange.

Esse universo deve ser derivado de:

- catálogo da exchange
- pares ativos
- pares negociáveis
- volume recente
- liquidez observável
- status operacional do provider
- regras de whitelist/blacklist

### 48.4 Watchlist como prioridade, não limite

A watchlist deve continuar existindo, mas não deve limitar o universo escaneado.

Ela deve servir para:

- favoritos
- prioridade adicional
- filtros visuais
- alertas personalizados
- acompanhamento próximo

O scanner principal deve continuar olhando o mercado BRL relevante mesmo quando a watchlist for pequena.

---

## 49. Tese consolidada do produto

### 49.1 Tese única

A tese do produto deve ser congelada nesta forma para evitar dispersão:

> **Radar de oportunidades operáveis em BRL, focado inicialmente em Mercado Bitcoin e NovaDAX, que monitora os principais pares líquidos, identifica movimentos fortes ou rompimentos relevantes, filtra por volume/liquidez, avalia margem operacional no livro e alerta apenas as melhores oportunidades para trade ou hold.**

### 49.2 O que está dentro do escopo agora

Está dentro do escopo:

- Mercado Bitcoin
- NovaDAX
- pares BRL
- principais pares líquidos
- scan leve amplo
- análise profunda apenas de candidatos
- classificação trade/hold/observe/avoid
- score de força
- score de liquidez/executabilidade
- score de margem operacional
- detecção de movimento forte
- detecção de lateralização seguida de rompimento
- alertas seletivos
- dashboard com shortlist operacional

### 49.3 O que fica fora do foco imediato

Fica fora do foco imediato:

- trading automático
- execução de ordens
- Binance como fonte principal
- múltiplas exchanges globais
- machine learning avançado
- paper trading complexo
- análise excessivamente sofisticada de microestrutura
- alertas em grande quantidade
- persistência detalhada de todos os pares

Esses itens podem existir como evolução futura, mas não devem competir com o foco operacional atual.

---

## 50. Novo padrão de oportunidade: lateralização + rompimento

### 50.1 Contexto

Foi observado um exemplo real em LAB/BRL:

- o ativo ficou lateralizado por um período
- permaneceu abaixo de uma faixa de preço por algum tempo
- depois rompeu fortemente
- chegou a movimento superior a 400%

Esse tipo de evento representa uma oportunidade que o sistema deve tentar detectar ou, pelo menos, destacar cedo quando começar a se formar.

### 50.2 Definição do padrão

O padrão **lateralização + rompimento** ocorre quando:

- o ativo permanece por um período relevante em faixa estreita ou relativamente controlada
- a volatilidade fica comprimida ou lateral
- o volume começa a aumentar
- o preço rompe uma faixa anterior
- o movimento ganha aceleração
- há liquidez suficiente para operação
- o rompimento não é apenas um candle isolado sem continuidade

### 50.3 Classificação esperada

Esse padrão pode gerar dois tipos de oportunidade:

#### Continuidade / hold

Quando houver:

- rompimento forte
- volume crescente
- persistência
- tendência clara
- liquidez suficiente

#### Trade

Quando houver:

- oscilação após rompimento
- margem operacional no livro
- zonas de compra e venda aproveitáveis
- repetição de movimentos

### 50.4 Métricas sugeridas

O sistema deve considerar métricas como:

- `range_compression_score`
- `breakout_strength_score`
- `volume_expansion_score`
- `breakout_confirmation_score`
- `post_breakout_liquidity_score`
- `continuation_potential_score`

### 50.5 Requisitos de implementação

O agente deve propor e/ou implementar uma primeira versão heurística para detectar:

- ativos lateralizados em janela recente
- rompimento de faixa recente
- aumento de volume no rompimento
- aceleração de preço
- continuidade após rompimento
- liquidez mínima após rompimento

### 50.6 Critério de aceitação

O sistema estará adequado quando conseguir:

- destacar ativos que saíram de lateralização e entraram em movimento forte
- diferenciar rompimento com volume de alta isolada sem liquidez
- classificar rompimentos como possíveis oportunidades de hold ou trade
- incluir esse padrão no ranking operacional
- exibir no alerta ou dashboard o motivo do sinal quando houver rompimento relevante

---

## 51. Ajuste de ranking para movimentos fortes perdidos

### 51.1 Problema observado

O sistema pode enviar sinais medianos enquanto existem ativos com movimentos muito mais fortes e líquidos no mercado.

Isso indica que o ranking deve comparar oportunidades dentro do universo amplo da exchange, e não avaliar cada sinal de forma isolada.

### 51.2 Requisito

O ranking deve considerar concorrência entre sinais.

Se houver ativos com:

- maior força de movimento
- maior liquidez
- maior continuidade
- maior margem operacional
- melhor classificação de oportunidade

esses ativos devem superar sinais médios.

### 51.3 Regra

Sinais `trade` ou `hold` com alta força, boa liquidez e boa margem devem ter prioridade sobre sinais apenas `observe` ou sinais médios.

### 51.4 Critério de aceitação

O sistema estará adequado quando:

- sinais fracos não forem alertados se houver sinais melhores no mesmo ciclo
- o Telegram priorizar apenas a shortlist real
- o dashboard deixar claro por que um sinal foi ranqueado acima de outro
- movimentos fortes em pares BRL relevantes não forem omitidos por escopo estreito

---

## 52. Configuração padrão recomendada

### 52.1 Exchanges

Configuração padrão:

- Mercado Bitcoin: habilitada
- NovaDAX: habilitada
- Binance: desabilitada

### 52.2 Pares

Configuração padrão:

- descobrir pares BRL automaticamente
- aplicar scan leve amplo
- promover candidatos para análise completa
- permitir watchlist manual como camada adicional

### 52.3 Alertas

Configuração padrão:

- alertar apenas shortlist qualificada
- priorizar trade e hold
- evitar alertas de observe, salvo se configurado
- não alertar avoid
- baixa frequência
- alto valor informativo

### 52.4 Painel

O painel deve mostrar:

- exchanges ativas
- mercado BRL em destaque
- oportunidades de trade
- oportunidades de hold
- watchlist/favoritos
- status do catálogo
- motivo de exclusão ou ausência de pares quando aplicável

---

## 53. Requisitos técnicos adicionais para providers

### 53.1 Provider não deve bloquear o sistema

Cada provider deve ser isolado.

Falha em uma exchange não deve derrubar o scanner inteiro.

### 53.2 Binance opcional

Quando Binance estiver desativada:

- não consultar endpoints Binance
- não exibir erros Binance como erro principal
- não afetar ranking
- não afetar health geral, exceto como provider desativado

Quando Binance estiver ativada:

- exibir status próprio
- aplicar os mesmos filtros de catálogo
- tratar erros regulatórios, geográficos ou HTTP de forma isolada

### 53.3 Mercado Bitcoin e NovaDAX como núcleo

O scanner deve garantir maior confiabilidade para:

- listagem de pares
- normalização
- ticker
- order book
- candles
- status de negociação

nessas duas exchanges.

---

## 54. Backlog adicional após refinamento de escopo

### P0

- configurar Binance como desativada por padrão
- garantir Mercado Bitcoin e NovaDAX ativas por padrão
- corrigir descoberta/listagem de pares BRL da NovaDAX
- garantir descoberta/listagem de pares BRL da Mercado Bitcoin
- implementar ou validar scan leve para principais pares BRL dessas exchanges
- garantir que watchlist não limite o scanner amplo
- ajustar ranking para priorizar melhores oportunidades do ciclo
- exibir exchanges ativas/inativas no painel

### P1

- implementar detecção heurística de lateralização + rompimento
- adicionar métricas de rompimento no score de força
- exibir motivo do sinal no alerta e dashboard
- criar ranking comparativo entre pares do mesmo ciclo
- melhorar UI de catálogo e diagnóstico por exchange

### P2

- calibrar rompimentos com outcomes históricos
- sugerir automaticamente novos pares relevantes para watchlist
- habilitar Binance como módulo opcional mais robusto
- paper trading futuro para validar trade/hold antes de automação

---

## 55. Critérios de aceitação atualizados

O produto estará alinhado com a direção atual quando:

- Mercado Bitcoin e NovaDAX forem o núcleo operacional padrão
- Binance estiver disponível, mas desativada por padrão
- o scanner descobrir principais pares BRL automaticamente
- a watchlist não limitar o mercado escaneado
- o sistema detectar movimentos fortes em pares BRL relevantes
- o sistema destacar rompimentos após lateralização
- sinais medianos não abafarem oportunidades muito melhores
- o ranking priorizar liquidez, força, margem e operabilidade
- o painel mostrar claramente o estado das exchanges e do catálogo
- o usuário conseguir entender por que determinada moeda apareceu ou não apareceu

---

## 56. Status de implementação do refinamento BRL

### 56.1 Implementado em 2026-05-06

- Mercado Bitcoin e NovaDAX passaram a ser as exchanges habilitadas por padrão em `AppConfig`.
- Binance passou a ficar disponível como provider complementar, mas desativada por padrão.
- O catálogo de pares passou a aceitar escopo de `enabled_exchanges`.
- O backend deixou de consultar providers desativados durante a construção do catálogo.
- Providers desativados passam a aparecer no catálogo com status `disabled`.
- A tela de configurações passou a solicitar o catálogo conforme as exchanges habilitadas no workspace.
- O scanner amplo continua usando a configuração agregada dos workspaces e consulta Binance apenas se ela estiver habilitada nessa configuração.

### 56.2 Ainda pendente após este refinamento

- implementar heurística dedicada de lateralização + rompimento
- enriquecer o ranking comparativo entre sinais do mesmo ciclo
- exibir motivo específico de rompimento no dashboard e nos alertas
- calibrar os novos padrões com outcomes históricos
