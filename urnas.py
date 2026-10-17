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
            actual_kind = kind
            if kind == "secao":
                if "detalhe" in name and ("seção" in name or "secao" in name):
                    actual_kind = "secao_detalhe"
                elif uf is None and "presidente" in name:
                    # O CSV nacional de Presidente repete secoes presentes
                    # nos CSVs estaduais; nunca somar ambas as fontes.
                    actual_kind = "secao_nacional"
            selected.append((actual_kind, uf or "BR", r))
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


def resource_revision(resource):
    return str(resource.get("last_modified") or resource.get("metadata_modified") or "")


def validate_archived_file(path, expected_size=0, expected_hash=None):
    if not path.exists() or not path.is_file() or path.stat().st_size == 0:
        return None
    if expected_size and path.stat().st_size != expected_size:
        return None
    digest = sha256_file(path)
    if expected_hash and expected_hash != digest:
        return None
    if path.suffix.lower() == ".zip" or zipfile.is_zipfile(path):
        try:
            with zipfile.ZipFile(path) as archive:
                bad = archive.testzip()
                if bad is not None:
                    return None
        except (OSError, zipfile.BadZipFile):
            return None
    return digest


def download(root, kind, uf, resource, reserve, legacy=None):
    """Baixa uma vez, valida, continua .part e preserva revisoes de fonte."""
    dest = resource_path(root, kind, uf, resource)
    state_file = Path(str(dest) + ".meta.json")
    url = str(resource["url"])
    expected_size = int(resource.get("size") or 0)
    official_hash = str(resource.get("hash") or "").strip().lower()
    # O CKAN nem sempre declara o algoritmo; só validar quando e SHA-256.
    official_sha = official_hash if re.fullmatch("[0-9a-f]{64}", official_hash) else None
    revision = resource_revision(resource)
    old_state = {}
    if state_file.exists():
        try:
            old_state = json.loads(state_file.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            pass

    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        old_sha = str(old_state.get("sha256") or "")
        same_revision = not (old_state.get("resource_revision") and revision and
                             old_state["resource_revision"] != revision)
        file_stat = dest.stat()
        # Cache de verificacao anterior: quando o manifesto foi criado depois
        # do arquivo e o tamanho nao mudou, nao reabrir ZIPs enormes.
        # Um 'verify' explicito continua conferindo todos os SHA256.
        source_matches = str(old_state.get("source_url") or "") == url
        prior_verified = any(old_state.get(k) for k in (
            "downloaded_at_utc", "checked_at_utc", "verified_at_utc",
            "recovered_partial", "migrated_from", "adopted_existing"))
        cached = (source_matches and prior_verified and
                  re.fullmatch(r"[0-9a-f]{64}", old_sha) and
                  int(old_state.get("bytes") or -1) == file_stat.st_size and
                  (not expected_size or file_stat.st_size == expected_size) and
                  (not official_sha or official_sha == old_sha) and
                  state_file.exists() and
                  file_stat.st_mtime_ns <= state_file.stat().st_mtime_ns and
                  same_revision)
        if cached:
            print(f"REUTILIZADO (cache verificado) {kind}/{uf}: {dest.name} "
                  f"({file_stat.st_size:,} bytes)", flush=True)
            return dest, old_sha
        print(f"VERIFICANDO SHA-256/ZIP {kind}/{uf}: {dest.name}; "
              "pode demorar em arquivos grandes", flush=True)
        sha = validate_archived_file(dest, expected_size,
                                    official_sha or old_sha or None)
        if sha and same_revision:
            atomic_json(state_file, {
                **old_state, "source_url": url, "sha256": sha,
                "bytes": dest.stat().st_size,
                "resource_revision": revision, "verified_at_utc": now(),
                "adopted_existing": bool(not old_state)})
            print(f"REUTILIZADO {kind}/{uf} {dest.name} ({dest.stat().st_size:,} bytes)")
            return dest, sha
        # Nunca apagar evidencia: uma revisao mais nova fica no destino anterior,
        # enquanto a versao velha fica identificada pelo seu SHA local.
        prior_sha = sha256_file(dest)
        old_dir = root / "previous-versions" / kind / uf
        old_dir.mkdir(parents=True, exist_ok=True)
        preserved = old_dir / (dest.name + "." + prior_sha[:16])
        if preserved.exists():
            if sha256_file(preserved) != prior_sha:
                raise RuntimeError("Colisao de nome na preservacao do arquivo anterior")
            dest.unlink()
        else:
            os.replace(dest, preserved)
        print(f"REVISAO/ARQUIVO INVALIDO: anterior preservado em {preserved}")

    legacy_source = find_legacy(resource, legacy)
    if legacy_source:
        digest = validate_archived_file(legacy_source, expected_size, official_sha)
        if digest:
            # Nao baixar da internet de novo; o dado antigo e copiado para H.
            free_enough(root, reserve, legacy_source.stat().st_size)
            shutil.copy2(legacy_source, dest)
            atomic_json(state_file, {"source_url": url, "sha256": digest,
                                     "bytes": dest.stat().st_size,
                                     "resource_revision": revision,
                                     "migrated_from": str(legacy_source),
                                     "checked_at_utc": now()})
            print(f"REUTILIZADO DO ACERVO ANTERIOR: {dest.name}")
            return dest, digest

    part = Path(str(dest) + ".part")
    offset = part.stat().st_size if part.exists() else 0
    if expected_size and offset == expected_size:
        digest = validate_archived_file(part, expected_size, official_sha)
        if digest:
            os.replace(part, dest)
            atomic_json(state_file, {"source_url": url, "sha256": digest,
                                     "bytes": expected_size, "resource_revision": revision,
                                     "recovered_partial": True, "checked_at_utc": now()})
            print(f"RETOMADO COMPLETO {kind}/{uf}: {dest.name}")
            return dest, digest
    if expected_size and offset > expected_size:
        part.unlink()
        offset = 0
    free_enough(root, reserve, max(0, expected_size - offset))
    headers = {"Range": f"bytes={offset}-"} if offset else {}
    try:
        response = urllib.request.urlopen(request(url, headers), timeout=120)
    except urllib.error.HTTPError as exc:
        if exc.code == 416 and offset:
            # Servidor considera o parcial completo: validar, ou recomecar uma vez.
            digest = validate_archived_file(part, expected_size, official_sha)
            if digest:
                os.replace(part, dest)
                atomic_json(state_file, {"source_url": url, "sha256": digest,
                                         "bytes": dest.stat().st_size,
                                         "resource_revision": revision,
                                         "recovered_partial": True, "checked_at_utc": now()})
                return dest, digest
            part.unlink()
            return download(root, kind, uf, resource, reserve, legacy=None)
        raise
    if offset and response.status == 206:
        content_range = response.headers.get("Content-Range", "")
        if not content_range.startswith(f"bytes {offset}-"):
            response.close()
            raise RuntimeError("Content-Range incorreto: download preservado para diagnostico")
        mode = "ab"
    else:
        # 200 em resposta a Range exige reescrever, nunca concatenar.
        mode = "wb"
        offset = 0
    digest = hashlib.sha256()
    if offset:
        with part.open("rb") as previous:
            for b in iter(lambda: previous.read(4 * 1024 * 1024), b""):
                digest.update(b)
    size = offset
    try:
        with response, part.open(mode) as output:
            for block in iter(lambda: response.read(1024 * 1024), b""):
                free_enough(root, reserve)
                output.write(block)
                digest.update(block)
                size += len(block)
            output.flush()
            os.fsync(output.fileno())
    except Exception:
        print(f"PARCIAL preservado: {part} ({size:,} bytes)")
        raise
    if expected_size and size != expected_size:
        raise RuntimeError(f"Arquivo parcial preservado: {size:,} de {expected_size:,} bytes")
    digest_hex = digest.hexdigest()
    if official_sha and official_sha != digest_hex:
        raise RuntimeError("SHA-256 oficial nao corresponde ao arquivo recebido: " + str(part))
    valid = validate_archived_file(part, expected_size, digest_hex)
    if not valid:
        raise RuntimeError("Arquivo incompleto, corrompido ou ZIP com CRC invalido: " + str(part))
    os.replace(part, dest)
    atomic_json(state_file, {"source_url": url, "resource_id": resource.get("id"),
                             "resource_name": resource.get("name"),
                             "resource_revision": revision, "bytes": size,
                             "sha256": digest_hex, "official_sha256": official_sha,
                             "downloaded_at_utc": now()})
    print(f"BAIXADO {kind}/{uf}: {dest.name} ({size:,} bytes) SHA256={digest_hex}")
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
        imported_utc TEXT NOT NULL, rows INTEGER NOT NULL, files INTEGER NOT NULL,
        parser_version INTEGER NOT NULL DEFAULT 1
    )""")
    cols = {row[1] for row in db.execute("PRAGMA table_info(imports)")}
    if "parser_version" not in cols:
        db.execute("ALTER TABLE imports ADD COLUMN parser_version INTEGER NOT NULL DEFAULT 1")
    db.execute("""CREATE TABLE IF NOT EXISTS votes (
        resource_key TEXT NOT NULL, member TEXT NOT NULL, line INTEGER NOT NULL,
        source_kind TEXT NOT NULL, uf TEXT, municipio TEXT,
        zona TEXT, secao TEXT, turno TEXT, cargo TEXT, votavel TEXT,
        votos INTEGER, dados_json TEXT NOT NULL,
        PRIMARY KEY(resource_key,member,line)
    )""")
    db.execute("""CREATE TABLE IF NOT EXISTS archive_entries (
        resource_key TEXT NOT NULL, member TEXT NOT NULL,
        bytes INTEGER, extensao TEXT, uf TEXT, municipio TEXT,
        zona TEXT, secao TEXT, sha256 TEXT,
        PRIMARY KEY(resource_key,member)
    )""")
    existing = {row[1] for row in db.execute("PRAGMA table_info(archive_entries)")}
    for col in ("uf", "municipio", "zona", "secao", "sha256"):
        if col not in existing:
            db.execute("ALTER TABLE archive_entries ADD COLUMN " + col + " TEXT")
    db.execute("CREATE INDEX IF NOT EXISTS idx_archives_secao "
               "ON archive_entries(uf,municipio,zona,secao,extensao)")
    db.execute("""CREATE TABLE IF NOT EXISTS import_progress (
        resource_key TEXT PRIMARY KEY, sha256 TEXT NOT NULL,
        started_utc TEXT NOT NULL, updated_utc TEXT NOT NULL
    )""")
    db.execute("""CREATE TABLE IF NOT EXISTS import_checkpoints (
        resource_key TEXT NOT NULL, member TEXT NOT NULL,
        last_line INTEGER NOT NULL, rows INTEGER NOT NULL,
        updated_utc TEXT NOT NULL,
        PRIMARY KEY(resource_key, member)
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



def section_from_name(filename, fallback_uf=""):
    """Extrai identificadores do nome do arquivo transmitido pelo TSE."""
    x = str(filename).replace("\\", "/").lower()
    match = re.search(r"[-_/]([a-z]{2})[-_/]m?(\d{4,6})[-_/]z?(\d{1,4})[-_/]s?(\d{1,4})(?:[^0-9]|$)", x)
    if not match:
        match = re.search(r"p\d+-([a-z]{2})-m(\d+)-z(\d+)-s(\d+)", x)
    if match:
        uf, mu, zo, se = match.groups()
        if uf.upper() in UF_SET:
            return uf.upper(), str(int(mu)), str(int(zo)), str(int(se))
    return fallback_uf, "", "", ""



def import_file(db, path, kind, key, digest):
    """Importacao em blocos, com checkpoints duraveis e retomada sem duplicar."""
    previous = db.execute(
        "SELECT sha256,parser_version FROM imports WHERE resource_key=?", (key,)
    ).fetchone()
    if previous and previous[0] == digest and previous[1] >= 2:
        print(f"INDEXADO ANTERIORMENTE: {path.name}", flush=True)
        return 0

    state = db.execute("SELECT sha256 FROM import_progress WHERE resource_key=?",
                       (key,)).fetchone()
    if not state or state[0] != digest:
        # Outra revisao ou nenhum checkpoint: reiniciar apenas este recurso.
        print("PREPARANDO importacao nova/revisada: " + path.name, flush=True)
        db.execute("DELETE FROM votes WHERE resource_key=?", (key,))
        db.execute("DELETE FROM archive_entries WHERE resource_key=?", (key,))
        db.execute("DELETE FROM import_checkpoints WHERE resource_key=?", (key,))
        db.execute("INSERT OR REPLACE INTO import_progress VALUES(?,?,?,?)",
                   (key, digest, now(), now()))
        db.commit()
    else:
        print("RETOMANDO importacao parcial: " + path.name, flush=True)

    count_new = 0
    csv_count = 0
    entries = 0
    try:
        if zipfile.is_zipfile(path):
            with zipfile.ZipFile(path) as archive:
                for info in archive.infolist():
                    if info.is_dir():
                        continue
                    ext = Path(info.filename).suffix.lower()
                    row_uf, mu, zo, se = section_from_name(
                        info.filename, path.parent.name.upper())
                    member_sha = None
                    if kind == "artefatos" and ext in (
                            ".bu", ".rdv", ".log", ".vota", ".imgbu"):
                        digest_member = hashlib.sha256()
                        with archive.open(info) as data_file:
                            for block in iter(lambda: data_file.read(1024 * 1024), b""):
                                digest_member.update(block)
                        member_sha = digest_member.hexdigest()
                    db.execute("""INSERT OR REPLACE INTO archive_entries
                        (resource_key,member,bytes,extensao,uf,municipio,zona,secao,sha256)
                        VALUES(?,?,?,?,?,?,?,?,?)""",
                        (key, info.filename, info.file_size, ext,
                         row_uf, mu, zo, se, member_sha))
                    entries += 1
                    if entries % 10000 == 0:
                        db.commit()
                        print(f"  ZIP: {entries:,} arquivos internos catalogados",
                              flush=True)
                    if kind in ("bu", "secao", "secao_nacional", "secao_detalhe") and ext == ".csv":
                        with archive.open(info) as stream:
                            count_new += import_csv_stream(
                                db, stream, key, info.filename, kind)
                        csv_count += 1
        elif path.suffix.lower() == ".csv" and kind in (
                "bu", "secao", "secao_nacional", "secao_detalhe"):
            with path.open("rb") as stream:
                count_new += import_csv_stream(db, stream, key, path.name, kind)
            csv_count = 1
        # A ausencia de checkpoint final seria resolvida na proxima execucao.
        total = db.execute("SELECT COUNT(*) FROM votes WHERE resource_key=?",
                           (key,)).fetchone()[0]
        db.execute("""INSERT OR REPLACE INTO imports
            (resource_key,sha256,imported_utc,rows,files,parser_version)
            VALUES (?,?,?,?,?,?)""", (key, digest, now(), total, csv_count, 3))
        db.execute("DELETE FROM import_progress WHERE resource_key=?", (key,))
        db.execute("DELETE FROM import_checkpoints WHERE resource_key=?", (key,))
        db.commit()
        print(f"INDEXADO {kind} {path.name}: {total:,} linhas, "
              f"{count_new:,} novas nesta execucao; {csv_count} CSV.",
              flush=True)
        return count_new
    except BaseException:
        # Somente o bloco ainda nao confirmado e desfeito. Os blocos
        # confirmados conservam checkpoints e voltam na proxima execucao.
        db.rollback()
        print("IMPORTACAO INTERROMPIDA/COM ERRO: blocos ja confirmados preservados: "
              + path.name, flush=True)
        raise



def normalized_cargo(row):
    """Identificador estavel mesmo se a fonte usa nome ou codigo do cargo."""
    raw = field(row, "CD_CARGO_PERGUNTA", "CD_CARGO")
    if raw:
        n = numeric(raw)
        if n is not None:
            return str(n)
    label = field(row, "DS_CARGO_PERGUNTA", "DS_CARGO").casefold().strip()
    known = {
        "presidente": "1", "governador": "3", "senador": "5",
        "deputado federal": "6", "deputado estadual": "7",
        "deputado distrital": "8",
    }
    return known.get(label, label)


def import_csv_stream(db, stream, key, member, kind):
    reader = open_csv(stream)
    if not reader.fieldnames:
        return 0
    headers = normalize_headers(reader.fieldnames)
    # O checkpoint so e usado depois de o SHA256 do recurso ser conferido.
    checkpoint = db.execute(
        "SELECT last_line, rows FROM import_checkpoints WHERE resource_key=? AND member=?",
        (key, member)).fetchone()
    resume_line = checkpoint[0] if checkpoint else 1
    previous_rows = checkpoint[1] if checkpoint else 0
    if resume_line > 1:
        print(f"  RETOMADA CSV {member}: pulando ate linha {resume_line:,} "
              "ja confirmada no banco", flush=True)
    batch = []
    count = 0
    last_saved_line = resume_line
    last_line_seen = resume_line

    def save_batch(current_line):
        nonlocal count, last_saved_line
        if batch:
            db.executemany("INSERT INTO votes VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)", batch)
            count += len(batch)
            batch.clear()
            last_saved_line = current_line
        if count and count % 20000 == 0 and last_saved_line > resume_line:
            db.execute("""INSERT OR REPLACE INTO import_checkpoints
                (resource_key,member,last_line,rows,updated_utc)
                VALUES(?,?,?,?,?)""",
                (key, member, last_saved_line, previous_rows + count, now()))
            db.execute("UPDATE import_progress SET updated_utc=? WHERE resource_key=?",
                       (now(), key))
            db.commit()
            print(f"  CSV {member}: {previous_rows + count:,} linhas ja confirmadas"
                  f" ({count:,} novas)", flush=True)

    for line, values in enumerate(reader, start=2):
        last_line_seen = line
        if line <= resume_line:
            continue
        if None in values:
            raise ValueError(f"CSV inconsistente {member} na linha {line}: colunas excessivas")
        obj = {headers[i]: values.get(name, "") for i, name in enumerate(reader.fieldnames)}
        uf = field(obj, "SG_UF")
        municipio = field(obj, "CD_MUNICIPIO")
        zona = field(obj, "NR_ZONA")
        secao = field(obj, "NR_SECAO")
        turno = field(obj, "NR_TURNO")
        cargo = normalized_cargo(obj)
        votavel = field(obj, "NR_VOTAVEL")
        votos = numeric(field(obj, "QT_VOTOS"))
        batch.append((key, member, line, kind, uf, municipio, zona, secao,
                      turno, cargo, votavel, votos, json.dumps(obj, ensure_ascii=False)))
        if len(batch) >= 2000:
            save_batch(line)
    if batch:
        # Ao encerrar um CSV, registrar inclusive o ultimo bloco parcial.
        db.executemany("INSERT INTO votes VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)", batch)
        count += len(batch)
        batch.clear()
    db.execute("""INSERT OR REPLACE INTO import_checkpoints
        (resource_key,member,last_line,rows,updated_utc)
        VALUES(?,?,?,?,?)""", (key, member,
                              max(last_saved_line, last_line_seen),
                              previous_rows + count, now()))
    db.commit()
    return count



def export_rows(db, output, ufs, municipio, zona, secao, turn, kind, candidate):
    conditions = []
    args = []
    for column, value in (("uf", ufs[0] if len(ufs) == 1 else None),
                          ("municipio", municipio), ("zona", zona), ("secao", secao),
                          ("turno", str(turn) if turn else None), ("source_kind", kind),
                          ("votavel", candidate)):
        if value:
            conditions.append(("CAST(" + column + " AS INTEGER) = CAST(? AS INTEGER)")
                              if column in ("municipio", "zona", "secao") else column + " = ?")
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




def write_analysis_reports(db, directory):
    """Relatorios compactos automaticos, sem exigir comandos separados."""
    directory.mkdir(parents=True, exist_ok=True)
    definitions = {
        "arquivos_por_uf.csv": (
            ["uf", "extensao", "quantidade", "bytes_descompactados",
             "arquivos_com_secao_identificada", "com_sha256"],
            """SELECT uf,extensao,COUNT(*),SUM(bytes),
                      SUM(CASE WHEN secao != '' THEN 1 ELSE 0 END),
                      SUM(CASE WHEN sha256 IS NOT NULL THEN 1 ELSE 0 END)
               FROM archive_entries GROUP BY uf,extensao ORDER BY uf,extensao"""),
        "votos_por_cargo_candidato.csv": (
            ["fonte", "uf", "turno", "cargo", "votavel", "votos", "registros"],
            """SELECT source_kind,uf,turno,cargo,votavel,SUM(votos),COUNT(*)
               FROM votes WHERE votos IS NOT NULL AND votavel != ''
               GROUP BY source_kind,uf,turno,cargo,votavel
               ORDER BY source_kind,uf,turno,cargo,votavel"""),
    }
    for filename, (columns, sql) in definitions.items():
        dest = directory / filename
        temp = dest.with_suffix(dest.suffix + ".part")
        with temp.open("w", newline="", encoding="utf-8-sig") as stream:
            out = csv.writer(stream, delimiter=";")
            out.writerow(columns)
            for row in db.execute(sql):
                out.writerow(row)
        os.replace(temp, dest)
        print("RELATORIO PRONTO:", dest)



def reconcile(db, output, ufs, turn):
    """Compara votos por chave UF/municipio/zona/secao/turno/cargo/votavel.

    Diferencas sao candidatas a investigacao, nao evidencia automatica de fraude.
    Sao excluidas linhas sem QT_VOTOS, numero de votavel ou identificacao da secao.
    """
    where = ["votos IS NOT NULL", "TRIM(votavel) != ''",
             "TRIM(secao) != ''", "TRIM(cargo) != ''"]
    values = []
    if turn:
        where.append("turno = ?")
        values.append(str(turn))
    if ufs:
        where.append("uf IN (" + ",".join("?" for _ in ufs) + ")")
        values.extend(ufs)
    cond = " AND ".join(where)
    sql = """
    WITH grouped AS (
        SELECT source_kind AS origem, UPPER(uf) AS uf,
               CAST(municipio AS INTEGER) AS municipio,
               CAST(zona AS INTEGER) AS zona, CAST(secao AS INTEGER) AS secao,
               turno, LOWER(TRIM(cargo)) AS cargo,
               CASE WHEN votavel GLOB '[0-9]*' THEN CAST(votavel AS TEXT)
                    ELSE UPPER(TRIM(votavel)) END AS votavel,
               SUM(votos) AS votos
        FROM votes WHERE """ + cond + """
        GROUP BY origem,uf,municipio,zona,secao,turno,cargo,votavel
    ),
    bu AS (SELECT * FROM grouped WHERE origem='bu'),
    sec AS (SELECT * FROM grouped WHERE origem='secao'),
    joined AS (
        SELECT b.uf,b.municipio,b.zona,b.secao,b.turno,b.cargo,b.votavel,
               b.votos AS bu_votos,s.votos AS secao_votos
        FROM bu b LEFT JOIN sec s ON
          b.uf=s.uf AND b.municipio=s.municipio AND b.zona=s.zona AND
          b.secao=s.secao AND b.turno=s.turno AND
          b.cargo=s.cargo AND b.votavel=s.votavel
        UNION ALL
        SELECT s.uf,s.municipio,s.zona,s.secao,s.turno,s.cargo,s.votavel,
               NULL,s.votos
        FROM sec s LEFT JOIN bu b ON
          b.uf=s.uf AND b.municipio=s.municipio AND b.zona=s.zona AND
          b.secao=s.secao AND b.turno=s.turno AND
          b.cargo=s.cargo AND b.votavel=s.votavel
        WHERE b.uf IS NULL
    )
    SELECT * FROM joined
    """
    output.parent.mkdir(parents=True, exist_ok=True)
    checked = differences = 0
    missing_bu = missing_sec = 0
    with output.open("w", newline="", encoding="utf-8-sig") as out:
        writer = csv.writer(out, delimiter=";")
        writer.writerow(["UF","municipio","zona","secao","turno","cargo","votavel",
                         "votos_BU","votos_secao","diferenca","situacao"])
        for row in db.execute(sql, values):
            checked += 1
            uf, mu, zo, se, tu, ca, vo, b, v = row
            if b is None:
                status = "SEM_BU"
                missing_bu += 1
            elif v is None:
                status = "SEM_SECAO"
                missing_sec += 1
            elif b != v:
                status = "DIFERENTE"
            else:
                continue
            differences += 1
            writer.writerow([uf,mu,zo,se,tu,ca,vo,b,v,
                             (b-v) if b is not None and v is not None else "",status])
    summary = {
        "created_at_utc": now(), "turn": turn, "ufs": ufs or "todas",
        "keys_compared": checked, "different_or_missing": differences,
        "missing_bu": missing_bu, "missing_section": missing_sec,
        "matches": checked - differences, "csv": str(output),
        "limitations": "Comparacao apenas nas chaves com votos e identificadores presentes nas duas fontes. "
        "Se zero chaves forem comparadas, a analise nao foi feita. "
        "Se houver secoes agregadas ou codificacoes diferentes, investigar antes de atribuir causa."
    }
    atomic_json(output.with_suffix(".summary.json"), summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if checked == 0 or checked == missing_bu + missing_sec:
        print("ATENCAO: sem intersecao validada de registros BU x secao.", file=sys.stderr)


def main():
    import run_control
    run_control.install()
    run_control.stage("analisando argumentos e preparando acesso ao drive de dados")
    parser = argparse.ArgumentParser(
        description="Gerenciador TSE: consultar, baixar sob demanda, validar e tornar BU/sections consultaveis")
    parser.add_argument("action", choices=("status", "fetch", "import", "export", "reconcile", "stats", "verify"),
                        help="status=apenas consultar; fetch=baixar e importar; import=processar arquivos locais")
    parser.add_argument("--root", help="Diretorio de dados (padrao no Windows: H:/TSE/forensics/urnas)")
    parser.add_argument("--kind", choices=("bu", "secao", "artefatos"), action="append",
                        help="Tipo; pode repetir. Padrao: bu + secao.")
    parser.add_argument("--uf", action="append", type=str.upper, default=[],
                        help="UF; pode repetir. Obrigatoria para fetch sem --all.")
    parser.add_argument("--all", action="store_true", help="Baixar para todas UFs (operacao volumosa)")
    parser.add_argument("--turn", type=int, choices=(1,2), default=None, help="Por padrao coleta todos os turnos publicados")
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
    if args.action in ("fetch", "stats", "reconcile", "import"):
        run_control.stage("preservando historico ANTES de substituir relatorios")
        # Antes de qualquer substituicao, arquivar os relatorios da ultima
        # execucao. Se arquivar falhar, nao sobrescrever analises anteriores.
        from history_forensics import snapshot as history_snapshot
        history_snapshot(root, "antes-" + args.action,
                         context={"tipos": args.kind or [], "ufs": args.uf,
                                  "turno": args.turn})
    if os.name == "nt":
        temporary = root / "tmp"
        temporary.mkdir(parents=True, exist_ok=True)
        os.environ["TMP"] = str(temporary.resolve())
        os.environ["TEMP"] = str(temporary.resolve())
        os.environ["TMPDIR"] = str(temporary.resolve())
    kinds = args.kind or (["bu", "secao"] if args.action != "verify" else list(DATASETS))
    kinds = list(dict.fromkeys(kinds))
    if args.action in ("status", "fetch"):
        run_control.stage("consultando recursos no catalogo oficial")
        datasets = catalog()
        atomic_json(root / "catalogo_latest.json", {
            "checked_at_utc": now(),
            "datasets": {k: {"title": v.get("title"), "resources": v.get("resources", [])}
                         for k, v in datasets.items()}})
        selected = select_resources(datasets, kinds, args.uf if not args.all else [], args.turn)
        local = sum(1 for kind, uf, resource in selected
                    if resource_path(root, kind, uf, resource).is_file())
        print(f"Catalogo: {len(selected)} recursos selecionados | locais={local} "
              f"| ausentes={len(selected)-local} | tipos={','.join(kinds)}", flush=True)
        if args.action == "status":
            for kind, uf, resource in selected:
                path = resource_path(root, kind, uf, resource)
                print(f"  {kind:15s} {uf}: {resource.get('name')} "
                      f"| {'LOCAL' if path.is_file() else 'REMOTO'}", flush=True)
            return
        if not selected:
            raise SystemExit("Nenhum recurso localizado. Nenhum download foi realizado.")
        minimum_bytes = int(args.reserve_gb * (1024 ** 3))
        legacy = Path("data/forensics/portal/files")
        db = None
        if not args.no_import:
            (root / "analysis").mkdir(parents=True, exist_ok=True)
            run_control.stage("abrindo banco SQLite e conferindo indices (pode levar tempo)")
            db = sqlite3.connect(root / "analysis" / "urna_2026.sqlite3", timeout=90)
            run_control.attach_db(db)
            schema(db)
            db.commit()
            run_control.stage("SQLite pronto; iniciando processamento dos arquivos")
        manifest_path = root / "download_manifest_latest.json"
        results = []
        errors = []
        reused = downloaded = indexed = 0
        try:
            for pos, (kind, uf, resource) in enumerate(selected, 1):
                if run_control.cancelled():
                    raise KeyboardInterrupt
                run_control.stage(f"recurso {pos}/{len(selected)}: {kind}/{uf} - "
                                  f"{resource.get('name')}")
                entry = {"time_utc": now(), "kind": kind, "uf": uf,
                         "id": resource.get("id"), "name": resource.get("name"),
                         "url": resource.get("url")}
                print(f"[{pos}/{len(selected)}] {kind}/{uf} {resource.get('name')}", flush=True)
                try:
                    dest = resource_path(root, kind, uf, resource)
                    existed = dest.exists() and dest.stat().st_size > 0
                    path, digest = download(root, kind, uf, resource, minimum_bytes, legacy)
                    entry.update({"status": "reused" if existed else "downloaded",
                                  "sha256": digest, "path": str(path)})
                    if existed:
                        reused += 1
                    else:
                        downloaded += 1
                    if db is not None:
                        run_control.stage(f"importando ou conferindo indice {pos}/{len(selected)}: "
                                          f"{kind}/{uf}, {path.name}")
                        key = kind + ":" + str(resource.get("id") or path.name)
                        num = import_file(db, path, kind, key, digest)
                        indexed += num
                        entry["imported_rows"] = num
                except Exception as exc:
                    if run_control.cancelled():
                        raise KeyboardInterrupt from exc
                    entry.update({"status": "error", "error": str(exc)})
                    errors.append(entry)
                    print(f"ERRO em {kind}/{uf} {resource.get('name')}: {exc}", file=sys.stderr)
                results.append(entry)
                atomic_json(manifest_path, {"updated_at_utc": now(),
                            "selected": len(selected), "processed": len(results),
                            "reused": reused, "downloaded": downloaded,
                            "indexed_rows_new": indexed, "errors": errors,
                            "resources": results})
            if db is not None:
                run_control.stage("gerando relatorios da base de votos")
                try:
                    write_analysis_reports(db, root / "analysis")
                except Exception as exc:
                    errors.append({"status": "error", "stage": "reports", "error": str(exc)})
                    print(f"ERRO gerando relatorios: {exc}", file=sys.stderr)
            if db is not None and "bu" in kinds and "secao" in kinds:
                try:
                    output = root / "analysis" / "reconciliacao_bu_secao.csv"
                    run_control.stage("reconciliacao automatica BU x votacao por secao")
                    print("Reconciliacao automatica BU x votacao por secao...", flush=True)
                    reconcile(db, output, args.uf if not args.all else [], args.turn)
                except Exception as exc:
                    errors.append({"status": "error", "stage": "reconcile",
                                   "time_utc": now(), "error": str(exc)})
                    print(f"ERRO na reconciliacao: {exc}", file=sys.stderr)
            if db is not None and "bu" in kinds:
                try:
                    from statistical_forensics import analyze as analyze_statistical
                    run_control.stage("executando bateria estatistica de secoes")
                    stats = analyze_statistical(db, root / "analysis" / "estatistica")
                    if stats["status"] != "analise_concluida":
                        errors.append({"status": "warning", "stage": "statistics",
                                       "error": "Sem dados BU de Presidente: analise estatistica nao executada"})
                except Exception as exc:
                    errors.append({"status": "error", "stage": "statistics",
                                   "time_utc": now(), "error": str(exc)})
                    print(f"ERRO na analise estatistica: {exc}", file=sys.stderr)
            atomic_json(manifest_path, {"updated_at_utc": now(),
                        "selected": len(selected), "processed": len(results),
                        "reused": reused, "downloaded": downloaded,
                        "indexed_rows_new": indexed, "errors": errors,
                        "resources": results,
                        "finished": True})
        finally:
            if db:
                run_control.attach_db(None)
                db.close()
        # Preservacao do resultado concluido ou parcial, antes de qualquer
        # codigo de saida diferente de zero.
        from history_forensics import snapshot as history_snapshot
        run_control.stage("salvando historico final dos relatorios")
        history_snapshot(root, "apos-coleta" if not errors else "apos-coleta-com-erros",
                         context={"recursos_selecionados": len(selected),
                                  "processados": len(results),
                                  "reutilizados": reused, "novos": downloaded,
                                  "linhas_indexadas": indexed,
                                  "erros": len(errors)})
        print(f"RESUMO: {len(selected)} recursos, {reused} reutilizados, "
              f"{downloaded} novos, {indexed:,} registros indexados, "
              f"{len(errors)} erros.", flush=True)
        print(f"Originais: {root / 'raw'}; banco e relatorios: {root / 'analysis'}", flush=True)
        if errors:
            raise SystemExit(1)
        return

    db_path = root / "analysis" / "urna_2026.sqlite3"
    if args.action in ("export", "import", "reconcile", "stats"):
        db_path.parent.mkdir(parents=True, exist_ok=True)
        run_control.stage("abrindo SQLite para tarefa local; conferindo indices")
        db = sqlite3.connect(db_path, timeout=90)
        run_control.attach_db(db)
        schema(db)
        db.commit()
        try:
            if args.action == "stats":
                from statistical_forensics import analyze as analyze_statistical
                result = analyze_statistical(db, Path(args.output) if args.output else root / "analysis" / "estatistica")
                if result["status"] != "analise_concluida":
                    raise SystemExit("Sem dados BU de Presidente. A analise nao foi executada.")
            elif args.action == "reconcile":
                output = Path(args.output or root / "analysis" / "reconciliacao_bu_secao.csv")
                reconcile(db, output, args.uf, args.turn)
            elif args.action == "export":
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
                        if kind not in (*DATASETS, "secao_nacional", "secao_detalhe") or (args.kind and kind not in args.kind):
                            continue
                        digest = sha256_file(path)
                        import_file(db, path, kind, kind + ":" + path.name.split("--")[0], digest)
                    except Exception as exc:
                        print(f"ERRO indexando {path}: {exc}", file=sys.stderr)
                        raise
        finally:
            run_control.attach_db(None)
            db.close()
        from history_forensics import snapshot as history_snapshot
        run_control.stage("preservando historico da tarefa concluida")
        history_snapshot(root, "apos-" + args.action,
                         context={"ufs": args.uf, "turno": args.turn})
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
    except KeyboardInterrupt:
        print("\nINTERRUPCAO CONCLUIDA. Os ZIPs prontos, o banco e os .part existentes "
              "permanecem no H:. A proxima coleta continua.", file=sys.stderr, flush=True)
        sys.exit(130)
    except (OSError, ValueError, RuntimeError, urllib.error.URLError, zipfile.BadZipFile) as exc:
        print("FALHA: " + str(exc), file=sys.stderr)
        sys.exit(1)
