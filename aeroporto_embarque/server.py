# -*- coding: utf-8 -*-
"""
server.py - Processo servidor (aeroporto).

Responsável por:
  - Receber passageiros da Queue e gerir a fila de embarque
  - Ordenar a fila por prioridade (alta > media > baixa) e hora de chegada
  - Detetar e registar desistências (TEMPO_MAX_ESPERA excedido)
  - Alocar portões via SharedMemory com exclusão mútua (Lock)
  - Suporte a interrupção: passageiro alta prioridade sobe à frente da fila
  - Gerar resumo final detalhado no log (desistências e interrupções)
"""

import time
import random
from multiprocessing import Process, Queue, Semaphore, Lock, Value
from multiprocessing.shared_memory import SharedMemory
from config import (
    TEMPO_MAX_ESPERA, NUM_PORTOES, PRIORIDADE_ORDEM,
    TEMPO_EMBARQUE, ICONE_PRIORIDADE
)
from utils import imprimir_e_log, cor_prioridade, agora, linha_divisoria, COR
from shared_state import obter_portao_livre, libertar_portao


def embarcar(p: dict, semaforo: Semaphore, lock: Lock, shm_name: str,
             passageiros_em_espera: Value) -> None:
    """
    Processo de embarque de um passageiro num portão.

    Utiliza semáforo para limitar a concorrência ao número de portões.
    Acede à SharedMemory para alocar e libertar o portão atomicamente.
    Regista: portão, agente, hora de embarque, tempo de espera e duração.

    Args:
        p: Dicionário com dados do passageiro.
        semaforo: Semáforo que limita o nº de embarques simultâneos.
        lock: Lock para I/O e acesso atómico à shared memory.
        shm_name: Nome do bloco de SharedMemory dos portões.
        passageiros_em_espera: Contador partilhado de passageiros na fila.
    """
    with semaforo:
        # Abre a memória partilhada existente (criada pelo servidor em main.py)
        shm = SharedMemory(name=shm_name)

        inicio = time.time()
        espera = inicio - p["chegada"]
        t_emb  = random.uniform(*TEMPO_EMBARQUE[p["prioridade"]])
        portao = obter_portao_livre(shm, lock)
        agente = portao  # Cada portão tem um agente dedicado

        cp = cor_prioridade(p["prioridade"])
        ip = ICONE_PRIORIDADE[p["prioridade"]]

        corpo_ini = (
            f"P{p['id']:02d}  "
            f"Portao {COR['azul']}G{portao}{COR['reset']}  "
            f"Agente {COR['magenta']}A{agente}{COR['reset']}  "
            f"Prioridade: {cp}{ip}{COR['reset']}  "
            f"Espera: {COR['amarelo']}{espera:.1f}s{COR['reset']}  "
            f"Hora embarque: {agora()}"
        )
        imprimir_e_log(lock, "EMBARQUE_INICIO", corpo_ini)

        time.sleep(t_emb)  # Simula duração do embarque

        hora_fim = agora()
        libertar_portao(shm, lock, portao)  # Liberta portão na SharedMemory
        shm.close()

        corpo_fim = (
            f"P{p['id']:02d}  "
            f"Portao {COR['azul']}G{portao}{COR['reset']}  "
            f"Duracao: {COR['verde']}{t_emb:.1f}s{COR['reset']}  "
            f"Hora fim: {hora_fim}"
        )
        imprimir_e_log(lock, "EMBARQUE_FIM", corpo_fim)

        # Decrementa contador de passageiros em espera
        with passageiros_em_espera.get_lock():
            passageiros_em_espera.value -= 1


def servidor(fila: Queue, total: int, semaforo: Semaphore, lock: Lock,
             passageiros_em_espera: Value, shm: SharedMemory,
             modo_alta_demanda: bool = False) -> None:
    """
    Processo servidor: gere a fila de embarque e os recursos do aeroporto.

    Funcionalidades implementadas:
      - Triagem por prioridade e ordem de chegada (alta > media > baixa)
      - Deteção e remoção de desistências (timeout TEMPO_MAX_ESPERA)
      - Interrupção: passageiro alta prioridade sobe à frente da fila
      - Alocação de portões via SharedMemory (exclusão mútua com Lock)
      - Visualização em consola da fila em tempo real (com cores ANSI)
      - Sumário final detalhado no log (desistências e interrupções)

    Args:
        fila: Queue partilhada com chegadas dos passageiros.
        total: Nº total de passageiros esperados.
        semaforo: Semáforo de controlo de portões.
        lock: Lock para exclusão mútua.
        passageiros_em_espera: Contador de passageiros na fila.
        shm: Bloco de SharedMemory para estado dos portões.
        modo_alta_demanda: Ativa logs de alta demanda.
    """
    fila_embarque      = []   # Lista local ordenada por prioridade
    processados        = 0
    desistencias       = 0
    embarcados         = 0
    processos_embarque = []
    desistencias_log   = []   # Registo detalhado de cada desistência
    interrompidos      = 0    # Contagem de interrupções por prioridade alta

    if modo_alta_demanda:
        imprimir_e_log(lock, "ALTA_DEMANDA",
                       f"{COR['amarelo']}Modo Alta Demanda ATIVO — "
                       f"passageiros a chegar em simultaneo!{COR['reset']}")

    imprimir_e_log(lock, "SERVIDOR",
                   f"Aeroporto iniciado  |  Portoes: {NUM_PORTOES}  |  "
                   f"Agentes: {NUM_PORTOES}  |  "
                   f"Passageiros esperados: {total}  |  "
                   f"Timeout desistencia: {TEMPO_MAX_ESPERA}s")
    print(linha_divisoria(), flush=True)

    while processados < total:

        # Drena todos os passageiros que chegaram à Queue partilhada
        while not fila.empty():
            novo = fila.get()

            # Interrupção: passageiro alta prioridade sobe à frente de media/baixa
            if novo["prioridade"] == "alta" and fila_embarque:
                primeiro = fila_embarque[0]
                if primeiro["prioridade"] in ("media", "baixa"):
                    interrompidos += 1
                    cp_novo = cor_prioridade(novo["prioridade"])
                    cp_pri  = cor_prioridade(primeiro["prioridade"])
                    corpo_int = (
                        f"P{novo['id']:02d} {cp_novo}[ALTA]{COR['reset']} "
                        f"interrompe P{primeiro['id']:02d} "
                        f"({cp_pri}{primeiro['prioridade']}{COR['reset']})"
                    )
                    imprimir_e_log(lock, "INTERRUPCAO", corpo_int)

            fila_embarque.append(novo)

        # ── Detetar e processar desistências ─────────────────────────────────
        nova_fila = []
        for p in fila_embarque:
            espera = time.time() - p["chegada"]
            if espera > TEMPO_MAX_ESPERA:
                cp = cor_prioridade(p["prioridade"])
                ip = ICONE_PRIORIDADE[p["prioridade"]]
                corpo = (
                    f"P{p['id']:02d}  Prioridade: {cp}{ip}{COR['reset']}  "
                    f"Espera: {COR['vermelho']}{espera:.1f}s "
                    f"(limite: {TEMPO_MAX_ESPERA}s){COR['reset']}  "
                    f"Chegou: {p['hora_chegada']}"
                )
                imprimir_e_log(lock, "DESISTIU", corpo)
                # Regista desistência para o resumo final
                desistencias_log.append({
                    "id":        p["id"],
                    "prioridade": p["prioridade"],
                    "espera":    round(espera, 1),
                    "chegada":   p["hora_chegada"],
                })
                processados  += 1
                desistencias += 1
                with passageiros_em_espera.get_lock():
                    passageiros_em_espera.value -= 1
            else:
                nova_fila.append(p)
        fila_embarque = nova_fila

        # ── Ordenar fila: prioridade (alta>media>baixa), desempate por chegada
        fila_embarque.sort(
            key=lambda x: (PRIORIDADE_ORDEM[x["prioridade"]], x["chegada"])
        )

        # ── Visualização em consola da fila atual ─────────────────────────────
        if fila_embarque:
            em_espera = passageiros_em_espera.value
            partes = []
            for p in fila_embarque:
                cp = cor_prioridade(p["prioridade"])
                partes.append(f"{cp}P{p['id']:02d}{COR['reset']}")
            corpo_fila = (
                f"Em espera ({COR['bold']}{em_espera}{COR['reset']}): "
                + " > ".join(partes)
            )
            imprimir_e_log(lock, "FILA", corpo_fila)

        # ── Embarcar o passageiro de maior prioridade ─────────────────────────
        if fila_embarque:
            p    = fila_embarque.pop(0)
            proc = Process(
                target=embarcar,
                args=(p, semaforo, lock, shm.name, passageiros_em_espera)
            )
            proc.start()
            processos_embarque.append(proc)
            embarcados  += 1
            processados += 1
        else:
            time.sleep(0.3)

    # Aguardar conclusão de todos os processos de embarque
    for proc in processos_embarque:
        proc.join()

    # ── Sumário final no terminal e no log ────────────────────────────────────
    print(linha_divisoria("="), flush=True)
    imprimir_e_log(lock, "SERVIDOR",
                   f"Todos os passageiros processados.  "
                   f"Embarcados: {COR['verde']}{embarcados}{COR['reset']}  |  "
                   f"Desistencias: {COR['vermelho']}{desistencias}{COR['reset']}  |  "
                   f"Interrupcoes alta prioridade: {COR['amarelo']}{interrompidos}{COR['reset']}  |  "
                   f"Aeroporto encerrado.")

    # Resumo detalhado de desistências no log
    if desistencias_log:
        imprimir_e_log(lock, "RESUMO",
                       f"Resumo de Desistencias ({desistencias} total):")
        for d in desistencias_log:
            cp = cor_prioridade(d["prioridade"])
            ip = ICONE_PRIORIDADE[d["prioridade"]]
            imprimir_e_log(lock, "RESUMO",
                           f"  P{d['id']:02d}  {cp}{ip}{COR['reset']}  "
                           f"Chegou: {d['chegada']}  "
                           f"Espera: {COR['vermelho']}{d['espera']}s{COR['reset']}")
    else:
        imprimir_e_log(lock, "RESUMO",
                       f"{COR['verde']}Nenhuma desistencia registada.{COR['reset']}")
