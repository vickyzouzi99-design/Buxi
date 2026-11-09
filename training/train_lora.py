"""Train a LoRA adapter on explicitly supplied JSONL; never export user chats.
Requires an operator-chosen local base model with tokenizer chat template.
"""
import argparse,json,hashlib
from pathlib import Path

def load_rows(path):
 rows=[json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]
 if not rows: raise ValueError('Empty dataset')
 for r in rows:
  m=r['messages']
  if not m or m[-1]['role']!='assistant' or not all(isinstance(x['content'],str) and x['role'] in ['system','user','assistant'] for x in m): raise ValueError('Invalid training messages')
 return rows

def main():
 p=argparse.ArgumentParser();p.add_argument('--base-model',required=True);p.add_argument('--train',default='training/data/train.jsonl');p.add_argument('--eval',default='training/data/eval.jsonl');p.add_argument('--output',default='training/output');p.add_argument('--epochs',type=float,default=1);p.add_argument('--max-steps',type=int,default=-1);a=p.parse_args()
 train=load_rows(a.train);valid=load_rows(a.eval)
 train_ids={r.get('card_id') for r in train if 'card_id' in r};valid_ids={r.get('card_id') for r in valid if 'card_id' in r}
 if train_ids&valid_ids: raise ValueError('Card identity leakage between train/eval')
 # Heavy imports deliberately occur only when training is requested.
 import torch
 from transformers import AutoTokenizer,AutoModelForCausalLM,Trainer,TrainingArguments,DataCollatorForSeq2Seq
 from peft import LoraConfig,get_peft_model,TaskType
 tokenizer=AutoTokenizer.from_pretrained(a.base_model,local_files_only=True,trust_remote_code=False)
 if not tokenizer.chat_template: raise ValueError('Choose a chat tokenizer with a chat template')
 if tokenizer.pad_token_id is None: tokenizer.pad_token=tokenizer.eos_token
 model=AutoModelForCausalLM.from_pretrained(a.base_model,local_files_only=True,trust_remote_code=False)
 model=get_peft_model(model,LoraConfig(task_type=TaskType.CAUSAL_LM,r=8,lora_alpha=16,lora_dropout=.05,target_modules='all-linear'))
 def encode(rows):
  result=[]
  for row in rows:
   msgs=row['messages'];prompt=tokenizer.apply_chat_template(msgs[:-1],tokenize=False,add_generation_prompt=True)
   text=tokenizer.apply_chat_template(msgs,tokenize=False,add_generation_prompt=False)
   prefix=tokenizer(prompt,add_special_tokens=False)['input_ids'];ids=tokenizer(text,add_special_tokens=False)['input_ids']
   if ids[:len(prefix)]!=prefix: raise ValueError('Chat template prefix mismatch: select compatible model')
   if len(ids)>1024: raise ValueError('Example exceeds 1024 tokens: shorten it before training')
   labels=[-100]*len(prefix)+ids[len(prefix):]
   if all(x==-100 for x in labels): raise ValueError('Empty target')
   result.append({'input_ids':ids,'attention_mask':[1]*len(ids),'labels':labels})
  return result
 args=TrainingArguments(output_dir=a.output,num_train_epochs=a.epochs,max_steps=a.max_steps,per_device_train_batch_size=1,per_device_eval_batch_size=1,gradient_accumulation_steps=4,learning_rate=2e-4,eval_strategy='epoch',save_strategy='epoch',report_to='none',seed=42,logging_steps=5)
 trainer=Trainer(model=model,args=args,train_dataset=encode(train),eval_dataset=encode(valid),data_collator=DataCollatorForSeq2Seq(tokenizer,padding=True,label_pad_token_id=-100))
 trainer.train();metrics=trainer.evaluate();model.save_pretrained(a.output);tokenizer.save_pretrained(a.output)
 manifest={'base_model':a.base_model,'train_sha256':hashlib.sha256(Path(a.train).read_bytes()).hexdigest(),'eval_sha256':hashlib.sha256(Path(a.eval).read_bytes()).hexdigest(),'metrics':metrics,'status':'trained_adapter_requires_human_quality_review'}
 Path(a.output,'training_manifest.json').write_text(json.dumps(manifest,indent=2))
if __name__=='__main__': main()
