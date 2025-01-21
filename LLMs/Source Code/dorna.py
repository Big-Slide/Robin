import torch
import transformers
from transformers import AutoTokenizer, AutoModelForCausalLM

# Set the model path to the directory containing the model files
model_path = "C:\\Py code\\Models\\Dorna"  # Path to the directory, not a single file


# Load the model from the .gguf file using the appropriate library
# This is a placeholder; replace with the actual loading method for your model
model = torch.load("C:\\Py code\\Models\\Dorna\\Dorna-Llama3-8B-Instruct.Q8_0.gguf")


# Load the tokenizer and model
tokenizer = AutoTokenizer.from_pretrained(model_path)
model = AutoModelForCausalLM.from_pretrained(
    model_path,
    torch_dtype=torch.bfloat16,
    device_map="auto",
)

# Prepare the messages for the model
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

# Define terminators for the generation
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

# Decode the response
response = outputs[0][input_ids.shape[-1]:]
print(tokenizer.decode(response, skip_special_tokens=True))