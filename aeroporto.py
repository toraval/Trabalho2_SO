# -*- coding: utf-8 -*-
"""
Sistema de Embarque de Passageiros - Aeroporto
Simulação com processos concorrentes, memória partilhada e semáforos.
"""

import re
import time
import random
import sys
from multiprocessing import Process, Queue, Semaphore, Lock, Value
from datetime import datetime


# ─────────────────────────────────────────────
# CONFIGURAÇÕES
# ─────────────────────────────────────────────
TEMPO_MAX_ESPERA  = 5
NUM_PORTOES       = 2
TOTAL_PASSAGEIROS = 10

prioridade_ordem = {"alta": 0, "media": 1, "baixa": 2}

# Cores ANSI (terminal)
COR = {
    "reset":   "\033[0m",
    "bold":    "\033[1m",
    "dim":     "\033[2m",
    "verde":   "\033[32m",
    "amarelo": "\033[33m",
    "vermelho":"\033[31m",
    "ciano":   "\033[36m",
    "magenta": "\033[35m",
    "azul":    "\033[34m",
    "branco":  "\033[97m",
}

PREFIXO = {
    "CHEGADA":         "[ CHEGADA        ]",
    "EMBARQUE INÍCIO": "[ EMBARQUE INÍCIO]",
    "EMBARQUE FIM":    "[ EMBARQUE FIM   ]",
    "DESISTIU":        "[ DESISTÊNCIA    ]",
    "SERVIDOR":        "[ SERVIDOR       ]",
    "FILA":            "[ FILA           ]",
}

COR_EVENTO = {
    "CHEGADA":         "ciano",
    "EMBARQUE INÍCIO": "verde",
    "EMBARQUE FIM":    "verde",
    "DESISTIU":        "vermelho",
    "SERVIDOR":        "magenta",
    "FILA":            "branco",
}

ICONE_PRIORIDADE = {"alta": "[ALTA]", "media": "[MED]", "baixa": "[BXIA]"}

_ANSI_RE = re.compile(r"\033\[[0-9;]*m")


# ─────────────────────────────────────────────
# UTILITÁRIOS
# ─────────────────────────────────────────────
def agora():
    return datetime.now().strftime("%H:%M:%S")


def cor_prioridade(p):
    return {"alta": COR["vermelho"], "media": COR["amarelo"], "baixa": COR["verde"]}[p]


def linha_divisoria(char="─", largura=72):
    return COR["dim"] + char * largura + COR["reset"]


def remover_ansi(texto):
    """Remove todos os códigos de escape ANSI de uma string."""
    return _ANSI_RE.sub("", texto)


def imprimir_e_log(lock, evento, corpo):
    ts     = f"[{agora()}]"
    prefx  = PREFIXO.get(evento, f"[ {evento:<15}]")
    cor_e  = COR.get(COR_EVENTO.get(evento, "branco"), COR["branco"])

    # Linha para o terminal (com cores)
    linha_terminal = f"{COR['dim']}{ts}{COR['reset']}  {cor_e}{prefx}{COR['reset']}  {corpo}"

    # Linha para o log (texto limpo, sem ANSI)
    linha_log = f"{ts}  {prefx}  {remover_ansi(corpo)}"

    with lock:
        print(linha_terminal, flush=True)
        with open("log.txt", "a", encoding="utf-8") as f:
            f.write(linha_log + "\n")


def gerar_prioridade():
    return random.choices(["alta", "media", "baixa"], weights=[20, 40, 40])[0]


# ─────────────────────────────────────────────
# PROCESSO PASSAGEIRO (cliente)
# ─────────────────────────────────────────────
def passageiro(pid, fila, lock, passageiros_em_espera):
    time.sleep(random.uniform(0.3, 3.0))

    prioridade = gerar_prioridade()
    chegada    = time.time()
    cp         = cor_prioridade(prioridade)
    ip         = ICONE_PRIORIDADE[prioridade]

    corpo = (f"Passageiro {COR['bold']}P{pid:02d}{COR['reset']}  "
             f"Prioridade: {cp}{ip}{COR['reset']}")
    imprimir_e_log(lock, "CHEGADA", corpo)

    with passageiros_em_espera.get_lock():
        passageiros_em_espera.value += 1

    fila.put({"id": pid, "prioridade": prioridade, "chegada": chegada})


# ─────────────────────────────────────────────
# EMBARQUE (processo filho)
# ─────────────────────────────────────────────
def embarcar(p, semaforo, lock, portao_id, passageiros_em_espera):
    with semaforo:
        inicio = time.time()
        espera = inicio - p["chegada"]

        duracao = {"alta": (0.5, 1.5), "media": (1.0, 2.5), "baixa": (2.0, 3.5)}
        t_emb   = random.uniform(*duracao[p["prioridade"]])

        cp = cor_prioridade(p["prioridade"])
        ip = ICONE_PRIORIDADE[p["prioridade"]]

        corpo_ini = (f"P{p['id']:02d}  Portao {COR['azul']}G{portao_id}{COR['reset']}  "
                     f"Agente {COR['magenta']}A{portao_id}{COR['reset']}  "
                     f"Prioridade: {cp}{ip}{COR['reset']}  "
                     f"Espera: {COR['amarelo']}{espera:.1f}s{COR['reset']}")
        imprimir_e_log(lock, "EMBARQUE INÍCIO", corpo_ini)

        time.sleep(t_emb)

        corpo_fim = (f"P{p['id']:02d}  Portao {COR['azul']}G{portao_id}{COR['reset']}  "
                     f"Duracao: {COR['verde']}{t_emb:.1f}s{COR['reset']}")
        imprimir_e_log(lock, "EMBARQUE FIM", corpo_fim)

        with passageiros_em_espera.get_lock():
            passageiros_em_espera.value -= 1


# ─────────────────────────────────────────────
# PROCESSO SERVIDOR (aeroporto)
# ─────────────────────────────────────────────
def servidor(fila, total, semaforo, lock, passageiros_em_espera):
    fila_embarque      = []
    processados        = 0
    processos_embarque = []
    portao_atual       = Value("i", 1)

    imprimir_e_log(lock, "SERVIDOR",
                   f"Aeroporto iniciado  |  Portoes: {NUM_PORTOES}  |  "
                   f"Passageiros esperados: {total}")
    print(linha_divisoria(), flush=True)

    while processados < total:

        while not fila.empty():
            fila_embarque.append(fila.get())

        nova_fila = []
        for p in fila_embarque:
            espera = time.time() - p["chegada"]
            if espera > TEMPO_MAX_ESPERA:
                cp = cor_prioridade(p["prioridade"])
                ip = ICONE_PRIORIDADE[p["prioridade"]]
                corpo = (f"P{p['id']:02d}  Prioridade: {cp}{ip}{COR['reset']}  "
                         f"Espera: {COR['vermelho']}{espera:.1f}s "
                         f"(limite atingido){COR['reset']}")
                imprimir_e_log(lock, "DESISTIU", corpo)
                processados += 1
                with passageiros_em_espera.get_lock():
                    passageiros_em_espera.value -= 1
            else:
                nova_fila.append(p)
        fila_embarque = nova_fila

        fila_embarque.sort(key=lambda x: (prioridade_ordem[x["prioridade"]], x["chegada"]))

        if fila_embarque:
            partes = []
            for p in fila_embarque:
                cp = cor_prioridade(p["prioridade"])
                partes.append(f"{cp}P{p['id']:02d}{COR['reset']}")
            em_espera = passageiros_em_espera.value
            corpo_fila = (f"Em espera ({COR['bold']}{em_espera}{COR['reset']}): "
                          + " > ".join(partes))
            imprimir_e_log(lock, "FILA", corpo_fila)

        if fila_embarque:
            p = fila_embarque.pop(0)
            with portao_atual.get_lock():
                portao = portao_atual.value
                portao_atual.value = (portao_atual.value % NUM_PORTOES) + 1

            proc = Process(
                target=embarcar,
                args=(p, semaforo, lock, portao, passageiros_em_espera)
            )
            proc.start()
            processos_embarque.append(proc)
            processados += 1
        else:
            time.sleep(0.3)

    for proc in processos_embarque:
        proc.join()

    print(linha_divisoria("═"), flush=True)
    imprimir_e_log(lock, "SERVIDOR",
                   "Todos os passageiros processados. Aeroporto encerrado.")


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
if __name__ == "__main__":
    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

    open("log.txt", "w", encoding="utf-8").close()

    fila                  = Queue()
    lock                  = Lock()
    semaforo              = Semaphore(NUM_PORTOES)
    passageiros_em_espera = Value("i", 0)

    print()
    print(linha_divisoria("═"))
    print(f"  {COR['bold']}{COR['ciano']}  SIMULACAO DE EMBARQUE — AEROPORTO  {COR['reset']}")
    print(linha_divisoria("═"))
    print()

    processos = []
    for i in range(TOTAL_PASSAGEIROS):
        p = Process(target=passageiro,
                    args=(i, fila, lock, passageiros_em_espera))
        processos.append(p)
        p.start()

    servidor(fila, TOTAL_PASSAGEIROS, semaforo, lock, passageiros_em_espera)

    for p in processos:
        p.join()

    print()
    print(linha_divisoria("═"))
    print(f"  {COR["bold"]}Simulacao concluida. Consulta o ficheiro {COR["ciano"]}log.txt{COR["reset"]}{COR["bold"]} para detalhes.{COR["reset"]}")
    print(linha_divisoria("═"))
    print()