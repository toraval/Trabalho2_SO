import time
import random
from multiprocessing import Process, Queue, Semaphore, Lock, Value
from datetime import datetime

prioridade_ordem = {"alta": 0, "media": 1, "baixa": 2}

TEMPO_MAX_ESPERA = 5  # segundos até desistir
NUM_PORTOES = 2       # número de portões disponíveis

def gerar_prioridade():
    return random.choice(["alta", "media", "baixa"])

# Escrever no log com segurança
def escrever_log(lock, mensagem):
    with lock:
        with open("log.txt", "a") as f:
            f.write(mensagem + "\n")

# Passageiro (processo cliente)
def passageiro(id, fila, lock, passageiros_em_espera):
    time.sleep(random.uniform(0.5, 3))

    prioridade = gerar_prioridade()
    chegada = time.time()
    hora_chegada = datetime.now().strftime("%H:%M:%S")

    msg = f"[CHEGADA] Passageiro {id} | Prioridade: {prioridade} | Hora: {hora_chegada}"
    print(msg)
    escrever_log(lock, msg)

    # Incrementar contador partilhado de passageiros em espera
    with passageiros_em_espera.get_lock():
        passageiros_em_espera.value += 1

    fila.put({
        "id": id,
        "prioridade": prioridade,
        "chegada": chegada,
        "hora_chegada": hora_chegada
    })

# Embarque com semáforo (simula agente num portão)
def embarcar(p, semaforo, lock, portao_id, passageiros_em_espera):
    with semaforo:
        inicio = time.time()
        espera = inicio - p["chegada"]
        hora_embarque = datetime.now().strftime("%H:%M:%S")

        # Tempo variável conforme prioridade
        if p["prioridade"] == "alta":
            tempo_embarque = random.uniform(0.5, 1.5)
        elif p["prioridade"] == "media":
            tempo_embarque = random.uniform(1, 2.5)
        else:
            tempo_embarque = random.uniform(2, 3.5)

        agente_id = portao_id  # agente associado ao portão

        msg_inicio = (
            f"[EMBARQUE INICIO] Passageiro {p['id']} | Prioridade: {p['prioridade']} | "
            f"Portão {portao_id} | Agente {agente_id} | "
            f"Hora: {hora_embarque} | Espera: {espera:.2f}s"
        )
        print(msg_inicio)
        escrever_log(lock, msg_inicio)

        time.sleep(tempo_embarque)

        fim = time.time()
        hora_fim = datetime.now().strftime("%H:%M:%S")

        msg_fim = (
            f"[EMBARQUE FIM] Passageiro {p['id']} | Portão {portao_id} | "
            f"Hora: {hora_fim} | Duração: {tempo_embarque:.2f}s"
        )
        print(msg_fim)
        escrever_log(lock, msg_fim)

        # Decrementar contador partilhado
        with passageiros_em_espera.get_lock():
            passageiros_em_espera.value -= 1

# Servidor (processo servidor / aeroporto)
def servidor(fila, total_passageiros, semaforo, lock, passageiros_em_espera):
    fila_embarque = []
    processados = 0
    processos_embarque = []
    portao_atual = Value('i', 1)  # memória partilhada para rotação de portões

    print(f"[SERVIDOR] Aeroporto iniciado. Aguardando {total_passageiros} passageiros...")
    escrever_log(lock, f"[SERVIDOR] Aeroporto iniciado. Total esperado: {total_passageiros} passageiros.")

    while processados < total_passageiros:

        # Receber passageiros da fila
        while not fila.empty():
            p = fila.get()
            fila_embarque.append(p)

        # Verificar desistências
        nova_fila = []
        for p in fila_embarque:
            tempo_espera = time.time() - p["chegada"]
            if tempo_espera > TEMPO_MAX_ESPERA:
                msg = (
                    f"[DESISTIU] Passageiro {p['id']} | Prioridade: {p['prioridade']} | "
                    f"Espera: {tempo_espera:.2f}s (limite atingido)"
                )
                print(msg)
                escrever_log(lock, msg)
                processados += 1
                with passageiros_em_espera.get_lock():
                    passageiros_em_espera.value -= 1
            else:
                nova_fila.append(p)

        fila_embarque = nova_fila

        # Ordenar por prioridade (alta > media > baixa), desempate por chegada
        fila_embarque.sort(key=lambda p: (prioridade_ordem[p["prioridade"]], p["chegada"]))

        # Mostrar estado atual da fila
        if fila_embarque:
            estado = ", ".join([f"P{p['id']}({p['prioridade']})" for p in fila_embarque])
            print(f"[FILA] Em espera ({passageiros_em_espera.value}): {estado}")

        # Embarcar o próximo passageiro com portão atribuído
        if fila_embarque:
            p = fila_embarque.pop(0)

            # Atribuir portão em rotação (memória partilhada)
            with portao_atual.get_lock():
                portao = portao_atual.value
                portao_atual.value = (portao_atual.value % NUM_PORTOES) + 1

            proc = Process(target=embarcar, args=(p, semaforo, lock, portao, passageiros_em_espera))
            proc.start()
            processos_embarque.append(proc)
            processados += 1
        else:
            time.sleep(0.3)

    for proc in processos_embarque:
        proc.join()

    msg_fim = "[SERVIDOR] Todos os passageiros processados. Encerrando aeroporto."
    print(msg_fim)
    escrever_log(lock, msg_fim)

# MAIN
if __name__ == "__main__":
    open("log.txt", "w").close()  # Limpar log anterior

    fila = Queue()
    lock = Lock()
    semaforo = Semaphore(NUM_PORTOES)

    # Memória partilhada: contador de passageiros atualmente em espera
    passageiros_em_espera = Value('i', 0)

    total_passageiros = 10
    processos = []

    # Criar e lançar processos dos passageiros
    for i in range(total_passageiros):
        p = Process(target=passageiro, args=(i, fila, lock, passageiros_em_espera))
        processos.append(p)
        p.start()

    # Lançar o servidor
    servidor(fila, total_passageiros, semaforo, lock, passageiros_em_espera)

    for p in processos:
        p.join()

    print("\n[FIM] Simulação concluída. Consulta o ficheiro log.txt para detalhes.")