#!/usr/bin/env python3
"""Reconciliação BU x votação por seção, retomável por UF/município/zona/turno.

Este módulo não modifica votos importados nem arquivos brutos. Mantém resultados
parciais e seus hashes em pasta separada, sob um identificador derivado das fontes.
Um resultado antigo nunca é reutilizado se os SHA-256 importados mudarem.
"""
from __future__ import annotations

import csv
import gzip
import hashlib
import json
import os
import shutil
import sqlite3
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

VERSION = "reconcile-zones-v2-presidential-national-fallback"
HEADER = ["UF", "municipio", "zona", "secao", "turno", "cargo",
          "votavel", "votos_BU", "votos_secao", "diferenca", "situacao"]


def utc():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical(value):
    raw = str(value or "").strip()
    try:
        return str(int(raw)) if raw else ""
    except ValueError:
        return raw.upper()


def key_sort(task):
    uf, mu, zone, turn = task["key"]
    def order(value):
        return (0, int(value)) if value.isdecimal() else (1, value)
    return (uf, order(turn), order(mu), order(zone))


def tasks_from_db(db, ufs, turn):
    """Uma única passagem pelos registros; apenas grupos existentes.

    A consulta de planejamento pode demorar em bancos enormes. A fase é
    anunciada e cronometrada separadamente, antes de qualquer estimativa.
    """
    where = ["source_kind IN ('bu', 'secao', 'secao_nacional')",
             "(source_kind != 'secao_nacional' OR cargo IN ('1', 'presidente'))",
             "votos IS NOT NULL",
             "TRIM(uf) != ''", "TRIM(municipio) != ''",
             "TRIM(zona) != ''", "TRIM(turno) != ''",
             "TRIM(secao) != ''", "TRIM(cargo) != ''", "TRIM(votavel) != ''"]
    args = []
    if ufs:
        where.append("uf IN (" + ",".join("?" for _ in ufs) + ")")
        args.extend(ufs)
    if turn is not None:
        where.append("CAST(turno AS INTEGER)=?")
        args.append(int(turn))
    sql = """SELECT uf,municipio,zona,turno,COUNT(*)
             FROM votes WHERE """ + " AND ".join(where) + """
             GROUP BY uf,municipio,zona,turno
             ORDER BY uf,municipio,zona,turno"""
    groups = {}
    n = 0
    for uf, mu, zone, tu, qty in db.execute(sql, args):
        k = (str(uf).upper(), canonical(mu), canonical(zone), canonical(tu))
        if not all(k):
            continue
        if k not in groups:
            groups[k] = {"key": k, "ufs": set(), "municipios": set(),
                         "zonas": set(), "turnos": set(), "rows": 0}
        item = groups[k]
        item["ufs"].add(str(uf))
        item["municipios"].add(str(mu))
        item["zonas"].add(str(zone))
        item["turnos"].add(str(tu))
        item["rows"] += int(qty)
        n += int(qty)
    tasks = sorted(groups.values(), key=key_sort)
    return tasks, n


def cached_tasks_from_db(db, ufs, turn, output):
    """Cache de planejamento; nao refaz GROUP BY nacional apos interrupcao."""
    imports = list(db.execute(
        """SELECT resource_key,sha256,rows FROM imports
           WHERE resource_key LIKE 'bu:%'
              OR resource_key LIKE 'secao:%'
              OR resource_key LIKE 'secao_nacional:%'
           ORDER BY resource_key"""))
    changes = list(db.execute(
        "SELECT resource_key,sha256,updated_utc FROM import_progress "
        "ORDER BY resource_key"))
    identity = json.dumps(
        {"schema": "zone-plan-v1", "algorithm": VERSION,
         "imports": imports, "partial_imports": changes,
         "ufs": sorted(ufs), "turn": turn},
        ensure_ascii=False, sort_keys=True)
    checksum = hashlib.sha256(identity.encode("utf-8")).hexdigest()
    cache_dir = Path(output).parent / "reconciliacao_checkpoints" / "plans"
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_path = cache_dir / (checksum + ".json.gz")
    if cache_path.is_file():
        with gzip.open(cache_path, "rt", encoding="utf-8") as stream:
            payload = json.load(stream)
        tasks = [{
            "key": tuple(x["key"]), "ufs": set(x["ufs"]),
            "municipios": set(x["municipios"]), "zonas": set(x["zonas"]),
            "turnos": set(x["turnos"]), "rows": x["rows"]}
            for x in payload["tasks"]]
        print(f"PLANO REUTILIZADO: {len(tasks):,} zonas do cache "
              "(sem repetir GROUP BY nacional).", flush=True)
        return tasks, payload["total_rows"]
    tasks, total_rows = tasks_from_db(db, ufs, turn)
    payload = {
        "total_rows": total_rows,
        "tasks": [{"key": x["key"],
                   "ufs": sorted(x["ufs"]),
                   "municipios": sorted(x["municipios"]),
                   "zonas": sorted(x["zonas"]),
                   "turnos": sorted(x["turnos"]),
                   "rows": x["rows"]} for x in tasks]}
    tmp = cache_dir / (checksum + ".tmp")
    try:
        with gzip.open(tmp, "wt", encoding="utf-8") as stream:
            json.dump(payload, stream, ensure_ascii=False)
        os.replace(tmp, cache_path)
    finally:
        if tmp.exists():
            tmp.unlink()
    print(f"PLANO PRESERVADO: {cache_path}", flush=True)
    return tasks, total_rows


def source_fingerprint(db, tasks, ufs, turn):
    try:
        source = [
            {"key": k, "sha256": sha, "rows": n}
            for k, sha, n in db.execute(
                """SELECT resource_key,sha256,rows FROM imports
                   WHERE resource_key LIKE 'bu:%'
                      OR resource_key LIKE 'secao:%'
                      OR resource_key LIKE 'secao_nacional:%'
                   ORDER BY resource_key""")]
    except sqlite3.OperationalError:
        source = []
    try:
        incomplete = [
            {"resource": key, "sha256": sha}
            for key, sha in db.execute(
                "SELECT resource_key,sha256 FROM import_progress "
                "ORDER BY resource_key")
        ]
    except sqlite3.OperationalError:
        incomplete = []
    info = {"algo": VERSION, "sources": source,
            "imports_incomplete": incomplete, "ufs": sorted(ufs),
            "turn": turn, "rows": sum(t["rows"] for t in tasks),
            "groups": len(tasks)}
    return hashlib.sha256(json.dumps(
        info, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest(), info


def state_schema(db):
    db.execute("""CREATE TABLE IF NOT EXISTS completed (
        fingerprint TEXT NOT NULL, task_key TEXT NOT NULL,
        checked INTEGER NOT NULL, different INTEGER NOT NULL,
        missing_bu INTEGER NOT NULL, missing_section INTEGER NOT NULL,
        digest TEXT NOT NULL, completed_utc TEXT NOT NULL,
        PRIMARY KEY(fingerprint, task_key)
    )""")
    db.commit()


def sql_group_for_task(task):
    # Usar igualdade/IN nos prefixos do índice (uf,municipio,zona,...).
    where = []
    params = []
    for column, values in (("uf", task["ufs"]), ("municipio", task["municipios"]),
                           ("zona", task["zonas"]), ("turno", task["turnos"])):
        group = sorted(values)
        where.append(column + " IN (" + ",".join("?" for _ in group) + ")")
        params.extend(group)
    where.extend(("source_kind IN ('bu','secao','secao_nacional')",
                  "(source_kind != 'secao_nacional' OR cargo IN ('1','presidente'))",
                  "votos IS NOT NULL",
                  "TRIM(votavel) != ''", "TRIM(cargo) != ''",
                  "TRIM(secao) != ''"))
    sql = """
    WITH grouped AS (
        SELECT source_kind AS origem, UPPER(TRIM(uf)) AS uf,
               CAST(municipio AS INTEGER) AS municipio,
               CAST(zona AS INTEGER) AS zona, CAST(secao AS INTEGER) AS secao,
               CAST(turno AS INTEGER) AS turno, LOWER(TRIM(cargo)) AS cargo,
               CASE WHEN TRIM(votavel) != ''
                      AND TRIM(votavel) NOT GLOB '*[^0-9]*'
                    THEN CAST(CAST(votavel AS INTEGER) AS TEXT)
                    ELSE UPPER(TRIM(votavel)) END AS votavel,
               SUM(votos) AS votos
        FROM votes INDEXED BY idx_votes_lookup WHERE """ + " AND ".join(where) + """
        GROUP BY origem,uf,municipio,zona,secao,turno,cargo,votavel
    ),
    bu AS (SELECT * FROM grouped WHERE origem='bu'),
    sec_state AS (SELECT * FROM grouped WHERE origem='secao'),
    sec_national AS (SELECT * FROM grouped WHERE origem='secao_nacional' AND cargo='1'),
    -- Fonte estadual tem precedencia por CHAVE exata. O arquivo nacional
    -- complementa somente os votos presidenciais que nao constam nele.
    -- Nunca somar linhas estaduais e nacionais para a mesma chave.
    sec AS (
        SELECT * FROM sec_state
        UNION ALL
        SELECT n.* FROM sec_national n
        WHERE NOT EXISTS (
            SELECT 1 FROM sec_state s
            WHERE s.uf=n.uf AND s.municipio=n.municipio AND
                  s.zona=n.zona AND s.secao=n.secao AND
                  s.turno=n.turno AND s.cargo=n.cargo AND
                  s.votavel=n.votavel
        )
    )
    SELECT b.uf,b.municipio,b.zona,b.secao,b.turno,b.cargo,b.votavel,
           b.votos,s.votos
    FROM bu b LEFT JOIN sec s ON
       b.uf=s.uf AND b.municipio=s.municipio AND b.zona=s.zona
       AND b.secao=s.secao AND b.turno=s.turno AND b.cargo=s.cargo
       AND b.votavel=s.votavel
    UNION ALL
    SELECT s.uf,s.municipio,s.zona,s.secao,s.turno,s.cargo,s.votavel,
           NULL,s.votos
    FROM sec s LEFT JOIN bu b ON
       b.uf=s.uf AND b.municipio=s.municipio AND b.zona=s.zona
       AND b.secao=s.secao AND b.turno=s.turno AND b.cargo=s.cargo
       AND b.votavel=s.votavel
    WHERE b.uf IS NULL
    """
    return sql, params * 1


def compare_task(db, task, tmp_csv):
    checked = different = missing_bu = missing_section = 0
    sql, params = sql_group_for_task(task)
    with Path(tmp_csv).open("w", newline="", encoding="utf-8") as output:
        writer = csv.writer(output, delimiter=";")
        writer.writerow(HEADER)
        for uf, mu, zo, se, turn, ca, vo, b, v in db.execute(sql, params):
            checked += 1
            if b is None:
                status = "SEM_BU"
                missing_bu += 1
            elif v is None:
                status = "SEM_SECAO"
                missing_section += 1
            elif b != v:
                status = "DIFERENTE"
            else:
                continue
            different += 1
            writer.writerow((uf, mu, zo, se, turn, ca, vo, b, v,
                             b - v if b is not None and v is not None else "",
                             status))
        output.flush()
        os.fsync(output.fileno())
    return checked, different, missing_bu, missing_section


def eta_text(seconds):
    if not (seconds >= 0 and seconds < 10**9):
        return "indisponivel"
    minutes = round(seconds / 60)
    if minutes < 1:
        return "menos de 1 min"
    if minutes < 60:
        return f"aprox. {minutes} min"
    return f"aprox. {minutes // 60} h {minutes % 60} min"


def atomic_json(path, data):
    path = Path(path)
    temp = Path(str(path) + ".tmp")
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(temp, path)


def reconcile_resumable(db, output, ufs=None, turn=None, after_chunk=None, workers=4):
    """Compara com leitura indexada por zona; N processos em paralelo.

    Mantem o mesmo fingerprint v2 e aproveita checkpoints anteriores:
    a mudanca e de desempenho, nao da regra de comparacao.
    """
    from collections import deque
    from concurrent.futures import ProcessPoolExecutor, wait, FIRST_COMPLETED
    from reconcile_fast import compare_task_fast, process_task

    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    ufs = [str(x).upper() for x in (ufs or [])]
    print("RECONCILIACAO RAPIDA: indice SQLite + agregacao local, sem "
          "CTEs e JOINs pesados; prioridade estadual e complemento "
          "nacional para Presidente.", flush=True)
    begin_plan = time.monotonic()
    tasks, total_rows = cached_tasks_from_db(db, ufs, turn, output)
    fingerprint, provenance = source_fingerprint(db, tasks, ufs, turn)
    checkpoint_dir = output.parent / "reconciliacao_checkpoints" / fingerprint
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    checkpoint = sqlite3.connect(
        output.parent / "reconciliacao_checkpoints" / "estado.sqlite3",
        timeout=60)
    state_schema(checkpoint)
    files_dir = checkpoint_dir / "partes"
    files_dir.mkdir(parents=True, exist_ok=True)
    print(f"PLANO PRONTO: {len(tasks):,} zonas/turnos; "
          f"{total_rows:,} linhas; planejamento em "
          f"{time.monotonic()-begin_plan:.1f}s.", flush=True)
    if not tasks:
        checkpoint.close()
        raise ValueError("Nao ha votos BU ou secao com chaves completas.")
    atomic_json(checkpoint_dir / "fontes_e_parametros.json", provenance)
    if provenance["imports_incomplete"]:
        print("AVISO: importacoes parciais; resultado sera marcado como parcial.",
              flush=True)

    database = next((row[2] for row in db.execute("PRAGMA database_list")
                     if row[1] == "main"), "")
    requested_workers = max(1, min(8, int(workers)))
    actual_workers = requested_workers if database and Path(database).is_file() else 1
    print(f"PROCESSAMENTO: {actual_workers} processo(s); "
          f"{'paralelo' if actual_workers > 1 else 'sequencial'}; "
          "cada zona concluida gera um checkpoint. "
          "O ganho depende da velocidade do disco.", flush=True)

    checked = different = missing_bu = missing_sec = 0
    done = resumed = done_rows = 0
    new_work_rows = new_work_tasks = 0
    new_work_seconds = 0.0
    total = len(tasks)
    started = time.monotonic()
    processing_start = None
    pending = deque()
    executor = None

    def update_progress():
        nonlocal done
        if done <= 2 or done % 20 == 0 or done == total:
            pct = 100.0 * done_rows / total_rows if total_rows else 100.0
            if new_work_tasks < 5 or new_work_rows == 0:
                eta = "calculando com os primeiros grupos"
            else:
                elapsed = ((time.monotonic()-processing_start)
                           if actual_workers > 1 and processing_start is not None
                           else new_work_seconds)
                eta = eta_text((total_rows-done_rows)
                               * elapsed / new_work_rows)
            if done == total:
                eta = "grupos completos; falta consolidar o relatorio"
            print(f"PROGRESSO: {done:,}/{total:,} zonas, {pct:.1f}% das linhas; "
                  f"{resumed:,} reutilizadas; {different:,} diferencas; "
                  f"ETA {eta} (aproximada).", flush=True)

    def save_completed(index, task, result, part, duration, was_cached=False):
        nonlocal checked, different, missing_bu, missing_sec
        nonlocal done, resumed, done_rows, new_work_rows, new_work_tasks
        nonlocal new_work_seconds
        nchecked, ndiff, nb, ns = result
        if was_cached:
            resumed += 1
        else:
            temp = part.with_suffix(".csv.part")
            digest = sha256_file(temp)
            os.replace(temp, part)
            checkpoint.execute(
                """INSERT OR REPLACE INTO completed VALUES (?,?,?,?,?,?,?,?)""",
                (fingerprint, "|".join(task["key"]), nchecked, ndiff,
                 nb, ns, digest, utc()))
            checkpoint.commit()
            new_work_rows += task["rows"]
            new_work_tasks += 1
            new_work_seconds += duration
        checked += nchecked
        different += ndiff
        missing_bu += nb
        missing_sec += ns
        done += 1
        done_rows += task["rows"]
        update_progress()
        if after_chunk:
            after_chunk(index, task)

    try:
        for index, task in enumerate(tasks, 1):
            key = "|".join(task["key"])
            slug = hashlib.sha256(key.encode("utf-8")).hexdigest()[:24]
            part = files_dir / (slug + ".csv")
            old = checkpoint.execute(
                """SELECT checked,different,missing_bu,missing_section,digest
                   FROM completed WHERE fingerprint=? AND task_key=?""",
                (fingerprint, key)).fetchone()
            if old and part.is_file() and sha256_file(part) == old[4]:
                save_completed(index, task, old[:4], part, 0.0, True)
            else:
                pending.append((index, task, part))

        processing_start = time.monotonic()
        if actual_workers == 1:
            while pending:
                index, task, part = pending.popleft()
                temp = part.with_suffix(".csv.part")
                clock = time.monotonic()
                try:
                    result = compare_task_fast(db, task, temp)
                    save_completed(index, task, result, part,
                                   time.monotonic()-clock)
                finally:
                    if temp.exists():
                        temp.unlink()
        else:
            executor = ProcessPoolExecutor(max_workers=actual_workers)
            inflight = {}
            # Fila limitada para nao sobrecarregar disco ou memoria.
            while pending or inflight:
                while pending and len(inflight) < actual_workers * 2:
                    index, task, part = pending.popleft()
                    temp = part.with_suffix(".csv.part")
                    t0 = time.monotonic()
                    future = executor.submit(process_task, database, task, str(temp))
                    inflight[future] = (index, task, part, t0)
                finished, _ = wait(tuple(inflight), return_when=FIRST_COMPLETED)
                for future in finished:
                    index, task, part, t0 = inflight.pop(future)
                    temp = part.with_suffix(".csv.part")
                    try:
                        result = future.result()
                        save_completed(index, task, result, part,
                                       time.monotonic()-t0)
                    finally:
                        if temp.exists():
                            temp.unlink()
            executor.shutdown(wait=True)
            executor = None

        print("RECONCILIACAO: consolidando somente divergencias ...",
              flush=True)
        temp_final = output.with_suffix(output.suffix + ".part")
        try:
            with temp_final.open("w", encoding="utf-8-sig", newline="") as out:
                out.write(";".join(HEADER) + "\n")
                for task in tasks:
                    slug = hashlib.sha256(
                        "|".join(task["key"]).encode("utf-8")).hexdigest()[:24]
                    with (files_dir / (slug + ".csv")).open(
                            "r", encoding="utf-8", newline="") as stream:
                        next(stream, None)
                        shutil.copyfileobj(stream, out)
            os.replace(temp_final, output)
        finally:
            if temp_final.exists():
                temp_final.unlink()

        summary = {
            "created_at_utc": utc(), "engine": VERSION,
            "execution_engine": "single-indexed-scan-per-zone",
            "workers": actual_workers,
            "status": ("calculado_com_importacoes_incompletas"
                       if provenance["imports_incomplete"] else "concluido"),
            "cobertura_nacional_confirmada": False,
            "importacoes_incompletas": provenance["imports_incomplete"],
            "fingerprint": fingerprint, "turn": turn, "ufs": ufs or "todas",
            "tasks_completed": done, "tasks_total": total,
            "source_rows_planned": total_rows,
            "keys_compared": checked, "different_or_missing": different,
            "missing_bu": missing_bu, "missing_section": missing_sec,
            "matches": checked - different, "reused_tasks": resumed,
            "csv": str(output), "checkpoint_folder": str(checkpoint_dir),
            "section_source_priority":
                "secao estadual por chave; secao_nacional so cargo 1; sem somar",
            "limitations": "Chaves existentes nas fontes oficiais; "
                           "comparacao nao e auditoria independente da urna."
        }
        atomic_json(output.with_suffix(".summary.json"), summary)
        print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)
        return summary
    except BaseException:
        checkpoint.rollback()
        if executor is not None:
            executor.shutdown(wait=False, cancel_futures=True)
        print(f"RECONCILIACAO INTERROMPIDA: {done:,}/{total:,} zonas "
              "preservadas; basta reexecutar para retomar.",
              file=sys.stderr, flush=True)
        raise
    finally:
        checkpoint.close()
