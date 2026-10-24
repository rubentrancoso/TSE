#!/usr/bin/env python3
"""Inventario de evidencia material das urnas 2026 — somente metadados.

Identifica quantidades de artefatos catalogados no SQLite, por UF e tipo;
separa arquivo oficial recebido do TSE de captura independente de terceiros.
NAO considera dois arquivos TSE evidencia independente.
Nao le votos, nao abre arquivos binarios, nao relê BU CSV e
nao verifica assinatura criptografica (SHA-256 nao e assinatura).
Nao carrega ou compara dados de 2022.

Opcional: um manifest.csv de capturas independentes no diretorio
<root>/evidencia_independente_2026, com colunas:
id;uf;municipio;zona;secao;turno;tipo;arquivo;origem;captura_utc;sha256
Os arquivos referidos devem estar dentro deste diretorio. O manifesto
comprova integridade desde a captura declarada, mas NAO comprova,
sozinho, independência, autenticidade ou integridade da urna.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sqlite3

from urnas import root_path

VERSION = "inventario-evidencia-urna-2026-v1"
EXTS = {".bu", ".imgbu", ".rdv", ".log", ".vota", ".jws", ".pdf", ".jpg", ".jpeg", ".png"}
UFs = set("AC AL AM AP BA CE DF ES GO MA MG MS MT PA PB PE PI PR RJ RN RO RR RS SC SE SP TO ZZ".split())
MANIFEST_FIELDS = {"id", "uf", "municipio", "zona", "secao",
                   "turno", "tipo", "arquivo", "origem",
                   "captura_utc", "sha256"}


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as fd:
        for block in iter(lambda: fd.read(4 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def official_inventory(dbpath):
    """Consulta somente tabela archive_entries e importa metadados, nunca votes."""
    if not dbpath.is_file():
        return {"status": "BANCO_AUSENTE", "por_uf": [],
                "totais_extensoes": {}, "amostras": [],
                "nota": "Sem banco catalogado, nao concluir que arquivos nao existem"}
    conn = sqlite3.connect(dbpath.resolve().as_uri() + "?mode=ro", uri=True,
                           timeout=30)
    try:
        conn.execute("PRAGMA query_only=ON")
        tables = {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'")}
        if "archive_entries" not in tables:
            return {"status": "CATALOGO_AUSENTE", "por_uf": [],
                    "totais_extensoes": {}, "amostras": [],
                    "nota": "SQLite existe, mas nao possui tabela archive_entries"}
        cols = {r[1] for r in conn.execute("PRAGMA table_info(archive_entries)")}
        needed = {"uf", "municipio", "zona", "secao",
                  "extensao", "member", "sha256"}
        if not needed <= cols:
            raise RuntimeError("Colunas de archive_entries insuficientes")
        by_uf = defaultdict(Counter)
        total = Counter()
        with_sha = Counter()
        for uf, ext, count, hashed in conn.execute(
                """SELECT UPPER(COALESCE(uf,'')),
                          LOWER(COALESCE(extensao,'')), COUNT(*),
                          SUM(CASE WHEN sha256 IS NOT NULL
                                   AND sha256 != '' THEN 1 ELSE 0 END)
                   FROM archive_entries
                   GROUP BY UPPER(COALESCE(uf,'')),
                            LOWER(COALESCE(extensao,''))"""):
            if ext not in EXTS:
                continue
            normalized = uf if uf in UFs else "NAO_IDENTIFICADA"
            by_uf[normalized][ext] += count
            total[ext] += count
            with_sha[ext] += hashed or 0
        samples = []
        for uf in sorted(UFs):
            for raw_uf, mu, zone, section, ext, member in conn.execute(
                    """SELECT uf, municipio, zona, secao, extensao, member
                       FROM archive_entries
                       WHERE uf = ? AND
                             extensao IN ('.bu','.imgbu','.rdv','.log','.vota')
                             AND secao IS NOT NULL AND secao != ''
                       LIMIT 2""", (uf,)):
                samples.append({
                    "UF": raw_uf, "municipio": mu, "zona": zone,
                    "secao": section, "tipo": ext, "member": member,
                    "natureza": "TSE_CATALOGO_OFICIAL",
                })
        return {
            "status": "CATALOGO_CONSULTADO",
            "totais_extensoes": dict(sorted(total.items())),
            "extensoes_com_sha256_member": dict(sorted(with_sha.items())),
            "por_uf": [{"UF": uf, **{ext: by_uf[uf].get(ext, 0)
                                      for ext in sorted(EXTS)}}
                       for uf in sorted(by_uf)],
            "amostras": samples,
            "nota": ("Esses objetos sao declarados arquivos de origem TSE; "
                     "mesmo com hash, nao constituem captura independente da urna. "
                     "Hash em archive_entries e hash do membro do ZIP, nao "
                     "verificacao criptografica de assinatura."),
        }
    finally:
        conn.close()


def independent_inventory(root):
    base = root / "evidencia_independente_2026"
    manifest = base / "manifest.csv"
    if not manifest.is_file():
        return {
            "status": "MANIFESTO_AUSENTE", "registros": 0,
            "arquivos_hash_ok": 0, "arquivos_hash_erro": 0,
            "declaracoes": [],
            "nota": "Nao ha registros declarados neste diretório; nao prova inexistencia de capturas fora dele",
        }
    recorded = []
    seen = set()
    verified = rejected = 0
    with manifest.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file, delimiter=";")
        if not MANIFEST_FIELDS <= set(reader.fieldnames or []):
            raise RuntimeError("Colunas obrigatorias ausentes no manifest.csv")
        for line in reader:
            record_id = line["id"].strip()
            if not record_id or record_id in seen:
                raise RuntimeError("ID vazio/duplicado no manifesto")
            seen.add(record_id)
            uf = line["uf"].upper().strip()
            if uf not in UFs:
                raise RuntimeError("UF invalida: " + uf)
            relative = Path(line["arquivo"])
            if relative.is_absolute() or ".." in relative.parts:
                raise RuntimeError("Arquivo fora de evidencia_independente_2026")
            location = (base / relative).resolve()
            if not location.is_relative_to(base.resolve()):
                raise RuntimeError("Arquivo fora de evidencia_independente_2026")
            declared = line["sha256"].strip().lower()
            if len(declared) != 64 or any(c not in "0123456789abcdef" for c in declared):
                raise RuntimeError("SHA-256 declarado invalido: " + record_id)
            valid = location.is_file() and digest(location) == declared
            verified += valid
            rejected += not valid
            recorded.append({
                "id": record_id, "UF": uf, "municipio": line["municipio"],
                "zona": line["zona"], "secao": line["secao"],
                "turno": line["turno"], "tipo": line["tipo"],
                "arquivo": str(relative),
                "origem_declarada": line["origem"],
                "captura_utc_declarada": line["captura_utc"],
                "sha256_declarado": declared,
                "sha256_confere": bool(valid),
                "proveniencia_verificada": False,
                "autenticidade_criptografica_verificada": False,
            })
    return {
        "status": "MANIFESTO_AUDITADO",
        "manifest_sha256": digest(manifest),
        "registros": len(recorded),
        "arquivos_hash_ok": verified,
        "arquivos_hash_erro": rejected,
        "declaracoes": recorded,
        "nota": ("Integridade entre arquivo atual e hash declarado foi testada; "
                 "independencia da fonte e autenticidade ainda exigem "
                 "verificacao externa da captura e da assinatura."),
    }


def run(root, *, write=True):
    root = Path(root)
    official = official_inventory(root / "analysis" / "urna_2026.sqlite3")
    independent = independent_inventory(root)
    report = {
        "version": VERSION,
        "escopo": "2026_EXCLUSIVO",
        "status": "INVENTARIO_DESCRITIVO",
        "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "official_artifacts": official,
        "independent_captures": independent,
        "limits": [
            "Sem leitura nem alteracao de registros individuais de votacao",
            "O banco pode conter catalogo incompleto de arquivos existentes no disco",
            "SHA-256 nao demonstra assinatura TSE nem independencia da fonte",
            "Ausencia no diretorio proprio nao descarta fotografias/QR nao inventariados",
            "Nao foram usados dados eleitorais de 2022",
        ],
        "prioridades": [
            "Identificar secoes com capturas fisicas de BU/QR por terceiros",
            "Verificar origem, data e autenticidade de cada BU/QR de forma independente",
            "Comparar valores individuais com os correspondentes BU digitais de 2026",
            "So depois analisar mecanismos matematicos hipoteticos de alteracao",
        ],
    }
    if write:
        output = root / "analysis" / "evidencia_material_2026" / "inventario.json"
        output.parent.mkdir(parents=True, exist_ok=True)
        tmp = Path(str(output) + ".part")
        try:
            tmp.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n",
                           encoding="utf-8")
            os.replace(tmp, output)
        finally:
            if tmp.exists():
                tmp.unlink()
        report["output"] = str(output)
    print("INVENTARIO DE EVIDENCIA MATERIAL 2026 CONCLUIDO")
    print(json.dumps({
        "catalogo_tse_status": official["status"],
        "artefatos_oficiais_por_extensao": official["totais_extensoes"],
        "artefatos_com_sha256_membro": official.get("extensoes_com_sha256_member", {}),
        "ufs_catalogadas": len(official["por_uf"]),
        "capturas_externas_registradas": independent["registros"],
        "capturas_hash_ok": independent["arquivos_hash_ok"],
        "capturas_hash_erro": independent["arquivos_hash_erro"],
        "alerta": ("Hash oficial de arquivo TSE nao comprova que o BU "
                   "na urna era igual; captura independente e verificação "
                   "criptografica permanecem distintas"),
        "output": report.get("output"),
    }, ensure_ascii=False, indent=2), flush=True)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", help="Pasta H: do acervo TSE")
    args = parser.parse_args()
    run(root_path(args.root))
