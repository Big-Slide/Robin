from transformers import AutoTokenizer, AutoModelForCausalLM
import torch
import PyPDF2

# Initialize device
device = 'cuda' if torch.cuda.is_available() else 'cpu'
print(device)

# Load tokenizer and model
tokenizer = AutoTokenizer.from_pretrained("PartAI/Dorna2-Llama3.1-8B-Instruct")
model = AutoModelForCausalLM.from_pretrained(
    "PartAI/Dorna2-Llama3.1-8B-Instruct",
    torch_dtype=torch.bfloat16,
    device_map={"": device},
)

# Function to read PDF content
def read_pdf(file_path):
    pdf_content = ""
    with open(file_path, "rb") as file:
        pdf_reader = PyPDF2.PdfReader(file)
        for page in pdf_reader.pages:
            pdf_content += page.extract_text() + "\n"
    return pdf_content

# Path to the PDF file
pdf_path = "c:\\Py code\\Sample\\resume.pdf"  # Replace with the actual path to your PDF file
pdf_text = read_pdf(pdf_path)

# Prepare messages
messages = [
    {"role": "system",
     "content": "You are a helpful Persian assistant inside Roobin company, and your job is to summarize or incase need translate too persian the CV provided to you and extract key attributes in persian language. Please answer questions in the asked language."},
    {"role": "user", "content": f":\n\n{pdf_text}"},
]

# Tokenize input
input_ids = tokenizer.apply_chat_template(
    messages,
    add_generation_prompt=True,
    return_tensors="pt"
).to(model.device)

# Define terminators
terminators = [
    tokenizer.eos_token_id,
    tokenizer.convert_tokens_to_ids("<|eot_id|>")
]

# Generate output
outputs = model.generate(
    input_ids,
    max_new_tokens=512,
    eos_token_id=terminators,
    do_sample=True,
    temperature=0.3,
    top_p=0.70,
)

# Decode response
response = outputs[-1][input_ids.shape[-1]:]
decoded_response = tokenizer.decode(response, skip_special_tokens=True)
print(decoded_response)

# Save the response to a text file
output_file = "model_response4.txt"
with open(output_file, "w", encoding="utf-8") as file:
    file.write(decoded_response)

print(f"Model response saved to {output_file}")
