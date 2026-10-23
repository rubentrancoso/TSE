#!/usr/bin/env python3
"""Benchmark de I/O do SQLite TSE sem modificar o banco e sem varrer tudo.

Compara leituras em ordem de rowid (paginas contiguas) com o plano atual
de leitura por indice. Amostras em tres pontos da tabela, com orcamento
de tempo por amostra. Nao cria indices nem altera bancos/checkpoints.
"""
from __future__ import annotations

import argparse
import os
import shutil
import sqlite3
import time
from pathlib import Path


COLUMNS = "source_kind,uf,municipio,zona,secao,turno,cargo,votavel,votos"


def sample_window(db, start_rowid, limit, timeout):
    sql = "SELECT " + COLUMNS + " FROM votes NOT INDEXED WHERE rowid>=? LIMIT ?"
    plan = " | ".join(str(p[-1]) for p in db.execute(
        "EXPLAIN QUERY PLAN " + sql, (start_rowid, limit)))
    begun = time.monotonic()
    last = [begun]
    count = 0
    def progress():
        t = time.monotonic()
        if t - last[0] >= 10:
            print(f"  [SQL ATIVO] {count:,} linhas em {t-begun:.1f}s",
                  flush=True)
            last[0] = t
        return 1 if t - begun >= timeout else 0
    db.set_progress_handler(progress, 10000)
    try:
        for _ in db.execute(sql, (start_rowid, limit)):
            count += 1
    except sqlite3.OperationalError as exc:
        if "interrupted" not in str(exc).lower():
            raise
        print("  [LIMITE] leitura SQL interrompida pelo orcamento.",
              flush=True)
    finally:
        db.set_progress_handler(None, 0)
    elapsed = time.monotonic()-begun
    return {"rows": count, "seconds": elapsed,
            "rows_per_sec": round(count / elapsed, 1) if elapsed else 0,
            "plan": plan}


def run(root, rows=100000, timeout=90):
    db_file = root / "analysis" / "urna_2026.sqlite3"
    if not db_file.is_file():
        raise FileNotFoundError(db_file)
    stat = db_file.stat()
    free = shutil.disk_usage(db_file.parent).free
    print("BENCHMARK DE I/O, SOMENTE LEITURA. Nenhum dado sera modificado.")
    print(f"SQLite: {stat.st_size / (1024**3):.2f} GiB; "
          f"espaco livre H: {free/(1024**3):.2f} GiB")
    print("Nao executar junto com a reconciliacao nacional.", flush=True)
    uri = db_file.resolve().as_uri() + "?mode=ro"
    with sqlite3.connect(uri, uri=True, timeout=15) as db:
        db.execute("PRAGMA query_only=ON")
        minimum, maximum = db.execute(
            "SELECT MIN(rowid),MAX(rowid) FROM votes").fetchone()
        if minimum is None:
            print("Tabela votes vazia.")
            return []
        middle = (minimum + maximum)//2
        spots = [("inicio", minimum),
                 ("meio", middle),
                 ("fim", max(minimum, maximum-rows))]
        output = []
        for label, start in spots:
            print(f"AMOSTRA {label}: ate {rows:,} registros desde rowid {start:,}",
                  flush=True)
            result = sample_window(db, start, rows, timeout)
            print(f"RESULTADO {label}: {result['rows']:,} linhas / "
                  f"{result['seconds']:.2f}s = "
                  f"{result['rows_per_sec']:,} linhas/s")
            print(f"  EXPLAIN: {result['plan']}", flush=True)
            output.append((label, result))
    if all(r["rows"] for _,r in output):
        print("Leitura sequencial COMPROVADA nas amostras, sem alterar o SQLite.")
    print("ATENCAO: amostras nao estimam precisamente o tempo de "
          "varredura de toda a base. Para escalonar, medir "
          "volume real de I/O e custo de gravar particoes.")
    return output


def main():
    parser = argparse.ArgumentParser(description="Medir I/O sequencial do SQLite")
    parser.add_argument("--root", default=("H:/TSE/forensics/urnas"
                                           if os.name=="nt" else "data/forensics/urnas"))
    parser.add_argument("--rows", type=int, default=100000)
    parser.add_argument("--budget", type=float, default=90)
    args = parser.parse_args()
    if args.rows < 100 or args.budget < 1:
        parser.error("--rows >= 100; --budget >= 1")
    run(Path(args.root), args.rows, args.budget)


if __name__ == "__main__":
    main()
