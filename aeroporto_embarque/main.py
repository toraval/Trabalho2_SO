# -*- coding: utf-8 -*-
"""
main.py - Ponto de entrada do Sistema de Embarque de Passageiros.

Inicializa os recursos partilhados (SharedMemory, Semaphore, Lock, Queue, Value),
lança os processos passageiro e executa o processo servidor, aguardando a conclusão.

Uso:
    python main.py
"""

import sys
import io
import os
from multiprocessing import Process, Queue, Semaphore, Lock, Value
from datetime import datetime

# Garante UTF-8 em sistemas com encoding diferente (ex: Windows)
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

# Adiciona o diretório do script ao path para imports relativos
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import (
    TOTAL_PASSAGEIROS, NUM_PORTOES, TEMPO_MAX_ESPERA, MODO_ALTA_DEMANDA
)
from utils import linha_divisoria, COR
from shared_state import criar_shared_memory
from passenger import passageiro
from server import servidor


def inicializar_log() -> None:
    """Cria o ficheiro log.txt com cabeçalho da simulação."""
    with open("log.txt", "w", encoding="utf-8") as f:
        f.write("=" * 60 + "\n")
        f.write("     LOG DE OPERACOES DO AEROPORTO\n")
        f.write("=" * 60 + "\n")
        f.write(f"Inicio      : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Passageiros : {TOTAL_PASSAGEIROS}\n")
        f.write(f"Portoes     : {NUM_PORTOES}\n")
        f.write(f"Agentes     : {NUM_PORTOES}\n")
        f.write(f"Timeout     : {TEMPO_MAX_ESPERA}s\n")
        f.write(f"Alta Demanda: {MODO_ALTA_DEMANDA}\n")
        f.write("=" * 60 + "\n\n")


def finalizar_log() -> None:
    """Adiciona rodapé ao ficheiro log.txt."""
    with open("log.txt", "a", encoding="utf-8") as f:
        f.write("\n" + "=" * 60 + "\n")
        f.write("     FIM DA SIMULACAO\n")
        f.write(f"Fim: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 60 + "\n")


if __name__ == "__main__":
    # ── Inicializar log ──────────────────────────────────────────────────────
    inicializar_log()

    # ── Recursos partilhados (IPC) ───────────────────────────────────────────
    fila                  = Queue()               # Comunicação passageiros -> servidor
    lock                  = Lock()                # Exclusão mútua: I/O e shared memory
    semaforo              = Semaphore(NUM_PORTOES) # Limita embarques simultâneos
    passageiros_em_espera = Value("i", 0)          # Contador em memória partilhada
    shm                   = criar_shared_memory()  # SharedMemory: estado dos portões

    # ── Banner de início ─────────────────────────────────────────────────────
    print()
    print(linha_divisoria("="))
    print(f"  {COR['bold']}{COR['ciano']}  SIMULACAO DE EMBARQUE - AEROPORTO  {COR['reset']}")
    if MODO_ALTA_DEMANDA:
        print(f"  {COR['amarelo']}  MODO ALTA DEMANDA ATIVO  {COR['reset']}")
    print(linha_divisoria("="))
    print()

    # ── Lança processos passageiro (clientes) ────────────────────────────────
    processos_passageiros = []
    for i in range(TOTAL_PASSAGEIROS):
        p = Process(
            target=passageiro,
            args=(i, fila, lock, passageiros_em_espera, MODO_ALTA_DEMANDA)
        )
        processos_passageiros.append(p)
        p.start()

    # ── Processo servidor (corre no processo principal) ──────────────────────
    servidor(fila, TOTAL_PASSAGEIROS, semaforo, lock,
             passageiros_em_espera, shm, MODO_ALTA_DEMANDA)

    # ── Aguarda conclusão de todos os passageiros ────────────────────────────
    for p in processos_passageiros:
        p.join()

    # ── Liberta a memória partilhada (SharedMemory) ──────────────────────────
    shm.close()
    shm.unlink()  # Remove o bloco de memória do sistema operativo

    # ── Rodapé do log ────────────────────────────────────────────────────────
    finalizar_log()

    print()
    print(linha_divisoria("="))
    print(f"  {COR['bold']}Simulacao concluida. Ficheiro {COR['ciano']}log.txt{COR['reset']}{COR['bold']} gerado com sucesso.{COR['reset']}")
    print(linha_divisoria("="))
    print()
