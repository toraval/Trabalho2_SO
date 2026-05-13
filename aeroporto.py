import time
import random
from multiprocessing import Process, Queue, Semaphore, Lock

prioridade_ordem = {"alta": 0, "media": 1, "baixa": 2}

TEMPO_MAX_ESPERA = 5  # segundos até desistir


def gerar_prioridade():
    return random.choice(["alta", "media", "baixa"])


# escrever no log com segurança
def escrever_log(lock, mensagem):
    with lock:
        with open("log.txt", "a") as f:
            f.write(mensagem + "\n")


# Passageiro
def passageiro(id, fila, lock):
    time.sleep(random.uniform(0.5, 3))

    prioridade = gerar_prioridade()
    chegada = time.time()

    msg = f"[CHEGADA] Passageiro {id} ({prioridade})"
    print(msg)
    escrever_log(lock, msg)

    fila.put({
        "id": id,
        "prioridade": prioridade,
        "chegada": chegada
    })


# Embarque com semáforo
def embarcar(p, semaforo, lock):
    with semaforo:
        inicio = time.time()

        espera = inicio - p["chegada"]

        msg_inicio = f"[EMBARQUE INICIO] Passageiro {p['id']} | Espera: {espera:.2f}s"
        print(msg_inicio)
        escrever_log(lock, msg_inicio)

        tempo_embarque = random.uniform(1, 3)
        time.sleep(tempo_embarque)

        fim = time.time()

        msg_fim = f"[EMBARQUE FIM] Passageiro {p['id']} | Duração: {tempo_embarque:.2f}s"
        print(msg_fim)
        escrever_log(lock, msg_fim)


# Servidor
def servidor(fila, total_passageiros, semaforo, lock):
    fila_embarque = []
    processados = 0
    processos_embarque = []

    while processados < total_passageiros:

        # receber passageiros
        while not fila.empty():
            p = fila.get()
            fila_embarque.append(p)

        # verificar desistências
        nova_fila = []
        for p in fila_embarque:
            tempo_espera = time.time() - p["chegada"]

            if tempo_espera > TEMPO_MAX_ESPERA:
                msg = f"[DESISTIU] Passageiro {p['id']} após {tempo_espera:.2f}s"
                print(msg)
                escrever_log(lock, msg)
                processados += 1
            else:
                nova_fila.append(p)

        fila_embarque = nova_fila

        # ordenar por prioridade
        fila_embarque.sort(key=lambda p: prioridade_ordem[p["prioridade"]])

        # embarcar
        if fila_embarque:
            p = fila_embarque.pop(0)

            proc = Process(target=embarcar, args=(p, semaforo, lock))
            proc.start()
            processos_embarque.append(proc)

            processados += 1
        else:
            time.sleep(0.5)

    for proc in processos_embarque:
        proc.join()


# MAIN
if __name__ == "__main__":
    open("log.txt", "w").close()  # limpar log

    fila = Queue()
    lock = Lock()
    semaforo = Semaphore(2)

    total_passageiros = 10
    processos = []

    # criar passageiros
    for i in range(total_passageiros):
        p = Process(target=passageiro, args=(i, fila, lock))
        processos.append(p)
        p.start()

    servidor(fila, total_passageiros, semaforo, lock)

    for p in processos:
        p.join()