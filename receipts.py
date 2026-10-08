"""Extract and verify exact provider-returned fields. No inference or network calls."""
import argparse, base64, csv, json, pathlib, zipfile
from analyze import ROOT, ARCHIVE_SHA, canonical, sha, require, write_json

def run(archive=None, build=False, indexes=False):
    rows=list(csv.DictReader((ROOT/'data/attempts.csv').open()))
    finals={r['slot_id']:r for r in csv.DictReader((ROOT/'data/trials.csv').open())}
    selected={x['slot_id']:x['number'] for x in json.loads((ROOT/'selection.json').read_text())['receipts']}
    z=None
    if archive:
        require(sha(archive.read_bytes())==ARCHIVE_SHA,'Source archive hash mismatch')
        z=zipfile.ZipFile(archive)
    require(not build or z is not None,'Build requires original archive')
    index=['# All Kimi receipts','', 'All 2,680 final trials and five earlier attempts. Links expose complete provider-returned reasoning, not guaranteed transcripts of internal computation. Missing fields remain missing.','', '| Trial | Attempt | Final | Class | Reasoning | Response |','|---|---:|---|---|---|---|']
    selected_lines=['# Ten post-hoc exhibits','', 'These illustrate the complete population; they are not a representative sample.','']
    nreason=0
    for r in rows:
        rel=pathlib.Path('receipts')/r['slot_id']/('attempt-'+r['attempt_number']);dest=ROOT/rel
        expected={}
        if z:
            raw=z.read(r['raw_member']);require(sha(raw)==r['raw_sha256'],'Envelope mismatch')
            envelope=json.loads(raw)
            body=base64.b64decode(envelope['transport']['raw_body_base64'],validate=True)
            request=canonical(envelope['request']['body'])
        else:
            body=(dest/'response.body').read_bytes();request=(dest/'request.json').read_bytes()
        require(sha(body)==r['response_sha256'],'Response mismatch')
        require(sha(request)==r['request_sha256'],'Request mismatch')
        expected['response.body']=body;expected['request.json']=request
        try: obj=json.loads(body)
        except ValueError: obj=None
        if isinstance(obj,dict): expected['response.json']=body
        msg=((obj or {}).get('choices') or [{}])[0].get('message') or {}
        reason=msg.get('reasoning_content');answer=msg.get('content')
        if isinstance(reason,str): expected['reasoning.txt']=reason.encode('utf-8');nreason+=1
        if isinstance(answer,str): expected['answer.txt']=answer.encode('utf-8')
        meta=dict(r,reasoning_present=isinstance(reason,str),answer_present=isinstance(answer,str),reasoning_sha256=sha(reason.encode()) if isinstance(reason,str) else None,answer_sha256=sha(answer.encode()) if isinstance(answer,str) else None,reasoning_utf8_bytes=len(reason.encode()) if isinstance(reason,str) else None,answer_utf8_bytes=len(answer.encode()) if isinstance(answer,str) else None)
        if r['event_type']=='trial_completed':
            f=finals[r['slot_id']]
            for field in ['reasoning_sha256','answer_sha256']:
                require((meta[field] or '')==f[field],'Final field hash mismatch')
        expected['metadata.json']=(json.dumps(meta,ensure_ascii=False,sort_keys=True,indent=2)+'\n').encode()
        if build:
            dest.mkdir(parents=True,exist_ok=False)
            for name,content in expected.items(): (dest/name).write_bytes(content)
        else:
            require({p.name for p in dest.iterdir()}==set(expected),'Receipt file-set mismatch')
            for name,content in expected.items():require((dest/name).read_bytes()==content,'Receipt mismatch: '+str(rel/name))
        link=lambda name: '../'+str(rel/name)
        reasoning=f'[read]({link("reasoning.txt")})' if isinstance(reason,str) else 'absent'
        index.append(f'| {r["slot_id"]} | {r["attempt_number"]} | {r["event_type"]=="trial_completed"} | {r["classification"]} | {reasoning} | [raw body]({link("response.body")}) |')
        if r['slot_id'] in selected and r['event_type']=='trial_completed':
            selected_lines.append(f'{selected[r["slot_id"]]:02d}. **{finals[r["slot_id"]]["prompt_text"]} / {r["classification"]}**: [reasoning]({link("reasoning.txt")}) · [response]({link("response.json")}) · [request]({link("request.json")}) · [answer]({link("answer.txt")})')
    if build or indexes:
        (ROOT/'browse').mkdir(exist_ok=True)
        landing=['# All 2,685 retained attempts','', 'Each page contains at most 100 attempts so GitHub can render the complete index.','']
        header=index[:6];entries=index[6:]
        for offset in range(0,len(entries),100):
            name=f'page-{offset//100+1:02d}.md'
            (ROOT/'browse'/name).write_text('\n'.join(header+entries[offset:offset+100])+'\n')
            landing.append(f'- [Attempts {offset+1}–{min(offset+100,len(entries))}]({name})')
        (ROOT/'browse/all.md').write_text('\n'.join(landing)+'\n')
        (ROOT/'browse/selected.md').write_text('\n'.join(selected_lines[:4]+sorted(selected_lines[4:]))+'\n')
    require(len(rows)==2685 and nreason==2679,'Receipt population mismatch')
    if z:z.close()
    print('PASS: 2685 attempts; 2679 exact reasoning fields; all response/request/answer hashes.' + (' Compared against original archive.' if archive else ''))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--archive',type=pathlib.Path);p.add_argument('--build',action='store_true');p.add_argument('--indexes',action='store_true');a=p.parse_args();run(a.archive,a.build,a.indexes)
