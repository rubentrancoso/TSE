"""Tests for ZZ election metrics auditing of 42 counter sections without BWEB."""
import json
from pathlib import Path
import tempfile
import unittest

import audit_zz_42_voting_status_2026 as subject
from reconcile_stream import sha256


class TestZZMetrics(unittest.TestCase):
    def test_classification_zero(self):
        metrics={"e.c":0,"v.vv":0,"v.vb":0,"v.tvn":0}
        self.assertEqual(subject.classify(metrics),"EA20_COMPARECIMENTO_E_VOTOS_ZERO")

    def test_positive_vote_or_turnout(self):
        base={"e.c":0,"v.vv":0,"v.vb":0,"v.tvn":0}
        for key in base:
            row=base.copy()
            row[key]=1
            self.assertEqual(subject.classify(row),"EA20_REGISTRA_COMPARECIMENTO_OU_VOTOS")

    def test_missing_is_not_zero(self):
        self.assertEqual(subject.classify({"e.c":None,"v.vv":None,
                   "v.vb":None,"v.tvn":None}),"CAMPOS_ESSENCIAIS_AUSENTES")
        self.assertEqual(subject.classify({"e.c":0,"v.vv":0,
                   "v.vb":None,"v.tvn":0}),"EA20_COMPARECIMENTO_ZERO_VOTOS_INCOMPLETOS")

    def test_extract_fields_and_locale(self):
        raw={"e":{"te":"1.200","est":"25","c":"0","a":"25"},
             "v":{"vv":"0","vb":"0","tvn":"0"}}
        vals={k:subject.field(raw,*k.split(".")) for k in subject.NEEDED}
        self.assertEqual(vals["e.te"],1200)
        self.assertEqual(vals["e.c"],0)
        self.assertEqual(vals["v.tvn"],0)
        self.assertEqual(subject.classify(vals),"EA20_COMPARECIMENTO_E_VOTOS_ZERO")

    def test_realistic_41_localities_with_original_hashes(self):
        with tempfile.TemporaryDirectory() as temporary:
            basedir=Path(temporary)
            repo=basedir/"repo"
            root=basedir/"H"
            run=repo/"data/forensics/runs/20261005T104314Z"
            summary2=repo/"data/forensics/analysis/phase2_sections_summary.json"
            summary2.parent.mkdir(parents=True,exist_ok=True)
            summary2.write_text(json.dumps({"latest_snapshot":run.name}),encoding="utf-8")
            manifest=run/"manifest.jsonl"
            manifest.parent.mkdir(parents=True,exist_ok=True)
            entries=[];manifest_lines=[]
            for i in range(41):
                code=10000+i
                gap=2 if i==0 else 1
                path=run/"live"/"municipio"/"zz"/f"{code}.json"
                path.parent.mkdir(parents=True,exist_ok=True)
                turnout=2 if i==1 else 0
                payload={"s":{"st":gap,"ts":gap},
                         "e":{"te":"20","c":str(turnout),"a":str(20-turnout),
                              "est":"20"},
                         "v":{"vv":str(turnout),"vb":"0","tvn":"0"}}
                path.write_text(json.dumps(payload),encoding="utf-8")
                manifest_lines.append(json.dumps({"uf":"zz","kind":"municipality",
                    "municipality_code":str(code),"sha256":sha256(path)}))
                entries.append({"municipio":str(code),"nome_configuracao":f"Local {i}",
                       "EA20_municipal_st":gap,"EA20_municipal_ts":gap,
                       "BWEB_secoes":0,"diferenca_st_menos_BWEB":gap,
                       "EA20_municipal_dia":"05/10/2026",
                       "EA20_municipal_hora":"04:00"})
            state=run/"live"/"uf"/"zz.json"
            state.parent.mkdir(parents=True,exist_ok=True)
            state.write_text(json.dumps({"s":{"st":1351,"ts":1351}}),encoding="utf-8")
            manifest_lines.append(json.dumps({"uf":"zz","kind":"state",
                         "sha256":sha256(state)}))
            manifest.write_text("\n".join(manifest_lines)+"\n",encoding="utf-8")
            outdir=root/subject.CACHE
            outdir.mkdir(parents=True)
            q={
                "status":"DIFERENCA_LOCALIZADA_NOS_CONTADORES_MUNICIPAIS_ZZ",
                "national":{"ZZ_st_UF":1351,"ZZ_BWEB_sections":1309,
                            "EA20_municipal_st_sum":1351,
                            "municipal_st_sum_minus_BWEB":42,
                            "EA20_municipal_files":41,
                            "EA20_municipal_archived_SHA_validated":41,
                            "all_municipal_counters_compared":True},
                "input_provenance":{
                    "phase2_sha256":sha256(summary2),
                    "original_manifest_sha256":sha256(manifest)},
                "municipal_detail":entries
            }
            qfile=outdir/subject.SOURCE_Q
            qfile.write_text(json.dumps(q),encoding="utf-8")
            result=subject.audit(root,repo)
            self.assertEqual(result["localities"],41)
            self.assertEqual(result["sections_without_corresponding_BWEB"],42)
            classes=result["classification_counts"]
            self.assertEqual(classes["EA20_COMPARECIMENTO_E_VOTOS_ZERO"],40)
            self.assertEqual(classes["EA20_REGISTRA_COMPARECIMENTO_OU_VOTOS"],1)
            self.assertEqual(classes["sections_EA20_COMPARECIMENTO_E_VOTOS_ZERO"],41)
            self.assertEqual(classes["sections_EA20_REGISTRA_COMPARECIMENTO_OU_VOTOS"],1)
            self.assertTrue((outdir/"phase5m_zz_42_voting_status_2026_summary.json").is_file())
            # Changed EA20 even with same st/ts cannot be silently accepted.
            (run/"live"/"municipio"/"zz"/"10001.json").write_text('{"s":{"st":1,"ts":1}}',
                                                                  encoding="utf-8")
            with self.assertRaises(RuntimeError):
                subject.audit(root,repo)


if __name__=="__main__":
    unittest.main()
