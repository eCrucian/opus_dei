# Nota Técnica — Modelo de Apreçamento: Bond Callable Perpétuo

**Produto:** Bond Callable Perpétuo  
**Área:** Risco de Mercado — Derivativos de Renda Fixa  
**Versão:** 1.0 (Rascunho)  
**Data:** Abril de 2026  

---

## 1. Objetivo

Este documento descreve a metodologia de apreçamento de um **bond callable perpétuo**, instrumento de dívida que paga cupons por prazo indefinido e confere ao emissor o direito de resgatar antecipadamente o principal em datas pré-especificadas.

Para fins práticos de implementação numérica, a perpetuidade é aproximada por um bond de **50 anos** (600 pagamentos mensais), truncamento suficiente para que o valor presente dos fluxos além desse horizonte seja desprezível sob as taxas de desconto usuais.

---

## 2. Estrutura do Instrumento

| Característica           | Descrição                                         |
|--------------------------|---------------------------------------------------|
| Tipo                     | Bond Callable Perpétuo                            |
| Principal (Face Value)   | R$ 1.000,00 (ou USD 1.000,00)                    |
| Cupom                    | Taxa fixa anual, pagamento mensal                 |
| Vencimento Efetivo       | 50 anos (aproximação da perpetuidade)             |
| Datas de Call            | Periódicas, após período de carência              |
| Prêmio de Call           | Conforme tabela contratual                        |
| Convenção de Dias        | ACT/360                                           |

---

## 3. Fatores de Risco

O modelo utiliza **dois fatores de risco**, ambos representados em termos de **fator de desconto** (não em taxa), o que facilita a composição direta de desconto e elimina ambiguidades de convenção de base.

### 3.1 Fator de Desconto da Taxa Livre de Risco — `df_rf`

**Definição:** Preço no instante `t` de um zero-coupon bond sem risco com vencimento em `T`:

$$
P_{rf}(t, T) = \exp\!\left(-\int_t^T f_{rf}(t,s)\,ds\right)
$$

onde $f_{rf}(t,s)$ é a taxa forward instantânea livre de risco.

Para implementação com discretização por tenor:

$$
P_{rf}(t, T) \approx \prod_{i=1}^{n} \frac{1}{1 + r_i \cdot \Delta t_i}
$$

**Faixas históricas observadas:** 0,60 a 0,95 para tenores de 1 a 10 anos.

### 3.2 Fator de Desconto do Spread de Crédito — `df_cs`

**Definição:** Componente de desconto associada ao risco de crédito do emissor:

$$
P_{cs}(t, T) = \exp\!\left(-\int_t^T cs(t,s)\,ds\right)
$$

onde $cs(t,s)$ é o spread de crédito forward (em continuamente composto).

**Faixas históricas observadas:** 0,85 a 0,99 para tenores de 1 a 10 anos, dependendo do rating do emissor.

### 3.3 Fator de Desconto Composto

O fator de desconto total, aplicável ao desconto de cada fluxo de caixa do bond:

$$
D(t, T_i) = P_{rf}(t, T_i) \cdot P_{cs}(t, T_i)
$$

---

## 4. Metodologia de Apreçamento

### 4.1 Componente Straight Bond (Sem Opcionalidade)

O valor de um bond equivalente sem opcionalidade (*straight bond*) é:

$$
PV_{straight}(t) = C \cdot \sum_{i=1}^{N} D(t, T_i) \cdot \tau_i + F \cdot D(t, T_N)
$$

onde:
- $C$ = cupom anual
- $\tau_i = T_i - T_{i-1}$ = fração de ano do período $i$ (ACT/360)
- $F$ = valor de face
- $N$ = número total de pagamentos ($N \approx 600$ para 50 anos mensais)
- $D(t, T_i)$ = fator de desconto composto para o tenor $i$

Para a perpetuidade com cupom constante e taxa de desconto constante $y$, a fórmula fechada é:

$$
PV_{perp} = \frac{C}{y}
$$

onde $y$ é o yield total (taxa livre de risco + spread de crédito). Esta expressão é usada como sanity check da implementação numérica de 50 anos.

### 4.2 Valor da Opção de Call via Monte Carlo

A opcionalidade de call é precificada via simulação de Monte Carlo nos fatores de desconto.

#### 4.2.1 Dinâmica dos Fatores de Desconto

Os fatores de desconto são simulados diretamente. Para cada tenor $T_i$ e passo de tempo $\Delta t$:

$$
P_{rf}(t+\Delta t, T_i) = P_{rf}(t, T_i) \cdot \exp\!\left(-r_t \cdot \Delta t + \sigma_{rf}\sqrt{\Delta t}\,Z^{(1)}_t\right)
$$

$$
P_{cs}(t+\Delta t, T_i) = P_{cs}(t, T_i) \cdot \exp\!\left(-cs_t \cdot \Delta t + \sigma_{cs}\sqrt{\Delta t}\,Z^{(2)}_t\right)
$$

onde $Z^{(1)}_t$ e $Z^{(2)}_t$ são variáveis normais padrão.

> **Nota:** A correlação entre os fatores de risco não está parametrizada nesta versão do documento.

#### 4.2.2 Exercício Ótimo da Opção de Call

Em cada data de call $T_k^{call}$, o emissor compara o custo de manter a dívida com o custo de refinanciamento. A regra de exercício é:

$$
\text{Call exercida em } T_k^{call} \text{ se } PV_{straight}(T_k^{call}) > F + P_{call}
$$

onde $P_{call}$ é o prêmio de call contratual.

#### 4.2.3 Estimativa do Preço via Simulação

$$
PV_{callable}(t) = \frac{1}{M} \sum_{m=1}^{M} \left[ \sum_{i=1}^{\tau^*(m)} C \cdot D^{(m)}(t, T_i) \cdot \tau_i + (F + P_{call}) \cdot D^{(m)}(t, T^*_m) \right]
$$

onde:
- $M$ = número de cenários Monte Carlo
- $\tau^*(m)$ = índice do último período de cupom antes da call (ou $N$ se não exercida)
- $T^*_m$ = data de call no cenário $m$ (ou $T_N$ se não exercida)

O valor da opção de call (do ponto de vista do **investidor**) é:

$$
V_{call\_option} = PV_{straight} - PV_{callable}
$$

---

## 5. Premissas do Modelo

1. **Mercado completo:** Os fatores de desconto são negociáveis e a medida risk-neutral existe.
2. **Sem fricções:** Ausência de custos de transação e impostos.
3. **Fatores independentes:** Os dois fatores de desconto são tratados como independentes na versão atual (correlação = 0).
4. **Volatilidade constante:** $\sigma_{rf}$ e $\sigma_{cs}$ são constantes ao longo do tempo.
5. **Exercício racional:** O emissor sempre exerce a call quando é financeiramente vantajoso.
6. **Truncamento em 50 anos:** O erro de truncamento da perpetuidade é considerado desprezível.

---

## 6. Parâmetros de Calibração

Os parâmetros do modelo são:

| Parâmetro   | Descrição                                    | Forma de Calibração          |
|-------------|----------------------------------------------|------------------------------|
| $\sigma_{rf}$ | Volatilidade do fator de desconto livre de risco | Implícita em swaptions      |
| $\sigma_{cs}$ | Volatilidade do fator de desconto de crédito | Implícita em CDS options     |
| $P_{call}$  | Prêmio de call                               | Contratual                   |

> **Lacuna documental:** O procedimento detalhado de calibração de $\sigma_{rf}$ e $\sigma_{cs}$ a partir de instrumentos de mercado não está descrito nesta versão.

---

## 7. Implementação Numérica

### 7.1 Parâmetros da Simulação Monte Carlo

A implementação utiliza simulação de Monte Carlo com os seguintes parâmetros de referência:

- Número de cenários: a ser definido conforme análise de convergência
- Geração de números aleatórios: método a ser especificado
- Semente: fixada para reprodutibilidade

> **Lacuna documental:** O número de cenários e o método de redução de variância não foram definidos. Não há análise de convergência documentada.

### 7.2 Discretização Temporal

A simulação é conduzida com passos mensais ($\Delta t = 1/12$), coincidindo com as datas de pagamento de cupom e as datas de call.

### 7.3 Pseudocódigo

```python
def price_callable_perpetual(df_rf_curve, df_cs_curve, coupon, face,
                              call_dates, call_premium, sigma_rf, sigma_cs, M):
    total_pv = 0.0
    for scenario in range(M):
        # Simular caminhos de df_rf e df_cs
        pv_path = simulate_path(df_rf_curve, df_cs_curve, sigma_rf, sigma_cs)
        # Verificar exercício de call
        call_date, pv_scenario = check_call_exercise(pv_path, call_dates,
                                                      call_premium, face)
        total_pv += pv_scenario
    return total_pv / M
```

---

## 8. Testes e Validações

### 8.1 Casos Limite

| Condição                   | Comportamento Esperado                                      |
|----------------------------|------------------------------------------------------------|
| $\sigma_{rf} = \sigma_{cs} = 0$ | $PV_{callable} \to PV_{straight}$ (sem incerteza, call não é exercida se out-of-the-money) |
| $P_{call} \to \infty$      | $PV_{callable} \to PV_{straight}$ (call nunca exercida)    |
| $y \to 0$                  | $PV_{straight} \to \infty$ (divergência esperada da perpetuidade) |

### 8.2 Verificação com Fórmula Fechada

Para o caso sem call, o preço deve convergir para $C/y$ à medida que o truncamento (50 anos) se torna suficiente.

> **Lacuna documental:** Não há análise de sensibilidade (greeks) documentada — duration, convexity, DV01 e CS01 em relação aos fatores de desconto.

---

## 9. Limitações do Modelo

- **Correlação não modelada:** A correlação entre taxa livre de risco e spread de crédito é ignorada, o que pode subestimar a volatilidade do preço em cenários de stress (flight-to-quality).
- **Volatilidade constante:** Não captura smile/skew de volatilidade.
- **Exercício racional puro:** O modelo não captura exercício subótimo ou motivações não-financeiras do emissor.
- **Sem risco de liquidez:** O spread bid-ask e a iliquidez do instrumento não estão modelados.
- **Truncamento:** Bonds com yields muito baixas (abaixo de 1% a.a.) podem ter erro de truncamento relevante.

---

## 10. Referências

- Brigo, D., Mercurio, F. (2006). *Interest Rate Models — Theory and Practice*. Springer.
- Hull, J. (2018). *Options, Futures, and Other Derivatives*. Pearson.
- Longstaff, F.A., Schwartz, E.S. (2001). Valuing American Options by Simulation. *Review of Financial Studies*.

---

*Documento em versão rascunho — pendente revisão de metodologia de calibração, análise de sensibilidade e definição dos parâmetros Monte Carlo.*
