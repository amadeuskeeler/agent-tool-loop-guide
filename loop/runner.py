import argparse,json
def run(turns,tools,max_turns=8):
 history=[]
 for _ in range(max_turns):
  item=turns[len(history)] if len(history)<len(turns) else {'type':'message','text':'done'}
  history.append(item)
  if item.get('type')!='tool_call': break
  name=item.get('name')
  if name not in tools: raise ValueError('unknown tool '+str(name))
  result=tools[name](item.get('arguments',{}));history.append({'type':'tool_result','name':name,'result':result})
 return history
def main():
 p=argparse.ArgumentParser();p.add_argument('fixture');a=p.parse_args();print(json.dumps(run(json.load(open(a.fixture)),{'echo':lambda x:x}),indent=2))
if __name__=='__main__':main()
