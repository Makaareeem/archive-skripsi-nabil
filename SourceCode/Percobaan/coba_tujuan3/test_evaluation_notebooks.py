"""Uji logika notebook tanpa mengunduh model atau menjalankan inferensi."""
import ast
import asyncio
import collections
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import re
import string
import tempfile
import time
from types import SimpleNamespace
import unittest

import nbformat
import numpy as np
import pandas as pd

HERE = Path(__file__).parent


# Muat definisi fungsi saja agar pengujian tidak memicu sel inferensi.
def functions_from_notebook(name):
    scope = dict(Path=Path, pd=pd, np=np, json=json, hashlib=hashlib,
                 re=re, string=string, collections=collections, Decimal=Decimal, time=time)
    notebook = nbformat.read(HERE / name, as_version=4)
    for cell in notebook.cells:
        if cell.cell_type == 'code' and 'pipeline_snapshot' not in cell.metadata.get('tags', []):
            tree = ast.parse(cell.source)
            nodes = [n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
            exec(compile(ast.Module(body=nodes, type_ignores=[]), name, 'exec'), scope)
    return scope


class NotebookTests(unittest.TestCase):
    # Persiapkan namespace fungsi dan direktori hasil sementara.
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.out = Path(self.temp.name)
        self.eval = functions_from_notebook('19-compute-evaluate-rag.ipynb')
        self.run = functions_from_notebook('18-evaluate-rag.ipynb')
        self.eval['OUT'] = self.run['OUT'] = self.out

    # Bersihkan hanya berkas uji sementara yang dibuat pengujian ini.
    def tearDown(self):
        self.temp.cleanup()

    # Pastikan notebook valid, setiap sel dapat dikompilasi, dan fungsi berkomentar.
    def test_notebook_structure_and_comments(self):
        for path in [*HERE.glob('18-*.ipynb'), *HERE.glob('19-*.ipynb'), *HERE.glob('20-*.ipynb')]:
            nb = nbformat.read(path, as_version=4)
            nbformat.validate(nb)
            for cell in nb.cells:
                if cell.cell_type != 'code':
                    continue
                self.assertEqual(cell.outputs, [])
                compile(cell.source, str(path), 'exec', flags=ast.PyCF_ALLOW_TOP_LEVEL_AWAIT)
                for node in ast.walk(ast.parse(cell.source)):
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        self.assertTrue(cell.source.splitlines()[node.lineno - 2].lstrip().startswith('#'))


    # Evaluasi gabungan dan evaluasi ulang harus memakai implementasi identik.
    def test_shared_evaluation_cells(self):
        sources = []
        for name in ['18-evaluate-rag.ipynb', '19-compute-evaluate-rag.ipynb']:
            nb = nbformat.read(HERE / name, as_version=4)
            sources.append([c.source for c in nb.cells if 'shared_evaluation' in c.metadata.get('tags', [])])
        self.assertEqual(sources[0], sources[1])
        self.assertEqual(len(sources[0]), 5)


    # Snapshot pipeline harus berdiri sendiri dan cocok dengan hash yang dicatat.
    def test_self_contained_pipeline_snapshot(self):
        nb = nbformat.read(HERE / '18-evaluate-rag.ipynb', as_version=4)
        snapshots = [c.source for c in nb.cells if 'pipeline_snapshot' in c.metadata.get('tags', [])]
        self.assertEqual(len(snapshots), 1)
        self.assertNotIn('from app.', snapshots[0])
        config = next(c.source for c in nb.cells if c.cell_type == 'code' and c.source.startswith('PIPELINE_HASH ='))
        expected = ast.literal_eval(ast.parse(config).body[0].value)
        self.assertEqual(hashlib.sha256(snapshots[0].encode()).hexdigest(), expected)

    # Acuan sintetis dan skor lama tidak diperlukan atau diteruskan ke evaluasi baru.
    def test_ragas_inputs_without_reference(self):
        row = dict(record_id='q', model_key='base', architecture='a', condition='K1',
                   protocol='end_to_end', status='ok', question='?', answer='jawaban',
                   contexts=[], use_rag=False, context_hash='h')
        frame = self.eval['prepare_ragas_inputs'](pd.DataFrame([row]))
        self.assertEqual(len(frame), 1)
        row.update(ans_ref='unused', token_f1=.9, em_numeric=1)
        clean = self.eval['prepare_ragas_inputs'](pd.DataFrame([row]))
        self.assertNotIn('ans_ref', clean)
        self.assertNotIn('token_f1', clean)
        self.assertNotIn('em_numeric', clean)
        row['contexts'] = ['unexpected context']
        with self.assertRaises(AssertionError):
            self.eval['prepare_ragas_inputs'](pd.DataFrame([row]))

    # Ringkasan tahap sistem harus berisi tepat tiga metrik, tanpa evaluator lama.
    def test_only_three_metrics(self):
        for name in ['18-evaluate-rag.ipynb', '19-compute-evaluate-rag.ipynb']:
            nb = nbformat.read(HERE / name, as_version=4)
            code = '\n'.join(c.source for c in nb.cells if c.cell_type == 'code')
            for obsolete in ['def numeric_em(', 'def token_f1(', 'def indobert_scores(',
                             'def retrieval_metrics(', 'bert-score==', 'rouge-score==']:
                self.assertNotIn(obsolete, code)
            assignments = [n for n in ast.parse(code).body if isinstance(n, ast.Assign)
                           and isinstance(n.targets[0], ast.Name) and n.targets[0].id == 'METRICS']
            self.assertEqual(ast.literal_eval(assignments[0].value),
                             ['faithfulness', 'answer_relevancy', 'context_relevance'])

    # Robustness lokal tidak mengimpor evaluator lama atau menyebut jumlah request sebagai akurasi.
    def test_robustness_reports_request_coverage(self):
        scope = functions_from_notebook('20-test-function-robustness-latency.ipynb')
        rows = pd.DataFrame([dict(kind='typo', model_key='m', use_rag=True, status=s)
                             for s in ['ok', 'ok', 'error']])
        report = scope['summarize_robustness'](rows)
        self.assertEqual(report.n_requests.sum(), 3)
        self.assertNotIn('load_token_f1', scope)

    # Generasi tetap berjalan tanpa kolom jawaban acuan.
    def test_generation_without_reference(self):
        self.fake_pipeline()
        ex = dict(record_id='no_ref', instruction='question')
        scenario = dict(architecture='a', condition='K1', model_key='base', use_rag=False)
        result = self.run['run_one'](ex, scenario, 'end_to_end', {'experiment_id': 'v1'}, None, None)
        self.assertEqual(result['status'], 'ok')

    # Jalankan seluruh sel evaluasi sampai ekspor tanpa API, qrels, encoder, atau acuan.
    def test_offline_evaluation_export(self):
        scenarios = [dict(architecture='a', condition=k, model_key='base', use_rag=rag)
                     for k, rag in [('K1', False), ('K2', True)]]
        self.run['write_json'](self.out / 'manifest.json', dict(
            experiment_id='v1', pilot=True, protocols=['end_to_end'], scenarios=scenarios))
        pd.DataFrame([dict(record_id='q', instruction='?')]).to_csv(self.out / 'test_selected.csv', index=False)
        for s in scenarios:
            self.run['write_json'](self.out / 'predictions' / (s['condition'] + '.json'), dict(
                **s, record_id='q', protocol='end_to_end', experiment_id='v1', status='ok',
                question='?', answer='jawaban', contexts=['bukti'] if s['use_rag'] else [], context_hash='h'))
        scope = dict(self.eval, RUN_RAGAS=False, display=lambda *args: None)
        nb = nbformat.read(HERE / '19-compute-evaluate-rag.ipynb', as_version=4)
        for c in nb.cells:
            if c.cell_type == 'code' and 'shared_evaluation' in c.metadata.get('tags', []):
                result = eval(compile(c.source, '<offline-export>', 'exec', flags=ast.PyCF_ALLOW_TOP_LEVEL_AWAIT), scope)
                if result is not None:
                    asyncio.run(result)
        result = pd.read_csv(self.out / 'system_scored.csv')
        self.assertEqual(len(result), 2)
        self.assertTrue({'answer_relevancy', 'faithfulness', 'context_relevance'} <= set(result))
        self.assertTrue(set(result).isdisjoint({'em_numeric', 'token_f1', 'rouge_l', 'indobertscore', 'recall_at_5', 'ans_ref'}))
        self.assertFalse((self.out / 'ragas_cache').exists())

    # Uji ketiga metrik, NA tanpa konteks, cache per metrik dan retry tanpa API.
    def test_three_ragas_metrics_and_cache(self):
        calls = collections.Counter()

        class FakeMetric:
            # Simpan nama metrik dan status kegagalan simulasi.
            def __init__(self, name):
                self.name = name

            # Gagal sekali hanya pada faithfulness untuk menguji retry terpisah.
            async def single_turn_ascore(self, sample):
                calls[self.name] += 1
                if self.name == 'faithfulness' and calls[self.name] == 1:
                    raise RuntimeError('simulated private detail')
                if self.name == 'context_relevance':
                    assert not hasattr(sample, 'response')
                return .75

        metrics = {n: FakeMetric(n) for n in ['faithfulness', 'answer_relevancy', 'context_relevance']}
        frame = pd.DataFrame([dict(question='q', answer='a', contexts=['c'], use_rag=True),
                              dict(question='q', answer='a', contexts=[], use_rag=False)])
        f = self.eval['score_ragas_cached']
        first = asyncio.run(f(frame, metrics, {'judge': 'fake'}, SimpleNamespace))
        self.assertTrue(np.isnan(first.loc[0, 'faithfulness']))
        self.assertEqual(first.loc[1, 'context_relevance_status'], 'no_rag_not_applicable')
        second = asyncio.run(f(frame, metrics, {'judge': 'fake'}, SimpleNamespace))
        self.assertEqual(second.loc[0, 'faithfulness'], .75)
        self.assertEqual(calls, {'faithfulness': 2, 'answer_relevancy': 1, 'context_relevance': 1})
        self.assertFalse(any('private detail' in p.read_text() for p in self.out.rglob('*.json')))
        frame.loc[0, 'contexts'] = ['x' * 7001]
        third = asyncio.run(f(frame, metrics, {'judge': 'fake'}, SimpleNamespace))
        self.assertTrue(third.loc[0, 'context_relevance_truncated'])
        self.assertEqual(third.loc[0, 'context_relevance_context_chars'], 7001)

    # Pemulihan tidak menimpa berkas yang berbeda.
    def test_restore_conflict_is_rejected(self):
        src, dst = self.out / 'src', self.out / 'dst'
        src.mkdir()
        dst.mkdir()
        (src / 'manifest.json').write_text('{}')
        (dst / 'manifest.json').write_text('{"other":1}')
        with self.assertRaises(ValueError):
            self.run['restore_run'](src, dst)
        self.assertEqual((dst / 'manifest.json').read_text(), '{"other":1}')






    # Verifikasi selisih berpasangan dan penolakan konteks controlled yang berbeda.
    def test_paired_comparison(self):
        self.eval['METRICS'] = ['answer_relevancy']
        frame = pd.DataFrame([
            dict(protocol='controlled', architecture='a', condition='K2', record_id='q', answer_relevancy=.2, context_hash='h'),
            dict(protocol='controlled', architecture='a', condition='K4', record_id='q', answer_relevancy=.8, context_hash='h'),
            dict(protocol='controlled', architecture='a', condition='K4', record_id='unpaired', answer_relevancy=1., context_hash='h')])
        result = self.eval['paired_differences'](frame)
        self.assertEqual(result.iloc[0].n_pairs, 1)
        self.assertAlmostEqual(result.iloc[0].mean_delta, .6)
        frame.loc[1, 'context_hash'] = 'different'
        with self.assertRaises(AssertionError):
            self.eval['paired_differences'](frame)

    # Susun komponen palsu untuk menguji pengarsipan tanpa model sungguhan.
    def fake_pipeline(self):
        self.run['cfg'] = SimpleNamespace(MODEL_REGISTRY={
            name: dict(ollama_name=name, system_role=True) for name in ['base', 'ft']})
        self.run['REFERENCE_MODEL'] = 'base'
        calls = {'retrieval': 0, 'generation': 0}

        # Catat berapa kali retrieval dipanggil.
        def retrieve(*args):
            calls['retrieval'] += 1
            return dict(docs=[dict(text='source', metadata={'chunk_id': 'c', 'faiss_id': 0}, score=1)],
                        expansions=['expanded'], retrieval_s=.1, ranked_ids=['c'], candidate_ids=['c'])

        # Catat generasi dan pastikan jawaban acuan tidak masuk prompt.
        def generate(*args, **kwargs):
            calls['generation'] += 1
            self.assertNotIn('GOLD_SECRET', str(args))
            return 'answer'

        self.run.update(retrieve=retrieve, generate=generate,
                        restore_docs=lambda snap: [SimpleNamespace(page_content=d['text'], metadata=d['metadata']) for d in snap['docs']],
                        generate_citations=lambda *args: {},
                        format_context=lambda docs: '\n'.join(d.page_content for d in docs),
                        build_messages=lambda q, docs, role, rag: [{'role': 'user', 'content': q + ''.join(d.page_content for d in docs)}])
        return calls

    # Pastikan cache identik lintas generator dan resume tidak mengulang inferensi.
    def test_controlled_cache_and_resume(self):
        calls = self.fake_pipeline()
        ex = dict(record_id='q', instruction='question', ans_ref='GOLD_SECRET')
        a = dict(architecture='a', condition='K2', model_key='base', use_rag=True)
        b = dict(architecture='a', condition='K4', model_key='ft', use_rag=True)
        f = self.run['run_one']
        first = f(ex, a, 'controlled', {'experiment_id': 'v1'}, None, None)
        second = f(ex, b, 'controlled', {'experiment_id': 'v1'}, None, None)
        f(ex, a, 'controlled', {'experiment_id': 'v1'}, None, None)
        self.assertEqual(first['status'], 'ok')
        self.assertEqual(first['context_hash'], second['context_hash'])
        self.assertEqual(calls, {'retrieval': 1, 'generation': 2})
        self.assertTrue(second['retrieval_cache_hit'])

    # Simpan kegagalan eksplisit dan izinkan percobaan ulang berhasil.
    def test_failure_then_retry(self):
        self.fake_pipeline()

        # Simulasikan kegagalan runtime inferensi.
        def fail(*args, **kwargs):
            raise RuntimeError('offline')

        self.run['generate'] = fail
        ex = dict(record_id='q', instruction='question', ans_ref='gold')
        scenario = dict(architecture='a', condition='K1', model_key='base', use_rag=False)
        f = self.run['run_one']
        result = f(ex, scenario, 'end_to_end', {'experiment_id': 'v1'}, None, None)
        self.assertEqual(result['status'], 'error')
        self.assertNotIn('answer', result)
        self.run['generate'] = lambda *a, **k: 'recovered'
        recovered = f(ex, scenario, 'end_to_end', {'experiment_id': 'v1'}, None, None)
        self.assertEqual(recovered['status'], 'ok')
        self.assertEqual(recovered['contexts'], [])



    # Pisahkan teks berbeda yang memakai chunk_id sama pada metadata aktual.
    def test_duplicate_source_ids_are_disambiguated(self):
        path = self.out / 'metadata.jsonl'
        records = [dict(chunk_id='toc', faiss_id=i, text=str(i)) for i in range(2)]
        path.write_text('\n'.join(json.dumps(r) for r in records), encoding='utf-8')
        chunks = self.run['load_chunks'](path)
        self.assertEqual(set(chunks), {'toc::faiss=0', 'toc::faiss=1'})



if __name__ == '__main__':
    unittest.main(verbosity=2)
