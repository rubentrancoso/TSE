"""Fase 5J: evidencias 2026 da diferenca de 42 contadores."""
from pathlib import Path
import csv
import json
import tempfile
import unittest
from unittest.mock import patch

import reconcile_42_section_counters_2026 as rec
from extract_bweb_received_2026 import VERSION as H_VERSION
from reconcile_stream import sha256


ROOT=Path(__file__).resolve().parents[1]


class Reconcile42Tests(unittest.TestCase):
    def test_real_phase2_counter_arithmetic_is_42(self):
        phase2=json.loads((ROOT/rec.STAGE2).read_text("utf-8"))
        b=phase2["ufs"]["BA"]
        m=phase2["ufs"]["MG"]
        self.assertEqual(b["state_st_minus_municipal_st"],6)
        self.assertEqual(m["state_st_minus_municipal_st"],36)
        self.assertEqual(
            sum(x["state_st_minus_municipal_st"] for x in phase2["ufs"].values()),
            42)
        zones=rec.csv_rows(ROOT/rec.ZONAL)
        muns=rec.csv_rows(ROOT/rec.MUNICIPAL)
        self.assertEqual(sum(int(x["ea20_zone_ts"])-int(x["ea20_zone_st"])
                    for x in zones),36)
        diffs=[x for x in muns if x["uf"] in ("BA","MG")
               and x["ea20_st"]!=x["ea20_ts"]]
        self.assertEqual(len(diffs),11)
        joaima=next(x for x in diffs if x["municipality_name"]=="JOAÍMA")
        self.assertEqual(int(joaima["ea20_ts"])-int(joaima["ea20_st"]),6)
        zjo=next(x for x in zones if x["municipality_name"]=="JOAÍMA")
        self.assertEqual(int(zjo["ea20_zone_st"]),40)
        self.assertEqual(int(joaima["ea20_st"]),34)

    def test_rejects_cache_sha_tamper_and_duplicate_key(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t)
            folder=root/rec.LOCAL
            folder.mkdir(parents=True)
            path=folder/"received-BA.csv"
            def write(rows):
                with path.open("w",newline="",encoding="utf-8") as f:
                    w=csv.writer(f,delimiter=";")
                    w.writerow(("UF","municipio","zona","secao","turno"))
                    w.writerows(rows)
            write([("BA","33693","177","109","1")])
            pathmg=folder/"received-MG.csv"
            with pathmg.open("w",newline="",encoding="utf-8") as f:
                w=csv.writer(f,delimiter=";")
                w.writerow(("UF","municipio","zona","secao","turno"))
                w.writerow(("MG","47198","149","1","1"))
            ufs={x:{"sections":0} for x in
                "AC AL AM AP BA CE DF ES GO MA MG MS MT PA PB PE PI PR RJ RN RO RR RS SC SE SP TO ZZ".split()}
            ufs["BA"].update({"sections":1,"shard_sha256":sha256(path)})
            ufs["MG"].update({"sections":1,"shard_sha256":sha256(pathmg)})
            ufs["ZZ"]["sections"]=1309
            (folder/"summary.json").write_text(
                json.dumps({"version":H_VERSION,"sections":499206,"ufs":ufs}),
                encoding="utf-8")
            manifest,sets,_=rec.read_h(root)
            self.assertEqual(len(sets["BA"]),1)
            self.assertEqual(manifest["sections"],499206)
            path.write_text("modified",encoding="utf-8")
            with self.assertRaises(RuntimeError):
                rec.read_h(root)
            write([("BA","33693","177","109","1"),
                   ("BA","33693","0177","0109","1")])
            ufs["BA"]["sections"]=2
            ufs["BA"]["shard_sha256"]=sha256(path)
            (folder/"summary.json").write_text(
                json.dumps({"version":H_VERSION,"sections":499206,"ufs":ufs}),
                encoding="utf-8")
            with self.assertRaises(RuntimeError):
                rec.read_h(root)

    def test_ea16_preserves_aggregated_identity(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t)
            folder=root/"data"/"forensics"/"phase3"/"raw"/"ea16"
            folder.mkdir(parents=True)
            refs={"sources":[]}
            for uf in ("BA","MG"):
                data={"abr":[{"cd":uf.lower(),"mu":[{
                    "cd":"33693","zon":[{"cd":"0177","sec":[
                       {"ns":"0109"},
                       {"ns":"0110","nsp":"0109"},
                       {"ns":"0111"}
                    ]}]
                }]}]}
                path=folder/f"{uf.lower()}-p003220-cs.json"
                path.write_text(json.dumps(data),encoding="utf-8")
                refs["sources"].append({"uf":uf,"sha256":sha256(path)})
            evidence,detail=rec.read_ea16(root,root,refs)
            self.assertEqual(len(evidence["BA"]["principal"]),2)
            self.assertEqual(len(evidence["BA"]["extra"]),1)
            self.assertEqual(detail["MG"]["status"],"EA16_SHA_VALIDADO")
            self.assertIn(("BA",33693,177,109),evidence["BA"]["principal"])
            self.assertNotIn(("BA",33693,177,110),evidence["BA"]["principal"])

    def test_aggregate_counts_do_not_identify_missing_keys(self):
        # O mesmo saldo de seis pode representar diversos conjuntos
        # diferentes de chaves; sem timestamp/lista ST nao ha identidade.
        configured=set(range(1,41))
        a=configured-set(range(1,7))
        b=configured-set(range(35,41))
        self.assertEqual(len(configured-a),len(configured-b))
        self.assertNotEqual(configured-a,configured-b)


if __name__=="__main__":
    unittest.main()
