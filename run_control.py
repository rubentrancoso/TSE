#!/usr/bin/env python3
"""Controle de execucao: progresso visivel e interrupcao com Ctrl+C."""
import signal
import sqlite3
import sys
import threading
import time

_label = "iniciando"
_since = time.monotonic()
_started = False
_stop = threading.Event()
_db = None


def stage(label):
    global _label, _since
    _label = str(label)
    _since = time.monotonic()
    print("[ETAPA] " + _label, flush=True)


def attach_db(db):
    global _db
    _db = db
    if db is not None:
        # Retorno nao-zero interrompe query extensa assim que SQLite
        # executar o proximo lote de instrucoes.
        db.set_progress_handler(lambda: 1 if _stop.is_set() else 0, 2000)


def _on_sigint(signum, frame):
    _stop.set()
    print("\n[INTERRUPCAO] Ctrl+C recebido. Encerrando sem apagar arquivos locais.",
          file=sys.stderr, flush=True)
    db = _db
    if db is not None:
        try:
            db.interrupt()
        except sqlite3.Error:
            pass
    raise KeyboardInterrupt


def _heartbeat():
    while not _stop.wait(15):
        elapsed = int(time.monotonic() - _since)
        print("[EM EXECUCAO] {} ({} s nesta etapa). Ctrl+C para interromper.".format(
            _label, elapsed), flush=True)


def install():
    global _started
    if _started:
        return
    _started = True
    signal.signal(signal.SIGINT, _on_sigint)
    thread = threading.Thread(target=_heartbeat, name="tse-progress",
                              daemon=True)
    thread.start()
    stage("controle de execucao ativo")


def shutdown():
    _stop.set()


def cancelled():
    return _stop.is_set()
