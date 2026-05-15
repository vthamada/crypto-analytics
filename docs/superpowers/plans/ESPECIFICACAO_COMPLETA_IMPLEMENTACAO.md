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

---

## 57. Refinamento final: universo dinâmico, fase do movimento e validação operacional

### 57.1 Objetivo deste refinamento

Este bloco consolida o refinamento final de produto após os exemplos mais recentes observados com TON/BRL e LAB/BRL.

A direção final do sistema não deve ser interpretada como uma simples lista fixa de moedas ou como um ranking de maiores altas.

O sistema deve funcionar como:

> **um radar operacional em BRL que monitora dinamicamente pares relevantes, identifica estruturas de compra/venda com liquidez, detecta rompimentos e movimentos fortes no momento útil, classifica a fase do movimento e aprende com o resultado dos sinais.**

---

## 58. Universo dinâmico de pares, sem limite rígido de 20 a 30 moedas

### 58.1 Contexto

Foi mencionado que algo como 20 a 30 moedas por corretora poderia valer a pena monitorar.

Esse número deve ser tratado como **referência operacional**, não como limite rígido.

### 58.2 Regra correta

O sistema não deve limitar o scanner a exatamente 20 ou 30 moedas.

O sistema deve:

- descobrir todos os pares BRL disponíveis nas exchanges habilitadas
- aplicar filtros mínimos de relevância, volume, liquidez e atividade
- classificar os pares por prioridade dinâmica
- monitorar pares mais promissores com maior frequência
- manter pares menos promissores em observação leve
- entregar ao usuário apenas a shortlist operacional

### 58.3 Interpretação prática

O número de pares monitoráveis pode variar conforme o mercado.

Em alguns momentos, podem existir:
- 10 pares realmente relevantes
- 25 pares realmente relevantes
- 50 ou mais pares com atividade suficiente

O sistema não deve excluir uma boa oportunidade apenas porque ultrapassou um limite artificial.

### 58.4 Modelo recomendado

O sistema deve trabalhar com quatro camadas:

#### Universo bruto
Todos os pares BRL disponíveis nas exchanges habilitadas.

#### Universo elegível
Pares que passaram pelos filtros mínimos de volume, liquidez, atividade e status operacional.

#### Universo priorizado
Pares classificados como `hot`, `warm` ou `cold`.

#### Shortlist operacional
Poucos pares destacados no dashboard e/ou Telegram.

### 58.5 Critério de aceitação

O sistema estará adequado quando:

- não houver limite fixo rígido de 20 a 30 moedas
- pares bons não forem descartados por limite arbitrário
- pares frios continuarem em observação leve
- pares quentes receberem análise mais frequente e profunda
- o frontend e o Telegram continuarem recebendo apenas shortlist qualificada

---

## 59. Fase do movimento

### 59.1 Problema

Um alerta pode ser inútil se chegar tarde demais.

Dizer apenas que um ativo subiu muito não é suficiente.

O sistema precisa indicar **em qual fase do movimento** o ativo parece estar.

### 59.2 Fases que o sistema deve reconhecer

O sistema deve classificar, sempre que possível, a fase do movimento como:

- `accumulation`: acumulação/lateralização
- `early_breakout`: início de rompimento
- `continuation`: continuação do movimento
- `extended`: movimento esticado
- `distribution_or_profit_zone`: possível zona de realização
- `exhaustion`: possível esgotamento
- `neutral`: sem fase clara

### 59.3 Uso prático

A fase do movimento deve ajudar a separar:

- oportunidade começando
- oportunidade em andamento
- oportunidade possivelmente atrasada
- oportunidade para realização/venda
- movimento já esgotado

### 59.4 Exemplo prático

Um ativo que lateralizou entre R$ 6 e R$ 8 e rompeu para R$ 12 deve ser tratado de forma diferente dependendo do momento:

- perto de R$ 6 a R$ 8: possível zona de compra/acumulação
- rompendo acima da faixa: início de oportunidade
- avançando com volume: continuação
- muito esticado após forte alta: possível realização ou alerta atrasado

### 59.5 Campos sugeridos

Adicionar ou calcular campos como:

- `movement_phase`
- `phase_confidence_score`
- `phase_reason`
- `is_late_entry_risk`
- `is_profit_zone_candidate`
- `distance_from_accumulation_zone_pct`
- `distance_from_breakout_pct`

### 59.6 Critério de aceitação

O sistema estará adequado quando:

- sinais não forem tratados todos como iguais
- o alerta indicar se o movimento está no início, em continuação ou esticado
- o usuário conseguir diferenciar oportunidade de entrada de possível zona de realização
- o ranking penalizar sinais muito atrasados para entrada, quando aplicável

---

## 60. Zona operacional e faixa operacional reaproveitável

### 60.1 Contexto

Foi observado que o usuário identifica oportunidades como:

- compras repetidas em uma faixa inferior
- vendas repetidas em uma faixa superior
- margem alta entre as duas zonas
- liquidez suficiente para operar valores relevantes

Exemplo observado:

- zona de compra entre 6 e 8
- zona de venda próxima de 12
- margem alta
- liquidez suficiente
- possibilidade de operar capital relevante

### 60.2 Conceito

O sistema deve implementar o conceito de:

> **Faixa Operacional Reaproveitável**

Uma faixa operacional reaproveitável ocorre quando existe:

- zona de compra relativamente clara
- zona de venda relativamente clara
- liquidez suficiente nas duas regiões
- margem operacional atrativa
- repetição ou recorrência do movimento
- possibilidade de entrada e saída sem risco excessivo de aprisionamento

### 60.3 Requisitos

O sistema deve estimar:

- `operational_buy_zone_low`
- `operational_buy_zone_high`
- `operational_sell_zone_low`
- `operational_sell_zone_high`
- `operational_range_margin_pct`
- `range_reuse_count`
- `range_reliability_score`
- `zone_liquidity_score`
- `capital_capacity_estimate_brl`

### 60.4 Capacidade de capital

O sistema deve avaliar se a oportunidade suporta diferentes tamanhos de operação.

Além das faixas já existentes, o sistema deve considerar explicitamente:

- operação pequena
- operação média
- operação maior
- operação relevante entre R$ 5.000 e R$ 10.000, quando houver liquidez suficiente

### 60.5 Classificação sugerida

A faixa operacional pode ser classificada como:

- `none`: sem faixa identificável
- `weak`: faixa fraca
- `valid_small_trade`: válida apenas para trade pequeno
- `valid_medium_trade`: válida para trade médio
- `valid_large_trade`: válida para capital maior
- `high_quality_reusable_range`: faixa de alta qualidade e reaproveitável

### 60.6 Critério de aceitação

O sistema estará adequado quando:

- conseguir apontar possível zona de compra e zona de venda
- estimar margem entre essas zonas
- indicar se o preço atual ainda está em região útil
- indicar se o movimento já está esticado
- avaliar se há liquidez para operar valores maiores
- destacar oportunidades com faixa operacional reaproveitável

---

## 61. Alertas por momento: início, confirmação e atraso

### 61.1 Problema

O mesmo ativo pode gerar diferentes tipos de alerta dependendo do momento.

Um alerta de início de rompimento tem valor diferente de um alerta enviado depois que o preço já subiu muito.

### 61.2 Tipos de alerta

O sistema deve diferenciar pelo menos estes tipos:

#### Alerta de preparação
Quando o ativo está lateralizado/acumulando com volume ou liquidez começando a melhorar.

Exemplo:
> TON/BRL está em lateralização com volume crescente. Possível preparação.

#### Alerta de início de rompimento
Quando o ativo começa a romper a faixa anterior com volume.

Exemplo:
> TON/BRL iniciou rompimento acima da zona de lateralização com aumento de volume.

#### Alerta de continuação
Quando o ativo segue forte após o rompimento e ainda há margem ou liquidez.

Exemplo:
> TON/BRL segue em continuação com volume e liquidez.

#### Alerta de movimento esticado
Quando o ativo já avançou muito e pode estar tarde para entrada.

Exemplo:
> TON/BRL teve forte avanço, mas já está distante da zona de compra. Avaliar risco de entrada atrasada.

#### Alerta de zona de realização
Quando o ativo se aproxima da zona de venda estimada ou apresenta sinais de esticamento.

Exemplo:
> TON/BRL se aproxima de zona de realização estimada.

### 61.3 Regra

O sistema deve evitar enviar alerta de compra implícita quando o movimento já estiver esticado.

A linguagem deve ser operacional e descritiva, não prescritiva.

### 61.4 Critério de aceitação

O sistema estará adequado quando:

- os alertas indicarem o momento/fase do sinal
- alertas atrasados forem rotulados como risco de entrada tardia
- alertas de rompimento inicial forem priorizados
- alertas de zona de realização forem diferenciados de alertas de entrada

---

## 62. Resultado dos sinais e simulação simples pós-sinal

### 62.1 Objetivo

O sistema deve medir se os sinais gerados teriam sido úteis depois de emitidos.

Isso ainda não é trading automático.

É uma simulação simples e operacional para validação.

### 62.2 Métricas pós-sinal

Para cada sinal relevante, o sistema deve medir:

- preço no momento do sinal
- preço após 5 minutos
- preço após 15 minutos
- preço após 1 hora
- preço após 4 horas
- preço após 24 horas
- maior preço após o sinal
- menor preço após o sinal
- volume após o sinal
- continuidade do movimento
- se houve rompimento confirmado
- se o sinal ficou atrasado
- se o sinal teria sido útil para trade
- se o sinal teria sido útil para hold

### 62.3 Campos sugeridos

Adicionar ou enriquecer `signal_outcomes` com:

- `entry_price_at_signal`
- `max_price_after_signal`
- `min_price_after_signal`
- `return_5m`
- `return_15m`
- `return_1h`
- `return_4h`
- `return_24h`
- `max_favorable_excursion_pct`
- `max_adverse_excursion_pct`
- `volume_after_signal`
- `movement_continued`
- `breakout_confirmed`
- `late_signal_detected`
- `outcome_label`

### 62.4 Labels de outcome

Classificações sugeridas:

- `excellent`
- `good`
- `neutral`
- `late`
- `false_positive`
- `illiquid`
- `failed_breakout`

### 62.5 Critério de aceitação

O sistema estará adequado quando:

- cada sinal relevante puder ser avaliado depois
- o usuário conseguir ver se o alerta foi útil ou atrasado
- o sistema puder calibrar ranking com base em dados reais
- a validação acontecer sem executar trades reais

---

## 63. Feedback manual do usuário

### 63.1 Objetivo

O conhecimento operacional do usuário deve virar dado.

O sistema deve permitir que o usuário marque a qualidade de cada oportunidade.

### 63.2 Feedbacks sugeridos

Para cada sinal/oportunidade, permitir marcar:

- útil
- fraca
- atrasada
- sem liquidez
- boa para trade
- boa para hold
- ignorar
- falso positivo
- boa margem
- margem insuficiente
- risco de ficar preso

### 63.3 Campos sugeridos

Criar ou enriquecer estrutura como `signal_feedback` com:

- `signal_id`
- `user_id`
- `workspace_id`
- `feedback_label`
- `feedback_note`
- `created_at`

### 63.4 Uso do feedback

O feedback deve ser usado para:

- calibrar pesos de score
- identificar falsos positivos recorrentes
- ajustar sensibilidade dos alertas
- entender preferências reais do operador
- melhorar ranking futuro

### 63.5 Critério de aceitação

O sistema estará adequado quando:

- o usuário conseguir marcar rapidamente a qualidade de um sinal
- o feedback aparecer em analytics
- os feedbacks puderem ser exportados ou usados para calibração futura
- o fluxo não atrapalhar o uso operacional

---

## 64. Diagnóstico reforçado da NovaDAX e das exchanges nacionais

### 64.1 Prioridade

A NovaDAX é parte do núcleo operacional do produto.

Se a NovaDAX não retornar moedas, pares ou dados corretamente, o sistema não atende ao escopo atual.

### 64.2 Requisito reforçado

O sistema deve ter uma tela ou seção clara de diagnóstico por exchange mostrando:

- exchange ativa ou inativa
- provider habilitado ou desabilitado
- último refresh do catálogo
- quantidade total de pares retornados
- quantidade de pares BRL retornados
- quantidade de pares ativos
- quantidade de pares negociáveis
- exemplos de símbolos retornados
- erros HTTP recentes
- erros de parsing
- status do cache
- motivo de ausência de pares esperados

### 64.3 Teste individual de par

O sistema deve permitir testar um par específico.

Exemplo:
- usuário procura `TON/BRL`
- sistema verifica se existe na exchange
- sistema mostra símbolo bruto da API
- sistema mostra símbolo normalizado
- sistema mostra se está ativo
- sistema mostra se ticker/order book/candles funcionam

### 64.4 Critério de aceitação

A correção será considerada adequada quando:

- falha da NovaDAX não for silenciosa
- o usuário conseguir entender por que não está recebendo dados da NovaDAX
- pares existentes puderem ser diagnosticados individualmente
- o catálogo puder ser atualizado manualmente
- o sistema usar último catálogo válido quando a API falhar temporariamente

---

## 65. Ranking comparativo por ciclo

### 65.1 Problema

O sistema não deve avaliar cada sinal isoladamente.

Se existirem 10 sinais no mesmo ciclo, ele precisa selecionar os melhores.

### 65.2 Requisito

Cada ciclo de scanner deve produzir uma visão comparativa.

O ranking deve considerar:

- score operacional final
- fase do movimento
- liquidez
- margem operacional
- força do rompimento
- risco de alerta atrasado
- qualidade da faixa operacional
- feedbacks anteriores
- outcomes históricos daquele tipo de sinal

### 65.3 Regra de entrega

O Telegram deve receber apenas os melhores sinais do ciclo, e não todos os sinais que passaram em algum threshold mínimo.

### 65.4 Critério de aceitação

O sistema estará adequado quando:

- oportunidades fortes não forem abafadas por sinais medianos
- alertas forem enviados com base no ranking global do ciclo
- o dashboard mostrar a shortlist ordenada por qualidade operacional
- sinais fracos ficarem visíveis apenas se o usuário quiser investigar

---

## 66. Backlog final consolidado

### 66.1 P0 — Núcleo operacional imediato

Implementar ou garantir:

- Mercado Bitcoin e NovaDAX habilitadas por padrão
- Binance desativada por padrão, mas ativável
- descoberta dinâmica de pares BRL
- ausência de limite rígido de 20 a 30 pares
- scan leve amplo
- análise profunda somente de candidatos
- correção/diagnóstico da NovaDAX
- catálogo com status técnico por exchange e por par
- shortlist operacional no dashboard
- alertas seletivos no Telegram
- ranking comparativo por ciclo
- identificação básica da fase do movimento
- marcação de alerta atrasado
- histórico paginado e payload reduzido
- redução contínua de egress do Supabase

### 66.2 P1 — Qualidade operacional

Implementar:

- detecção heurística de lateralização + rompimento
- zona operacional de compra/venda
- faixa operacional reaproveitável
- score de rompimento
- score de fase do movimento
- score de faixa operacional
- simulação simples pós-sinal
- feedback manual do usuário
- dashboard com motivo do sinal
- alertas com fase e risco de entrada tardia

### 66.3 P2 — Aprendizado e evolução

Implementar posteriormente:

- calibração por outcomes reais
- ranking adaptativo por feedback
- paper trading simples
- relatórios de sinais úteis vs falsos positivos
- sugestão automática de pares para watchlist
- ajuste automático de thresholds por exchange
- evolução opcional da Binance
- preparação futura para automação, sem execução real por enquanto

---

## 67. Critérios finais de aceitação do produto

O produto estará alinhado ao objetivo quando conseguir:

- monitorar dinamicamente o mercado BRL relevante sem limite rígido artificial
- priorizar Mercado Bitcoin e NovaDAX
- manter Binance opcional e desativada por padrão
- identificar pares com volume, liquidez e atividade suficiente
- detectar lateralização, rompimento, continuação e movimento esticado
- estimar zona de compra, zona de venda e margem operacional
- identificar faixas operacionais reaproveitáveis
- avaliar se há liquidez para capital pequeno, médio e maior
- marcar sinais atrasados ou em zona de realização
- enviar alertas seletivos e úteis
- reduzir ruído operacional
- mostrar por que um ativo apareceu ou não apareceu
- permitir feedback manual do usuário
- medir outcome pós-sinal
- reduzir egress e custo operacional
- servir como assistente operacional, não como robô automático de ordens

---

## 68. Definição final do sistema

A definição final consolidada é:

> **Um assistente operacional de oportunidades em cripto BRL, focado inicialmente em Mercado Bitcoin e NovaDAX, que monitora dinamicamente pares relevantes, identifica zonas de compra e venda, detecta lateralização, rompimento e continuação, avalia liquidez, margem e risco de atraso, entrega apenas shortlist qualificada e aprende com outcomes e feedbacks do usuário.**

Essa definição deve orientar as próximas implementações.

---

## 69. Confiabilidade do funil de sinais

### 69.1 Objetivo

O sistema deve explicar por que uma oportunidade foi detectada, promovida, ranqueada, exibida, alertada, descartada, bloqueada ou perdida por erro técnico.

A dor operacional observada é:

> **houve um movimento bom no mercado e o sistema não avisou.**

Portanto, o problema não deve ser tratado como prioridade fixa de uma moeda específica. A regra correta é:

> **Todo movimento operacionalmente relevante, em qualquer par BRL monitorável, deve deixar rastro no pipeline.**

Nenhum movimento relevante deve desaparecer sem explicação.

---

## 70. Rastreabilidade ponta a ponta

Para cada par monitorável em cada ciclo relevante, o sistema deve conseguir responder:

- o par estava no catálogo?
- a exchange estava habilitada?
- o par estava ativo e negociável?
- houve coleta de ticker, candles e/ou livro de ofertas?
- houve erro de API, timeout, cache vazio ou cache desatualizado?
- o par passou no scan leve?
- se não passou, qual foi o motivo?
- o par foi promovido para análise profunda?
- se não foi, qual foi o motivo?
- houve cálculo de score?
- houve classificação como `trade`, `hold`, `observe` ou `avoid`?
- qual foi o score operacional?
- qual foi a fase do movimento?
- qual foi a liquidez estimada?
- qual foi a margem operacional estimada?
- entrou no ranking comparativo do ciclo?
- se não entrou, por quê?
- entrou na shortlist?
- se não entrou, por quê?
- o alerta foi criado?
- o alerta foi bloqueado por threshold, cooldown, limite diário ou ranking?
- o Telegram estava habilitado?
- o Telegram enviou ou falhou?

### 70.1 Situações finais permitidas

Todo movimento relevante deve terminar em uma destas situações:

- `alerted`: alertado com sucesso
- `visible_shortlist`: visível na shortlist
- `visible_observe`: visível como oportunidade observável
- `discarded_with_reason`: descartado com motivo claro
- `blocked_with_reason`: bloqueado por regra clara
- `provider_error`: falha técnica registrada
- `insufficient_data`: dados insuficientes registrados
- `not_monitorable`: par não monitorável com motivo explícito

Nenhum par relevante deve terminar em estado implícito ou desconhecido.

---

## 71. Diagnóstico de sinal perdido

### 71.1 Conceito

O sistema deve possuir diagnóstico para investigar casos em que o usuário afirma:

> “teve movimento bom e o sistema não avisou.”

A busca deve aceitar:

- exchange
- par
- intervalo de tempo
- tipo de movimento
- status do pipeline

### 71.2 Endpoint recomendado

Criar endpoint semelhante a:

- `GET /api/diagnostics/missed-signal?exchange=...&pair=...&from=...&to=...`

Esse endpoint deve retornar uma linha do tempo do pipeline para o par no período pesquisado.

### 71.3 Conteúdo da resposta

A resposta deve conter:

- status do par no catálogo
- status da exchange
- eventos de coleta
- erros de provider
- dados de ticker, volume e liquidez disponíveis
- resultado do scan leve
- motivo de descarte, se houver
- resultado da análise profunda, se houver
- scores calculados
- ranking do ciclo
- posição na shortlist
- regras de bloqueio aplicadas
- status de alerta
- status de entrega no Telegram

### 71.4 Critério de aceitação

Deve ser possível identificar se a falha ocorreu em:

- catálogo
- provider
- coleta
- cache
- normalização
- filtro
- threshold
- análise profunda
- ranking
- cooldown
- limite de alerta
- Telegram
- configuração do workspace

---

## 72. Motivos padronizados de descarte e bloqueio

### 72.1 Motivos de descarte no scan leve

Exemplos de `scan_discard_reason`:

- `exchange_disabled`
- `pair_not_in_catalog`
- `pair_inactive`
- `pair_not_tradable`
- `not_brl_pair`
- `provider_error`
- `provider_timeout`
- `invalid_price`
- `missing_ticker`
- `missing_volume`
- `volume_below_minimum`
- `movement_below_minimum`
- `spread_too_high`
- `cache_empty`
- `cache_stale`
- `cooldown_active`
- `blacklisted_pair`

### 72.2 Motivos de não promoção para análise profunda

Exemplos de `promotion_block_reason`:

- `weak_preliminary_score`
- `insufficient_liquidity`
- `insufficient_movement`
- `insufficient_volume`
- `spread_unfavorable`
- `provider_unstable`
- `candidate_limit_lower_priority`
- `missing_required_market_data`

### 72.3 Motivos de não alerta

Exemplos de `alert_block_reason`:

- `below_alert_threshold`
- `not_in_top_shortlist`
- `lower_than_competing_signals`
- `cooldown_active`
- `daily_alert_limit_reached`
- `opportunity_type_not_alertable`
- `movement_too_late`
- `high_late_entry_risk`
- `insufficient_operational_margin`
- `telegram_disabled`
- `telegram_send_failed`
- `workspace_alerts_disabled`

### 72.4 Critério de aceitação

Todo descarte ou bloqueio relevante deve possuir:

- motivo padronizado
- timestamp
- exchange
- par
- etapa do pipeline
- dados mínimos que justificam a decisão

---

## 73. Auditoria por ciclo de scanner

### 73.1 Objetivo

Cada ciclo do scanner deve gerar um resumo auditável.

O resumo deve permitir entender:

- quantos pares foram vistos
- quantos passaram no scan leve
- quantos foram descartados
- quantos foram promovidos
- quantos viraram sinais
- quantos entraram na shortlist
- quantos geraram alerta
- quantos falharam por provider
- quais foram os principais motivos de descarte

### 73.2 Campos sugeridos

Campos sugeridos para `scanner_cycle_audit` ou estrutura equivalente:

- `cycle_id`
- `started_at`
- `finished_at`
- `duration_ms`
- `exchanges_enabled`
- `pairs_seen_count`
- `brl_pairs_seen_count`
- `pairs_scan_passed_count`
- `pairs_discarded_count`
- `pairs_promoted_count`
- `deep_analysis_count`
- `signals_created_count`
- `shortlist_count`
- `alerts_created_count`
- `alerts_sent_count`
- `provider_errors_count`
- `top_discard_reasons`
- `top_block_reasons`

### 73.3 Retenção

Para evitar aumento de custo:

- manter auditoria detalhada por curto período
- manter agregados por mais tempo
- não persistir dados brutos grandes de todos os pares
- armazenar apenas amostras úteis para debugging

---

## 74. Tratamento de movimentos em ativos de alta liquidez

### 74.1 Regra correta

O sistema não deve favorecer uma moeda específica de forma fixa.

Porém, deve tratar corretamente ativos com alta liquidez.

Movimentos menores em ativos muito líquidos podem ser operacionalmente relevantes.

### 74.2 Requisito

A lógica de thresholds deve ser sensível ao contexto.

O sistema deve considerar:

- liquidez absoluta
- volume recente
- book disponível
- capacidade de entrada e saída
- variação relativa ao próprio histórico do ativo
- movimento atípico em relação ao comportamento normal do par

### 74.3 Regra de promoção

Um par com alta liquidez e movimento atípico em relação ao próprio histórico deve ser promovido para análise profunda mesmo que a variação percentual absoluta seja menor do que em moedas pequenas.

### 74.4 Não confundir com prioridade fixa

Essa regra não significa que USDT, BTC, SOL ou qualquer outro ativo deve ser sempre alertado.

Significa apenas que:

> **o sistema deve ajustar a régua de relevância conforme liquidez e comportamento histórico do próprio ativo.**

---

## 75. Tela ou seção de auditoria operacional

### 75.1 Objetivo

O painel deve permitir entender rapidamente se o sistema está fazendo o papel dele.

### 75.2 Funcionalidades recomendadas

Criar seção de auditoria com:

- status das exchanges
- status dos catálogos
- últimos ciclos do scanner
- pares vistos por exchange
- pares descartados por motivo
- sinais gerados
- sinais bloqueados
- alertas enviados
- alertas bloqueados
- falhas de Telegram
- busca por par e período
- diagnóstico de movimento perdido

### 75.3 Perguntas que a UI deve responder

A interface deve responder:

- a NovaDAX está funcionando?
- quantos pares BRL a NovaDAX retornou?
- o par pesquisado foi monitorado?
- por que o par não apareceu?
- por que o par não alertou?
- o Telegram falhou?
- o alerta foi bloqueado por regra?
- o sinal foi considerado atrasado?
- havia sinais melhores no ciclo?

---

## 76. Atualização do backlog com auditoria do funil

### 76.1 P0 — Confiabilidade imediata

Adicionar ao P0:

- registrar motivo de descarte no scan leve
- registrar motivo de não promoção para análise profunda
- registrar motivo de não entrada na shortlist
- registrar bloqueios de alerta
- registrar status de envio Telegram
- criar endpoint de diagnóstico por par/período
- criar auditoria resumida por ciclo de scanner
- garantir que falhas de provider apareçam no painel
- impedir cache vazio como catálogo válido
- diagnosticar NovaDAX ponta a ponta

### 76.2 P1 — Auditoria operacional no painel

Adicionar ao P1:

- tela de auditoria operacional
- busca de movimento perdido por par/período
- visualização de funil por ciclo
- indicadores de falsos negativos
- agregados de motivos de descarte
- histórico de alertas bloqueados

### 76.3 P2 — Aprendizado com falsos negativos

Adicionar ao P2:

- registrar eventos que o usuário marcou como “sistema deveria ter avisado”
- comparar esses eventos com os dados do pipeline
- ajustar thresholds com base em falsos negativos
- criar relatório de oportunidades perdidas
- usar feedback para reduzir perdas futuras

---

## 77. Critério final de confiança operacional

O sistema só deve ser considerado confiável quando cumprir esta regra:

> **Se uma oportunidade boa aparecer dentro do universo monitorável, o sistema deve alertar, mostrar na shortlist, registrar como observável, descartar com motivo claro ou registrar erro técnico. Nunca deve simplesmente não acontecer nada.**

Esse critério deve ser tratado como requisito central do produto.

---

## 78. Definição final revisada

A definição final do sistema passa a ser:

> **Um assistente operacional de oportunidades em cripto BRL, focado inicialmente em Mercado Bitcoin e NovaDAX, que monitora dinamicamente pares relevantes, identifica zonas de compra e venda, detecta lateralização, rompimento e continuação, avalia liquidez, margem e risco de atraso, entrega apenas shortlist qualificada, aprende com outcomes e feedbacks do usuário e mantém auditoria ponta a ponta para explicar por que cada oportunidade foi alertada, descartada ou perdida.**

Essa definição deve orientar as próximas implementações.

---

## 79. Status de implementacao da auditoria P0

### 79.1 Implementado

- NovaDAX: `get_ticker()` passou a derivar `change_pct_24h` a partir de `open24h` quando `change24h` nao vem na API publica.
- NovaDAX: a descoberta de pares passou a normalizar `AAA_BRL`, `AAABRL`, `AAA/BRL` e payloads com `baseCurrency`/`quoteCurrency`, evitando perda de pares por variacao de formato da API.
- Catalogo: resposta vazia de provider nao substitui mais o ultimo catalogo valido; quando houver catalogo anterior, o sistema marca `stale` com erro explicito.
- Alertas: `alert_worthiness_score`, `alert_trigger_type`, `has_actionable_trigger`, `alert_state_key` e `alert_block_reason` passaram a ser campos persistidos e visiveis no detalhe da oportunidade.
- Telegram: repeticao do mesmo estado operacional para o mesmo destino/par passa a ser bloqueada como `no_state_change`, reduzindo alertas de moedas paradas na mesma fase.
- Diagnostico: `GET /api/diagnostics/funnel-quality` passa a consolidar qualidade do funil com pares vistos, candidatos, sinais, shortlist, alertas, taxas de conversao e principais motivos de descarte/bloqueio.
- Scanner: o funil passou a emitir eventos compactos para scan leve, promocao, analise profunda, ranking e alertas.
- Persistencia: foram adicionadas as tabelas `scanner_cycle_audits` e `signal_pipeline_events`.
- API: foi criado `GET /api/diagnostics/missed-signal?exchange=...&pair=...&from=...&to=...`.
- Frontend: a tela de configuracoes passou a ter uma busca de sinal perdido com janela movel, resumo por ciclo e linha do tempo do funil.
- Worker/API local: cada ciclo salva resumo auditavel com pares vistos, candidatos, analises profundas, sinais, alertas e principais motivos.
- Custo: a auditoria salva payload resumido, nao persiste candles/order book brutos e possui retencao separada para eventos e ciclos.

### 79.2 Ainda pendente

- Filtros avancados de periodo customizado na tela de auditoria; a primeira versao usa janelas moveis de 1h, 4h, 24h e 72h.
- Explicabilidade mais rica para bloqueios por workspace quando o sinal existe globalmente, mas nao entra na configuracao daquele workspace.
- Evolucao P1 de fase, lateralizacao, zonas operacionais e alertas por momento com apoio da auditoria.

### 79.3 Decisao tecnica

A auditoria deve continuar compacta. O sistema nao deve gravar todos os dados brutos de mercado por par/ciclo. Quando houver muitos pares no universo monitoravel, os agregados por ciclo continuam obrigatorios e os eventos detalhados devem priorizar candidatos, erros, descartes relevantes, pares de watchlist e alertas.

---

## 80. Separação entre oportunidade operacional e registro técnico

### 80.1 Problema observado

Foi observado que o sistema está exibindo registros como:

- movimento fraco
- variação zero ou muito pequena
- margem negativa
- classificação `avoid`
- combinações contraditórias como `Operável` junto com `Evitar` ou `Margem negativa`

Isso cria ruído para o usuário final.

A tela principal e os alertas não devem se comportar como um log de tudo que o scanner viu.

A tela principal deve responder:

> **Quais oportunidades operacionais realmente merecem atenção agora?**

Movimentos fracos, descartes e registros técnicos podem existir para auditoria, mas não devem ser tratados como oportunidades.

### 80.2 Regra principal

O sistema deve separar claramente:

- dado observado
- candidato
- sinal avaliado
- oportunidade operacional
- alerta
- descarte técnico
- evento de auditoria

A regra é:

> **Movimento fraco pode ser registrado para auditoria, mas não deve aparecer como oportunidade operacional.**

### 80.3 Definição de oportunidade operacional

Uma oportunidade operacional visível deve atender critérios mínimos de:

- força de movimento ou padrão relevante
- liquidez suficiente
- volume suficiente
- margem operacional aceitável
- fase útil do movimento
- risco aceitável de entrada tardia
- capacidade mínima de entrada e saída

Se um registro não atende esses critérios, ele não deve aparecer na lista principal de oportunidades.

---

## 81. Nova taxonomia do pipeline

### 81.1 Estados recomendados

O sistema deve usar uma taxonomia clara para evitar chamar tudo de “oportunidade”.

Estados sugeridos:

- `observed_pair`
- `discarded_observation`
- `candidate`
- `evaluated_signal`
- `operational_opportunity`
- `published_opportunity`
- `alerted_opportunity`
- `blocked_signal`
- `technical_audit_event`
- `signal_outcome`

### 81.2 Significado dos estados

#### `observed_pair`

O par foi visto pelo scanner.

Não significa oportunidade.

#### `discarded_observation`

O par foi analisado no scan leve e descartado com motivo.

Não deve aparecer para o usuário final como oportunidade.

#### `candidate`

O par passou na triagem leve e merece análise mais profunda.

Ainda não é oportunidade.

#### `evaluated_signal`

O sistema calculou scores, liquidez, margem, fase e classificação.

Pode virar oportunidade ou ser descartado.

#### `operational_opportunity`

O sinal passou nos critérios operacionais mínimos.

Pode aparecer no dashboard principal.

#### `published_opportunity`

A oportunidade foi publicada na shortlist ou em seção visível.

#### `alerted_opportunity`

A oportunidade foi enviada por Telegram.

#### `blocked_signal`

O sinal foi bloqueado por regra, ranking, cooldown, limite ou risco.

#### `technical_audit_event`

Evento técnico usado para auditoria, diagnóstico ou calibração.

#### `signal_outcome`

Resultado posterior do sinal.

### 81.3 Critério de aceitação

O sistema estará adequado quando:

- a tela principal não misturar observações fracas com oportunidades reais
- cada item tiver um estado claro no pipeline
- o histórico distinguir oportunidade publicada de observação técnica
- os nomes usados na UI não induzirem o usuário a achar que todo registro é uma oportunidade

---

## 82. Regras de visibilidade no produto

### 82.1 Tela principal

A tela principal deve exibir somente:

- `operational_opportunity`
- `published_opportunity`
- oportunidades `trade`
- oportunidades `hold`
- oportunidades `observe` somente se forem fortes e operacionalmente relevantes

A tela principal não deve exibir por padrão:

- movimento fraco
- `avoid`
- margem negativa
- baixa liquidez
- sinal atrasado sem utilidade
- variação irrelevante
- par visto sem sinal
- descarte técnico

### 82.2 Histórico

O histórico deve ser separado em abas ou filtros claros:

#### Histórico operacional

Mostra:

- oportunidades publicadas
- alertas enviados
- sinais relevantes avaliados
- outcomes

#### Auditoria técnica

Mostra:

- descartes
- bloqueios
- falhas de provider
- motivos de não alerta
- eventos de diagnóstico

### 82.3 Telegram

O Telegram deve receber apenas:

- oportunidades `trade` ou `hold` qualificadas
- alertas de rompimento/início/continuação relevantes
- alertas de zona de realização, quando fizer sentido
- resumos compactos, se configurado

O Telegram não deve enviar:

- movimento fraco
- `avoid`
- margem negativa
- baixa liquidez
- descarte técnico
- observação sem valor operacional

### 82.4 Critério de aceitação

O usuário final deve conseguir usar o dashboard e o Telegram sem ser exposto ao ruído técnico.

A auditoria deve existir, mas ficar em área própria.

---

## 83. Regras para movimentos fracos, negativos e descartes

### 83.1 Movimento fraco

Movimentos fracos devem ser tratados como:

- não acionáveis
- não alertáveis
- não visíveis na tela principal
- registráveis apenas como auditoria curta ou agregado estatístico

### 83.2 Margem negativa

Sinais com margem operacional negativa devem ser:

- excluídos da tela principal
- classificados como `avoid` ou `blocked_signal`
- registrados com motivo claro
- usados apenas para auditoria e calibração

### 83.3 Baixa liquidez

Sinais com baixa liquidez devem ser:

- descartados ou rebaixados
- impedidos de virar alerta
- registrados com motivo de baixa liquidez
- usados para calibrar filtros futuros

### 83.4 Variação irrelevante

Pares com variação irrelevante podem ser vistos no scan leve, mas não devem gerar sinal operacional.

### 83.5 Combinações contraditórias

O sistema deve impedir combinações contraditórias no dashboard principal.

Exemplos proibidos na lista principal:

- `Operável` + `Evitar`
- `Operável` + `Margem negativa`
- `Trade` + `Margem negativa`
- `Hold` + `Volume insuficiente`
- `Oportunidade` + `Movimento fraco`, salvo se houver outro padrão forte explícito e justificado

### 83.6 Critério de aceitação

O sistema estará adequado quando movimentos fracos forem tratados como descarte/auditoria, e não como oportunidade.

---

## 84. O que registrar e por quanto tempo

### 84.1 Princípio

Não mostrar não significa apagar.

O sistema precisa registrar o suficiente para:

- auditoria
- calibração
- diagnóstico de sinal perdido
- análise de falsos positivos
- análise de falsos negativos
- evolução para paper trading e automação futura

Mas não deve persistir dados irrelevantes em alto volume.

### 84.2 Camada A — Memória ou cache curto

Usar para observações fracas e descartes comuns.

Exemplos:

- par visto
- score preliminar
- motivo de descarte
- timestamp
- exchange
- volume resumido
- variação resumida

Retenção sugerida:

- minutos a poucas horas

### 84.3 Camada B — Agregados

Usar para estatísticas de descarte e saúde do scanner.

Exemplos:

- quantidade descartada por volume baixo
- quantidade descartada por margem negativa
- quantidade descartada por spread alto
- falhas de provider
- quantidade de pares vistos por exchange
- quantidade de pares promovidos

Retenção sugerida:

- dias a semanas

### 84.4 Camada C — Detalhado

Usar apenas para casos importantes.

Exemplos:

- oportunidade operacional
- alerta enviado
- sinal candidato próximo do corte
- erro técnico relevante
- movimento perdido reportado
- sinal com outcome relevante
- sinal marcado manualmente pelo usuário

Retenção sugerida:

- maior, conforme custo e necessidade analítica

### 84.5 Critério de aceitação

O sistema deve preservar explicabilidade sem transformar o banco em depósito de ruído.

---

## 85. Near misses: candidatos quase bons

### 85.1 Conceito

Além de oportunidades e descartes comuns, o sistema deve identificar `near_misses`.

Um `near_miss` é um sinal que quase virou oportunidade, mas falhou por um ou poucos critérios.

Exemplos:

- bom movimento, mas liquidez um pouco insuficiente
- boa liquidez, mas margem insuficiente
- bom rompimento, mas entrada já atrasada
- bom volume, mas spread alto
- sinal forte, mas ficou fora da shortlist por haver sinais melhores

### 85.2 Por que registrar

Near misses são importantes para:

- calibrar thresholds
- identificar oportunidades que o sistema pode estar perdendo
- entender falsos negativos
- melhorar ranking
- preparar paper trading

### 85.3 Requisitos

O sistema deve registrar `near_misses` de forma resumida, com:

- exchange
- par
- timestamp
- score preliminar
- critério que falhou
- distância para o threshold
- motivo de bloqueio
- se havia sinais melhores no ciclo

### 85.4 Visibilidade

Near misses não devem aparecer na tela principal por padrão.

Devem aparecer apenas em:

- auditoria
- analytics técnico
- diagnóstico de sinal perdido
- tela de calibragem

---

## 86. Impacto na evolução para trading automatizado

### 86.1 Princípio

A separação entre oportunidades reais, descartes e auditoria é essencial para futura automação.

Um robô de trading não pode aprender apenas com sinais bons.

Ele também precisa saber:

- o que foi ignorado
- por que foi ignorado
- o que parecia bom e falhou
- o que foi bloqueado corretamente
- o que foi perdido indevidamente
- onde houve erro técnico

### 86.2 Evitar viés de sobrevivência

Se o sistema salvar apenas oportunidades publicadas, o histórico ficará enviesado.

Isso gera risco em backtests e paper trading, pois o sistema só enxerga os sinais que sobreviveram aos filtros.

Para automação futura, é necessário manter amostras e agregados de:

- descartes
- bloqueios
- near misses
- falsos positivos
- falsos negativos
- sinais atrasados
- falhas técnicas

### 86.3 Regras de bloqueio futuras

Os registros de descartes e bloqueios serão a base para regras futuras como:

- não comprar se liquidez for baixa
- não comprar se margem líquida for negativa
- não comprar se movimento estiver esticado
- não comprar se spread estiver alto
- não comprar se a exchange estiver instável
- não comprar se o par falhou no order book
- não comprar se o sinal estiver atrasado
- não comprar se houver falha de catálogo
- não comprar se houver alta chance de aprisionamento

### 86.4 Explicabilidade obrigatória

Antes de qualquer automação real, o sistema deve explicar:

- por que entraria
- por que não entraria
- por que sairia
- por que ignorou um movimento
- por que bloqueou uma operação
- qual dado sustentou a decisão

Sem essa explicabilidade, a automação não deve avançar.

### 86.5 Paper trading

Antes de trading real automatizado, o sistema deve evoluir para paper trading.

O paper trading deve usar:

- oportunidades publicadas
- sinais bloqueados
- near misses
- outcomes
- feedback do usuário
- custos estimados
- slippage estimado
- liquidez estimada

### 86.6 Critério de aceitação para automação futura

Nenhuma automação de ordem deve ser implementada antes de existir:

- auditoria ponta a ponta
- outcome confiável
- paper trading
- regras de bloqueio
- simulação de slippage
- controle de risco
- logs explicáveis
- kill switch
- confirmação humana opcional
- limites de capital
- tratamento de erro de exchange

---

## 87. Camada futura de risco para trading automatizado

### 87.1 Objetivo

Mesmo não executando ordens agora, a arquitetura deve preparar uma futura camada de risco.

### 87.2 Componentes mínimos futuros

Quando o sistema evoluir para automação, deve existir:

- limite máximo por operação
- limite diário de perda
- limite diário de exposição
- limite por ativo
- limite por exchange
- kill switch manual
- pausa automática por falha de provider
- pausa automática por slippage anormal
- pausa automática por liquidez insuficiente
- modo somente alerta
- modo paper trading
- modo semi-automático com confirmação humana
- modo automático somente após validação

### 87.3 Relação com registros fracos e descartes

Registros de movimentos fracos, descartes e bloqueios ajudam a construir essa camada de risco.

Eles mostram quando o sistema deve **não operar**.

---

## 88. Ajustes obrigatórios na interface

### 88.1 Dashboard principal

O dashboard principal deve ser renomeado conceitualmente para mostrar oportunidades operacionais, não todos os sinais.

Deve ocultar por padrão:

- `fraco`
- `avoid`
- margem negativa
- baixa liquidez
- variação irrelevante
- dados meramente técnicos

### 88.2 Filtros recomendados

Adicionar filtros claros:

- Oportunidades
- Candidatos
- Observáveis
- Alertados
- Descartados
- Bloqueados
- Auditoria

Por padrão, selecionar apenas:

- Oportunidades
- Alertados
- Observáveis fortes, se aplicável

### 88.3 Histórico

O histórico deve diferenciar:

- histórico operacional
- histórico técnico
- auditoria
- outcomes

### 88.4 Cards e badges

Badges contraditórias devem ser evitadas.

Quando existir motivo negativo forte, o item deve sair da lista principal ou ser marcado claramente como não operacional.

Exemplo:

- em vez de `Operável` + `Evitar`
- exibir em auditoria: `Bloqueado: margem negativa`

### 88.5 Critério de aceitação

O usuário final deve ver menos ruído e mais clareza.

A equipe técnica deve continuar tendo acesso à auditoria.

---

## 89. Métricas de qualidade do produto

### 89.1 Métricas obrigatórias

O sistema deve acompanhar:

- quantidade de pares vistos
- quantidade de candidatos
- quantidade de oportunidades publicadas
- quantidade de alertas enviados
- taxa de alertas úteis
- taxa de alertas atrasados
- falsos positivos
- falsos negativos reportados
- sinais bloqueados corretamente
- motivos mais comuns de descarte
- oportunidades perdidas por falha técnica
- oportunidades perdidas por threshold
- oportunidades perdidas por ranking

### 89.2 Métricas para validar valor ao usuário

Medir:

- oportunidades úteis por dia
- alertas úteis por semana
- tempo economizado
- redução de ruído
- sinais que o usuário marcou como úteis
- sinais que o usuário marcou como fracos
- sinais em que o usuário disse “deveria ter avisado”

### 89.3 Critério de aceitação

O sistema deve evoluir com base em dados reais, não apenas em opinião pontual.

---

## 90. Regras finais para persistência, custo e UX

### 90.1 Não persistir lixo operacional

Não persistir detalhadamente todos os movimentos fracos.

### 90.2 Persistir o que explica decisão

Persistir ou agregar o suficiente para explicar:

- por que alertou
- por que não alertou
- por que descartou
- por que bloqueou
- por que falhou

### 90.3 UX limpa

A experiência do usuário deve ser:

- shortlist limpa
- poucos alertas
- motivos claros
- foco operacional
- sem poluição técnica

### 90.4 Auditoria completa

A experiência técnica deve permitir:

- investigar problemas
- calibrar thresholds
- auditar funil
- preparar automação futura

### 90.5 Regra final

> **O usuário vê oportunidades. O sistema registra decisões. A auditoria explica o caminho.**

---

## 91. Definição final expandida

A definição final expandida do sistema é:

> **Um assistente operacional de oportunidades em cripto BRL, focado inicialmente em Mercado Bitcoin e NovaDAX, que monitora dinamicamente pares relevantes, separa observações fracas de oportunidades reais, identifica zonas de compra e venda, detecta lateralização, rompimento e continuação, avalia liquidez, margem e risco de atraso, entrega apenas shortlist qualificada, registra descartes e bloqueios de forma controlada, aprende com outcomes e feedbacks, reduz ruído para o usuário e mantém auditoria suficiente para explicar decisões e preparar uma futura evolução segura para paper trading e automação.**

Essa definição deve substituir qualquer entendimento anterior de que todo movimento observado deve ser exibido como oportunidade.

---

## 92. Status de implementacao - visibilidade operacional

Implementado em 2026-05-08:

- oportunidades agora carregam `pipeline_status`, `visibility_reason` e `operationally_visible`
- dashboard, shortlist, WebSocket e Telegram usam o portao central de oportunidade operacional
- `/api/opportunities` retorna somente oportunidades operacionais por padrao e aceita `include_technical=true`
- `/api/history` e `/api/history/summary` aceitam `visibility=operational|technical|all`
- a tela de historico permite alternar entre historico operacional, auditoria tecnica e todos os registros
- registros tecnicos continuam disponiveis para calibragem, mas deixam de poluir a experiencia principal do usuario
- near misses compactos sao registrados como `event_type=near_miss` no funil para descartes proximos de threshold e candidatos bloqueados por limite de promocao
- `GET /api/diagnostics/near-misses` permite consultar near misses por periodo, exchange e par

Proximo refinamento recomendado:

- validar visualmente todas as telas com dados reais para remover combinacoes contraditorias restantes
- criar tela dedicada de auditoria operacional fora de Settings
- criar UI de calibragem de near misses e agregar metricas de qualidade do funil

---

## 93. Refinamento após feedback real: alertas úteis e spreads operacionais

### 93.1 Contexto

Após uso real do sistema, o usuário final trouxe novos feedbacks importantes:

- o sistema está enviando muitos alertas de ADA e XRP mesmo quando as moedas estão paradas
- sinais em `accumulation` / `preparation` estão indo para Telegram cedo demais
- o usuário não quer apenas movimentos direcionais
- o usuário opera spreads dentro da própria corretora
- o usuário opera spreads entre Mercado Bitcoin e NovaDAX
- o usuário quer ser avisado quando o spread começa a abrir
- o usuário quer operar mais rápido com ajuda do sistema
- o usuário considera que spreads operáveis podem ser mais comuns do que movimentos direcionais tradicionais

Esses feedbacks refinam a tese do produto.

O sistema não deve ser apenas um scanner de moedas que sobem.

O sistema deve ser um:

> **radar de operações possíveis em BRL, capaz de detectar movimentos direcionais, faixas operacionais, spreads internos de livro e spreads entre corretoras, sempre filtrando por liquidez, margem líquida, execução e risco.**

### 93.2 Regra de prevalência

Esta seção prevalece sobre qualquer interpretação anterior que trate:

- acumulação simples como alerta obrigatório
- spread alto apenas como problema
- todo score técnico alto como oportunidade de Telegram
- todo movimento observado como oportunidade operacional
- arbitragem entre exchanges como lucro garantido

---

## 94. Separação entre score operacional e score de alerta

### 94.1 Problema observado

O sistema pode atribuir score alto a ativos parados porque eles possuem:

- boa liquidez
- bom spread
- boa executabilidade
- volume razoável
- book saudável

Isso não significa que existe uma oportunidade agora.

Um ativo pode ser saudável, mas não acionável.

### 94.2 Requisito

O sistema deve separar obrigatoriamente:

#### `operational_score`

Mede se o ativo/par é operacionalmente saudável.

Considera:

- liquidez
- volume
- spread
- profundidade do book
- slippage
- executabilidade
- risco de ficar preso

#### `alert_worthiness_score`

Mede se vale interromper o usuário agora.

Considera:

- mudança recente de estado
- gatilho operacional novo
- abertura de spread
- rompimento
- volume entrando
- alteração relevante no book
- margem líquida nova ou crescente
- fase útil do movimento
- novidade em relação ao último alerta
- risco de alerta repetido
- risco de oportunidade atrasada

### 94.3 Regra

Um ativo pode ter `operational_score` alto e `alert_worthiness_score` baixo.

Nesse caso:

- pode aparecer no painel como observável
- não deve gerar Telegram
- deve registrar motivo de bloqueio do alerta

### 94.4 Campos sugeridos

Adicionar ou calcular:

- `operational_score`
- `alert_worthiness_score`
- `alert_trigger_type`
- `alert_block_reason`
- `last_alerted_phase`
- `last_alerted_at`
- `state_changed_since_last_alert`
- `has_actionable_trigger`

### 94.5 Critério de aceitação

O sistema estará adequado quando:

- ativos parados com boa liquidez não gerarem alertas repetidos
- score técnico alto não for suficiente para Telegram
- todo alerta tiver um gatilho operacional claro
- o painel puder observar ativos saudáveis sem alertar o usuário

---

## 95. Controle de ruído: acumulação e preparação não devem alertar por padrão

### 95.1 Problema observado

O usuário final relatou receber muitos alertas de ADA e XRP, mas as moedas estavam paradas.

Os alertas mostravam estados como:

- `accumulation`
- `preparation`
- possível lateralização
- ativo em preparação

Para o usuário final, isso não é suficiente para interrupção por Telegram.

### 95.2 Regra principal

`accumulation` e `preparation` não devem gerar alerta de Telegram por padrão.

Esses estados devem ser tratados como:

- observação no painel
- possível candidato para acompanhamento
- base para detecção futura de rompimento ou spread
- não como oportunidade acionável imediata

### 95.3 Quando preparação pode alertar

Preparação só pode virar alerta se houver gatilho adicional forte, como:

- aumento relevante de volume
- abertura relevante de spread interno
- abertura relevante de spread entre exchanges
- tentativa clara de rompimento
- mudança brusca no book
- saída da faixa lateral
- melhora relevante de margem operacional
- entrada em `early_breakout`
- oportunidade de spread líquido operável

### 95.4 Motivos padronizados de bloqueio

Adicionar motivos como:

- `preparation_without_trigger`
- `sideways_without_volume_expansion`
- `no_state_change`
- `repeated_same_phase_alert`
- `insufficient_alert_worthiness`
- `accumulation_only`
- `no_actionable_book_structure`
- `no_actionable_spread`

### 95.5 Cooldown por fase

Implementar cooldown por par e por fase:

- `preparation`: não alertar por padrão ou cooldown alto
- `accumulation`: não alertar por padrão ou cooldown alto
- `early_breakout`: pode alertar com cooldown menor
- `continuation`: pode alertar se ainda houver margem
- `extended`: alertar apenas como risco/realização, quando útil
- `spread_opening`: pode alertar se margem líquida e liquidez forem suficientes
- `spread_closing`: não alertar como oportunidade; registrar para auditoria

### 95.6 Critério de aceitação

O sistema estará adequado quando:

- ADA/XRP parados não gerarem alertas repetidos
- Telegram não for usado para preparação simples
- painel puder mostrar observáveis sem poluir alertas
- todo alerta explicar o gatilho real
- alertas repetidos da mesma fase forem bloqueados

---

## 96. Nova taxonomia de oportunidades operacionais

### 96.1 Necessidade

Com base no comportamento real do usuário, o sistema precisa diferenciar várias famílias de oportunidade.

Não é correto tratar tudo como `trade` ou `hold`.

### 96.2 Tipos obrigatórios

Adicionar ou consolidar os seguintes tipos:

- `directional_trade`
- `range_trade`
- `hold_continuation`
- `breakout_trade`
- `intra_exchange_spread`
- `book_scalping`
- `cross_exchange_arbitrage`
- `inventory_arbitrage`
- `transfer_arbitrage`
- `profit_zone`
- `observe_only`
- `avoid`

### 96.3 Significado

#### `directional_trade`

Movimento direcional com volume, liquidez e margem.

#### `range_trade`

Compra em zona inferior e venda em zona superior dentro de uma faixa reaproveitável.

#### `hold_continuation`

Movimento forte com possibilidade de continuidade por horas ou dias.

#### `breakout_trade`

Rompimento de lateralização ou faixa relevante.

#### `intra_exchange_spread`

Oportunidade de capturar spread dentro da própria exchange.

#### `book_scalping`

Operação curta baseada em ordens limitadas no livro da mesma corretora.

#### `cross_exchange_arbitrage`

Diferença de preço entre duas exchanges.

#### `inventory_arbitrage`

Arbitragem com saldo ou inventário pré-posicionado nas duas exchanges.

#### `transfer_arbitrage`

Arbitragem que depende de comprar em uma exchange, transferir a cripto e vender em outra.

#### `profit_zone`

Ativo em região potencial de realização/venda.

#### `observe_only`

Ativo interessante, mas sem gatilho operacional suficiente.

#### `avoid`

Ativo ou sinal que deve ser evitado.

### 96.4 Critério de aceitação

O sistema estará adequado quando:

- oportunidades direcionais não forem misturadas com arbitragem
- spread interno não for misturado com arbitragem entre exchanges
- preparação/lateralização puder ser observação sem Telegram
- cada alerta indicar claramente o tipo de oportunidade

---

## 97. Módulo de spread interno e scalping de livro

### 97.1 Contexto

O usuário final informou que trades dentro da própria corretora são muito comuns para ele.

Exemplo citado:

- USDT na NovaDAX já apresentou spreads no próprio livro
- o usuário comprou e vendeu várias vezes dentro da própria corretora
- esses trades são mais comuns para o usuário

### 97.2 Princípio

O sistema deve diferenciar:

> **spread como custo de execução imediata**

de

> **spread como oportunidade para ordem limitada**

Um spread alto pode ser ruim para uma ordem a mercado, mas pode ser oportunidade para quem opera ordens limitadas, desde que haja liquidez, margem líquida e repetição.

### 97.3 Requisito

Criar ou refinar módulo de:

- `intra_exchange_spread`
- `book_scalping`
- `internal_book_spread_opportunity`

Esse módulo deve analisar oportunidades dentro da mesma exchange.

### 97.4 O que calcular

Para cada par em cada exchange habilitada, quando promovido para análise de book, calcular:

- melhor bid
- melhor ask
- spread bruto
- spread percentual
- zonas de compra limitadas
- zonas de venda limitadas
- profundidade em BRL no lado comprador
- profundidade em BRL no lado vendedor
- quantidade disponível por nível relevante
- margem bruta entre zona de compra e zona de venda
- taxas estimadas de compra e venda
- margem líquida estimada
- risco de execução parcial
- risco de ficar preso
- estabilidade do spread
- repetição do spread
- tempo de permanência do spread
- capital suportado
- adequação para operação pequena, média ou maior

### 97.5 Campos sugeridos

Adicionar ou calcular:

- `intra_exchange_spread_pct`
- `internal_spread_gross_brl`
- `internal_spread_net_brl`
- `internal_spread_net_pct`
- `book_buy_zone_low`
- `book_buy_zone_high`
- `book_sell_zone_low`
- `book_sell_zone_high`
- `book_scalping_capacity_brl`
- `book_spread_repetition_score`
- `book_spread_stability_score`
- `limited_order_required`
- `market_order_not_recommended`
- `partial_fill_risk_score`
- `trapped_inventory_risk_score`

### 97.6 Regras

- spread sem liquidez não é oportunidade
- spread sem margem líquida não é oportunidade
- spread pontual sem repetição deve ser rebaixado
- spread operável deve indicar que requer ordem limitada
- `spread_too_high` não deve ser bloqueio absoluto universal
- `spread_too_high` deve bloquear execução a mercado, mas pode virar candidato de spread interno
- o alerta deve deixar claro quando a oportunidade é de spread interno, não de movimento direcional

### 97.7 Critério de aceitação

O sistema estará adequado quando:

- detectar oportunidades de spread interno na NovaDAX e Mercado Bitcoin
- mostrar quando a oportunidade é dentro da própria corretora
- calcular margem líquida depois de taxas
- estimar capital suportado pelo book
- evitar alertar spread bonito sem liquidez
- alertar spread interno apenas quando houver margem, liquidez e repetição suficientes

---

## 98. Módulo de arbitragem entre Mercado Bitcoin e NovaDAX

### 98.1 Contexto

O usuário final informou que faz arbitragem entre Mercado Bitcoin e NovaDAX.

Fluxo observado:

- compra cripto na Mercado Bitcoin
- transfere a cripto para a NovaDAX
- vende a cripto na NovaDAX
- transfere o dinheiro da NovaDAX de volta para a Mercado Bitcoin
- repete o ciclo quando o spread compensa

Exemplo informado:

- compra de 10 SOL na Mercado Bitcoin por aproximadamente R$ 4.609,90
- venda de 10 SOL na NovaDAX por aproximadamente R$ 4.980,00
- spread bruto aproximado de R$ 370,10

### 98.2 Requisito

Criar módulo de arbitragem cross-exchange entre:

- Mercado Bitcoin
- NovaDAX

Inicialmente focado em pares BRL comuns.

### 98.3 O que calcular

Para cada par comum entre as duas exchanges:

- preço de compra na exchange barata
- preço de venda na exchange cara
- direção da arbitragem
- spread bruto em R$
- spread percentual
- profundidade disponível para compra
- profundidade disponível para venda
- slippage estimado na compra
- slippage estimado na venda
- taxa de compra
- taxa de venda
- taxa de saque da cripto
- tempo estimado de transferência
- lucro bruto estimado
- lucro líquido estimado
- margem de segurança
- risco de execução
- risco de transferência
- risco de fechamento do spread
- capital suportado
- classificação da oportunidade

### 98.4 Campos sugeridos

Adicionar ou calcular:

- `arbitrage_pair`
- `buy_exchange`
- `sell_exchange`
- `buy_price_estimated`
- `sell_price_estimated`
- `gross_spread_brl`
- `gross_spread_pct`
- `estimated_buy_slippage_pct`
- `estimated_sell_slippage_pct`
- `estimated_trading_fees_brl`
- `estimated_withdraw_fee_brl`
- `estimated_net_profit_brl`
- `estimated_net_profit_pct`
- `transfer_time_estimate_minutes`
- `spread_decay_risk_score`
- `execution_risk_score`
- `arbitrage_capacity_brl`
- `arbitrage_mode`
- `arbitrage_confidence`

### 98.5 Classificações

`arbitrage_mode` deve aceitar:

- `inventory_arbitrage`
- `transfer_arbitrage`
- `theoretical_arbitrage`

`arbitrage_confidence` deve aceitar:

- `high`
- `medium`
- `low`
- `avoid`

### 98.6 Critério de aceitação

O sistema estará adequado quando:

- mostrar oportunidades Mercado Bitcoin ↔ NovaDAX em módulo separado
- indicar onde comprar e onde vender
- calcular spread bruto e líquido estimado
- descontar taxas e slippage
- indicar se há liquidez suficiente
- indicar risco de transferência
- não chamar spread pequeno de oportunidade
- enviar alerta apenas quando a arbitragem for materialmente relevante

---

## 99. Arbitragem com inventário versus arbitragem com transferência

### 99.1 Problema

Comprar em uma corretora, transferir a cripto e vender em outra envolve risco relevante.

A transferência é o principal risco desse tipo de arbitragem.

### 99.2 Arbitragem com inventário pré-posicionado

Mais segura.

Exemplo:

- BRL disponível na Mercado Bitcoin
- cripto disponível na NovaDAX

Nesse cenário, o usuário consegue:

- comprar na Mercado Bitcoin
- vender na NovaDAX quase ao mesmo tempo

Depois ele rebalanceia os saldos.

### 99.3 Arbitragem com transferência

Mais arriscada.

Exemplo:

- compra na Mercado Bitcoin
- transfere para NovaDAX
- vende depois

Durante a transferência:

- o preço pode mudar
- o spread pode fechar
- a rede pode atrasar
- a exchange pode atrasar crédito
- o book pode perder liquidez
- a ordem pode não executar
- taxas podem consumir margem
- o ativo pode ficar temporariamente preso

### 99.4 Regra

Arbitragem com transferência não deve ser tratada como lucro garantido.

Deve ser classificada como:

> **oportunidade estimada com risco de execução e tempo**

### 99.5 Requisito

O sistema deve diferenciar claramente:

- oportunidade executável agora com saldo pré-posicionado
- oportunidade teórica que depende de transferência
- oportunidade arriscada demais para alertar

### 99.6 Critério de aceitação

O alerta deve explicitar:

- se depende de transferência
- tempo estimado de transferência
- risco de fechamento do spread
- lucro líquido estimado
- margem de segurança
- que não é lucro garantido

---

## 100. Ciclo e fases do spread

### 100.1 Objetivo

O usuário quer aproveitar spreads desde o início.

Portanto, o sistema deve detectar não apenas quando o spread já está grande, mas quando ele começa a abrir.

### 100.2 Fases do spread

Adicionar classificação:

- `normal_spread`
- `spread_opening`
- `spread_operable`
- `spread_peak`
- `spread_closing`
- `spread_stale`
- `false_spread`
- `illiquid_spread`

### 100.3 Significado

#### `normal_spread`

Spread normal para o par/exchange, sem oportunidade.

#### `spread_opening`

Spread começou a abrir acima do padrão recente.

#### `spread_operable`

Spread tem margem líquida, liquidez e execução suficientes.

#### `spread_peak`

Spread muito alto, mas pode estar próximo de fechar ou sem liquidez.

#### `spread_closing`

Spread está reduzindo.

#### `spread_stale`

Spread parado há muito tempo sem execução ou sem liquidez.

#### `false_spread`

Diferença aparente sem book executável.

#### `illiquid_spread`

Spread alto, mas com liquidez insuficiente.

### 100.4 Requisitos

O sistema deve calcular:

- spread atual
- média recente do spread
- desvio do spread atual contra o padrão recente
- tempo de permanência do spread
- recorrência do spread
- liquidez disponível durante o spread
- margem líquida estimada
- se o spread está abrindo ou fechando

### 100.5 Alertas

Alertar preferencialmente:

- `spread_opening` com indícios fortes
- `spread_operable` com liquidez e margem
- `spread_peak` apenas se ainda houver execução viável

Não alertar:

- `normal_spread`
- `spread_stale`
- `false_spread`
- `illiquid_spread`
- `spread_closing`, salvo se for alerta informativo de encerramento configurado

---

## 101. Regras para alertas de spread

### 101.1 Princípio

Alertas de spread devem ser separados dos alertas de movimento direcional.

O usuário deve entender imediatamente:

- se é operação dentro da exchange
- se é arbitragem entre exchanges
- se depende de ordem limitada
- se depende de transferência
- se é oportunidade estimada ou executável

### 101.2 Conteúdo mínimo do alerta de spread interno

O alerta deve conter:

- par
- exchange
- tipo: spread interno / book scalping
- zona de compra
- zona de venda
- spread bruto
- margem líquida estimada
- liquidez disponível
- capital suportado
- necessidade de ordem limitada
- risco de execução parcial
- motivo do alerta

### 101.3 Conteúdo mínimo do alerta de arbitragem

O alerta deve conter:

- par
- comprar em qual exchange
- vender em qual exchange
- preço estimado de compra
- preço estimado de venda
- spread bruto
- spread líquido estimado
- liquidez dos dois lados
- capital suportado
- modo: inventário ou transferência
- risco de transferência
- tempo estimado de transferência
- motivo do alerta

### 101.4 Bloqueios de alerta de spread

Adicionar motivos:

- `spread_below_minimum`
- `net_spread_negative`
- `insufficient_book_depth`
- `spread_not_recurrent`
- `spread_stale`
- `spread_closing`
- `false_spread`
- `transfer_risk_too_high`
- `fees_consume_spread`
- `slippage_consumes_spread`
- `no_common_pair_between_exchanges`
- `deposit_withdraw_status_unknown`
- `requires_inventory_not_available`

### 101.5 Critério de aceitação

O sistema estará adequado quando:

- Telegram não confundir spread com alta de preço
- cada alerta de spread explicar exatamente a operação observada
- spreads pequenos, falsos ou sem liquidez forem bloqueados
- spreads operáveis forem priorizados

---

## 102. Ajustes nas configurações operacionais

### 102.1 Problema observado

Configurações atuais podem funcionar como cortes rígidos e bloquear oportunidades ou gerar ruído.

Pontos críticos:

- tamanho único de ordem em R$ 1.000
- slippage de saída rígido
- spread máximo como bloqueio universal
- liquidez mínima em unidades
- volatilidade mínima aplicada antes da fase correta
- pesos de score favorecendo volatilidade em detrimento de margem e liquidez
- alertas de preparação enviados sem gatilho

### 102.2 Requisitos

O sistema deve substituir cortes globais rígidos por régua contextual, considerando:

- tipo de oportunidade
- fase do movimento
- fase do spread
- tipo do ativo
- liquidez absoluta
- tamanho de operação simulado
- margem líquida
- risco de execução
- risco de transferência

### 102.3 Tamanhos simulados

O sistema deve simular múltiplos tamanhos:

- R$ 25
- R$ 300
- R$ 1.000
- R$ 5.000
- R$ 10.000

Classificar:

- bom para teste pequeno
- bom para operação média
- bom para operação maior
- insuficiente para o tamanho solicitado

### 102.4 Liquidez

Priorizar liquidez em BRL, não apenas em unidades.

Métricas principais:

- profundidade em BRL para compra
- profundidade em BRL para venda
- slippage por tamanho simulado
- capital máximo estimado
- liquidez no nível de preço relevante

### 102.5 Spread máximo

`max_spread_pct` não deve ser bloqueio universal.

Deve ser interpretado conforme contexto:

- para execução a mercado: spread alto é risco
- para ordem limitada: spread alto pode ser oportunidade
- para arbitragem: spread precisa sobreviver a taxas, slippage e risco
- para spread interno: spread precisa ter book, repetição e margem líquida

### 102.6 Critério de aceitação

O sistema estará adequado quando:

- thresholds não bloquearem boas oportunidades por regra rígida
- oportunidades forem avaliadas por contexto
- configurações mostrarem efeito esperado ao usuário
- liquidez em unidades não for usada como métrica dominante
- spread for tratado como risco ou oportunidade conforme tipo de operação

---

## 103. Ajustes obrigatórios na interface

### 103.1 Dashboard

O dashboard deve separar claramente:

- oportunidades direcionais
- faixas operacionais
- spreads internos
- arbitragem entre exchanges
- observáveis
- auditoria técnica

### 103.2 Cards principais

Adicionar ou refinar cards para:

- oportunidades operacionais
- spreads internos ativos
- arbitragem MB ↔ NovaDAX
- alertas enviados
- sinais bloqueados
- saúde da NovaDAX

### 103.3 Histórico

O histórico deve permitir filtrar por:

- direcional
- faixa
- spread interno
- arbitragem
- alerta
- bloqueado
- descartado
- auditoria

### 103.4 Detalhe da oportunidade

Cada oportunidade deve mostrar:

- tipo da oportunidade
- motivo do sinal
- gatilho do alerta
- dados usados
- liquidez
- margem bruta
- margem líquida
- riscos
- se requer ordem limitada
- se depende de transferência
- por que foi alertada ou bloqueada

### 103.5 Critério de aceitação

O usuário deve conseguir diferenciar rapidamente:

- moeda subindo
- moeda em faixa
- spread dentro da corretora
- arbitragem entre corretoras
- observação sem ação
- alerta bloqueado por falta de gatilho

---

## 104. Backlog consolidado após spreads e controle de ruído

### 104.1 P0 — Confiabilidade e ruído

Implementar primeiro:

- corrigir NovaDAX ponta a ponta
- impedir alertas repetidos de `accumulation` / `preparation` sem gatilho
- criar `alert_worthiness_score`
- separar score operacional de score de alerta
- implementar bloqueios `preparation_without_trigger`, `no_state_change` e `insufficient_alert_worthiness`
- garantir que Telegram receba apenas oportunidades acionáveis
- registrar motivo de bloqueio de alertas
- ajustar dashboard para não exibir observações fracas como oportunidades
- revisar thresholds que hoje funcionam como cortes rígidos

### 104.2 P1 — Spread interno e arbitragem

Implementar depois do P0:

- módulo de spread interno / book scalping
- módulo de arbitragem Mercado Bitcoin ↔ NovaDAX
- cálculo de spread bruto e líquido
- cálculo de margem líquida após taxas e slippage
- fase do spread
- alerta de `spread_opening` e `spread_operable`
- separação entre `inventory_arbitrage` e `transfer_arbitrage`
- exibição de risco de transferência
- dashboard separado para spreads e arbitragem

### 104.3 P2 — Validação e evolução

Implementar posteriormente:

- outcomes específicos para oportunidades de spread
- feedback manual por tipo de oportunidade
- paper trading de spread interno
- paper trading de arbitragem
- integração autenticada futura para saldos
- status de saque/depósito por exchange
- estimativa real de taxas de rede
- relatório de spreads perdidos
- calibragem de thresholds por par e exchange

---

## 105. Critérios finais de aceitação após este refinamento

O produto estará alinhado ao uso real quando conseguir:

- parar de alertar moedas paradas sem gatilho operacional
- diferenciar observação de oportunidade
- detectar movimentos direcionais úteis
- detectar lateralização seguida de rompimento
- detectar faixas operacionais reaproveitáveis
- detectar spread interno dentro da mesma corretora
- detectar arbitragem entre Mercado Bitcoin e NovaDAX
- diferenciar arbitragem com inventário de arbitragem com transferência
- mostrar risco de transferência quando aplicável
- calcular margem líquida, não apenas margem bruta
- alertar quando o spread começa a abrir
- bloquear spreads falsos ou sem liquidez
- explicar por que alertou ou bloqueou
- reduzir ruído no Telegram
- manter auditoria para investigação e calibração
- preparar evolução futura para paper trading sem automatizar ordens reais agora

---

## 106. Definição final revisada do sistema

A definição final revisada passa a ser:

> **Um assistente operacional de oportunidades em cripto BRL, focado inicialmente em Mercado Bitcoin e NovaDAX, que monitora dinamicamente pares relevantes, diferencia observação de oportunidade acionável, identifica movimentos direcionais, faixas operacionais, spreads internos de livro e spreads entre corretoras, avalia liquidez, margem líquida, execução, fase, risco de atraso e risco de transferência, entrega apenas alertas úteis, reduz ruído para o usuário, mantém auditoria ponta a ponta e prepara a base para paper trading futuro sem executar ordens automaticamente.**

Essa definição deve orientar as próximas implementações e substituir qualquer entendimento anterior de que o produto é apenas um scanner de sinais ou ranking de moedas em alta.
