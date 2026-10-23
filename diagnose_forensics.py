#!/usr/bin/env python3
"""Diagnóstico local, somente leitura, do último processamento de urnas.

Lê o manifesto e os relatórios já gerados. Não baixa recursos, não reimporta
votos, não recalcula a reconciliação e não modifica arquivos brutos.
"""
from __future__ import annotations

import argparse
import collections
import csv
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path


def load(path):
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (ValueError, OSError) as exc:
        return {"error": f"Arquivo nao legivel: {exc}"}


def diagnostic(root: Path, *, detailed=True, emit=print):
    root = Path(root)
    manifest = load(root / "download_manifest_latest.json")
    recap = load(root / "analysis" / "reconciliacao_bu_secao.summary.json")
    stats = load(root / "analysis" / "estatistica" / "estatistica_resumo.json")

    emit("=== DIAGNOSTICO LOCAL TSE (SEM NOVO DOWNLOAD) ===")
    if manifest is None:
        emit("ATENCAO: manifesto de recursos nao encontrado.")
        resources = []
        errors = []
    else:
        resources = manifest.get("resources", [])
        errors = manifest.get("errors", [])
        emit("Manifesto: selecionados={}, processados={}, reutilizados={}, novos={}, erros={}".format(
            manifest.get("selected", "?"), manifest.get("processed", "?"),
            manifest.get("reused", "?"), manifest.get("downloaded", "?"),
            len(errors) if isinstance(errors, list) else "?"))
        for i, error in enumerate(errors if isinstance(errors, list) else [], 1):
            emit("ERRO #{i}: fase={stage} recurso={kind}/{uf} nome={name}".format(
                i=i, stage=error.get("stage", "recurso"), kind=error.get("kind", "?"),
                uf=error.get("uf", "?"), name=error.get("name", "?")))
            emit("  MOTIVO: " + str(error.get("error", "sem detalhe no manifesto")))
            if error.get("url"):
                emit("  ENDERECO: " + str(error["url"]))

    if recap:
        emit("RECONCILIACAO: chaves={:,}; coincidentes={:,}; SEM_BU={:,}; "
             "SEM_SECAO={:,}; outros_desvios={:,}".format(
                 int(recap.get("keys_compared") or 0),
                 int(recap.get("matches") or 0),
                 int(recap.get("missing_bu") or 0),
                 int(recap.get("missing_section") or 0),
                 max(0, int(recap.get("different_or_missing") or 0)
                     - int(recap.get("missing_bu") or 0)
                     - int(recap.get("missing_section") or 0))))
        emit("  ATENCAO: chave de comparacao nao equivale a eleitor, voto ou secao unica.")
    else:
        emit("RECONCILIACAO: resumo indisponivel.")

    if stats:
        emit("ESTATISTICA: {} secoes; {} desvios locais; status={}".format(
            stats.get("secoes", "?"), stats.get("desvios_locais_sinalizados", "?"),
            stats.get("status", "?")))
    else:
        emit("ESTATISTICA: resumo indisponivel.")

    errors_by_uf = collections.Counter()
    errors_by_uf_cargo = collections.Counter()
    statuses = collections.Counter()
    examples = []
    comparison = root / "analysis" / "reconciliacao_bu_secao.csv"
    scanned = 0
    if detailed and comparison.is_file():
        emit("DIAGNOSTICO: agrupando as diferencas do CSV ja existente por UF, turno e cargo...")
        with comparison.open("r", newline="", encoding="utf-8-sig") as stream:
            for record in csv.DictReader(stream, delimiter=";"):
                scanned += 1
                status = (record.get("situacao") or "?").strip()
                statuses[status] += 1
                if status == "SEM_SECAO":
                    uf = (record.get("UF") or "?").strip().upper()
                    turn = (record.get("turno") or "?").strip()
                    cargo = (record.get("cargo") or "?").strip()
                    errors_by_uf[(uf, turn)] += 1
                    errors_by_uf_cargo[(uf, turn, cargo)] += 1
                    if len(examples) < 10:
                        examples.append({k: record.get(k, "") for k in (
                            "UF", "municipio", "zona", "secao", "turno",
                            "cargo", "votavel", "votos_BU", "votos_secao",
                            "situacao")})
                if scanned % 500000 == 0:
                    emit("  {:,} linhas classificadas; SEM_SECAO={:,}".format(
                        scanned, statuses["SEM_SECAO"]))
        emit("DIVERGENCIAS no CSV: {:,} linhas; por tipo: {}".format(
            scanned, ", ".join(f"{k}={v:,}" for k, v in statuses.most_common())))
        emit("SEM_SECAO por UF/turno (maiores contagens):")
        for (uf, turn), amount in errors_by_uf.most_common(15):
            emit(f"  {uf} turno {turn}: {amount:,} chaves")
        emit("SEM_SECAO por UF/turno/cargo (maiores contagens):")
        for (uf, turn, cargo), amount in errors_by_uf_cargo.most_common(15):
            emit(f"  {uf} turno {turn} cargo {cargo}: {amount:,} chaves")
    elif detailed:
        emit("ATENCAO: CSV de reconciliacao indisponivel para agrupar diferencas.")

    report = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "kind": "diagnostico-descritivo",
        "manifest_path": str(root / "download_manifest_latest.json"),
        "selected": manifest.get("selected") if manifest else None,
        "processed": manifest.get("processed") if manifest else None,
        "errors": errors if isinstance(errors, list) else [],
        "reconciliation": recap,
        "statistical_summary": {
            "secoes": stats.get("secoes"), "desvios_locais_sinalizados": stats.get(
                "desvios_locais_sinalizados"), "status": stats.get("status")}
            if stats else None,
        "csv_rows_scanned": scanned,
        "status_counts": dict(statuses),
        "missing_section_by_state_turn": [
            {"uf": uf, "turn": turn, "keys": count}
            for (uf, turn), count in errors_by_uf.most_common()],
        "missing_section_by_state_turn_office": [
            {"uf": uf, "turn": turn, "cargo": cargo, "keys": count}
            for (uf, turn, cargo), count in errors_by_uf_cargo.most_common()],
        "examples": examples,
        "limitations": [
            "Esta analise agrupa chaves nao reconciliadas; nao prova ausencia fisica de votos.",
            "O erro de um recurso deve ser analisado antes de inferir discrepancia eleitoral.",
            "As fontes podem ter cobertura e codificacoes distintas.",
            "Uma igualdade entre duas fontes publicadas pelo TSE nao e auditoria independente do voto."
        ]
    }
    target = root / "analysis" / "diagnostico_execucao.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    temp = Path(str(target) + ".part")
    try:
        temp.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(temp, target)
    finally:
        if temp.exists():
            temp.unlink()
    emit("RELATORIO DIAGNOSTICO: " + str(target))
    return report


def main():
    parser = argparse.ArgumentParser(description="Diagnostico dos erros e ausencias sem download.")
    parser.add_argument("--root", default=("H:/TSE/forensics/urnas"
                                          if os.name == "nt" else "data/forensics/urnas"))
    parser.add_argument("--quick", action="store_true",
                        help="Apenas manifesto e resumos; nao varrer CSV grande")
    args = parser.parse_args()
    import run_control
    run_control.install()
    run_control.configure_log(Path(args.root))
    run_control.stage("diagnostico das fontes e reconciliacao, sem download")
    try:
        diagnostic(Path(args.root), detailed=not args.quick)
    except KeyboardInterrupt:
        print("Diagnostico interrompido; dados originais preservados.",
              file=sys.stderr, flush=True)
        return 130
    finally:
        run_control.shutdown()
    return 0


if __name__ == "__main__":
    sys.exit(main())
