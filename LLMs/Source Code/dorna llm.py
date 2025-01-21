from huggingface_hub import login
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM

# Authenticate with Hugging Face
access_token = "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"
login(token=access_token)

# Define the model path
model_path = "meta-llama/Meta-Llama-3-8B-Instruct"

# Load the tokenizer and model
tokenizer = AutoTokenizer.from_pretrained(model_path)
model = AutoModelForCausalLM.from_pretrained(
    model_path,
    torch_dtype=torch.bfloat16,
    device_map="auto",
)

# Define the chat messages
messages = [
    {"role": "system", "content": "You are a helpful Persian assistant. Please answer questions in the asked language."},
    {"role": "user", "content": "کاغذ A4 بزرگ تر است یا A5؟"},
]

# Tokenize the input messages
input_ids = tokenizer.apply_chat_template(
    messages,
    add_generation_prompt=True,
    return_tensors="pt"
).to(model.device)

# Define termination tokens
terminators = [
    tokenizer.eos_token_id,
    tokenizer.convert_tokens_to_ids("<|eot_id|>")
]

# Generate the response
outputs = model.generate(
    input_ids,
    max_new_tokens=256,
    eos_token_id=terminators,
    do_sample=True,
    temperature=0.6,
    top_p=0.9,
)

# Decode and print the response
response = outputs[0][input_ids.shape[-1]:]
print(tokenizer.decode(response, skip_special_tokens=True))