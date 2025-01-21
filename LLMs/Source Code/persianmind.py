from transformers import AutoTokenizer, AutoModelForCausalLM
import torch

device = "cuda" if torch.cuda.is_available() else "cpu"
print(device)
model = AutoModelForCausalLM.from_pretrained(
    "universitytehran/PersianMind-v1.0",
    torch_dtype=torch.bfloat16,
    low_cpu_mem_usage=True,
    device_map={"": device},
)
tokenizer = AutoTokenizer.from_pretrained(
    "universitytehran/PersianMind-v1.0",
)

TEMPLATE = "{context}\nشما: {prompt}\nکامپیوتر: "
CONTEXT = "نام این کامپیوتر علیرضا است"
PROMPT = "نام?"

model_input = TEMPLATE.format(context=CONTEXT, prompt=PROMPT)
input_tokens = tokenizer(model_input, return_tensors="pt")
input_tokens = input_tokens.to(device)
#generate_ids = model.generate(**input_tokens, max_new_tokens=512, do_sample=False, repetition_penalty=1.1)
generate_ids = model.generate(**input_tokens, max_new_tokens=256, do_sample=True, temperature=0.4, repetition_penalty=1.1)
model_output = tokenizer.batch_decode(generate_ids, skip_special_tokens=True, clean_up_tokenization_spaces=False)[0]

print(model_output[len(model_input):])
# فرض کنید model_output و model_input از قبل تعریف شده‌اند
output_text = model_output[len(model_input):]

# ذخیره خروجی در فایل txt
with open("c:\\Py code\\outputs\\output4.txt", "w", encoding="utf-8") as file:
    file.write(output_text)

print("خروجی با موفقیت در فایل output4.txt ذخیره شد.")