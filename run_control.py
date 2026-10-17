#!/usr/bin/env python3
"""Controle de execucao: progresso visivel e interrupcao com Ctrl+C."""
import signal
import sqlite3
import sys
import threading
import time
import os
import _thread

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
    # Opcao de cancelamento adicional no Windows quando a thread principal
    # estiver ocupada no SQLite ou em uma descompactacao longa.
    try:
        import msvcrt
    except ImportError:
        msvcrt = None
    next_message = time.monotonic() + 15
    while not _stop.wait(0.2):
        if msvcrt is not None:
            try:
                if msvcrt.kbhit():
                    key = msvcrt.getwch()
                    if key.casefold() == "q":
                        print("\\n[CANCELAMENTO] Tecla Q recebida.", flush=True)
                        _stop.set()
                        db = _db
                        if db is not None:
                            try:
                                db.interrupt()
                            except sqlite3.Error:
                                pass
                        _thread.interrupt_main()
                        return
            except (OSError, ValueError):
                msvcrt = None
        moment = time.monotonic()
        if moment >= next_message:
            elapsed = int(moment - _since)
            print("[EM EXECUCAO] {} ({} s nesta etapa). "
                  "Ctrl+C ou Q para interromper.".format(_label, elapsed),
                  flush=True)
            next_message = moment + 15


def install():
    global _started
    if _started:
        return
    _started = True
    signal.signal(signal.SIGINT, _on_sigint)
    if hasattr(signal, "SIGBREAK"):
        signal.signal(signal.SIGBREAK, _on_sigint)
    thread = threading.Thread(target=_heartbeat, name="tse-progress",
                              daemon=True)
    thread.start()
    stage("controle de execucao ativo (Ctrl+C ou Q para cancelar)")


def shutdown():
    _stop.set()


def cancelled():
    return _stop.is_set()
