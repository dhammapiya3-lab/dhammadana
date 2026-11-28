import json,re
P=json.load(open('en_paras.json'))
W={'mefta':'metta','metia':'metta','meffa':'metta','merta':'metta','metfa':'metta','meftta':'metta','metita':'metta','merra':'metta','metra':'metta','mertta':'metta','meita':'metta','meta':'metta',
'fiana':'ñana','fana':'ñana','flana':'ñana','Hana':'ñana','nana':'ñana','jfiana':'ñana',
'panna':'pañña','pafinia':'pañña','pajifia':'pañña','Pafifia':'Pañña','pafifia':'pañña','paniia':'pañña','pafifatti':'paññatti',
'hana':'jhana','shanas':'jhanas','jJhana':'jhana','swkha':'sukha','suwkha':'sukha','obha':'lobha','semsara':'samsara',
'Vencrable':'Venerable','retumed':'returned','Strect':'Street','cnemies':'enemies','fecling':'feeling','bom':'born','Ifa':'If a','Jn':'In','PARTI':'PART I','Aywi':'kywi','patina':'pañña','ail':'all','Meta':'Metta','1s':'is'}
n=0
for p in P:
    t=p['t']
    t=re.sub(r'y;hana|;hana','jhana',t)
    t=re.sub(r'/(lobha|obha)',r'lobha',t); t=re.sub(r"‘/t ","‘It ",t)
    t=re.sub(r'(?<=[ ,.‘])\|(?= )','I',t)
    t=re.sub(r"^Sadhu\S* Sadhu\S* Sadhu!$","Sadhu! Sadhu! Sadhu!",t)
    t=re.sub(r"kywi kywi’\?","kywi kywi’",t); t=re.sub(r"kywi kywi\?","kywi kywi’",t)
    t=re.sub(r"\bmetta Call\b","metta call",t)
    t=t.replace('second jana','second jhana').replace('fourth jana','fourth jhana').replace('adinava jana','adinava ñana').replace('{f you','If you').replace('now Ill ','now I’ll ').replace(' _ ',' ')
    t=t.replace('noting left, night,','noting left, right,').replace('harm us, Incredulous','harm us.’ Incredulous').replace('‘May J be','‘May I be').replace('when J heard','when I heard').replace('heart. J also','heart. I also')
    for a,b in W.items(): t=re.sub(r'(?<![A-Za-zñ])'+a+r'(?![A-Za-zñ])',b,t)
    t=t.replace('lobha','lobha').replace('  ',' ')
    if t!=p['t']: n+=1
    p['t']=t
P=[p for p in P if p['t'] not in ('Ik','4)')]
json.dump(P,open('en_paras2.json','w'),ensure_ascii=False,indent=1); print(n,'paras changed')
