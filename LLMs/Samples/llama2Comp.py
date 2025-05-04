import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import re
from datetime import datetime
import os

def evaluate_communication_response(response, criteria):
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

def analyze_presentation_skills(responses):
    q1_criteria = {
        'clarity': ['تقسیم بندی', 'مرحله به مرحله', 'ساده سازی'],
        'structure': ['ابتدا', 'سپس', 'در نهایت'],
        'examples': ['مثال', 'نمونه', 'تجربه'],
        'engagement': ['بازخورد', 'پرسش و پاسخ'],
        'confidence': ['موفق', 'اطمینان']
    }
    
    q2_criteria = {
        'clarity': ['برنامه ریزی', 'آمادگی', 'تمرین'],
        'structure': ['مطالعه', 'تحقیق', 'بررسی'],
        'examples': ['تجربه قبلی', 'موارد مشابه'],
        'engagement': ['ارتباط چشمی', 'زبان بدن'],
        'confidence': ['اعتماد به نفس', 'مثبت']
    }
    
    q3_criteria = {
        'clarity': ['تعامل', 'مشارکت', 'پویایی'],
        'structure': ['تنوع', 'استراحت', 'بخش بندی'],
        'examples': ['داستان', 'مثال عملی'],
        'engagement': ['سوال', 'فعالیت'],
        'confidence': ['انرژی', 'اشتیاق']
    }
    
    q4_criteria = {
        'clarity': ['مشاهده', 'دقت', 'توجه'],
        'structure': ['تحلیل', 'ارزیابی'],
        'examples': ['تجربه', 'موقعیت'],
        'engagement': ['همدلی', 'درک'],
        'confidence': ['انعطاف', 'سازگاری']
    }
    
    scores = {
        'q1': evaluate_communication_response(responses['q1'], q1_criteria),
        'q2': evaluate_communication_response(responses['q2'], q2_criteria),
        'q3': evaluate_communication_response(responses['q3'], q3_criteria),
        'q4': evaluate_communication_response(responses['q4'], q4_criteria)
    }
    
    return scores

def get_feedback_text(score, skill_area):
    if score >= 90:
        return f"عالی - تسلط بسیار خوب در {skill_area}"
    elif score >= 75:
        return f"خوب - مهارت قابل قبول در {skill_area}"
    elif score >= 60:
        return f"متوسط - نیاز به بهبود در {skill_area}"
    else:
        return f"نیاز به تقویت جدی در {skill_area}"

def generate_feedback(scores):
    feedback = {
        'q1': {
            'score': scores['q1'],
            'feedback': get_feedback_text(scores['q1'], 'توانایی ارائه اطلاعات پیچیده')
        },
        'q2': {
            'score': scores['q2'],
            'feedback': get_feedback_text(scores['q2'], 'آمادگی برای ارائه')
        },
        'q3': {
            'score': scores['q3'],
            'feedback': get_feedback_text(scores['q3'], 'حفظ توجه مخاطب')
        },
        'q4': {
            'score': scores['q4'],
            'feedback': get_feedback_text(scores['q4'], 'تحلیل و واکنش به مخاطب')
        }
    }
    return feedback

def write_to_file(responses, feedback, output_dir=None):
    # Create output directory if it doesn't exist
    if output_dir is None:
        output_dir = r"C:\Py code\outputs"
    
    # Create the directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Create filename with current date and time
    current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = os.path.join(output_dir, f"communication_analysis_{current_time}.txt")
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write("تحلیل مهارت‌های ارتباطی\n")
        f.write("=" * 50 + "\n\n")
        
        # Write date and time
        f.write(f"تاریخ و زمان تحلیل: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        # Calculate average score
        avg_score = sum(feedback[q]['score'] for q in feedback) / len(feedback)
        f.write(f"نمره کل: {avg_score:.2f}/100\n")
        f.write("=" * 50 + "\n\n")
        
        # Write detailed analysis for each question
        questions = {
            'q1': "زمانی را توصیف کنید که مجبور بودید اطلاعات پیچیده‌ای را به تیم خود ارائه دهید. چگونه آن را به روشی مؤثر ارائه کردید؟",
            'q2': "وقتی برای اولین بار در مقابل گروهی از افراد قرار می‌گیرید، چگونه خود را آماده می‌کنید؟",
            'q3': "چطور می‌توانید توجه و تمرکز مخاطبان خود را در طول یک ارائه طولانی حفظ کنید؟",
            'q4': "چگونه می‌توانید احساسات و واکنش‌های مخاطبان را در حین ارائه خود تحلیل و واکنش نشان دهید؟"
        }
        
        for q in feedback:
            f.write(f"\nسوال {q}:\n")
            f.write(f"{questions[q]}\n\n")
            f.write("پاسخ:\n")
            f.write(f"{responses[q]}\n\n")
            f.write("تحلیل:\n")
            f.write(f"نمره: {feedback[q]['score']}/100\n")
            f.write(f"بازخورد: {feedback[q]['feedback']}\n")
            f.write("-" * 50 + "\n")
    
    return filename

def main():
    # Sample responses
    responses = {
        'q1': 'برای ارائه اطلاعات پیچیده، ابتدا موضوع را به بخش‌های کوچکتر تقسیم کردم و با مثال‌های عملی توضیح دادم...',
        'q2': 'قبل از ارائه، کاملاً مطالعه می‌کنم و تمرین می‌کنم. به زبان بدن و ارتباط چشمی توجه خاصی دارم...',
        'q3': 'با استفاده از داستان‌های جذاب و مثال‌های کاربردی، و طرح سوالات تعاملی...',
        'q4': 'با دقت به واکنش‌های مخاطبان توجه می‌کنم و با انعطاف‌پذیری محتوا را تنظیم می‌کنم...'
    }
    
    scores = analyze_presentation_skills(responses)
    feedback = generate_feedback(scores)
    
    # Write analysis to file
    output_file = write_to_file(responses, feedback)
    
    print(f"تحلیل با موفقیت در فایل زیر ذخیره شد:")
    print(output_file)

if __name__ == "__main__":
    main()