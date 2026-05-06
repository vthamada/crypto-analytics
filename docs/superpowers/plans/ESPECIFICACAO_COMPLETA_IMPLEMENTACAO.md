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

A Binance pode existir como provider complementar, mas o núcleo do produto deve refletir o comportamento do mercado BRL.

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

