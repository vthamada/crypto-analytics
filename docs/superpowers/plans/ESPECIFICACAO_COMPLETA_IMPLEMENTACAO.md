# Especificação Reestruturada — Radar de Operações Executáveis em Cripto BRL

## 0. Decisão de produto

Este documento substitui a lógica anterior de “scanner de sinais” por uma direção mais precisa:

> **O sistema deve ser um radar de operações executáveis em cripto BRL, focado inicialmente em Mercado Bitcoin e NovaDAX, que identifica situações concretas de operação com volume, liquidez, margem, entrada, saída e risco compreensível.**

A pergunta central do produto não é:

> “Qual moeda tem score técnico alto?”

A pergunta central passa a ser:

> **“Existe uma operação concreta agora ou em formação, com preço de entrada, preço de saída, liquidez, margem e risco aceitável?”**

Se o sistema não consegue explicar **qual operação seria possível**, ele não deve enviar alerta operacional.

---

## 1. Problema real a resolver

O usuário final não precisa de mais uma tela dizendo que uma moeda está “forte”, “em preparação” ou “em acumulação”.

O problema real é:

> **Encontrar oportunidades operacionais em pares BRL antes que fiquem óbvias demais, filtrando tudo que não tem volume, liquidez, margem ou possibilidade real de saída.**

O sistema deve ajudar a responder rapidamente:

- onde existe uma operação possível?
- qual é o par?
- em qual exchange?
- onde poderia comprar?
- onde poderia vender?
- qual é a margem bruta?
- qual é a margem líquida estimada?
- existe volume?
- existe liquidez?
- cabe quanto capital?
- é operação pequena, média ou maior?
- está no início, em continuação ou atrasado?
- depende de ordem limitada?
- depende de transferência?
- existe risco de ficar preso?
- vale interromper o usuário agora?

---

## 2. O que o sistema não deve ser

O sistema **não** deve ser:

- ranking de moedas em alta
- feed de sinais técnicos
- detector genérico de volatilidade
- alerta de acumulação parada
- alerta repetido do mesmo par sem mudança relevante
- lista de tudo que o scanner viu
- ferramenta que valoriza alta percentual sem liquidez
- robô automático de compra e venda
- promessa de lucro
- recomendação de investimento

---

## 3. O que o sistema deve entregar

O sistema deve entregar uma **shortlist operacional** com poucas oportunidades de alto valor.

Cada oportunidade visível deve ter uma **tese operacional explícita**.

Uma tese operacional deve conter, no mínimo:

- tipo da oportunidade
- par
- exchange
- motivo do alerta
- gatilho detectado
- preço atual
- zona provável de entrada
- zona provável de saída
- margem bruta estimada
- margem líquida estimada
- volume
- liquidez
- capacidade estimada de capital
- risco principal
- fase do movimento ou do spread
- se exige ordem limitada
- se depende de transferência
- se é apenas observação ou alerta acionável

Se esses elementos não puderem ser estimados, o item deve ser tratado como **observável**, **candidato**, **near miss** ou **auditoria**, mas não como oportunidade operacional.

---

## 4. Perfil operacional do usuário final

O usuário final:

- opera preferencialmente em **BRL**
- utiliza principalmente **Mercado Bitcoin** e **NovaDAX**
- considera Binance opcional, não prioritária
- valoriza volume e liquidez acima de percentual de alta
- evita moedas com risco de aprisionamento
- aceita começar pequeno e aumentar se houver liquidez
- observa suporte, resistência e faixa de preço
- observa livro de ofertas
- aproveita spreads dentro da própria corretora
- aproveita spreads entre corretoras quando compensam
- procura movimentos assimétricos em moedas que começam a “acordar”
- não quer receber alerta de moeda parada sem operação concreta

Referências operacionais iniciais:

- volume mínimo operacional: **R$ 3.000/dia**
- operação pequena/teste: **R$ 25 a R$ 300**
- operação média: **R$ 1.000 ou mais**
- operação maior: **R$ 5.000 a R$ 10.000**, quando houver liquidez
- slippage tolerável em ativos grandes: **3% a 5%**
- slippage tolerável em ativos menores: **5% a 10%**, apenas se a margem compensar
- abaixo de R$ 3.000/dia, o ativo não deve entrar no radar operacional principal

---

## 5. Princípios de produto

## 5.1 Operação concreta antes de alerta

Nenhum alerta deve ser enviado só porque existe score técnico alto.

O alerta só deve sair se houver uma das seguintes teses:

- faixa operacional clara
- spread interno operável
- arbitragem entre exchanges com margem líquida
- rompimento com volume e liquidez
- mudança de regime com liquidez mínima
- zona de realização relevante
- continuação com margem ainda útil

## 5.2 Painel observa; Telegram interrompe

O painel pode mostrar observações, candidatos e ativos em preparação.

O Telegram deve interromper somente quando houver uma oportunidade acionável ou um evento operacional relevante.

## 5.3 Liquidez domina o ranking

Um ativo com 3% de movimento e alta liquidez pode ser melhor do que um ativo com 100% de alta sem volume.

Moeda sem volume suficiente deve ser penalizada fortemente ou excluída do radar operacional.

## 5.4 Spread pode ser risco ou oportunidade

Spread alto não deve ser tratado automaticamente como ruim.

O sistema deve diferenciar:

- spread como custo de execução imediata
- spread como oportunidade para ordem limitada dentro da exchange
- spread como arbitragem entre exchanges
- spread falso sem liquidez
- spread teórico que não sobrevive a taxas e slippage

## 5.5 Preparação não é alerta

`accumulation` e `preparation` não devem gerar Telegram por padrão.

Esses estados só podem virar alerta se houver gatilho adicional, como:

- aumento de volume
- rompimento
- abertura de spread
- melhoria relevante de book
- mudança clara de fase
- margem operacional nova
- oportunidade de spread interno
- arbitragem relevante

---

## 6. Escopo inicial obrigatório

## 6.1 Exchanges

Configuração padrão:

- Mercado Bitcoin: habilitada
- NovaDAX: habilitada
- Binance: desabilitada

A Binance pode existir como provider opcional, mas não deve contaminar dashboard, ranking, health ou alertas quando estiver desativada.

## 6.2 Mercado

O foco inicial é:

- pares BRL
- exchanges nacionais
- liquidez em reais
- volume em reais
- livro de ofertas em reais
- oportunidades operáveis para usuário brasileiro

## 6.3 Universo de pares

O sistema não deve depender de watchlist fixa.

Deve trabalhar com quatro camadas:

1. **Universo bruto**  
   Todos os pares BRL disponíveis nas exchanges habilitadas.

2. **Universo elegível**  
   Pares com volume, liquidez, status ativo e dados confiáveis.

3. **Universo priorizado**  
   Pares classificados como `hot`, `warm` ou `cold`.

4. **Shortlist operacional**  
   Poucos pares realmente relevantes para dashboard e Telegram.

---

## 7. Tipos de oportunidade que o sistema deve reconhecer

## 7.1 `range_trade` — Faixa operacional

Oportunidade baseada em suporte, resistência e margem entre zonas.

Exemplo operacional:

- suporte entre R$ 415 e R$ 420
- resistência perto de R$ 500
- margem potencial suficiente
- liquidez para operar capital relevante

O sistema deve estimar:

- zona de compra
- zona de venda
- posição atual dentro da faixa
- margem potencial
- capital suportado
- risco de rompimento contra
- se o preço ainda está em região útil

## 7.2 `intra_exchange_spread` — Spread interno

Oportunidade dentro da própria corretora.

Exemplo:

- comprar e vender USDT/BRL dentro da NovaDAX
- aproveitar diferença entre compradores e vendedores
- usar ordens limitadas
- repetir a operação se o livro permitir

O sistema deve calcular:

- melhor bid
- melhor ask
- spread bruto
- spread líquido
- profundidade dos dois lados
- capital suportado
- repetição do spread
- estabilidade do spread
- risco de execução parcial
- risco de ficar preso

## 7.3 `book_scalping` — Scalping de livro

Variação mais curta do spread interno.

Requer:

- book com níveis aproveitáveis
- margem líquida positiva
- liquidez suficiente
- baixa chance de execução parcial ruim
- indicação clara de que exige ordem limitada

Não deve ser confundido com ordem a mercado.

## 7.4 `cross_exchange_arbitrage` — Arbitragem entre exchanges

Oportunidade baseada em diferença de preço entre Mercado Bitcoin e NovaDAX.

O sistema deve indicar:

- onde comprar
- onde vender
- spread bruto
- spread líquido
- taxa de compra
- taxa de venda
- slippage
- risco de transferência
- tempo estimado de transferência
- capital suportado
- confiança da oportunidade

## 7.5 `inventory_arbitrage` — Arbitragem com inventário

Cenário mais seguro.

Exemplo:

- BRL já disponível na exchange barata
- cripto já disponível na exchange cara
- compra e venda podem ocorrer quase simultaneamente
- transferências posteriores servem para rebalancear

Deve receber prioridade maior que arbitragem dependente de transferência.

## 7.6 `transfer_arbitrage` — Arbitragem com transferência

Cenário mais arriscado.

Exemplo:

- compra na Mercado Bitcoin
- transfere cripto para NovaDAX
- vende depois da transferência

Deve ser classificado como:

> oportunidade estimada com risco de tempo e execução

Nunca deve ser apresentada como lucro garantido.

## 7.7 `breakout_trade` — Rompimento

Ativo sai de lateralização ou faixa relevante com volume.

Requer:

- faixa anterior detectável
- rompimento de preço
- expansão de volume
- liquidez mínima
- continuidade inicial
- risco controlado de entrada tardia

## 7.8 `hold_continuation` — Continuação / hold

Ativo já iniciou movimento e pode continuar por horas ou dias.

Requer:

- volume sustentado
- liquidez suficiente
- força persistente
- distância aceitável da zona de entrada
- não estar em euforia extrema

## 7.9 `emerging_regime_change` — Mudança de regime / assimetria

Detector para casos como moeda que ficou parada por longo período e começou a acordar.

Deve procurar:

- base longa ou dormência
- aumento de volume contra o próprio histórico
- rompimento inicial
- mudança de volatilidade
- expansão em múltiplos timeframes
- liquidez mínima crescente
- ainda não totalmente esticado

Deve separar:

- emergente em observação
- operacional
- tardio
- eufórico
- evitar

## 7.10 `profit_zone` — Zona de realização

Quando o ativo está próximo de uma zona provável de venda, resistência ou esticamento.

Não deve ser comunicado como entrada.

Deve ser comunicado como:

- atenção
- possível realização
- risco de entrada tardia
- região de saída para quem já estava posicionado

## 7.11 `observe_only`

Ativo interessante, mas sem operação concreta.

Pode aparecer no painel, mas não deve ir para Telegram por padrão.

## 7.12 `avoid`

Ativo que deve ser evitado.

Motivos comuns:

- volume baixo
- liquidez baixa
- spread falso
- margem negativa
- movimento atrasado
- risco alto de aprisionamento
- book fraco
- operação sem saída clara

---

## 8. Taxonomia do funil

O sistema deve parar de chamar tudo de “sinal” ou “oportunidade”.

Estados oficiais:

1. `observed_pair`  
   Par visto pelo scanner.

2. `discarded_observation`  
   Par descartado no scan leve.

3. `candidate`  
   Par promovido para análise profunda.

4. `evaluated_signal`  
   Sinal avaliado tecnicamente.

5. `operational_thesis`  
   Tese operacional construída.

6. `operational_opportunity`  
   Oportunidade real com margem, liquidez e execução.

7. `published_opportunity`  
   Oportunidade visível no dashboard.

8. `alerted_opportunity`  
   Oportunidade enviada por Telegram.

9. `blocked_signal`  
   Sinal bloqueado por falta de gatilho, ranking, liquidez, margem ou cooldown.

10. `near_miss`  
    Quase oportunidade, útil para calibração.

11. `technical_audit_event`  
    Evento técnico de auditoria.

12. `signal_outcome`  
    Resultado posterior do sinal.

---

## 9. Regra obrigatória: tese operacional antes de publicação

Antes de aparecer como oportunidade no dashboard principal, o sistema deve tentar construir uma tese operacional.

Formato mínimo:

```text
Tipo:
Par:
Exchange:
Gatilho:
Entrada estimada:
Saída estimada:
Margem bruta:
Margem líquida:
Liquidez:
Capital suportado:
Fase:
Risco principal:
Motivo para mostrar agora:
```

Se o sistema não conseguir preencher isso minimamente, o item não deve virar oportunidade principal.

---

## 10. Scores necessários

O sistema não deve depender de score único.

## 10.1 `movement_score`

Mede força de movimento.

Considera:

- variação
- aceleração
- volatilidade
- persistência
- rompimento
- continuidade

## 10.2 `liquidity_score`

Mede possibilidade de operar.

Considera:

- volume 24h em BRL
- volume recente
- profundidade do livro
- slippage por tamanho
- capacidade de saída
- risco de aprisionamento

## 10.3 `range_score`

Mede qualidade de faixa operacional.

Considera:

- suporte
- resistência
- largura da faixa
- repetição
- confiabilidade
- posição atual dentro da faixa

## 10.4 `spread_score`

Mede oportunidade de spread interno.

Considera:

- spread bruto
- spread líquido
- profundidade
- repetição
- estabilidade
- risco de execução parcial

## 10.5 `arbitrage_score`

Mede qualidade da arbitragem entre exchanges.

Considera:

- spread bruto
- spread líquido
- liquidez dos dois lados
- slippage
- taxas
- risco de transferência
- tempo
- confiança

## 10.6 `regime_change_score`

Mede mudança de regime.

Considera:

- dormência anterior
- aumento de volume
- rompimento inicial
- expansão de volatilidade
- liquidez crescente
- estágio do movimento

## 10.7 `operational_score`

Mede se a operação é viável.

Considera:

- liquidez
- margem
- execução
- risco
- capital suportado

## 10.8 `alert_worthiness_score`

Mede se vale interromper o usuário agora.

Considera:

- novidade
- urgência
- gatilho real
- mudança desde último alerta
- qualidade da oportunidade
- ranking no ciclo
- risco de ruído

Regra:

> `operational_score` alto não basta para Telegram. É necessário `alert_worthiness_score` suficiente e gatilho acionável.

---

## 11. Regras de alerta

## 11.1 Telegram deve enviar apenas alertas acionáveis

Telegram pode alertar:

- spread interno operável
- arbitragem relevante
- rompimento com volume
- faixa operacional clara
- mudança de regime operacional
- continuação com margem ainda útil
- zona de realização, se configurado

Telegram não deve alertar por padrão:

- acumulação simples
- preparação sem gatilho
- variação irrelevante
- movimento fraco
- margem negativa
- baixa liquidez
- `avoid`
- repetição do mesmo estado
- score técnico alto sem operação concreta

## 11.2 Bloqueios obrigatórios

Motivos de bloqueio:

- `preparation_without_trigger`
- `accumulation_only`
- `no_actionable_trigger`
- `no_state_change`
- `repeated_same_phase_alert`
- `insufficient_alert_worthiness`
- `volume_below_operational_minimum`
- `insufficient_liquidity`
- `negative_net_margin`
- `spread_without_depth`
- `false_spread`
- `transfer_risk_too_high`
- `fees_consume_spread`
- `slippage_consumes_margin`
- `late_entry_risk`
- `better_opportunities_in_cycle`
- `cooldown_active`

## 11.3 Cooldown por par e por fase

O cooldown deve considerar:

- par
- exchange
- tipo de oportunidade
- fase
- último gatilho
- último alerta
- mudança de estado

Repetição do mesmo estado sem mudança deve bloquear alerta.

## 11.4 Conteúdo mínimo do alerta

Todo alerta deve conter:

- tipo da oportunidade
- par
- exchange
- motivo
- entrada/zona de compra
- saída/zona de venda
- margem bruta
- margem líquida
- volume
- liquidez
- capital suportado
- risco principal
- fase
- observação se exige ordem limitada ou transferência

---

## 12. Módulo de faixa operacional

## 12.1 Objetivo

Detectar oportunidades onde existe uma faixa clara entre suporte e resistência.

## 12.2 Entradas

- candles de múltiplos timeframes
- preço atual
- volume
- order book
- máximas/mínimas recentes
- zonas de rejeição
- recorrência de preço

## 12.3 Saídas

Campos sugeridos:

- `support_zone_low`
- `support_zone_high`
- `resistance_zone_low`
- `resistance_zone_high`
- `current_position_in_range`
- `range_margin_pct`
- `range_margin_brl`
- `estimated_net_range_margin_pct`
- `range_reliability_score`
- `range_reuse_count`
- `capital_capacity_estimate_brl`
- `is_near_support`
- `is_near_resistance`
- `is_mid_range`
- `late_entry_risk`

## 12.4 Critério de aceite

O sistema deve conseguir explicar casos como:

> “SOL/BRL está próxima de suporte em R$ 415–420, resistência estimada perto de R$ 500, margem potencial relevante e liquidez suficiente para determinado capital.”

---

## 13. Módulo de spread interno / book scalping

## 13.1 Objetivo

Detectar oportunidades dentro da mesma exchange, especialmente quando o usuário pode capturar spread com ordens limitadas.

## 13.2 Entradas

- order book
- best bid
- best ask
- níveis próximos
- volume por nível
- histórico recente de spread
- taxas estimadas
- execução recente, se disponível

## 13.3 Saídas

Campos sugeridos:

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

## 13.4 Regras

- spread sem liquidez não é oportunidade
- spread sem margem líquida não é oportunidade
- spread pontual deve ser rebaixado
- spread recorrente com book suficiente pode alertar
- alertas devem dizer que a operação exige ordem limitada

---

## 14. Módulo de arbitragem Mercado Bitcoin ↔ NovaDAX

## 14.1 Objetivo

Detectar spreads entre exchanges nacionais.

## 14.2 Entradas

- preço e book do par na Mercado Bitcoin
- preço e book do par na NovaDAX
- taxas estimadas
- slippage estimado
- status operacional de depósito/saque, quando disponível
- tempo estimado de transferência, quando disponível

## 14.3 Saídas

Campos sugeridos:

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

## 14.4 Modos

- `inventory_arbitrage`
- `transfer_arbitrage`
- `theoretical_arbitrage`

## 14.5 Regras

- arbitragem com inventário tem maior confiança
- arbitragem com transferência tem risco maior
- spread bruto não basta
- lucro líquido deve descontar taxas, slippage e margem de segurança
- dependência de transferência deve aparecer claramente no alerta
- nunca chamar de lucro garantido

---

## 15. Módulo de mudança de regime / assimetria

## 15.1 Objetivo

Detectar moedas que estavam dormentes ou lateralizadas e começam a apresentar comportamento novo.

## 15.2 Motivação

O usuário quer que a IA avise moedas como LAB/BRL antes de movimentos extremos, não depois que a alta já ficou óbvia.

## 15.3 Entradas

- candles de janelas longas e curtas
- volume histórico
- volume recente
- volatilidade histórica
- volatilidade recente
- rompimento de faixa longa
- liquidez atual
- estágio da alta

## 15.4 Saídas

Campos sugeridos:

- `dormancy_score`
- `base_duration_days`
- `volume_expansion_vs_baseline`
- `volatility_expansion_vs_baseline`
- `early_breakout_from_base`
- `regime_change_score`
- `asymmetry_score`
- `stage_label`
- `is_too_extended`
- `operational_liquidity_reached`

## 15.5 Estágios

- `dormant`
- `awakening`
- `early_expansion`
- `operational_expansion`
- `extended`
- `euphoric`
- `exhaustion`

## 15.6 Regra de liquidez

Ativo com grande alta, mas volume diário muito baixo, não deve virar oportunidade operacional.

Pode virar:

- observação emergente
- radar de assimetria
- near miss

Mas não alerta principal, salvo configuração explícita.

---

## 16. Módulo de rompimento

## 16.1 Objetivo

Detectar lateralização seguida de rompimento com volume e liquidez.

## 16.2 Campos sugeridos

- `range_compression_score`
- `breakout_strength_score`
- `volume_expansion_score`
- `breakout_confirmation_score`
- `post_breakout_liquidity_score`
- `continuation_potential_score`

## 16.3 Regra

Rompimento sem volume e sem liquidez não é oportunidade.

Rompimento já muito esticado deve ser classificado como risco de entrada tardia.

---

## 17. Liquidez e capital suportado

## 17.1 Métrica dominante

Priorizar liquidez em BRL.

Não usar unidades como métrica dominante.

O sistema deve calcular:

- volume 24h em BRL
- volume recente em BRL
- profundidade de compra em BRL
- profundidade de venda em BRL
- slippage para tamanhos simulados
- capital máximo suportado
- risco de saída

## 17.2 Tamanhos simulados

Simular pelo menos:

- R$ 25
- R$ 300
- R$ 1.000
- R$ 5.000
- R$ 10.000

Classificações:

- `not_operable`
- `small_test_only`
- `medium_trade`
- `large_trade`
- `high_capacity`

---

## 18. Controle de ruído

## 18.1 Regra

O sistema deve reduzir ruído, não aumentar.

Não devem aparecer como oportunidades principais:

- movimento fraco
- variação zero
- margem negativa
- `avoid`
- baixa liquidez
- volume abaixo do mínimo
- acumulação sem gatilho
- preparação repetida
- spread sem profundidade
- arbitragem teórica sem liquidez

## 18.2 Onde esses dados podem aparecer

Itens fracos podem existir em:

- auditoria
- diagnóstico
- agregados
- near misses
- histórico técnico
- tela de calibração

Mas não devem poluir:

- dashboard principal
- Telegram
- shortlist operacional

---

## 19. Dashboard recomendado

O dashboard deve ser reorganizado por intenção operacional.

## 19.1 Blocos principais

1. **Oportunidades acionáveis agora**
   - somente oportunidades com tese operacional completa

2. **Faixas operacionais**
   - suporte, resistência, margem e capital suportado

3. **Spreads internos**
   - oportunidades dentro da mesma exchange

4. **Arbitragem MB ↔ NovaDAX**
   - oportunidades entre exchanges

5. **Mudanças de regime**
   - ativos acordando, com estágio e liquidez

6. **Em observação**
   - preparação, acumulação e near misses

7. **Auditoria**
   - descartes, bloqueios, falhas e sinais perdidos

## 19.2 O que a tela principal não deve fazer

A tela principal não deve misturar:

- sinais técnicos fracos
- auditoria
- oportunidades reais
- observações sem ação
- alertas bloqueados

Cada item precisa ter rótulo claro.

---

## 20. Histórico

O histórico deve ser separado em:

- histórico operacional
- alertas enviados
- oportunidades publicadas
- near misses
- bloqueios
- descartes
- auditoria técnica
- outcomes

O histórico principal não deve ser uma lista única de tudo.

---

## 21. Auditoria e sinais perdidos

## 21.1 Regra

Se o usuário disser:

> “essa moeda mexeu e o sistema não avisou”

o sistema deve conseguir explicar:

- o par estava no catálogo?
- a exchange estava ativa?
- havia dados?
- foi descartado?
- por qual motivo?
- foi candidato?
- foi bloqueado?
- havia sinais melhores?
- o Telegram estava ativo?
- houve cooldown?
- o alerta falhou?

## 21.2 Endpoint recomendado

`GET /api/diagnostics/missed-signal?exchange=...&pair=...&from=...&to=...`

## 21.3 Estados finais permitidos

Todo movimento relevante deve terminar como:

- `alerted`
- `visible_shortlist`
- `visible_observe`
- `discarded_with_reason`
- `blocked_with_reason`
- `provider_error`
- `insufficient_data`
- `not_monitorable`

Nada relevante deve desaparecer sem rastro.

---

## 22. NovaDAX como requisito crítico

A NovaDAX é parte central do produto.

O sistema deve possuir diagnóstico claro para:

- catálogo
- pares BRL
- pares ativos
- pares negociáveis
- ticker
- order book
- candles
- cache
- erros HTTP
- erros de parsing
- símbolos normalizados
- símbolos brutos

Se a NovaDAX falhar, o sistema deve mostrar a falha.

Não pode haver falha silenciosa.

---

## 23. Arquitetura de baixo custo

## 23.1 Princípio

> **Escanear amplo, processar barato, persistir pouco e entregar apenas shortlist qualificada.**

## 23.2 Scan em dois estágios

### Estágio 1 — Scan leve

Para universo amplo:

- ticker
- preço
- volume
- variação
- melhor bid/ask simples, se barato
- status do par

Não buscar book completo e candles longos para tudo.

### Estágio 2 — Análise profunda

Apenas para candidatos:

- order book
- candles
- slippage
- suporte/resistência
- margem
- spread interno
- arbitragem
- mudança de regime
- tese operacional

## 23.3 Persistência seletiva

Persistir detalhado apenas para:

- oportunidades publicadas
- alertas enviados
- candidatos relevantes
- near misses importantes
- erros técnicos relevantes
- outcomes

Usar agregados para descartes comuns.

## 23.4 Supabase egress

O frontend deve consumir endpoints resumidos.

Analytics pesados devem ser sob demanda.

Histórico deve ser paginado.

---

## 24. Modelo de dados reestruturado

## 24.1 `market_observations`

Observação leve do mercado.

Campos:

- exchange
- pair
- timestamp
- price
- volume_24h_brl
- variation_pct
- best_bid
- best_ask
- simple_spread_pct
- provider_status

## 24.2 `candidate_evaluations`

Candidatos promovidos.

Campos:

- observation_id
- candidate_reason
- scan_temperature
- preliminary_score
- promotion_reason
- rejection_reason

## 24.3 `operational_theses`

Teses operacionais.

Campos:

- candidate_id
- opportunity_type
- trigger_type
- entry_zone_low
- entry_zone_high
- exit_zone_low
- exit_zone_high
- gross_margin_pct
- net_margin_pct
- liquidity_score
- capital_capacity_brl
- operational_score
- alert_worthiness_score
- risk_summary
- thesis_status

## 24.4 `published_opportunities`

Oportunidades publicadas.

Campos:

- thesis_id
- dashboard_visible
- telegram_alert_sent
- rank_position
- alert_payload
- published_at

## 24.5 `pipeline_events`

Auditoria.

Campos:

- cycle_id
- exchange
- pair
- event_type
- reason
- payload_summary
- created_at

## 24.6 `signal_outcomes`

Resultado posterior.

Campos:

- opportunity_id
- return_5m
- return_15m
- return_1h
- return_4h
- return_24h
- max_favorable_excursion_pct
- max_adverse_excursion_pct
- outcome_label

## 24.7 `signal_feedback`

Feedback manual.

Campos:

- opportunity_id
- user_id
- feedback_label
- feedback_note
- created_at

---

## 25. Backlog reestruturado

## 25.1 P0 — Fazer o sistema parar de alertar errado

Implementar primeiro:

- bloquear Telegram para `accumulation` e `preparation` sem gatilho
- criar `alert_worthiness_score`
- separar `operational_score` de alerta
- exigir `has_actionable_trigger`
- adicionar `alert_trigger_type`
- adicionar `alert_block_reason`
- aplicar volume mínimo operacional em BRL
- bloquear alertas repetidos do mesmo par/fase
- separar observável de oportunidade
- corrigir/validar NovaDAX ponta a ponta
- garantir que dashboard principal mostre somente oportunidades acionáveis
- adicionar explicação “por que alertou agora”
- adicionar explicação “por que bloqueou”
- revisar pesos e thresholds para não premiar XRP/ADA parados

## 25.2 P1 — Entregar o que o usuário realmente opera

Implementar depois do P0:

- módulo de faixa operacional
- suporte/resistência
- margem entre zonas
- capital suportado
- módulo de spread interno
- módulo de book scalping
- módulo de arbitragem MB ↔ NovaDAX
- separação `inventory_arbitrage` vs `transfer_arbitrage`
- módulo de mudança de regime
- módulo de rompimento
- fases do spread
- alertas específicos por tipo de oportunidade
- dashboard reorganizado por tipo operacional

## 25.3 P2 — Validar, aprender e preparar evolução

Implementar posteriormente:

- outcomes por tipo de oportunidade
- feedback manual
- near misses
- relatórios de falsos positivos
- relatórios de falsos negativos
- paper trading
- calibração por exchange/par
- simulação de taxas reais
- status de depósito/saque
- integração autenticada futura para saldos
- gestão de risco para eventual automação futura

---

## 26. Critérios de aceite por caso real

## 26.1 XRP/ADA parados

Se XRP ou ADA estiverem em `accumulation` ou `preparation`, mas sem gatilho novo:

Resultado esperado:

- aparece no painel como observável, se relevante
- não envia Telegram
- registra bloqueio `preparation_without_trigger` ou `no_state_change`

## 26.2 Neiro com volume diário muito baixo

Se uma moeda tiver volume de aproximadamente R$ 200/dia:

Resultado esperado:

- não entra no radar operacional
- pode aparecer em auditoria ou observação técnica
- não envia Telegram
- motivo: `volume_below_operational_minimum`

## 26.3 SOL com suporte e resistência

Se SOL estiver em faixa com suporte entre R$ 415 e R$ 420 e resistência próxima de R$ 500:

Resultado esperado:

- sistema identifica faixa operacional
- estima margem
- estima capital suportado
- mostra se está perto de suporte, meio da faixa ou perto de resistência
- alerta apenas se houver momento útil

## 26.4 LAB começando mudança de regime

Se ativo ficou lateralizado/dormente e começa expansão de volume/preço:

Resultado esperado:

- sistema classifica como `emerging_regime_change`
- mostra estágio
- exige liquidez mínima para virar oportunidade operacional
- se já estiver eufórico, marca risco de atraso

## 26.5 USDT com spread interno na NovaDAX

Se USDT apresentar spread interno com book suficiente:

Resultado esperado:

- sistema classifica como `intra_exchange_spread`
- calcula margem líquida
- informa que exige ordem limitada
- estima capital suportado
- alerta somente se spread for recorrente e líquido

## 26.6 SOL com diferença MB ↔ NovaDAX

Se SOL estiver mais barata na Mercado Bitcoin e mais cara na NovaDAX:

Resultado esperado:

- sistema classifica como arbitragem
- indica onde comprar e vender
- calcula spread bruto e líquido
- mostra risco de transferência
- diferencia inventário de transferência
- não apresenta como lucro garantido

---

## 27. Critérios finais de aceitação do produto

O sistema estará alinhado quando conseguir:

- entregar poucas oportunidades realmente acionáveis
- parar de alertar preparação sem gatilho
- detectar faixas operacionais
- detectar spreads internos
- detectar arbitragem entre MB e NovaDAX
- detectar mudanças de regime cedo o suficiente
- filtrar volume baixo
- priorizar liquidez e margem líquida
- mostrar capital suportado
- explicar cada alerta
- explicar cada bloqueio
- manter auditoria de sinais perdidos
- reduzir ruído no Telegram
- manter custo controlado
- preparar base para paper trading futuro
- continuar sem executar ordens reais

---

## 28. Frase-guia para o agente de codificação

> **Não implemente mais “sinais”. Implemente teses operacionais. Um alerta só deve existir quando houver uma operação explicável com entrada, saída, liquidez, margem, risco e motivo para agir agora.**

---

## 29. Definição final do sistema

> **Um radar operacional de cripto BRL, focado inicialmente em Mercado Bitcoin e NovaDAX, que monitora pares relevantes, identifica faixas de compra/venda, spreads internos, arbitragem entre exchanges, rompimentos e mudanças de regime, filtra por volume e liquidez, calcula margem líquida e capital suportado, entrega apenas alertas acionáveis e mantém auditoria para explicar por que alertou, bloqueou ou descartou cada oportunidade.**
