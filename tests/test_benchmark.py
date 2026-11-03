import copy
import json
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from teobench.cli import ROOT, load, verify
from teobench.evaluate import grade, python_outputs, sandbox_command, sql_outputs
from teobench import studies


class BenchmarkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tasks, cls.answers, cls.manifest = load()

    def reference(self, task):
        acceptance = self.answers[task['id']]
        answer = acceptance.get('reference', json.dumps(acceptance.get('expected')))
        history = [{'name':'lookup', 'arguments':{'id':key}, 'ok':True,
                    'output':acceptance['catalog'][key]}
                   for key in acceptance.get('required_ids', [])]
        return answer, history

    def test_original_bytes_and_generator(self):
        report = verify()
        self.assertEqual(report['tasks'], 30)
        self.assertEqual(report['code_cases'], 300)
        self.assertEqual(report['sql_databases'], 72)
        self.assertEqual(report['public_sha256'], 'b43eed73570506edfa73940174a6e2a0dbc4b384eda43978f331dc5d93445c7b')

    def test_all_oracles_pass_and_empty_answers_fail(self):
        for task in self.tasks:
            with self.subTest(task=task['id']):
                answer, history = self.reference(task)
                result = grade(task, answer, self.answers[task['id']], history)
                self.assertTrue(result['strict_pass'], result)
                self.assertFalse(grade(task, '', self.answers[task['id']], [])['semantic_pass'])

    def test_wrong_answers_fail(self):
        for task in self.tasks:
            answer = {'code':'def solve(data): return "wrong"', 'sql':'SELECT 999999'}.get(task['family'], '{"wrong":999999}')
            with self.subTest(task=task['id']):
                self.assertFalse(grade(task, answer, self.answers[task['id']], [])['semantic_pass'])

    def test_bin_regression_and_private_local_names(self):
        self.assertEqual(python_outputs('def solve(data): return bin(data).count("1")', [7, 0, 8]), [3, 0, 1])
        self.assertEqual(python_outputs('def solve(data):\n _total = 0\n for _ in data: _total += _\n return _total', [[1,2,3]]), [6])

    def test_code_restrictions_and_timeout(self):
        for source in ['import os\ndef solve(x): return 1', 'def solve(x): return x.__class__',
                       'def solve(x): return open("/etc/passwd").read()',
                       'def solve(x):\n while True: pass']:
            with self.subTest(source=source), self.assertRaises((ValueError, RuntimeError, subprocess.TimeoutExpired)):
                python_outputs(source, [1])

    def test_os_sandbox_denies_references_and_network(self):
        reference = ROOT/'Easy-Bench/tasks/answers.json'
        script = 'try:\n open('+repr(str(reference))+').read()\nexcept PermissionError:\n print("BLOCKED")'
        result = subprocess.run(sandbox_command(script), capture_output=True, text=True, timeout=5, cwd='/')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), 'BLOCKED')
        with socket.socket() as listener:
            listener.bind(('127.0.0.1',0))
            script = 'import socket\ntry:\n socket.create_connection(("127.0.0.1",'+str(listener.getsockname()[1])+'),timeout=1)\nexcept PermissionError:\n print("BLOCKED")'
            result = subprocess.run(sandbox_command(script), capture_output=True, text=True, timeout=5, cwd='/')
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.strip(), 'BLOCKED')

    def test_no_sandbox_means_no_unsafe_fallback(self):
        with patch('teobench.evaluate.Path.exists', return_value=False), self.assertRaisesRegex(RuntimeError,'OS_sandbox_unavailable'):
            sandbox_command('print(1)')

    def test_sql_cannot_write_attach_or_load_extensions(self):
        fixture = {'tables':{'items':{'columns':['id'],'rows':[[1],[2]]}}}
        for query in ['DELETE FROM items', 'ATTACH DATABASE "/tmp/no.db" AS other', 'SELECT load_extension("x")']:
            with self.subTest(query=query), self.assertRaises(Exception):
                sql_outputs(query, fixture)
        self.assertEqual(sql_outputs('SELECT id FROM items ORDER BY id',fixture), [[1],[2]])
        with self.assertRaisesRegex(ValueError,'sql_length_limit'):
            sql_outputs('SELECT 1 '+(' '*100001),fixture)

    def test_json_format_duplicate_keys_and_non_finite(self):
        task = next(t for t in self.tasks if t['id']=='R02')
        acceptance = self.answers['R02']
        answer = json.dumps(acceptance['expected'])
        result = grade(task,'Answer: '+answer,acceptance)
        self.assertTrue(result['semantic_pass'])
        self.assertFalse(result['strict_pass'])
        for answer in ['{"minutes":NaN}','{"minutes":37,"minutes":37}', '{"minutes":Infinity}']:
            self.assertFalse(grade(task,answer,acceptance)['semantic_pass'])

    def test_tools_require_real_matching_receipts(self):
        task = next(t for t in self.tasks if t['id']=='T01')
        answer, history = self.reference(task)
        self.assertFalse(grade(task,answer,self.answers['T01'],[])['semantic_pass'])
        self.assertFalse(grade(task,answer,self.answers['T01'],history[:-1])['semantic_pass'])
        forged = copy.deepcopy(history)
        forged[0]['output']['amount'] += 1
        self.assertFalse(grade(task,answer,self.answers['T01'],forged)['semantic_pass'])

    def test_cli_show_and_grade(self):
        result = subprocess.run([sys.executable,'-m','teobench','show','R02'],cwd=ROOT,capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
        public = json.loads(result.stdout)
        self.assertNotIn('expected',public)
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'answer.txt'
            path.write_text(json.dumps(self.answers['R02']['expected']))
            result=subprocess.run([sys.executable,'-m','teobench','grade','R02','--answer',str(path)],cwd=ROOT,capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stdout)


class StudyTests(unittest.TestCase):
    def setUp(self):
        self.study=studies.create('unit-test-study','test-provider','macOS; synthetic test environment')
        self.tasks,self.answers,_=load()

    def full_run(self, correct=True):
        for task in self.tasks:
            acceptance=self.answers[task['id']]
            if correct:
                answer=acceptance.get('reference',json.dumps(acceptance.get('expected')))
                history=[{'name':'lookup','arguments':{'id':key},'ok':True,'output':acceptance['catalog'][key]} for key in acceptance.get('required_ids',[])]
            else:
                answer='def solve(data): return None' if task['family']=='code' else ('SELECT 999999' if task['family']=='sql' else '{}')
                history=[]
            studies.add_record(self.study,task['id'],'test-model','high',answer,history)
        return self.study

    def test_complete_report_regrade_and_statistics(self):
        study=self.full_run()
        report=studies.validate(study)
        self.assertEqual(report['records'],30)
        self.assertEqual(report['semantic_pass'],30)
        self.assertEqual(report['complete_runs'],1)
        with tempfile.TemporaryDirectory() as directory:
            first=Path(directory)/'one.json';second=Path(directory)/'two.json'
            studies.save(first,study)
            duplicate=copy.deepcopy(study);duplicate['study_id']='different-study-id'
            studies.save(second,duplicate)
            report=studies.statistics_report([first,second],regrade=False)
            self.assertEqual(report['duplicate_studies_excluded'],1)
            self.assertEqual(report['groups'][0]['median_pass_rate'],1)

    def test_incomplete_does_not_enter_statistics(self):
        studies.add_record(self.study,'R02','test-model','high',json.dumps(self.answers['R02']['expected']),[])
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'study.json';studies.save(path,self.study)
            report=studies.statistics_report([path])
            self.assertEqual(report['incomplete_runs_excluded'],1)
            self.assertEqual(report['groups'],[])

    def test_duplicate_condition_and_forged_score_rejected(self):
        studies.add_record(self.study,'R02','test-model','high','{}',[])
        forged=copy.deepcopy(self.study);forged['records'][0]['evaluation']['semantic_pass']=True
        with self.assertRaisesRegex(ValueError,'regrade_mismatch'):
            studies.validate(forged)
        self.study['records'].append(copy.deepcopy(self.study['records'][0]))
        with self.assertRaisesRegex(ValueError,'duplicate_task'):
            studies.validate(self.study,regrade=False)

    def test_malformed_code_is_a_model_failure_not_rejected_study(self):
        studies.add_record(self.study,'C01','test-model','high','not python !!!',[])
        report=studies.validate(self.study)
        self.assertEqual(report['semantic_pass'],0)
        self.assertEqual(report['records'],1)

    def test_transport_failure_is_retained(self):
        studies.add_record(self.study,'R02','test-model','high','',[],transport_error='timeout')
        report=studies.validate(self.study)
        self.assertEqual(report['transport_errors'],1)
        self.assertIsNone(self.study['records'][0]['evaluation'])

    def test_extra_fields_hashes_secrets_and_nan_rejected(self):
        for mutator in [lambda x:x.update(api_key='private'),
                        lambda x:x['benchmark'].update(tasks_sha256='0'*64),
                        lambda x:x.update(access_route='Bearer '+'a'*30)]:
            value=copy.deepcopy(self.study);mutator(value)
            with self.assertRaises(ValueError): studies.validate(value)
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'bad.json';path.write_text('{"x":NaN}')
            with self.assertRaises(ValueError):studies.load_json(path)

    def test_preview_never_calls_github(self):
        studies.add_record(self.study,'R02','test-model','high',json.dumps(self.answers['R02']['expected']),[])
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'study.json';studies.save(path,self.study)
            with patch('teobench.studies.subprocess.run',side_effect=AssertionError('unexpected network')):
                report=studies.publish(path)
                self.assertIn('preview',report)

    def test_submission_is_pr_without_automatic_merge(self):
        studies.add_record(self.study,'R02','test-model','high',json.dumps(self.answers['R02']['expected']),[])
        replies=[{'login':'contributor'}, {'default_branch':'main'}, {'object':{'sha':'a'*40}},
                 {'full_name':'contributor/TeoBench','default_branch':'main'}, {'object':{'sha':'a'*40}},
                 {}, {}, {'html_url':'https://github.com/teo-nex/TeoBench/pull/1'}]
        calls=[]
        def fake(command,**kwargs):
            calls.append((command,kwargs))
            return subprocess.CompletedProcess(command,0,json.dumps(replies[len(calls)-1]),'')
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'study.json';studies.save(path,self.study)
            with patch('teobench.studies.subprocess.run',side_effect=fake):
                result=studies.publish(path,publish=True,gh='gh')
        self.assertFalse(result['auto_merged'])
        self.assertTrue(calls[-1][0][2].endswith('/pulls'))
        self.assertEqual(json.loads(calls[-1][1]['input'])['base'],'main')
        self.assertIn('Easy-Bench/studies/unit-test-study/study.json',calls[-2][0][2])


if __name__=='__main__':
    unittest.main()
