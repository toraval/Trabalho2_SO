# -*- coding: utf-8 -*-
"""
passenger.py - Processo passageiro (cliente).

Cada passageiro é um processo independente que:
  1. Aguarda um tempo aleatório antes de chegar ao aeroporto
  2. Gera a sua prioridade com base na classe do bilhete (aleatória)
  3. Regista a chegada e coloca-se na fila de embarque partilhada (Queue)
"""

import time
import random
from multiprocessing import Queue
from config import ICONE_PRIORIDADE
from utils import imprimir_e_log, cor_prioridade, agora, COR


def gerar_prioridade() -> str:
    """
    Gera prioridade aleatória simulando a classe do bilhete:
      - 20% alta  (Primeira Classe)
      - 40% media (Executiva)
      - 40% baixa (Económica)
    """
    return random.choices(["alta", "media", "baixa"], weights=[20, 40, 40])[0]


def passageiro(pid: int, fila: Queue, lock, passageiros_em_espera,
               modo_alta_demanda: bool = False) -> None:
    """
    Processo cliente: simula a chegada de um passageiro ao aeroporto.

    Args:
        pid: Identificador único do passageiro.
        fila: Queue partilhada para enviar dados ao servidor.
        lock: Lock para acesso exclusivo ao log e I/O.
        passageiros_em_espera: Value partilhado com contador de passageiros na fila.
        modo_alta_demanda: Se True, chegadas concentradas (0.0s-0.5s).
    """
    # Simula o tempo de deslocação até ao aeroporto
    if modo_alta_demanda:
        time.sleep(random.uniform(0.0, 0.5))
    else:
        time.sleep(random.uniform(0.3, 3.0))

    prioridade = gerar_prioridade()
    chegada    = time.time()
    cp         = cor_prioridade(prioridade)
    ip         = ICONE_PRIORIDADE[prioridade]

    corpo = (
        f"Passageiro {COR['bold']}P{pid:02d}{COR['reset']}  "
        f"Prioridade: {cp}{ip}{COR['reset']}  "
        f"Hora chegada: {agora()}"
    )
    imprimir_e_log(lock, "CHEGADA", corpo)

    # Incrementa contador de passageiros em espera (memória partilhada Value)
    with passageiros_em_espera.get_lock():
        passageiros_em_espera.value += 1

    # Envia dados completos do passageiro ao servidor via Queue
    fila.put({
        "id":           pid,
        "prioridade":   prioridade,
        "chegada":      chegada,
        "hora_chegada": agora(),
    })
