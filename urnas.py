#!/usr/bin/env python3
"""Gerenciador de dados oficiais de urna do TSE 2026.

Sem dependencias externas: catalogo CKAN, downloads retomaveis,
arquivo original com SHA-256 e indexacao consultavel em SQLite.
O CSV do BU e o CSV de votacao por secao sao importados. BU/RDV
binarios sao preservados, catalogados, mas NAO sao decodificados aqui.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import re
import shutil
import sqlite3
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path

API = "https://dadosabertos.tse.jus.br/api/3/action"
DATASETS = {
    "bu": "resultados-2026-boletim-de-urna",
    "secao": "resultados-2026",
    "artefatos": "resultados-2026-arquivos-transmitidos-para-totalizacao",
}
UF_SET = set("AC AL AM AP BA CE DF ES GO MA MG MS MT PA PB PE PI PR RJ RN RO RR RS SC SE SP TO ZZ".split())
USER_AGENT = "TSE-forensics-urnas/1.0 (public-data research)"


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def root_path(value):
    if value:
        return Path(value).expanduser()
    if os.name == "nt":
        if Path("H:/").is_dir():
            return Path("H:/TSE/forensics/urnas")
        raise SystemExit("O drive H: nao esta disponivel. Use --root DRIVE:/pasta. Nada sera gravado no C:.")
    return Path(os.environ.get("TSE_URNAS_DIR", "./data/forensics/urnas"))


def sha256_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def atomic_json(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    part = path.with_suffix(path.suffix + ".tmp")
    part.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(part, path)


def request(url, headers=None):
    parsed = urllib.parse.urlparse(url)
    host = (parsed.hostname or "").lower()
    if parsed.scheme != "https" or not (host == "tse.jus.br" or host.endswith(".tse.jus.br")):
        raise ValueError("URL rejeitada: origem nao oficial do TSE: " + url)
    hdr = {"User-Agent": USER_AGENT}
    if headers:
        hdr.update(headers)
    return urllib.request.Request(url, headers=hdr)


def get_json(url):
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request(url), timeout=90) as response:
                return json.load(response)
        except (urllib.error.URLError, TimeoutError):
            if attempt == 2:
                raise
            time.sleep(attempt + 1)


def catalog():
    found = {}
    for kind, slug in DATASETS.items():
        obj = get_json(API + "/package_show?id=" + urllib.parse.quote(slug))
        if not obj.get("success"):
            raise RuntimeError("Catalogo sem resposta valida: " + slug)
        found[kind] = obj["result"]
    return found


def safe_name(raw):
    value = re.sub(r"[^A-Za-z0-9._-]+", "_", str(raw))
    return value[:180] or "recurso"


def uf_from_resource(resource):
    name = str(resource.get("name", ""))
    url = str(resource.get("url", ""))
    candidate = re.search(r"^\s*(AC|AL|AM|AP|BA|CE|DF|ES|GO|MA|MG|MS|MT|PA|PB|PE|PI|PR|RJ|RN|RO|RR|RS|SC|SE|SP|TO|ZZ)\s*[-_]", name.upper())
    if candidate:
        return candidate.group(1)
    filename = urllib.parse.unquote(Path(urllib.parse.urlparse(url).path).name).upper()
    for pattern in (r"BWEB_[12]T_([A-Z]{2})_", r"_(AC|AL|AM|AP|BA|CE|DF|ES|GO|MA|MG|MS|MT|PA|PB|PE|PI|PR|RJ|RN|RO|RR|RS|SC|SE|SP|TO|ZZ)(?:_|\.)"):
        match = re.search(pattern, filename)
        if match and match.group(1) in UF_SET:
            return match.group(1)
    return None


def select_resources(datasets, kinds, ufs, turn):
    selected = []
    for kind in kinds:
        for r in datasets[kind].get("resources", []):
            name = (str(r.get("name", "")) + " " + str(r.get("url", ""))).lower()
            # Para o conjunto 'resultados-2026', selecionar exclusivamente votos por secao.
            if kind == "secao" and not ("seção eleitoral" in name or "secao" in name or "seção" in name):
                continue
            if kind == "bu":
                # Inclui os respectivos arquivos oficiais de hashes SHA2.
                if not ("boletim" in name or "bweb" in name or "hash" in name):
                    continue
            if turn:
                is_t1 = bool(re.search(r"1[oº°]?\s*turno|primeiro turno|1t", name))
                is_t2 = bool(re.search(r"2[oº°]?\s*turno|segundo turno|2t", name))
                if turn == 1 and is_t2:
                    continue
                if turn == 2 and is_t1:
                    continue
            uf = uf_from_resource(r)
            if ufs and uf not in ufs:
                continue
            url = str(r.get("url") or "")
            if not url:
                continue
            selected.append((kind, uf or "BR", r))
    return selected


def resource_path(root, kind, uf, resource):
    url = str(resource["url"])
    filename = safe_name(Path(urllib.parse.unquote(urllib.parse.urlparse(url).path)).name)
    if filename in (".", "", "recurso"):
        filename = safe_name(resource.get("name", "arquivo"))
    prefix = safe_name(str(resource.get("id", "sem-id")))[:12]
    return root / "raw" / kind / uf / (prefix + "--" + filename)


def free_enough(root, minimum_bytes, remaining=0):
    anchor = root
    while not anchor.exists() and anchor != anchor.parent:
        anchor = anchor.parent
    free = shutil.disk_usage(anchor).free
    if free < minimum_bytes + remaining:
        raise OSError(f"Espaco insuficiente em {anchor}: livres={free:,} bytes, "
                      f"reserva={minimum_bytes:,}, ainda necessários={remaining:,}")


def find_legacy(resource, legacy):
    if not legacy or not legacy.exists():
        return None
    url_name = safe_name(Path(urllib.parse.urlparse(resource["url"]).path).name)
    key = safe_name(str(resource.get("id", "")))[:12]
    for item in legacy.rglob(key + "--" + url_name):
        if item.is_file() and item.stat().st_size:
            return item
    return None


def download(root, kind, uf, resource, reserve, legacy=None):
    dest = resource_path(root, kind, uf, resource)
    state_file = Path(str(dest) + ".meta.json")
    url = resource["url"]
    expected_size = int(resource.get("size") or 0)
    state = {}
    if state_file.exists():
        try:
            state = json.loads(state_file.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            pass

    if dest.exists() and dest.stat().st_size:
        size = dest.stat().st_size
        digest = sha256_file(dest)
        if size == expected_size or not expected_size:
            if not state.get("sha256") or state["sha256"] == digest:
                if not state:
                    atomic_json(state_file, {"source_url": url, "sha256": digest, "bytes": size,
                                             "verified_at_utc": now(), "adopted_existing": True})
                print(f"REUTILIZADO {kind}/{uf} {dest.name} ({size:,} bytes)")
                return dest, digest
        raise RuntimeError("Arquivo local diverge do esperado; revisao manual necessaria: " + str(dest))

    legacy_source = find_legacy(resource, legacy)
    if legacy_source:
        free_enough(root, reserve, legacy_source.stat().st_size)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(legacy_source, dest)
        digest = sha256_file(dest)
        atomic_json(state_file, {"source_url": url, "sha256": digest,
                                 "bytes": dest.stat().st_size, "migrated_from": str(legacy_source), "checked_at_utc": now()})
        print(f"COPIADO DO ACERVO ANTERIOR: {dest.name}")
        return dest, digest

    dest.parent.mkdir(parents=True, exist_ok=True)
    part = Path(str(dest) + ".part")
    offset = part.stat().st_size if part.exists() else 0
    free_enough(root, reserve, max(0, expected_size - offset))
    headers = {"Range": f"bytes={offset}-"} if offset else {}
    response = urllib.request.urlopen(request(url, headers), timeout=120)
    code = response.status
    if offset and code == 206:
        content_range = response.headers.get("Content-Range", "")
        if not content_range.startswith(f"bytes {offset}-"):
            response.close()
            raise RuntimeError("Content-Range inesperado; download interrompido")
        mode = "ab"
    else:
        # Um servidor que ignora Range devolve 200. Nunca concatenar o arquivo inteiro.
        mode = "wb"
        offset = 0
    counter = offset
    digest = hashlib.sha256()
    if offset:
        with part.open("rb") as previous:
            for b in iter(lambda: previous.read(4 * 1024 * 1024), b""):
                digest.update(b)
    try:
        with response, part.open(mode) as out:
            for block in iter(lambda: response.read(1024 * 1024), b""):
                free_enough(root, reserve)
                out.write(block)
                digest.update(block)
                counter += len(block)
            out.flush()
            os.fsync(out.fileno())
    except Exception:
        print(f"PARCIAL preservado: {part} ({counter:,} bytes)")
        raise
    if expected_size and counter != expected_size:
        raise RuntimeError(f"Tamanho divergente (recebido {counter}, esperado {expected_size})")
    if zipfile.is_zipfile(part):
        with zipfile.ZipFile(part) as z:
            bad = z.testzip()
            if bad:
                raise RuntimeError("ZIP corrompido em " + bad)
    os.replace(part, dest)
    digest_hex = digest.hexdigest()
    atomic_json(state_file, {"source_url": url, "resource_id": resource.get("id"),
                             "resource_name": resource.get("name"),
                             "bytes": counter, "sha256": digest_hex,
                             "downloaded_at_utc": now()})
    print(f"BAIXADO {kind}/{uf}: {dest.name} ({counter:,} bytes) SHA256={digest_hex}")
    return dest, digest_hex


def normalize_headers(headers):
    result = []
    used = set()
    for index, item in enumerate(headers):
        name = str(item or "").replace("\ufeff", "").strip().upper()
        if not name:
            name = "COL_" + str(index)
        while name in used:
            name += "_DUP"
        used.add(name)
        result.append(name)
    return result


def field(row, *names):
    for name in names:
        x = row.get(name)
        if x is not None and str(x).strip() != "":
            return str(x).strip()
    return ""


def numeric(value):
    x = str(value).strip()
    if re.fullmatch(r"[+-]?\d+", x):
        return int(x)
    return None


def schema(db):
    db.execute("""CREATE TABLE IF NOT EXISTS imports (
        resource_key TEXT PRIMARY KEY, sha256 TEXT NOT NULL,
        imported_utc TEXT NOT NULL, rows INTEGER NOT NULL, files INTEGER NOT NULL
    )""")
    db.execute("""CREATE TABLE IF NOT EXISTS votes (
        resource_key TEXT NOT NULL, member TEXT NOT NULL, line INTEGER NOT NULL,
        source_kind TEXT NOT NULL, uf TEXT, municipio TEXT,
        zona TEXT, secao TEXT, turno TEXT, cargo TEXT, votavel TEXT,
        votos INTEGER, dados_json TEXT NOT NULL,
        PRIMARY KEY(resource_key,member,line)
    )""")
    db.execute("""CREATE TABLE IF NOT EXISTS archive_entries (
        resource_key TEXT NOT NULL, member TEXT NOT NULL,
        bytes INTEGER, extensao TEXT, PRIMARY KEY(resource_key,member)
    )""")
    db.execute("CREATE INDEX IF NOT EXISTS idx_votes_lookup ON votes(uf,municipio,zona,secao,turno,cargo,votavel)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_votes_kind ON votes(source_kind,uf,turno)")


def open_csv(stream):
    # Os CSVs do TSE normalmente usam Latin-1 e separador ponto e virgula.
    # Encodings tentados no inicio, sem ler o arquivo inteiro.
    peek = stream.read(4096)
    stream.seek(0)
    enc = "utf-8-sig"
    try:
        peek.decode(enc)
    except UnicodeDecodeError:
        enc = "latin-1"
    text = io.TextIOWrapper(stream, encoding=enc, errors="replace", newline="")
    # CSV oficial do TSE: delimiter=';' e campos entre aspas.
    return csv.DictReader(text, delimiter=";", quotechar='"')


def import_file(db, path, kind, key, digest):
    previous = db.execute("SELECT sha256 FROM imports WHERE resource_key=?", (key,)).fetchone()
    if previous and previous[0] == digest:
        print(f"INDEXADO ANTERIORMENTE: {path.name}")
        return 0
    db.execute("BEGIN")
    count = 0
    csv_count = 0
    try:
        db.execute("DELETE FROM votes WHERE resource_key=?", (key,))
        db.execute("DELETE FROM archive_entries WHERE resource_key=?", (key,))
        files = []
        if zipfile.is_zipfile(path):
            with zipfile.ZipFile(path) as archive:
                for info in archive.infolist():
                    if info.is_dir():
                        continue
                    ext = Path(info.filename).suffix.lower()
                    db.execute("INSERT INTO archive_entries VALUES(?,?,?,?)",
                               (key, info.filename, info.file_size, ext))
                    if kind in ("bu", "secao") and ext == ".csv":
                        with archive.open(info) as stream:
                            count += import_csv_stream(db, stream, key, info.filename, kind)
                        csv_count += 1
        elif path.suffix.lower() == ".csv" and kind in ("bu", "secao"):
            with path.open("rb") as stream:
                count += import_csv_stream(db, stream, key, path.name, kind)
            csv_count = 1
        db.execute("INSERT OR REPLACE INTO imports VALUES (?,?,?,?,?)",
                   (key, digest, now(), count, csv_count))
        db.commit()
        print(f"INDEXADO {kind} {path.name}: {count:,} linhas / {csv_count} CSV; "
              "binarios mantidos no arquivo original")
        return count
    except Exception:
        db.rollback()
        raise


def import_csv_stream(db, stream, key, member, kind):
    reader = open_csv(stream)
    if not reader.fieldnames:
        return 0
    headers = normalize_headers(reader.fieldnames)
    # Restaurar o mapeamento original mesmo com colunas repetidas.
    batch = []
    count = 0
    for line, values in enumerate(reader, start=2):
        if None in values:
            raise ValueError(f"CSV inconsistente {member} na linha {line}: numero excessivo de colunas")
        obj = {headers[i]: values.get(name, "") for i, name in enumerate(reader.fieldnames)}
        uf = field(obj, "SG_UF")
        municipio = field(obj, "CD_MUNICIPIO")
        zona = field(obj, "NR_ZONA")
        secao = field(obj, "NR_SECAO")
        turno = field(obj, "NR_TURNO")
        cargo = field(obj, "DS_CARGO_PERGUNTA", "DS_CARGO")
        votavel = field(obj, "NR_VOTAVEL")
        votos = numeric(field(obj, "QT_VOTOS"))
        batch.append((key, member, line, kind, uf, municipio, zona, secao,
                      turno, cargo, votavel, votos, json.dumps(obj, ensure_ascii=False)))
        if len(batch) >= 2000:
            db.executemany("INSERT INTO votes VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)", batch)
            count += len(batch)
            batch.clear()
    if batch:
        db.executemany("INSERT INTO votes VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)", batch)
        count += len(batch)
    return count


def export_rows(db, output, ufs, municipio, zona, secao, turn, kind, candidate):
    conditions = []
    args = []
    for column, value in (("uf", ufs[0] if len(ufs) == 1 else None),
                          ("municipio", municipio), ("zona", zona), ("secao", secao),
                          ("turno", str(turn) if turn else None), ("source_kind", kind),
                          ("votavel", candidate)):
        if value:
            conditions.append(column + " = ?")
            args.append(str(value))
    if len(ufs) > 1:
        conditions.append("uf IN (" + ",".join("?" for _ in ufs) + ")")
        args.extend(ufs)
    sql = ("SELECT source_kind,uf,municipio,zona,secao,turno,cargo,votavel,votos,"
           "dados_json,member,line FROM votes")
    if conditions:
        sql += " WHERE " + " AND ".join(conditions)
    sql += " ORDER BY uf,municipio,zona,secao,turno,cargo,votavel"
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.writer(file, delimiter=";")
        writer.writerow(["fonte","uf","municipio","zona","secao","turno","cargo",
                         "votavel","votos","dados_json","arquivo_interno","linha"])
        counter = 0
        for row in db.execute(sql, args):
            writer.writerow(row)
            counter += 1
    print(f"EXPORTADO {counter:,} registros: {output}")


def main():
    parser = argparse.ArgumentParser(
        description="Gerenciador TSE: consultar, baixar sob demanda, validar e tornar BU/sections consultaveis")
    parser.add_argument("action", choices=("status", "fetch", "import", "export", "verify"),
                        help="status=apenas consultar; fetch=baixar e importar; import=processar arquivos locais")
    parser.add_argument("--root", help="Diretorio de dados (padrao no Windows: H:/TSE/forensics/urnas)")
    parser.add_argument("--kind", choices=("bu", "secao", "artefatos"), action="append",
                        help="Tipo; pode repetir. Padrao: bu + secao.")
    parser.add_argument("--uf", action="append", type=str.upper, default=[],
                        help="UF; pode repetir. Obrigatoria para fetch sem --all.")
    parser.add_argument("--all", action="store_true", help="Baixar para todas UFs (operacao volumosa)")
    parser.add_argument("--turn", type=int, choices=(1,2), default=1)
    parser.add_argument("--municipio", help="Codigo TSE para exportacao por secao")
    parser.add_argument("--zona", help="Zona eleitoral para exportacao")
    parser.add_argument("--secao", help="Secao eleitoral para exportacao")
    parser.add_argument("--candidate", help="Numero do votavel para exportacao")
    parser.add_argument("--output", help="Caminho do CSV exportado")
    parser.add_argument("--reserve-gb", type=float, default=2.0,
                        help="Espaco livre minimo adicional, padrao 2 GB")
    parser.add_argument("--no-import", action="store_true", help="Somente baixar e validar (nao importar CSV)")
    args = parser.parse_args()

    if any(uf not in UF_SET for uf in args.uf):
        parser.error("UF invalida")
    if args.action == "fetch" and not args.all and not args.uf:
        parser.error("Para evitar download nacional acidental, especifique --uf XX ou --all")
    if args.action == "fetch" and (args.municipio or args.zona or args.secao):
        parser.error("O catalogo distribui ZIP por UF. Baixe com --uf e depois use export --municipio/--zona/--secao")
    root = root_path(args.root)
    kinds = args.kind or (["bu", "secao"] if args.action != "verify" else list(DATASETS))
    kinds = list(dict.fromkeys(kinds))
    if args.action in ("status", "fetch"):
        datasets = catalog()
        atomic_json(root / "catalogo_latest.json", {
            "checked_at_utc": now(),
            "datasets": {k: {"title": v.get("title"), "resources": v.get("resources", [])}
                         for k, v in datasets.items()}})
        selected = select_resources(datasets, kinds, args.uf if not args.all else [], args.turn)
        print(f"Catalogo: {len(selected)} recursos selecionados (tipos={','.join(kinds)}, UFs={args.uf or 'todas'})")
        for kind, uf, resource in selected:
            path = resource_path(root, kind, uf, resource)
            print(f"  {kind:9s} {uf}: {resource.get('name')} "
                  f"| bytes={resource.get('size') or '?'} "
                  f"| {'LOCAL' if path.exists() else 'REMOTO'}")
        if args.action == "status":
            return
        if not selected:
            raise SystemExit("Nenhum recurso localizado. Nenhum download foi realizado.")
        minimum_bytes = int(args.reserve_gb * (1024 ** 3))
        legacy = Path("data/forensics/portal/files")
        db = None
        if not args.no_import:
            (root / "analysis").mkdir(parents=True, exist_ok=True)
            db = sqlite3.connect(root / "analysis" / "urna_2026.sqlite3", timeout=90)
            schema(db)
            db.commit()
        try:
            for kind, uf, resource in selected:
                try:
                    path, digest = download(root, kind, uf, resource, minimum_bytes, legacy)
                    if db is not None and kind in ("bu", "secao", "artefatos"):
                        key = kind + ":" + str(resource.get("id") or path.name)
                        import_file(db, path, kind, key, digest)
                except Exception as exc:
                    print(f"ERRO em {kind}/{uf} {resource.get('name')}: {exc}", file=sys.stderr)
                    raise
        finally:
            if db:
                db.close()
        print(f"Concluido. Originais: {root / 'raw'}; consulta: {root / 'analysis' / 'urna_2026.sqlite3'}")
        return

    db_path = root / "analysis" / "urna_2026.sqlite3"
    if args.action in ("export", "import"):
        db_path.parent.mkdir(parents=True, exist_ok=True)
        db = sqlite3.connect(db_path)
        schema(db)
        db.commit()
        try:
            if args.action == "export":
                if not db.execute("SELECT 1 FROM imports LIMIT 1").fetchone():
                    raise SystemExit("Base vazia. Execute fetch primeiro.")
                output = Path(args.output or root / "analysis" / "consulta_urnas.csv")
                export_rows(db, output, args.uf, args.municipio, args.zona,
                            args.secao, args.turn, args.kind[0] if args.kind else None, args.candidate)
            else:
                for path in sorted((root / "raw").rglob("*")):
                    if not path.is_file() or path.name.endswith((".part", ".json")):
                        continue
                    try:
                        kind = path.relative_to(root / "raw").parts[0]
                        if kind not in DATASETS or (args.kind and kind not in args.kind):
                            continue
                        digest = sha256_file(path)
                        import_file(db, path, kind, kind + ":" + path.name.split("--")[0], digest)
                    except Exception as exc:
                        print(f"ERRO indexando {path}: {exc}", file=sys.stderr)
                        raise
        finally:
            db.close()
        return
    if args.action == "verify":
        total = 0
        errors = 0
        for meta in (root / "raw").rglob("*.meta.json"):
            file = Path(str(meta)[:-len(".meta.json")])
            info = json.loads(meta.read_text(encoding="utf-8"))
            ok = file.is_file() and sha256_file(file) == info.get("sha256")
            total += 1
            errors += not ok
            print(("OK  " if ok else "ERRO") + " " + str(file))
        print(f"Verificados: {total}; divergencias: {errors}")
        if errors:
            raise SystemExit(1)


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, RuntimeError, urllib.error.URLError, zipfile.BadZipFile) as exc:
        print("FALHA: " + str(exc), file=sys.stderr)
        sys.exit(1)
