"""Conciliação exterior ZZ 2026; testes sintéticos sem rede."""
import csv
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import audit_zz_42_sections_2026 as module
from extract_bweb_received_2026 import VERSION as H_VERSION
from reconcile_stream import sha256


class AuditZZTest(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.base=Path(tmp.name)
        self.repo=self.base/"repo"
        self.root=self.base/"H"
        self.runname="20261005T104314Z"
        self.work=self.repo/"data"/"forensics"/"runs"/self.runname
        self.work.mkdir(parents=True)
        self.cache=self.root/module.CACHE
        self.cache.mkdir(parents=True)
        phase2=self.repo/"data/forensics/analysis/phase2_sections_summary.json"
        phase2.parent.mkdir(parents=True)
        phase2.write_text(json.dumps({"latest_snapshot":self.runname}),encoding="utf-8")
        shard=self.cache/"received-ZZ.csv"
        with shard.open("w",encoding="utf-8",newline="") as f:
            w=csv.writer(f,delimiter=";")
            w.writerow(("UF","municipio","zona","secao","turno"))
            w.writerows([("ZZ","10010","1","1","1"),
                         ("ZZ","10010","1","2","1"),
                         ("ZZ","20020","2","1","1")])
        (self.cache/"summary.json").write_text(json.dumps({
            "version":H_VERSION,"ufs":{"ZZ":{"sections":3,
                                         "shard_sha256":sha256(shard)}}}),encoding="utf-8")
        self.patchA=patch.object(module,"EXPECTED_BWEB",3)
        self.patchB=patch.object(module,"EXPECTED_UF_ST",5)
        self.patchC=patch.object(module,"EXPECTED_DELTA",2)
        for p in (self.patchA,self.patchB,self.patchC):
            p.start();self.addCleanup(p.stop)
        config=self.work/"config/municipios.json"
        config.parent.mkdir(parents=True)
        config.write_text(json.dumps({"abr":[{"cd":"zz","mu":[
            {"cd":"10010","nm":"Cidade A"},{"cd":"20020","nm":"Cidade B"}]}]}),encoding="utf-8")

    def create_snapshots(self,a,b,state=5):
        records=[]
        def add(kind,code,path,s,t):
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_text(json.dumps({"s":{"st":str(s),"ts":str(t)},
                   "dt":"05/10/2026","ht":"03:05:00"}),encoding="utf-8")
            item={"kind":kind,"uf":"zz","sha256":sha256(path)}
            if kind=="municipality":item["municipality_code"]=str(code)
            records.append(item)
        add("state",0,self.work/"live/uf/zz.json",state,state)
        add("municipality",10010,self.work/"live/municipio/zz/10010.json",a,a)
        add("municipality",20020,self.work/"live/municipio/zz/20020.json",b,b)
        (self.work/"manifest.jsonl").write_text(
            "\n".join(json.dumps(x) for x in records)+"\n",encoding="utf-8")

    def test_difference_wholly_state_aggregation(self):
        self.create_snapshots(2,1,5)
        report=module.run(self.root,self.repo)
        self.assertEqual(report["status"],"DIFERENCA_APENAS_NO_AGREGADO_ZZ")
        self.assertEqual(report["national"]["UF_st_minus_municipal_st_sum"],2)
        self.assertEqual(report["national"]["municipal_st_sum_minus_BWEB"],0)
        self.assertEqual(report["national"]["EA20_municipal_archived_SHA_validated"],2)

    def test_difference_wholly_in_municipal_counters(self):
        self.create_snapshots(3,2,5)
        report=module.run(self.root,self.repo)
        self.assertEqual(report["status"],"DIFERENCA_LOCALIZADA_NOS_CONTADORES_MUNICIPAIS_ZZ")
        self.assertEqual(report["national"]["municipal_st_sum_minus_BWEB"],2)
        self.assertEqual(report["national"]["UF_st_minus_municipal_st_sum"],0)
        self.assertEqual(report["national"]["municipalities_with_st_greater_than_BWEB"],2)

    def test_split_difference_between_levels(self):
        self.create_snapshots(3,1,5)
        report=module.run(self.root,self.repo)
        self.assertEqual(report["status"],"DIFERENCA_DIVIDIDA_ENTRE_NIVEIS_ZZ")
        self.assertEqual(report["national"]["UF_st_minus_municipal_st_sum"],1)
        self.assertEqual(report["national"]["municipal_st_sum_minus_BWEB"],1)

    def test_invalid_source_hash_is_fatal(self):
        self.create_snapshots(3,2,5)
        file=self.work/"live/municipio/zz/10010.json"
        file.write_text('{"s":{"st":0,"ts":0}}',encoding="utf-8")
        with self.assertRaises(RuntimeError):
            module.run(self.root,self.repo)

    def test_absent_municipality_not_called_zero(self):
        self.create_snapshots(3,2,5)
        file=self.work/"live/municipio/zz/10010.json"
        file.unlink()
        report=module.run(self.root,self.repo)
        self.assertEqual(report["status"],"COBERTURA_MUNICIPAL_INCOMPLETA")
        self.assertFalse(report["national"]["all_municipal_counters_compared"])
        self.assertIsNone(report["national"]["UF_st_minus_municipal_st_sum"])


if __name__=="__main__":
    unittest.main()
