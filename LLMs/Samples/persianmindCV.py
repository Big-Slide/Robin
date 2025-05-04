from transformers import AutoTokenizer, AutoModelForCausalLM
import torch
import PyPDF2  # Library for extracting text from PDF files

# Check if GPU is available
device = "cuda" if torch.cuda.is_available() else "cpu"
print("Using device:", device)

# Function to extract text from a PDF
def pdf_to_text(pdf_path):
    """
    Extracts text from a PDF file.

    Args:
        pdf_path (str): The path to the PDF file to extract text from.
    
    Returns:
        str: Extracted text from the PDF.
    """
    with open(pdf_path, 'rb') as pdf_file:
        # Create PDF reader object
        pdf_reader = PyPDF2.PdfReader(pdf_file)

        # Initialize a string for storing text
        text = ""
        for page in pdf_reader.pages:
            # Extract text from each page and add a newline for readability
            text += page.extract_text() + "\n"
        
        return text

# Load PersianMind model and tokenizer
model = AutoModelForCausalLM.from_pretrained(
    "universitytehran/PersianMind-v1.0",
    torch_dtype=torch.bfloat16,
    low_cpu_mem_usage=True,
    device_map={"": device},  # Map to appropriate device
)
tokenizer = AutoTokenizer.from_pretrained("universitytehran/PersianMind-v1.0")

# Prepare PDF input
pdf_path = 'c:\\Py code\\sample\\input.pdf'  # Update this with your PDF file path
CONTEXT = pdf_to_text(pdf_path)  # Extract context from the PDF

# Handle long context by truncating if necessary
MAX_CONTEXT_TOKENS = 512  # Reserve space for the prompt and generated text
context_tokens = tokenizer(CONTEXT, max_length=MAX_CONTEXT_TOKENS, truncation=True)
CONTEXT = tokenizer.decode(context_tokens["input_ids"], skip_special_tokens=True)

# Define the prompt (user's query)
PROMPT = "خلاصه متن را توضیح بده"  # Translate: "Summarize the text."

# Prepare the input string for the conversational model
TEMPLATE = "{context}\nشما: {prompt}\nکامپیوتر: "
model_input = TEMPLATE.format(context=CONTEXT, prompt=PROMPT)

# Tokenize the input and move it to the appropriate device
input_tokens = tokenizer(model_input, return_tensors="pt")
input_tokens = input_tokens.to(device)

# Generate response from the model
generate_ids = model.generate(
    **input_tokens,
    max_new_tokens=512,  # Limit the length of the generated text
    do_sample=True,      # Enable sampling for variability in responses
    temperature=0.6,     # Set temperature for more focused sampling
    repetition_penalty=1.1  # Penalize repeated tokens for more diverse responses
)

# Decode the generated text
model_output = tokenizer.batch_decode(
    generate_ids,
    skip_special_tokens=True,
    clean_up_tokenization_spaces=False
)[0]

# Extract only the generated continuation (removing the input context)
output_text = model_output[len(model_input):]

# Save the output to a text file
output_file_path = "c:\\Py code\\outputs\\output13.txt"  # Update this path if necessary
with open(output_file_path, "w", encoding="utf-8") as file:
    file.write(output_text)

print("خروجی با موفقیت در فایل output5.txt ذخیره شد.")  # Translate: "Output successfully saved in output5.txt."