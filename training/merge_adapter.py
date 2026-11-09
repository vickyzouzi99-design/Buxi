"""Merge a locally trained adapter for serving through an OpenAI-compatible server."""
import argparse
p=argparse.ArgumentParser();p.add_argument('--base-model',required=True);p.add_argument('--adapter',required=True);p.add_argument('--output',required=True);a=p.parse_args()
from transformers import AutoModelForCausalLM,AutoTokenizer
from peft import PeftModel
base=AutoModelForCausalLM.from_pretrained(a.base_model,local_files_only=True,trust_remote_code=False)
model=PeftModel.from_pretrained(base,a.adapter,is_trainable=False).merge_and_unload()
model.save_pretrained(a.output,safe_serialization=True)
AutoTokenizer.from_pretrained(a.adapter,local_files_only=True).save_pretrained(a.output)
