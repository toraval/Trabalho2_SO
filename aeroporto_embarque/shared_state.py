# -*- coding: utf-8 -*-
"""
shared_state.py - Gestão da memória partilhada entre processos.

Utiliza multiprocessing.shared_memory.SharedMemory para armazenar o estado
dos portões (livre/ocupado) em memória partilhada real, acessível por todos
os processos sem cópias. Cada portão ocupa 1 byte: 0 = livre, 1 = ocupado.
"""

from multiprocessing.shared_memory import SharedMemory
from config import NUM_PORTOES


def criar_shared_memory() -> SharedMemory:
    """
    Cria um bloco de memória partilhada para o estado dos portões.
    Cada byte representa um portão: 0 = livre, 1 = ocupado.
    Retorna o objeto SharedMemory (deve ser guardado pelo processo criador).
    """
    shm = SharedMemory(create=True, size=NUM_PORTOES)
    # Inicializa todos os portões como livres
    for i in range(NUM_PORTOES):
        shm.buf[i] = 0
    return shm


def obter_portao_livre(shm: SharedMemory, lock) -> int:
    """
    Procura e reserva o primeiro portão livre na memória partilhada.
    Retorna o índice (1-based) do portão alocado, ou 1 como fallback.
    Protegido por lock para evitar condições de corrida.
    """
    with lock:
        for i in range(NUM_PORTOES):
            if shm.buf[i] == 0:
                shm.buf[i] = 1   # Marca como ocupado
                return i + 1     # Retorna portão 1-based
    return 1  # fallback: todos ocupados (semáforo já garante disponibilidade)


def libertar_portao(shm: SharedMemory, lock, portao_id: int) -> None:
    """
    Liberta um portão na memória partilhada após o embarque.
    Protegido por lock para evitar condições de corrida.
    """
    with lock:
        shm.buf[portao_id - 1] = 0   # Marca como livre
