# -*- coding: utf-8 -*-
"""
utils.py - Utilitários: logging, cores ANSI, formatação de output.
"""

import re
from datetime import datetime
from config import PREFIXO_EVENTO, ICONE_PRIORIDADE

# Cores ANSI para terminal colorido
COR = {
    "reset":    "\033[0m",
    "bold":     "\033[1m",
    "dim":      "\033[2m",
    "verde":    "\033[32m",
    "amarelo":  "\033[33m",
    "vermelho": "\033[31m",
    "ciano":    "\033[36m",
    "magenta":  "\033[35m",
    "azul":     "\033[34m",
    "branco":   "\033[97m",
}

COR_EVENTO = {
    "CHEGADA":         "ciano",
    "EMBARQUE_INICIO": "verde",
    "EMBARQUE_FIM":    "verde",
    "DESISTIU":        "vermelho",
    "SERVIDOR":        "magenta",
    "FILA":            "branco",
    "ALTA_DEMANDA":    "amarelo",
    "INTERRUPCAO":     "amarelo",
    "RESUMO":          "ciano",
}

_ANSI_RE = re.compile(r"\033\[[0-9;]*m")


def agora() -> str:
    """Devolve a hora atual formatada HH:MM:SS."""
    return datetime.now().strftime("%H:%M:%S")


def remover_ansi(texto: str) -> str:
    """Remove todos os códigos de escape ANSI de uma string."""
    return _ANSI_RE.sub("", texto)


def cor_prioridade(p: str) -> str:
    """Devolve o código de cor ANSI correspondente à prioridade."""
    return {"alta": COR["vermelho"], "media": COR["amarelo"], "baixa": COR["verde"]}[p]


def linha_divisoria(char: str = "─", largura: int = 72) -> str:
    """Gera uma linha divisória formatada."""
    return COR["dim"] + char * largura + COR["reset"]


def imprimir_e_log(lock, evento: str, corpo: str) -> None:
    """
    Imprime uma linha formatada no terminal (com cores ANSI) e escreve
    a versão limpa no ficheiro log.txt, protegida por lock para evitar
    condições de corrida entre processos.
    """
    ts    = f"[{agora()}]"
    prefx = PREFIXO_EVENTO.get(evento, f"[ {evento:<15}]")
    cor_e = COR.get(COR_EVENTO.get(evento, "branco"), COR["branco"])

    linha_terminal = f"{COR['dim']}{ts}{COR['reset']}  {cor_e}{prefx}{COR['reset']}  {corpo}"
    linha_log      = f"{ts}  {prefx}  {remover_ansi(corpo)}"

    with lock:
        print(linha_terminal, flush=True)
        with open("log.txt", "a", encoding="utf-8") as f:
            f.write(linha_log + "\n")
