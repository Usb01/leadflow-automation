"""Validate and deduplicate inbound leads with a transactional SQLite ledger."""
import argparse,csv,hashlib,json,re,sqlite3
from pathlib import Path
from report import report
EMAIL=re.compile(r'^[^\s@]+@[^\s@]+\.[^\s@]+$')

def normalize(row):
    name=str(row.get('name','')).strip();email=str(row.get('email','')).strip().lower()
    if not name or len(name)>100: raise ValueError('Invalid name')
    if len(email)>254 or not EMAIL.fullmatch(email): raise ValueError('Invalid email')
    try: budget=int(str(row.get('budget','0')).strip())
    except ValueError: raise ValueError('Budget must be a whole number')
    if not 0<=budget<=10000000: raise ValueError('Budget out of range')
    interest=str(row.get('interest','')).strip()[:300]
    return {'name':name,'email':email,'budget':budget,'interest':interest,'route':'priority_review' if budget>=2000 else 'standard_review'}

def process(rows,db_path):
    con=sqlite3.connect(db_path);con.execute('CREATE TABLE IF NOT EXISTS leads (email TEXT PRIMARY KEY, payload TEXT NOT NULL)')
    results=[]
    with con:
        for number,row in enumerate(rows,1):
            try:
                lead=normalize(row)
                cur=con.execute('INSERT OR IGNORE INTO leads VALUES (?,?)',(lead['email'],json.dumps(lead)))
                results.append({'row':number,'status':'accepted' if cur.rowcount else 'duplicate','contact':lead['email'],'route':lead['route'],'detail':'Ready for review' if cur.rowcount else 'Already in ledger'})
            except ValueError as e: results.append({'row':number,'status':'rejected','contact':'','route':'manual_review','detail':str(e)})
    con.close();return results

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--demo',action='store_true');parser.add_argument('--input',default='sample.csv');parser.add_argument('--output',default='runs');args=parser.parse_args()
    out=Path(args.output);out.mkdir(parents=True,exist_ok=True)
    source=Path(__file__).with_name('sample.csv') if args.demo else Path(args.input)
    with source.open(newline='',encoding='utf-8-sig') as f: rows=list(csv.DictReader(f))
    result=process(rows,out/'leads.sqlite');(out/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    metrics={s:sum(x['status']==s for x in result) for s in ['accepted','duplicate','rejected']}
    report(out/'report.html','LeadFlow','Validate incoming leads, prevent repeated imports, and route records for review.',result,metrics)
    print(json.dumps(metrics))
if __name__=='__main__':main()
