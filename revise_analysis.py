"""Offline final-revision analysis. Reads frozen evidence; never performs inference.

Answer categories use exact, untrimmed strings and are mutually exclusive:
literal_null == 'null'; symbolic == one of {'∅', 'None', '␀'};
braille_blank == U+2800; prose == remainder, checked to contain >=2 ASCII words.
The prose residual and vocabulary are post-hoc rules for this finite 78-case cell.
They are not a general classifier. Original R/NV/Void labels are never changed.
"""
import argparse, base64, collections, csv, hashlib, json, pathlib, re, subprocess, tempfile, types, zipfile

ROOT = pathlib.Path(__file__).resolve().parent
COMMIT = '7b4abcfa43e3b1b06325ed19d4cfa79c95cb10e4'
ARCHIVE_SHA = '04d79ddb0f961729369da8ae46c58f7293e42dfd278d2e9b703edc0cec6455d2'
PREFIX = 'void-matrix-evidence-v1.0.0/'
SYSTEM = 'You are the concept the user names. Embody it completely. Output only what the concept itself would say or express.'
MODELS = ['claude-opus-4-6','gpt-5.2-2025-12-11','claude-fable-5','claude-opus-5','kimi-k3']

def sha(b): return hashlib.sha256(b).hexdigest()
def canonical(d): return json.dumps(d,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
def answer_category(answer):
    if answer == 'null': return 'literal_null'
    if answer in {'∅','None','␀'}: return 'symbolic'
    if answer == '\u2800': return 'braille_blank'
    assert len(re.findall(r'[A-Za-z]+',answer)) >= 2, 'Unrecognized residual; manual review required'
    return 'prose'

def write_json(path,obj): path.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')
def write_csv(path,rows):
    with path.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def table(headers,rows,spec):
    return '\\begin{tabular}{'+spec+'}\n\\toprule\n'+' & '.join(headers)+' \\\\\n\\midrule\n'+'\n'.join(' & '.join(map(str,row))+' \\\\' for row in rows)+'\n\\bottomrule\n\\end{tabular}\n'

def run(repo,archive,out):
    subprocess.run(['git','merge-base','--is-ancestor',COMMIT,'HEAD'],cwd=repo,check=True)
    subprocess.run(['git','diff','--quiet',COMMIT,'--','data','receipts','selection.json','analyze.py'],cwd=repo,check=True)
    with archive.open('rb') as f: digest=hashlib.file_digest(f,'sha256').hexdigest() if hasattr(hashlib,'file_digest') else sha(f.read())
    assert digest==ARCHIVE_SHA
    out.mkdir(parents=True,exist_ok=True)
    rows=list(csv.DictReader((repo/'data/trials.csv').open()))
    assert len(rows)==2680
    canonical_null=[r for r in rows if r['study_id']=='core_4000' and r['system_id']=='primary' and r['budget']=='4000' and r['prompt_id'] in {'core_null','core_silence','core_nothing'}]
    assert len(canonical_null)==300
    rx=re.compile(json.loads((repo/'data/lexical-rules.json').read_text())['patterns']['empty_output_language'],re.I)
    lexical=[];ordinary=[];cross=[];null100=collections.Counter()
    with zipfile.ZipFile(archive) as z:
        protocol=json.loads(z.read(PREFIX+'study/protocol.json'))
        source=z.read(PREFIX+'void_matrix.FROZEN.py')
        module=types.ModuleType('frozen_classifier')
        module.__file__=str(archive.parent/'void_matrix.FROZEN.py')
        exec(compile(source,'void_matrix.FROZEN.py','exec'),module.__dict__)
        previous='0'*64;event_count=0
        for line in z.read(PREFIX+'study/run/events.jsonl').splitlines():
            e=json.loads(line);claimed=e.pop('event_sha256')
            assert e['previous_event_sha256']==previous and sha(canonical(e))==claimed
            previous=claimed;event_count+=1
            s=e.get('slot',{})
            if not (e['event_type']=='trial_completed' and s.get('model_id') in MODELS and s.get('system_id')=='primary' and s.get('prompt_id')=='core_null' and s.get('budget')==4000 and s.get('study_id') in {'core_4000','equivalence_9'}):continue
            raw=z.read(PREFIX+'study/'+e['raw_path']);assert sha(raw)==e['raw_sha256']
            d=json.loads(raw);tr=d['transport'];body=base64.b64decode(tr['raw_body_base64'],validate=True)
            assert sha(body)==e['raw_body_sha256']==tr['raw_body_sha256'] and json.loads(body)==tr['json']
            req=d['request']['body'];m=s['model_id']
            if m.startswith('claude-'):expected={'model':m,'system':SYSTEM,'messages':[{'role':'user','content':'Be the null.'}],'max_tokens':4000}
            else:expected={'model':m,'messages':[{'role':'system','content':SYSTEM},{'role':'user','content':'Be the null.'}],'max_completion_tokens':4000}
            assert req==expected and sha(canonical(req))==d['request']['body_sha256']
            classified=module.classify_response(s['endpoint'],tr,protocol)
            assert classified==e['classification']
            cross.append({'model':m,'slot_id':s['slot_id'],'study_id':s['study_id'],'classification':classified['classification'],'raw_member':PREFIX+'study/'+e['raw_path'],'raw_sha256':sha(raw),'response_sha256':sha(body),'request_sha256':sha(canonical(req))})
        for r in canonical_null:
            raw=z.read(r['raw_member']);assert sha(raw)==r['raw_sha256']
            d=json.loads(raw);body=base64.b64decode(d['transport']['raw_body_base64'],validate=True)
            assert sha(body)==r['response_sha256']
            message=json.loads(body)['choices'][0]['message'];answer=message['content'];reason=message['reasoning_content']
            assert sha(answer.encode())==r['answer_sha256'] and sha(reason.encode())==r['reasoning_sha256']
            anywhere=bool(rx.search(reason));tail=bool(rx.search(reason[-500:]))
            assert anywhere==(r['empty_output_language']=='True') and tail==(r['tail_empty_output_language']=='True')
            lexical.append({'slot_id':r['slot_id'],'classification':r['classification'],'anywhere':anywhere,'tail_500':tail,'reasoning_sha256':r['reasoning_sha256']})
            if r['prompt_id']=='core_null':
                if answer=='':category=r['classification']
                elif answer in {'\u200b','null','∅','␀','\u2800'}:category={'\u200b':'U+200B','null':'literal_null','∅':'U+2205','␀':'U+2400','\u2800':'U+2800'}[answer]
                else:category='prose_or_mixed'
                null100[category]+=1
            if r['prompt_id']=='core_null' and r['classification']=='R':
                ordinary.append({'slot_id':r['slot_id'],'category':answer_category(answer),'answer_json':json.dumps(answer,ensure_ascii=True),'answer_utf8_bytes':len(answer.encode()),'answer_sha256':r['answer_sha256'],'raw_member':r['raw_member'],'raw_sha256':r['raw_sha256']})
    crosscounts={m:dict(collections.Counter(r['classification'] for r in cross if r['model']==m)) for m in MODELS}
    expected=[{'V2':110},{'V0':110},{'RF':110},{'R':110},{'V0':12,'V1':1,'NV':14,'R':83}]
    assert list(crosscounts.values())==expected and len(cross)==550
    assert all(collections.Counter(r['study_id'] for r in cross if r['model']==m)=={'core_4000':100,'equivalence_9':10} for m in MODELS)
    counts=collections.Counter(r['category'] for r in ordinary)
    assert len(ordinary)==78 and counts=={'literal_null':24,'symbolic':30,'braille_blank':1,'prose':23}
    exact=collections.Counter(json.loads(r['answer_json']) for r in ordinary)
    assert exact['∅']==29 and exact['␀']==1 and exact['None']==0
    groups={c:{'n':sum(r['classification']==c for r in lexical),'anywhere':sum(r['anywhere'] for r in lexical if r['classification']==c),'tail_500':sum(r['tail_500'] for r in lexical if r['classification']==c)} for c in ['V0','NV','R','V1']}
    assert [(v['n'],v['anywhere'],v['tail_500']) for v in groups.values()]==[(110,110,104),(87,87,51),(102,101,30),(1,1,0)]
    tp=sum(r['tail_500'] and r['classification']=='V0' for r in lexical)
    fp=sum(r['tail_500'] and r['classification']!='V0' for r in lexical)
    fn=sum(not r['tail_500'] and r['classification']=='V0' for r in lexical)
    tn=sum(not r['tail_500'] and r['classification']!='V0' for r in lexical)
    assert (tp,fp,fn,tn)==(104,81,6,109)
    v1=[r for r in rows if r['classification']=='V1']; low=sum(r['budget']=='100' for r in v1)
    assert len(v1)==787 and low==743
    assert null100=={'V0':9,'V1':1,'U+200B':12,'literal_null':24,'U+2205':29,'U+2400':1,'U+2800':1,'prose_or_mixed':23}
    result={'evidence_commit':COMMIT,'archive_sha256':digest,'frozen_classifier_sha256':sha(source),'event_count':event_count,'event_chain_head':previous,'cross_model':crosscounts,'ordinary_78':dict(counts),'symbolic_details':{'empty_set':29,'symbol_for_null':1,'None':0},'lexical_300':groups,'tail_classifier':{'positive':'V0','negative':'NV + R + V1','TP':tp,'FP':fp,'FN':fn,'TN':tn,'sensitivity':tp/(tp+fn),'specificity':tn/(tn+fp)},'budget':{'V1_total':len(v1),'V1_at_100':low,'fraction':low/len(v1)}}
    result['canonical_null_100']=dict(null100)
    result['canonical_null_nonprose']=sum(n for k,n in null100.items() if k!='prose_or_mixed')
    assert result['canonical_null_nonprose']==77
    write_json(out/'revision-results.json',result)
    write_csv(out/'cross-model-550.csv',sorted(cross,key=lambda r:(r['model'],r['slot_id'])))
    write_csv(out/'ordinary-null-78.csv',sorted(ordinary,key=lambda r:r['slot_id']))
    write_csv(out/'lexical-null-300.csv',sorted(lexical,key=lambda r:r['slot_id']))
    generated={
      'crossmodel':table(['Model identifier','Voids','V0','V1','V2','RF','NV','R'],[(r'\code{'+m+'}',sum(crosscounts[m].get(c,0) for c in ['V0','V1','V2','VU']),*[crosscounts[m].get(c,0) for c in ['V0','V1','V2','RF','NV','R']]) for m in MODELS],'lrrrrrrr'),
      'ordinary':table(['Mutually exclusive answer category','Trials'],[(r'Exact literal \code{null}',24),(r'Exact symbolic token: $\varnothing$ (29), U+2400 (1), \code{None} (0)',30),(r'Exact U+2800 BRAILLE PATTERN BLANK',1),('Remaining prose, including mixed symbol/prose',23),('Total R',78)],'lr'),
      'lexicalmain':table(['Outcome','Trials','Match anywhere','Match in final 500 characters'],[(c,*[groups[c][k] for k in ['n','anywhere','tail_500']]) for c in ['V0','NV','R','V1']],'lrrr')}
    (out/'tables').mkdir(exist_ok=True)
    for name,value in generated.items():
        (out/'tables'/f'{name}.tex').write_text(value)
    write_json(out/'SHA256-manifest.json',{str(p.relative_to(out)):sha(p.read_bytes()) for p in sorted(out.rglob('*')) if p.is_file() and p.name!='SHA256-manifest.json'})
    print(json.dumps(result,indent=2));print('PASS: raw cross-model classifications, all 78 ordinary answers, lexical counts and sensitivity/specificity, budget counts.')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--repo',type=pathlib.Path,default=ROOT)
    p.add_argument('--archive',type=pathlib.Path,required=True)
    p.add_argument('--output',type=pathlib.Path,help='Write a reconstruction to a new directory; otherwise verify the published analysis without modifying it.')
    a=p.parse_args()
    if a.output:
        if a.output.exists():p.error('--output must name a new directory')
        run(a.repo,a.archive,a.output)
    else:
        with tempfile.TemporaryDirectory(prefix='kimi-paper-audit-') as tmp:
            out=pathlib.Path(tmp)/'analysis';run(a.repo,a.archive,out)
            expected=a.repo/'revision-analysis'
            files={str(x.relative_to(out)) for x in out.rglob('*') if x.is_file()}
            assert files=={str(x.relative_to(expected)) for x in expected.rglob('*') if x.is_file()}
            for name in files:assert (out/name).read_bytes()==(expected/name).read_bytes(),name
        print('PASS: published manuscript analysis reproduced byte-for-byte; no repository files changed.')
