"""FlowLens — explainable freelancer cash-flow predictor MVP."""
import os, csv, io, json
from datetime import date, timedelta
from flask import Flask, render_template, request, jsonify, session
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'dev-only-change-me')

# The demo uses the same deterministic, auditable ledger approach described in the Team 7 pitch.
SAMPLE = {
    'currency': 'USD', 'opening_balance': 3200, 'safety_buffer': 1500,
    'invoices': [
        {'client':'Northstar Studio','label':'Website milestone','amount':2000,'week':1,'status':'expected','due_date':''},
        {'client':'Atlas Labs','label':'Consulting invoice','amount':600,'week':2,'status':'expected','due_date':''},
        {'client':'Mira Co.','label':'Design review','amount':350,'week':3,'status':'expected','due_date':''},
        {'client':'Northstar Studio','label':'Retainer','amount':500,'week':4,'status':'expected','due_date':''},
        {'client':'Atlas Labs','label':'Project completion','amount':2300,'week':5,'status':'expected','due_date':''},
        {'client':'Mira Co.','label':'Final milestone','amount':1650,'week':6,'status':'expected','due_date':''},
    ],
    'expenses': [
        {'label':'Rent & workspace','amount':1100,'week':1,'kind':'essential'},
        {'label':'Software and utilities','amount':1250,'week':2,'kind':'essential'},
        {'label':'Tax reserve and bills','amount':1450,'week':3,'kind':'essential'},
        {'label':'Quarterly tax + equipment','amount':1900,'week':4,'kind':'essential'},
        {'label':'Living costs','amount':1100,'week':5,'kind':'essential'},
        {'label':'Rent & operating costs','amount':1450,'week':6,'kind':'essential'},
    ]
}

def forecast(data):
    balance = float(data.get('opening_balance', 0) or 0)
    buffer = float(data.get('safety_buffer', 0) or 0)
    invoices = data.get('invoices', [])
    expenses = data.get('expenses', [])
    weeks, first_risk = [], None
    for w in range(1, 7):
        incoming = sum(max(0, float(x.get('amount',0) or 0)) for x in invoices if int(x.get('week',1)) == w)
        outgoing = sum(max(0, float(x.get('amount',0) or 0)) for x in expenses if int(x.get('week',1)) == w)
        opening = balance
        balance = opening + incoming - outgoing
        risk = balance < buffer
        if risk and first_risk is None: first_risk = w
        weeks.append({'week':w,'opening':round(opening,2),'inflow':round(incoming,2),'outflow':round(outgoing,2),'closing':round(balance,2),'risk':risk,'gap':round(max(0,buffer-balance),2)})
    lowest = min(weeks, key=lambda x:x['closing']) if weeks else {'closing':balance,'week':0}
    return {'weeks':weeks,'lowest_balance':lowest['closing'],'lowest_week':lowest['week'],'first_risk_week':first_risk,'buffer':buffer,'gap':round(max(0,buffer-lowest['closing']),2),'opening_balance':float(data.get('opening_balance',0) or 0),'currency':data.get('currency','USD')}

def recommendations(data, result):
    out=[]; low=result['lowest_balance']; buffer=result['buffer']; risk=result['first_risk_week']
    if risk:
        # Only recommend an early invoice if a later-week invoice can plausibly be moved, without claiming it is guaranteed.
        later = sorted([x for x in data.get('invoices',[]) if int(x.get('week',1)) > risk and float(x.get('amount',0) or 0)>0], key=lambda x:int(x.get('week',1)))
        if later:
            inv=later[0]; amt=float(inv.get('amount',0)); old=int(inv.get('week',1)); new=max(1,risk-1)
            impact=round(amt,2)
            out.append({'type':'invoice','tag':'MOVE CASH FORWARD','title':'Ask to invoice a completed milestone earlier','message':f"Week {risk} is projected to fall to {money(low, result['currency'])}, {money(result['gap'], result['currency'])} below your safety buffer. If {inv.get('client','your client')} approves moving the {money(amt,result['currency'])} {inv.get('label','invoice')} from week {old} to week {new}, your low point could improve by up to {money(impact,result['currency'])}.",'impact':impact,'cta':'Review invoice timing','week':risk})
        optional=[x for x in data.get('expenses',[]) if x.get('kind')=='optional' and int(x.get('week',1))<=risk]
        if optional:
            exp=optional[0]; amt=float(exp.get('amount',0)); out.append({'type':'save','tag':'PROTECT YOUR BUFFER','title':'Review one optional expense','message':f"A shortfall is possible by week {risk}. If the {money(amt,result['currency'])} item “{exp.get('label','optional expense')}” is genuinely nonessential, postponing it could preserve that cash. Keep tax, rent and essential bills protected.",'impact':amt,'cta':'Review expense','week':risk})
        else:
            out.append({'type':'save','tag':'PROTECT YOUR BUFFER','title':'Create a temporary cash guardrail','message':f"Your forecast is {money(result['gap'],result['currency'])} below the selected buffer. Review upcoming discretionary spend and identify a realistic amount to pause before week {risk}; do not defer essential bills or tax obligations.",'impact':0,'cta':'Review spending plan','week':risk})
        delayed=sorted([x for x in data.get('invoices',[]) if int(x.get('week',1))>risk and float(x.get('amount',0) or 0)>0], key=lambda x:int(x.get('week',1)))
        if delayed:
            inv=delayed[-1]; amt=round(float(inv.get('amount',0))*.3,2)
            out.append({'type':'followup','tag':'REDUCE PAYMENT UNCERTAINTY','title':'Send a friendly payment-date check-in','message':f"A later receipt from {inv.get('client','a client')} is part of your runway. Ask them to confirm the expected payment date; if they agree to a partial settlement of around {money(amt,result['currency'])} by week {risk}, recalculate the forecast. The app does not assume they will pay early.",'impact':amt,'cta':'Draft reminder','week':risk})
    else:
        out=[{'type':'safe','tag':'RUNWAY HEALTHY','title':'Keep the buffer intact','message':f"Your lowest projected balance is {money(low,result['currency'])}, above your {money(buffer,result['currency'])} safety buffer. Keep invoice dates updated and re-check the forecast whenever a payment or expense changes.",'impact':0,'cta':'Review forecast','week':6}]
    return out[:3]

def money(value, currency='USD'):
    symbol={'USD':'$','INR':'₹','EUR':'€','GBP':'£'}.get(currency,'')
    return f"{symbol}{float(value):,.0f}" if symbol else f"{float(value):,.0f} {currency}"

@app.route('/')
def index():
    return render_template('index.html', supabase_url=os.getenv('SUPABASE_URL',''), supabase_key=os.getenv('SUPABASE_ANON_KEY',''))

@app.get('/api/demo')
def demo():
    f=forecast(SAMPLE)
    return jsonify({'data':SAMPLE,'forecast':f,'recommendations':recommendations(SAMPLE,f),'mode':'illustrative demo'})

@app.post('/api/forecast')
def api_forecast():
    data=request.get_json(silent=True) or {}
    try:
        # Defensive bounds keep malformed form values from breaking the ledger.
        data['opening_balance']=max(0,float(data.get('opening_balance',0)))
        data['safety_buffer']=max(0,float(data.get('safety_buffer',0)))
        data['invoices']=[x for x in data.get('invoices',[]) if 1<=int(x.get('week',1))<=6]
        data['expenses']=[x for x in data.get('expenses',[]) if 1<=int(x.get('week',1))<=6]
        data['currency']=data.get('currency','USD')
        f=forecast(data)
        return jsonify({'forecast':f,'recommendations':recommendations(data,f),'data':data,'mode':'calculated from your entered events'})
    except (TypeError, ValueError) as e:
        return jsonify({'error':'Check that all amounts and week numbers are valid.'}),400

@app.post('/api/import-csv')
def import_csv():
    file=request.files.get('file')
    if not file: return jsonify({'error':'Choose a CSV file first.'}),400
    try:
        text=file.stream.read().decode('utf-8-sig')
        reader=csv.DictReader(io.StringIO(text))
        rows=[]
        for row in reader:
            kind=(row.get('type') or row.get('kind') or '').strip().lower()
            amount=float(row.get('amount') or 0); week=int(row.get('week') or 1)
            if kind not in ('invoice','income','expense','outflow') or not 1<=week<=6: continue
            rows.append({'type':'invoice' if kind in ('invoice','income') else 'expense','label':row.get('label') or row.get('description') or 'Imported item','client':row.get('client') or 'Client','amount':abs(amount),'week':week,'kind':row.get('category','optional')})
        return jsonify({'rows':rows,'count':len(rows),'message':'CSV parsed. Review the rows before adding them to your forecast.'})
    except Exception:
        return jsonify({'error':'Could not parse CSV. Use columns: type,label,client,amount,week,category.'}),400

@app.post('/api/ai-advice')
def ai_advice():
    """Optional AI wording only. Core calculations never depend on an LLM."""
    body=request.get_json(silent=True) or {}
    provider=body.get('provider','gemini')
    prompt=body.get('prompt','Explain this cash-flow forecast in plain language: '+json.dumps(body.get('summary',{})))
    try:
        import requests
        if provider=='openrouter':
            key=os.getenv('OPENROUTER_API_KEY')
            if not key: return jsonify({'error':'OPENROUTER_API_KEY is not configured. Add it to .env.'}),400
            model=os.getenv('OPENROUTER_MODEL','openai/gpt-4o-mini')
            r=requests.post('https://openrouter.ai/api/v1/chat/completions',headers={'Authorization':f'Bearer {key}','Content-Type':'application/json','HTTP-Referer':request.host_url,'X-Title':'FlowLens'},json={'model':model,'messages':[{'role':'system','content':'You are FlowLens, a cautious cash-flow explainer. Never invent amounts. Treat forecast as estimates, do not give investment/tax/legal advice, and suggest only user-approved actions.'},{'role':'user','content':prompt}], 'temperature':0.3},timeout=25)
            r.raise_for_status(); answer=r.json()['choices'][0]['message']['content']
        else:
            key=os.getenv('GEMINI_API_KEY')
            if not key: return jsonify({'error':'GEMINI_API_KEY is not configured. Add it to .env.'}),400
            model=os.getenv('GEMINI_MODEL','gemini-2.5-flash')
            r=requests.post(f'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}',headers={'Content-Type':'application/json'},json={'contents':[{'parts':[{'text':'You are FlowLens, a cautious cash-flow explainer. Never invent amounts. Treat forecast as estimates, do not give investment/tax/legal advice, and suggest only user-approved actions.\n\n'+prompt}]}]},timeout=25)
            r.raise_for_status(); answer=r.json()['candidates'][0]['content']['parts'][0]['text']
        return jsonify({'answer':answer,'provider':provider})
    except Exception as e:
        return jsonify({'error':'AI provider request failed. Check API key, model name and internet connection. The forecast engine still works without AI.'}),502

@app.get('/health')
def health(): return jsonify({'status':'ok','app':'FlowLens'})

if __name__=='__main__':
    app.run(debug=os.getenv('FLASK_DEBUG','false').lower()=='true', host='0.0.0.0', port=int(os.getenv('PORT','5000')))
