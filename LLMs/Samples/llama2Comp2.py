from transformers import AutoTokenizer, AutoModelForCausalLM
import torch
import os
from datetime import datetime
import matplotlib.pyplot as plt
import arabic_reshaper
from bidi.algorithm import get_display

# Initialize device
device = 'cuda' if torch.cuda.is_available() else 'cpu'
print(f"Using device: {device}")

# Load tokenizer and model
tokenizer = AutoTokenizer.from_pretrained("PartAI/Dorna2-Llama3.1-8B-Instruct")
model = AutoModelForCausalLM.from_pretrained(
    "PartAI/Dorna2-Llama3.1-8B-Instruct",
    torch_dtype=torch.bfloat16,
    device_map={"": device},
)

# Define the questions
questions = {
    'q1': "زمانی را توصیف کنید که مجبور بودید اطلاعات پیچیده‌ای را به تیم خود ارائه دهید. چگونه آن را به روشی مؤثر ارائه کردید؟",
    'q2': "وقتی برای اولین بار در مقابل گروهی از افراد قرار می‌گیرید، چگونه خود را آماده می‌کنید؟",
    'q3': "چطور می‌توانید توجه و تمرکز مخاطبان خود را در طول یک ارائه طولانی حفظ کنید؟",
    'q4': "چگونه می‌توانید احساسات و واکنش‌های مخاطبان را در حین ارائه خود تحلیل و واکنش نشان دهید؟"
}

# Function to generate answers using the LLM
def generate_answer(question):
    messages = [
        {"role": "system",
         "content": "You are a helpful Persian assistant inside Roobin company. Please answer the following question in Persian."},
        {"role": "user", "content": question},
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
    return decoded_response

# Function to evaluate competency for each question
def evaluate_response(response, criteria):
    score = 0
    max_score = 100
    
    weights = {
        'clarity': 0.25,
        'structure': 0.25,
        'examples': 0.20,
        'engagement': 0.15,
        'confidence': 0.15
    }
    
    for key, weight in weights.items():
        if key in criteria:
            if any(word in response.lower() for word in criteria[key]):
                score += weight * max_score
    
    return min(round(score), 100)

# Define criteria for each question
criteria = {
    'q1': {
        'clarity': ['تقسیم بندی', 'مرحله به مرحله', 'ساده سازی'],
        'structure': ['ابتدا', 'سپس', 'در نهایت'],
        'examples': ['مثال', 'نمونه', 'تجربه'],
        'engagement': ['بازخورد', 'پرسش و پاسخ'],
        'confidence': ['موفق', 'اطمینان']
    },
    'q2': {
        'clarity': ['برنامه ریزی', 'آمادگی', 'تمرین'],
        'structure': ['مطالعه', 'تحقیق', 'بررسی'],
        'examples': ['تجربه قبلی', 'موارد مشابه'],
        'engagement': ['ارتباط چشمی', 'زبان بدن'],
        'confidence': ['اعتماد به نفس', 'مثبت']
    },
    'q3': {
        'clarity': ['تعامل', 'مشارکت', 'پویایی'],
        'structure': ['تنوع', 'استراحت', 'بخش بندی'],
        'examples': ['داستان', 'مثال عملی'],
        'engagement': ['سوال', 'فعالیت'],
        'confidence': ['انرژی', 'اشتیاق']
    },
    'q4': {
        'clarity': ['مشاهده', 'دقت', 'توجه'],
        'structure': ['تحلیل', 'ارزیابی'],
        'examples': ['تجربه', 'موقعیت'],
        'engagement': ['همدلی', 'درک'],
        'confidence': ['انعطاف', 'سازگاری']
    }
}

# Function to plot scores
def plot_scores(scores):
    labels = [
        "ارائه اطلاعات پیچیده",
        "آمادگی برای ارائه",
        "حفظ توجه مخاطب",
        "تحلیل و واکنش به مخاطب"
    ]
    
    reshaped_labels = [get_display(arabic_reshaper.reshape(label)) for label in labels]
    values = [scores[q] for q in scores]
    
    plt.figure(figsize=(10, 6))
    plt.bar(reshaped_labels, values, color='skyblue')
    plt.ylim(0, 100)
    plt.xlabel("مهارت‌ها", fontsize=12)
    plt.ylabel("نمره (از 100)", fontsize=12)
    plt.title(get_display(arabic_reshaper.reshape("تحلیل مهارت‌های ارتباطی")), fontsize=14)
    plt.xticks(rotation=15, fontsize=10)
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    plt.tight_layout()
    
    # Save the plot
    output_dir = r"C:\Py code\outputs"
    os.makedirs(output_dir, exist_ok=True)
    plot_file = os.path.join(output_dir, "communication_analysis_plot.png")
    plt.savefig(plot_file)
    plt.show()
    print(f"نمودار تحلیل در فایل زیر ذخیره شد:")
    print(plot_file)

# Main function
def main():
    responses = {}
    scores = {}
    
    # Generate answers and evaluate scores
    for q_key, question in questions.items():
        print(f"Generating answer for: {question}")
        response = generate_answer(question)
        responses[q_key] = response
        print(f"Answer: {response}\n")
        
        # Evaluate the response
        scores[q_key] = evaluate_response(response, criteria[q_key])
    
    # Display scores
    print("\nCompetency Scores:")
    for q_key, score in scores.items():
        print(f"{questions[q_key]}: {score}/100")
    
    # Plot the scores
    plot_scores(scores)

if __name__ == "__main__":
    main()