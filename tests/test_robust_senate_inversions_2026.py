"""Testes sinteticos de robustez 2026 (nenhum dado eleitoral real)."""
import csv
import hashlib
import json
from pathlib import Path
import statistics
import tempfile
import unittest
from unittest.mock import patch

import robust_senate_inversions_2026 as robust
from senate_robustness_io_2026 import aggregate_shard
from senate_robustness_stats_2026 import analyze, sum_cov
from reconcile_stream import sha256


FIELDS=["UF","municipio","zona","secao","turno","cargo","votavel","votos_BU"]


def fixture(path, part=0):
    observations=[("101","1",10,70),("101","2",20,80),
                  ("102","3",70,10),("102","4",80,20)]
    with path.open("w",newline="",encoding="utf-8") as f:
        w=csv.writer(f,delimiter=";")
        w.writerow(FIELDS)
        for mu, sec, p13, sen170 in observations:
            if part and int(sec)%2!=(part-1):
                continue
            for office,cand,n in [
                ("1","13",p13),("1","22",100-p13),
                ("5","170",sen170),("5","171",100-sen170),
                ("5","172",100)]:
                w.writerow(["AC",mu,"1",sec,"1",office,cand,n])


def moments(path):
    return aggregate_shard(path,{("AC","13","170"):{},("AC","22","170"):{}})


class RobustnessTest(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.folder=self.root/"analysis"/"entre_cargos"/"fixture"
        (self.folder/"candidatos").mkdir(parents=True)

    def test_generator_moments_are_not_consumed_mid_sum(self):
        values = [(1.0,2.0,3.0),(4.0,5.0,6.0)]
        self.assertEqual(sum_cov(values),sum_cov(x for x in values))
        self.assertEqual(sum_cov(x for x in values),(5.0,7.0,9.0))

    def test_simpson_and_bootstrap_sign(self):
        path=self.folder/"candidatos"/"bucket-0000.csv"
        fixture(path)
        groups=moments(path)
        sample=[m for k,m in groups.items() if k[4:]==("13","170")]
        self.assertEqual(sum(m[0] for m in sample),4)
        raw=statistics.correlation([.1,.2,.7,.8],[.7,.8,.1,.2])
        self.assertLess(raw,-0.9)
        data=analyze(sample,4,2,raw,1.0,42,100)
        self.assertAlmostEqual(data["r_ajustado"],1.0,places=5)
        self.assertAlmostEqual(data["r_bruto"],raw,places=5)
        self.assertEqual(data["pct_loo_mesmo_sinal"],100)
        self.assertEqual(data["pct_boot_mesmo_sinal"],100)
        self.assertEqual(data["r_zonas_n5"],"")
        self.assertEqual(data["bootstrap_validos"],100)

    def test_reconstruction_rejects_tampered_reference(self):
        path=self.folder/"candidatos"/"bucket-0000.csv"
        fixture(path)
        group=[m for k,m in moments(path).items() if k[4:]==("13","170")]
        with self.assertRaises(RuntimeError):
            analyze(group,4,2,-.1,1.0,42,100)

    def test_resume_checkpoints_reuses_without_reading(self):
        p1=self.folder/"candidatos"/"bucket-0000.csv"
        p2=self.folder/"candidatos"/"bucket-0001.csv"
        fixture(p1,1)
        fixture(p2,2)
        fp="f"*64
        (self.folder/"state.json").write_text(json.dumps({
            "completed":{str(i):{"candidate_sha256":sha256(p)}
                         for i,p in enumerate((p1,p2))}
        }),encoding="utf-8")
        base=self.folder/"correlacao_presidente_senado_v2"
        comparison=base/"comparacao_metodologica"
        comparison.mkdir(parents=True)
        csv_file=base/"pares_por_uf.csv"
        x=[.1,.2,.7,.8];y=[.7,.8,.1,.2]
        raw=round(statistics.correlation(x,y),6)
        with csv_file.open("w",newline="",encoding="utf-8") as f:
            w=csv.DictWriter(f,delimiter=";",fieldnames=[
                "UF","presidente","senador","secoes_com_dois_cargos",
                "zonas_com_variacao","correlacao_bruta_pearson",
                "correlacao_dentro_municipio_zona"])
            w.writeheader()
            w.writerow({"UF":"AC","presidente":"13","senador":"170",
                        "secoes_com_dois_cargos":4,"zonas_com_variacao":2,
                        "correlacao_bruta_pearson":raw,
                        "correlacao_dentro_municipio_zona":1.0})
        hash_v2=sha256(csv_file)
        (base/"summary.json").write_text(json.dumps({
            "version":"cross-office-senate-v2","fingerprint":fp,
            "csv":str(csv_file),"csv_sha256":hash_v2}),encoding="utf-8")
        comp_csv=comparison/"pares_v1_v2.csv"
        comp_csv.write_text("fixture",encoding="utf-8")
        (comparison/"summary.json").write_text(json.dumps({
            "fingerprint":fp,"source_v2_sha256":hash_v2,
            "output":str(comp_csv),"output_sha256":sha256(comp_csv),
            "totals":{"v2_inversoes":1},
            "v2_pares_com_inversao":[{"UF":"AC","presidente":"13",
                                     "senador":"170","r_bruto":raw,
                                     "r_ajustado":1.0}]}),encoding="utf-8")
        with patch.object(robust,"source",return_value=(
            self.folder,{"source_fingerprint":fp},[p1,p2])):
            first=robust.run(self.root,replicacoes=100)
            second=robust.run(self.root,replicacoes=100)
        self.assertEqual(first["pares"],1)
        self.assertEqual(first["results"],second["results"])
        self.assertEqual(second["checkpoints_reutilizados"],2)
        self.assertEqual(first["results"][0]["pct_loo_mesmo_sinal"],100)
        self.assertEqual(sha256(Path(first["csv"])),first["csv_sha256"])


if __name__=="__main__":
    unittest.main()
