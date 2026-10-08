#!/usr/bin/env python3
"""Offline analysis of an existing archive. No credentials, inference, or network."""
import argparse
import base64
import collections
import csv
import hashlib
import json
import pathlib
import re
import statistics
import zipfile

ROOT = pathlib.Path(__file__).resolve().parent
PREFIX = 'void-matrix-evidence-v1.0.0/study/'
ARCHIVE_SHA = '04d79ddb0f961729369da8ae46c58f7293e42dfd278d2e9b703edc0cec6455d2'
INVISIBLE = {0x200B,0x200C,0x200D,0x200E,0x200F,0xFEFF,0x2060,0x2061,0x2062,0x2063,0x2064,0x2066,0x2067,0x2068,0x2069,0x202A,0x202B,0x202C,0x202D,0x202E}
ELLIPSES = {'.','..','...','....','…','….'}
CANONICAL = {'core_nothing','core_silence','core_null','matched_something','matched_speech','matched_value'}
NULL = {'core_nothing','core_silence','core_null'}
MATCHED = {'matched_something','matched_speech','matched_value'}
PATTERNS = {
 'empty_output_language': r'\b(?:empty\s+(?:response|answer|message|output|string)|(?:output|return|emit|produce|say|write|render)\s+(?:absolutely\s+)?nothing|no\s+(?:visible\s+)?(?:output|response|answer|text)|zero[ -](?:byte|character)s?)\b',
 'visible_alternative_language': r'\b(?:ellipsis|ellipses|whitespace|blank\s+(?:line|space)|invisible\s+character|unicode|punctuation|symbol|poem|poetic|philosophical)\b|\.\.\.|…',
 'decision_language': r"\b(?:decision|I\s+(?:will|should|must|choose|decide)|I'll|let me|final\s+(?:answer|response)|best\s+(?:answer|response|approach))\b",
}
RX = {k: re.compile(v,re.I) for k,v in PATTERNS.items()}

def sha(b): return hashlib.sha256(b).hexdigest()
def canonical(x): return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
def require(condition, message):
    if not condition: raise ValueError(message)
def write_json(path, value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2)+'\n',encoding='utf-8')
def write_csv(path, rows):
    with path.open('w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)

def classify(status, payload):
    if status != 200 or not isinstance(payload,dict) or not payload.get('choices'): return 'E'
    choice=payload['choices'][0]; message=choice.get('message') or {}
    if payload.get('error'): return 'E'
    if message.get('refusal') or choice.get('finish_reason')=='refusal': return 'RF'
    if message.get('tool_calls') or message.get('function_call'): return 'TC'
    text=message.get('content'); stop=choice.get('finish_reason')
    require(text is None or isinstance(text,str),'Unexpected answer representation')
    if text:
        return 'NV' if all(ord(c) in INVISIBLE or c.isspace() for c in text) or text.strip() in ELLIPSES else 'R'
    if stop=='length': return 'V1'
    if stop=='stop': return 'V0' if isinstance(text,str) else 'V2'
    return 'VU'

def summary(rows):
    result={}
    for cls in sorted({r['classification'] for r in rows}):
        group=[r for r in rows if r['classification']==cls]
        sizes=[r['reasoning_utf8_bytes'] for r in group if r['reasoning_nonempty']]
        item={'n':len(group),'nonempty_reasoning':sum(r['reasoning_nonempty'] for r in group),
              'reasoning_bytes_min_median_max':[min(sizes),statistics.median(sizes),max(sizes)] if sizes else None}
        for name in RX:
            for key in (name,'tail_'+name): item[key]=sum(r[key] for r in group)
        result[cls]=item
    return result

def reconstruct(archive, output, extract=None):
    require(sha(archive.read_bytes())==ARCHIVE_SHA,'Original archive checksum mismatch')
    selection=json.loads((ROOT/'selection.json').read_text())
    wanted={x['slot_id']:x for x in selection['receipts']}
    output.mkdir(parents=True,exist_ok=True)
    if extract:
        require(not extract.exists(),'Extraction destination must be new')
        extract.mkdir(parents=True)
    final=[]; attempts=[]; selected={}; requests={}; prompt_catalog={}; failures=[]
    with zipfile.ZipFile(archive) as z:
        protocol=json.loads(z.read(PREFIX+'protocol.json'))
        prompts=json.loads(z.read(PREFIX+'prompts.json'))
        schedule={}
        for line in z.read(PREFIX+'schedule.jsonl').splitlines():
            slot=json.loads(line)
            if slot['model_id']=='kimi-k3':
                require(slot['slot_id'] not in schedule,'Duplicate scheduled slot');schedule[slot['slot_id']]=slot
        previous='0'*64; event_count=0; start_ids=set(); completion_ids=set(); all_ids=set()
        for line in z.read(PREFIX+'run/events.jsonl').splitlines():
            e=json.loads(line); claimed=e.pop('event_sha256')
            require(e['previous_event_sha256']==previous and sha(canonical(e))==claimed,'Event chain mismatch')
            previous=claimed;event_count+=1
            if e.get('slot',{}).get('model_id')!='kimi-k3': continue
            if e['event_type']=='trial_started':
                require(e['attempt_id'] not in start_ids,'Duplicate attempt start');start_ids.add(e['attempt_id']);continue
            require(e['attempt_id'] not in all_ids,'Duplicate completed attempt');all_ids.add(e['attempt_id'])
            raw=z.read(PREFIX+e['raw_path']);d=json.loads(raw);tr=d['transport'];body=base64.b64decode(tr['raw_body_base64'],validate=True)
            require(sha(raw)==e['raw_sha256'],'Raw envelope hash mismatch')
            require(sha(body)==e['raw_body_sha256']==tr['raw_body_sha256'],'Response hash mismatch')
            require(d['attempt_id']==e['attempt_id'] and d['attempt_number']==e['attempt_number'],'Attempt identity mismatch')
            slot=d['slot'];require(slot==schedule[slot['slot_id']],'Scheduled slot drift')
            req=d['request'];request=req['body'];rh=sha(canonical(request))
            require(rh==req['body_sha256'],'Request hash mismatch')
            system=prompts['systems'][slot['system_id']]['text'];user=prompts['cases'][slot['prompt_id']]['text']
            expected={'model':'kimi-k3','messages':([{'role':'system','content':system}] if system else [])+[{'role':'user','content':user}],'max_completion_tokens':slot['budget']}
            require(request==expected and req['endpoint_url']=='https://api.moonshot.ai/v1/chat/completions','Request protocol drift')
            require(all(v=='REDACTED' for k,v in req.get('headers',{}).items() if k.lower() in {'authorization','x-api-key'}),'Unredacted credential')
            requests[rh]=request;prompt_catalog[slot['prompt_id']]=user
            try: response=json.loads(body)
            except ValueError: response=None
            require(tr['json']==response,'Parsed and raw response differ')
            cls=classify(tr['http_status'],response)
            require(cls==e['classification']['classification'],'Classification disagreement')
            attempts.append({'slot_id':slot['slot_id'],'attempt_id':e['attempt_id'],'attempt_number':e['attempt_number'],'event_type':e['event_type'],'http_status':tr['http_status'],'classification':cls,'retry_scheduled':e['retry_scheduled'],'raw_member':PREFIX+e['raw_path'],'raw_sha256':sha(raw),'response_sha256':sha(body),'request_sha256':rh})
            if e['event_type']!='trial_completed': continue
            require(slot['slot_id'] not in completion_ids,'Duplicate final slot');completion_ids.add(slot['slot_id'])
            obj=response or {};choice=(obj.get('choices') or [{}])[0];message=choice.get('message') or {}
            text=message.get('content');reasoning=message.get('reasoning_content');reason=reasoning if isinstance(reasoning,str) else ''
            usage=obj.get('usage') or {}
            if tr['http_status']==200: require(obj.get('model')=='kimi-k3','Returned model mismatch')
            row={k:slot[k] for k in ['slot_id','study_id','system_id','prompt_id','block','replicate','budget','parameter_track']}
            row.update(prompt_text=user,role='null' if slot['prompt_id'] in NULL else 'matched_control' if slot['prompt_id'] in MATCHED else 'other',http_status=tr['http_status'],classification=cls,finish_reason=choice.get('finish_reason'),returned_model=obj.get('model'),attempt_number=d['attempt_number'],started_utc=tr['started_utc'],ended_utc=tr['ended_utc'],answer_container_present=isinstance(text,str),answer_utf8_bytes=len(text.encode()) if isinstance(text,str) else None,answer_sha256=sha(text.encode()) if isinstance(text,str) else None,reasoning_field_present='reasoning_content' in message,reasoning_type=type(reasoning).__name__,reasoning_nonempty=bool(reason),reasoning_utf8_bytes=len(reason.encode()),reasoning_characters=len(reason),reasoning_sha256=sha(reason.encode()) if isinstance(reasoning,str) else None,reasoning_tokens=usage.get('completion_tokens_details',{}).get('reasoning_tokens'),completion_tokens=usage.get('completion_tokens'),prompt_tokens=usage.get('prompt_tokens'),cached_prompt_tokens=usage.get('prompt_tokens_details',{}).get('cached_tokens'),refusal=bool(message.get('refusal')),tool_use=bool(message.get('tool_calls') or message.get('function_call')),request_sha256=rh,raw_member=PREFIX+e['raw_path'],raw_sha256=sha(raw),response_sha256=sha(body))
            for name,rx in RX.items():row[name]=bool(rx.search(reason));row['tail_'+name]=bool(rx.search(reason[-500:]))
            final.append(row)
            if slot['slot_id'] in wanted:
                meta=dict(row,number=wanted[slot['slot_id']]['number'],selection_rationale=wanted[slot['slot_id']]['rationale'],request=request)
                if isinstance(text,str) and len(text.encode())<=3:
                    meta.update(answer_json=json.dumps(text,ensure_ascii=True),answer_hex=text.encode().hex(),answer_codepoints=[f'U+{ord(c):04X}' for c in text])
                selected[meta['number']]=meta
                if extract:
                    dest=extract/f"{meta['number']:02d}";dest.mkdir()
                    (dest/'raw.json').write_bytes(raw);(dest/'response.json').write_bytes(body)
                    (dest/'request.canonical.json').write_bytes(canonical(request))
                    (dest/'reasoning.txt').write_bytes(reason.encode());(dest/'answer.txt').write_bytes(text.encode())
                    write_json(dest/'metadata.json',meta)
        require(start_ids==all_ids,'Missing started or completed attempt')
        require(completion_ids==set(schedule),'Missing final scheduled trial')
        require(len(final)==2680 and len(attempts)==2685,'Population count mismatch')
        require(len(selected)==10,'Incomplete selected receipts')
        final.sort(key=lambda r:r['slot_id']);attempts.sort(key=lambda r:(r['slot_id'],r['attempt_number']))
        for n,m in selected.items():
            same=[r for r in final if r['request_sha256']==m['request_sha256'] and r['study_id']==m['study_id']]
            m['within_study_identical_request_counts']=dict(sorted(collections.Counter(r['classification'] for r in same).items()))
            require(m['attempt_number']==1,'Selected receipt not first attempt')
            write_json(output/'selected'/f'{n:02d}.json',m)
        require(len({selected[n]['request_sha256'] for n in [1,2,3,7]})==1,'Four-way request mismatch')
        require(selected[5]['request_sha256']==selected[6]['request_sha256'],'Short/long request mismatch')
        for a,b in [(1,4),(8,9)]:
            x=json.loads(json.dumps(selected[a]['request']));y=selected[b]['request'];x['messages'][-1]['content']=y['messages'][-1]['content']
            require(x==y and selected[a]['block']==selected[b]['block'] and selected[a]['replicate']==selected[b]['replicate'],'Control pair mismatch')
        core=[r for r in final if r['study_id']=='core_4000' and r['prompt_id'] in CANONICAL]
        nullcore=[r for r in core if r['prompt_id'] in NULL];controls=[r for r in core if r['prompt_id'] in MATCHED]
        canonical_all=[r for r in final if r['system_id']=='primary' and r['budget']==4000 and r['prompt_id'] in CANONICAL]
        report={'all_trials':summary(final),'canonical_600':summary(core),'canonical_null_300':summary(nullcore),'canonical_controls_300':summary(controls),'broader_primary_4000_null_330':summary([r for r in canonical_all if r['prompt_id'] in NULL]),'broader_primary_4000_controls_330':summary([r for r in canonical_all if r['prompt_id'] in MATCHED]),'core_null_cell_100':summary([r for r in nullcore if r['prompt_id']=='core_null'])}
        write_json(output/'summary.json',report)
        write_json(output/'within-prompt.json',{p:summary([r for r in core if r['prompt_id']==p]) for p in sorted(CANONICAL)})
        write_json(output/'audit.json',{'archive_sha256':ARCHIVE_SHA,'scheduled_final_trials':len(final),'retained_attempts':len(attempts),'classifications':dict(sorted(collections.Counter(r['classification'] for r in final).items())),'final_attempt_numbers':dict(sorted(collections.Counter(r['attempt_number'] for r in final).items())),'event_chain_entries':event_count,'event_chain_head':previous,'all_hashes_requests_and_classifications_verified':True})
        write_json(output/'four-outcomes.json',[selected[n] for n in [1,2,3,7]])
        write_json(output/'request-catalog.json',requests)
        write_json(output/'prompt-catalog.json',{'systems':{k:v['text'] for k,v in prompts['systems'].items()},'cases':prompt_catalog})
        write_json(output/'original-protocol.json',protocol)
        write_json(output/'lexical-rules.json',{'patterns':PATTERNS,'tail_characters':500,'interpretation':'Post-hoc lexical counts, not semantic commitment labels or causal measures. Quotes, negations and alternatives may match. Trace length and prompt composition are not controlled by pooled counts.'})
        write_csv(output/'trials.csv',final)
        write_csv(output/'v0-references.csv',[r for r in final if r['classification']=='V0'])
        write_csv(output/'canonical-600.csv',core)
        write_csv(output/'matched-controls.csv',[r for r in final if r['prompt_id'] in MATCHED])
        write_csv(output/'attempts.csv',attempts)
    return report

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--archive',type=pathlib.Path,required=True)
    ap.add_argument('--out',type=pathlib.Path,required=True)
    ap.add_argument('--extract-selected',type=pathlib.Path,help='Optional NEW folder for ten full original receipts')
    args=ap.parse_args();require(not args.out.exists(),'Output directory must be new')
    report=reconstruct(args.archive,args.out,args.extract_selected)
    print(json.dumps(report['all_trials'],indent=2))
if __name__=='__main__': main()
