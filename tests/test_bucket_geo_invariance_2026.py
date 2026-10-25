"""Garante que a mesma zona/turno nao seja dividida entre buckets.

Regressao para interpretacao correta da comparacao Senado v1/v2 2026.
Testa a chave do particionador, sem acessar dados eleitorais reais.
"""
import unittest
import zlib

from reconcile_stream import bucket_for, normalize


class GeographicBucketInvariantTest(unittest.TestCase):
    def test_all_sections_offices_and_candidates_same_zone(self):
        for uf, mu, zona, turno in [
            ("AC", "1007", "9", "1"),
            ("AL", "2003", "11", "1"),
            ("SP", "71072", "1", "1"),
            ("TO", "97376", "33", "1"),
        ]:
            expected = zlib.crc32(
                f"{uf}|{int(mu)}|{int(zona)}|{int(turno)}".encode("utf-8")
            ) % 256
            for section in ("1", "2", "9999"):
                for office, candidate in [
                    ("1", "13"), ("1", "22"),
                    ("5", "111"), ("5", "222"),
                    ("3", "45"), ("6", "9000"),
                ]:
                    row = (1, "bu", uf, mu, zona, section,
                           turno, office, candidate, 12)
                    normalized = normalize(row, None, None)
                    self.assertIsNotNone(normalized)
                    self.assertEqual(bucket_for(normalized, 256), expected)

    def test_same_zone_is_stable_for_various_partition_counts(self):
        a = ("AC", "1007", "9", "1", "1", "1", "13", "bu", "20")
        b = ("AC", "1007", "9", "900", "1", "5", "277", "bu", "10")
        for count in (2, 8, 32, 64, 256):
            self.assertEqual(bucket_for(a, count), bucket_for(b, count))


if __name__ == "__main__":
    unittest.main()
