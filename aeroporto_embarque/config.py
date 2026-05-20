# -*- coding: utf-8 -*-
"""
config.py - Configurações globais do sistema de embarque.
"""

TEMPO_MAX_ESPERA  = 15      # segundos máximos na fila antes de desistir
NUM_PORTOES       = 3       # número de portões disponíveis
NUM_AGENTES       = 3       # número de agentes de embarque (igual a portões)
TOTAL_PASSAGEIROS = 15      # número total de passageiros a simular
MODO_ALTA_DEMANDA = False   # se True, muitos passageiros chegam ao mesmo tempo

# Mapeamento de prioridade para valor numérico (ordenação crescente)
PRIORIDADE_ORDEM = {"alta": 0, "media": 1, "baixa": 2}

# Tempo de embarque (segundos) por prioridade: (mínimo, máximo)
TEMPO_EMBARQUE = {
    "alta":  (0.5, 1.5),
    "media": (1.0, 2.5),
    "baixa": (2.0, 3.5),
}

# Ícones de prioridade para consola
ICONE_PRIORIDADE = {"alta": "[ALTA]", "media": "[MED ]", "baixa": "[BXIA]"}

# Prefixos dos eventos no log
PREFIXO_EVENTO = {
    "CHEGADA":         "[ CHEGADA        ]",
    "EMBARQUE_INICIO": "[ EMBARQUE INÍCIO]",
    "EMBARQUE_FIM":    "[ EMBARQUE FIM   ]",
    "DESISTIU":        "[ DESISTÊNCIA    ]",
    "SERVIDOR":        "[ SERVIDOR       ]",
    "FILA":            "[ FILA           ]",
    "ALTA_DEMANDA":    "[ ALTA DEMANDA   ]",
    "INTERRUPCAO":     "[ INTERRUPÇÃO    ]",
    "RESUMO":          "[ RESUMO         ]",
}
