# Requisitos Operacionais do Usuário

## 1. Objetivo do documento

Este documento consolida o perfil operacional do usuário final e traduz suas respostas em requisitos objetivos para o desenvolvimento do sistema.

O objetivo do produto é identificar **bons ativos operáveis**, priorizando volatilidade acompanhada de volume e liquidez, com movimentos úteis para trade ou hold e baixo risco de aprisionamento no ativo.

---

## 2. Resumo executivo

O usuário final não busca simplesmente ativos em alta ou com grande variação percentual.

O sistema deve priorizar:

- ativos com **volume**
- ativos com **liquidez suficiente**
- ativos com **volatilidade útil**
- ativos com **movimentos reaproveitáveis**
- ativos com **capacidade real de entrada e saída**
- ativos que permitam **operações práticas e escaláveis**

A regra central do sistema é:

> **Encontrar bons ativos operáveis**

---

## 3. Universo inicial de ativos

### Ativos que devem ser acompanhados no início
- SOL
- WBTC
- USDT

### Prioridade
As três moedas são prioridade máxima.

### Requisito funcional
O sistema deve permitir configuração explícita de uma watchlist inicial enxuta, com foco nos ativos prioritários do operador.

---

## 4. Critérios de liquidez

### 4.1 Liquidez considerada boa
- **Moedas pequenas:** entre 3 mil e 5 mil por dia
- **Moedas maiores:** a partir de 10 mil por dia

### 4.2 Liquidez mínima por faixa operacional
- **Operação pequena:** 3.000
- **Operação média:** 5.000
- **Operação maior:** 10.000 por dia

### 4.3 Interpretação operacional
Liquidez não é um fator secundário. Ela é um dos principais determinantes de entrada, saída e segurança operacional.

### Requisitos
O sistema deve:
- medir liquidez mínima por faixa de operação
- distinguir entre liquidez aceitável para operação pequena, média e maior
- tratar baixa liquidez como fator crítico de descarte

---

## 5. Tamanho operacional

### 5.1 Entrada inicial
- Para moedas pequenas: começa com **R$ 25**

### 5.2 Escalada de posição
- Aumenta para **R$ 200, R$ 300 ou mais** se houver boa liquidez

### 5.3 Operação média
- **R$ 1.000 ou mais**

### 5.4 Ponto em que liquidez passa a fazer muita diferença
- **A partir de R$ 1.000**

### Requisitos
O sistema deve:
- considerar diferentes tamanhos de ordem
- estimar se o ativo suporta escalada de posição
- separar oportunidade boa para teste pequeno de oportunidade boa para operação maior

---

## 6. Entrada, saída e risco de aprisionamento

### 6.1 O que dá segurança para entrar
- **Volume**

### 6.2 O que dá segurança para sair
- **Volume**

### 6.3 O que indica risco de ficar preso
- **Baixo volume**

### Interpretação
Para o usuário, volume e liquidez são os principais sinais de segurança operacional.

### Requisitos
O sistema deve:
- atribuir peso alto a volume e liquidez no ranking
- sinalizar risco de baixa executabilidade
- alertar quando houver risco de aprisionamento no ativo

---

## 7. Slippage e execução

### 7.1 Slippage considerado ruim
- **Grandes ativos:** entre 3% e 5%
- **Ativos menores:** entre 5% e 10%

### 7.2 Fatores que mais incomodam
- spread alto
- demora para executar
- dificuldade para vender

### Requisitos
O sistema deve:
- estimar slippage por tamanho de ordem
- exibir risco de execução
- considerar spread e velocidade estimada de execução
- refletir o custo operacional real do ativo

---

## 8. O que caracteriza um movimento atípico útil

### 8.1 Fatores que mais chamam atenção
- aumento de volume
- repetição de oscilações

### 8.2 Tipos de movimento valorizados
- **Disparo forte:** útil para hold
- **Oscilação sustentada:** útil para trades

### Interpretação
O sistema precisa diferenciar tipos de oportunidade:
- oportunidade de continuidade
- oportunidade de oscilação

### Requisitos
O sistema deve:
- detectar aumento anormal de volume
- detectar repetição de oscilações
- classificar movimentos por utilidade operacional
- distinguir oportunidade para trade de oportunidade para hold

---

## 9. Duração útil do movimento

### 9.1 Duração mínima desejada
- **Horas ou dias**

### 9.2 Quando o movimento perde a graça
- quando cessa a volatilidade
- quando cessa o volume

### Requisitos
O sistema deve:
- modelar duração útil do movimento
- acompanhar deterioração do sinal
- marcar quando o movimento perdeu volume e volatilidade
- evitar priorizar impulsos mortos

---

## 10. Critérios de ranking das oportunidades

### 10.1 Ordem de importância
O usuário prioriza:
1. volatilidade com volume e liquidez
2. repetição do movimento
3. facilidade de saída, como consequência de volume e liquidez

### Interpretação
Não basta encontrar movimento. O sistema deve encontrar movimento acompanhado de condições reais de execução.

### Requisitos
O ranking deve considerar fortemente:
- volatilidade útil
- volume
- liquidez
- repetição
- capacidade de saída

---

## 11. Alertas

### 11.1 Tipo de alerta desejado
- alertas das melhores oportunidades
- alertas de oportunidades médias também

### 11.2 Quantidade ideal
- entre **1 e 2 alertas por dia**

### 11.3 Conteúdo mínimo do alerta
- volatilidade do ativo, com mínimo de 3%
- volume de compradores e vendedores

### Requisitos
O sistema deve:
- suportar alertas de oportunidades fortes e médias
- permitir configuração da sensibilidade
- mostrar no alerta:
  - ativo
  - volatilidade
  - volume
  - pressão de compradores/vendedores
  - contexto de operabilidade

---

## 12. Critérios de descarte

### 12.1 Moeda que não compensa
- volatilidade sem volume/liquidez
- moeda sem volume
- cenário de prisão, perda de tempo e prejuízo

### 12.2 Gráfico bonito, mas ruim para operar
- alta volatilidade sem volume/liquidez

### Interpretação
Para o usuário, movimento sem liquidez é um falso positivo operacional.

### Requisitos
O sistema deve:
- rebaixar fortemente sinais chamativos sem liquidez
- não priorizar alta percentual isolada
- distinguir ativo interessante de ativo realmente operável

---

## 13. Resultado esperado

### 13.1 O que o sistema deve ajudar a fazer
- encontrar oportunidades antes
- evitar moedas ruins
- aumentar valor operado
- ganhar tempo

### 13.2 Resultado principal esperado
- **retorno significativo nas operações**

### Requisito de produto
O sistema deve ser desenhado para melhorar a qualidade operacional das decisões e aumentar a eficiência na busca por oportunidades relevantes.

---

## 14. Regra principal do sistema

A regra mais importante resumida pelo usuário é:

> **Encontrar bons ativos operáveis**

Essa frase deve orientar as decisões de produto, score, filtros e alertas.

---

## 15. Tradução prática para requisitos do sistema

Com base nas respostas do usuário, o sistema deve evoluir para funcionar como:

> **um radar de ativos operáveis, que prioriza volatilidade acompanhada de volume e liquidez, identifica movimentos úteis para trade ou hold e reduz o risco de operar ativos sem saída**

---

## 16. Requisitos funcionais prioritários

### P0
- acompanhar watchlist inicial: SOL, WBTC e USDT
- medir volume e liquidez como fatores centrais
- medir liquidez por faixa operacional
- estimar slippage por tamanho de ordem
- criar score de executabilidade
- diferenciar sinal interessante de sinal operável
- exibir risco de aprisionamento
- alertar com volatilidade e volume

### P1
- identificar aumento anormal de volume
- detectar repetição de oscilações
- classificar oportunidade para trade ou hold
- medir duração útil do movimento
- detectar deterioração do sinal
- suportar escalabilidade de capital

### P2
- personalização fina por perfil operacional
- calibragem por histórico real de outcomes
- evolução do ranking com base em performance observada

---

## 17. Critérios de aceitação do produto

O sistema estará alinhado ao perfil operacional do usuário quando conseguir:

- mostrar poucos ativos realmente relevantes
- priorizar liquidez acima de altas percentuais ilusórias
- diferenciar movimento chamativo de movimento operável
- indicar quando um ativo suporta operação pequena, média ou maior
- identificar movimentos úteis para trade ou hold
- alertar com baixa frequência e alta utilidade
- reduzir tempo perdido com ativos ruins
- diminuir o risco de ficar preso em moedas sem saída

---

## 18. Frase final de definição do produto

> **O sistema deve encontrar bons ativos operáveis, priorizando volatilidade acompanhada de volume e liquidez, com movimentos úteis para trade ou hold e baixo risco de aprisionamento no ativo.**
---

## 19. Status de implementacao apos Release E

Itens ja implementados em codigo:

- watchlist default orientada a SOL_BRL, WBTC_BRL e USDT_BRL para novas configs
- perfil operacional por workspace
- tamanho de ordem usado no calculo de slippage
- volume notional minimo usado no filtro de operabilidade
- limites separados de slippage de entrada e saida
- alertas Telegram configuraveis por tipo, score, cooldown e somente operaveis
- UI administrativa para editar e autosalvar os campos operacionais

Itens ainda pendentes:

- duracao util real do movimento
- taxonomia v2 separando melhor trade de hold
- repeticao de oscilacoes com leitura mais temporal
- calibragem automatica por outcomes
- analise explicita de volume comprador/vendedor alem do proxy de book bid/ask
