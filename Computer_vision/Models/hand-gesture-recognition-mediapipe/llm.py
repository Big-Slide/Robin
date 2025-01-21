# pip install accelerate
# Load model directly
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM

tokenizer = AutoTokenizer.from_pretrained("google/flan-t5-large")
model = AutoModelForSeq2SeqLM.from_pretrained("google/flan-t5-large")

input_text = "talk too me: what is your favorite country"
input_ids = tokenizer(input_text, return_tensors="pt").input_ids.to("cpu")

outputs = model.generate(input_ids)
print(tokenizer.decode(outputs[0]))
