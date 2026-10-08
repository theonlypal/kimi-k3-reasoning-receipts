#!/usr/bin/env python3
"""Verify release hashes, then optionally reconstruct every result offline."""
import argparse, collections, csv, json, pathlib, tempfile
from analyze import ROOT, reconstruct, require, sha

def verify_manifest():
    listed=set()
    for line in (ROOT/'SHA256SUMS.txt').read_text().splitlines():
        digest,name=line.split('  ',1);p=ROOT/name
        require(p.resolve().is_relative_to(ROOT.resolve()),'Manifest path escapes root')
        require(name not in listed,'Duplicate manifest entry');listed.add(name)
        require(sha(p.read_bytes())==digest,'Checksum mismatch: '+name)
    actual={str(p.relative_to(ROOT)) for p in ROOT.rglob('*') if p.is_file() and not any(x in {'.git','__pycache__'} for x in p.relative_to(ROOT).parts) and p.name!='SHA256SUMS.txt'}
    require(actual==listed,'Manifest does not cover exact package file set')
    return len(listed)

def verify_counts(data):
    rows=list(csv.DictReader((data/'trials.csv').open()))
    require(len(rows)==2680 and len({r['slot_id'] for r in rows})==2680,'Final population mismatch')
    require(collections.Counter(r['classification'] for r in rows)=={'V0':360,'V1':787,'NV':264,'R':1268,'E':1},'Census mismatch')
    require(sum(r['reasoning_nonempty']=='True' for r in rows)==2679,'Reasoning presence mismatch')
    for cls in ('V0','V1','NV','R'):
        require(all(r['reasoning_nonempty']=='True' for r in rows if r['classification']==cls),'Missing reasoning')
    core=[r for r in rows if r['study_id']=='core_4000']
    for prompt,nv0 in [('core_nothing',53),('core_silence',48),('core_null',9)]:
        cell=[r for r in core if r['prompt_id']==prompt];require(len(cell)==100 and sum(r['classification']=='V0' for r in cell)==nv0,'Core count mismatch')
    control=[r for r in core if r['prompt_id'] in {'matched_value','matched_speech','matched_something'}]
    require(len(control)==300 and all(r['classification']=='R' for r in control),'Control mismatch')
    require(len(list(csv.DictReader((data/'v0-references.csv').open())))==360,'V0 index mismatch')
    selected=[json.loads((data/'selected'/f'{n:02d}.json').read_text()) for n in range(1,11)]
    for number,filter_fn in [(6,lambda r:r['study_id']=='core_4000' and r['prompt_id']=='core_nothing' and r['classification']=='V0'),(10,lambda r:r['system_id']=='extended' and r['prompt_id']=='core_silence' and r['budget']=='16000' and r['classification']=='V0')]:
        require(selected[number-1]['reasoning_tokens']==min(int(r['reasoning_tokens']) for r in rows if filter_fn(r)),'Extreme-selection mismatch')

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--archive',type=pathlib.Path);args=p.parse_args()
    n=verify_manifest();verify_counts(ROOT/'data')
    if args.archive:
        with tempfile.TemporaryDirectory(prefix='kimi-offline-') as tmp:
            out=pathlib.Path(tmp)/'data';reconstruct(args.archive,out)
            expected={str(p.relative_to(ROOT/'data')) for p in (ROOT/'data').rglob('*') if p.is_file()}
            actual={str(p.relative_to(out)) for p in out.rglob('*') if p.is_file()};require(actual==expected,'Generated file-set mismatch')
            for name in expected:require((out/name).read_bytes()==(ROOT/'data'/name).read_bytes(),'Nonidentical regeneration: '+name)
        print(f'PASS: {n} file hashes; 2680 final trials; 2685 attempts; event chain; byte-identical full reconstruction.')
    else:print(f'PASS: {n} file hashes and published counts. Raw evidence NOT rechecked; supply --archive for full verification.')
if __name__=='__main__':main()
