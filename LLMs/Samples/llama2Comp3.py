import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
import matplotlib.pyplot as plt
import os
from datetime import datetime
import arabic_reshaper
from bidi.algorithm import get_display
import random

# Device configuration
device = 'cuda' if torch.cuda.is_available() else 'cpu'
print(f"Using device: {device}")

class CommunicationSkillsAnalyzer:
    def __init__(self, num_questions=None):
        # Initialize tokenizer and model
        self.tokenizer = AutoTokenizer.from_pretrained("PartAI/Dorna2-Llama3.1-8B-Instruct")
        self.model = AutoModelForCausalLM.from_pretrained(
            "PartAI/Dorna2-Llama3.1-8B-Instruct",
            torch_dtype=torch.bfloat16,
            device_map={"": device},
        )

        # Define questions and answers
        self.questions = [
            "زمانی را توصیف کنید که مجبور بودید اطلاعات پیچیده‌ای را به تیم خود ارائه دهید. چگونه آن را به روشی مؤثر ارائه کردید؟",
            "چگونه محیطی را ایجاد می‌کنید که تمامی اعضای تیم به راحتی بتوانند با یکدیگر همکاری کنند؟",
            "چگونه اطمینان حاصل می‌کنید که تمامی اقدامات شما مطابق با اصول اخلاقی سازمان است؟",
            "چگونه مهارت‌ها و دانش خود را به طور مداوم به‌روز نگه می‌دارید؟",
            "چطور می‌توانید توجه و تمرکز مخاطبان خود را در طول یک ارائه طولانی حفظ کنید؟"
        ]

        self.answers = [
            "در طی سالها تجربه کارکردن من متوجه شدم که بهترین روش برای توضیح اطلاعات پیچیده ارائه آنها به صورت توضیحات تصویری و جدول و نمودار هستش. به طور مثال برای تفهیم تاثیر میزان پراکندگی کارکنان در واحدهای مختلف در یک سازمان را به وسیله نمودار و اختصاص رنگهای مختلف به هر واحد برای مدیران ارشد توضیح دادیم و به این طریق توانستیم برای به تعادل رساندن جذب افراد برای واحدهای مختلف گام مهمی برداریم.",
            "با یکدلی",
            "در ابتدا ورودم به یک سازمان آیین نامه های مربوط با اصول اخلاقی را مطالعه می کنم و سعی می کنم با حق و حقوق کارمندان آشنا بشم. در گام بعدی سعی می کنم با افراد با سابقه شرکت در معاشرت کنم تا از تجربیات آنها استفاده کنم و رفتار سازمانی را به صورت عینی و دریچه نگاه آنها هم درک کنم. در مرحل آخر با کارشناسان منابع انسانی سازمان صحبت خواهم کرد که از تجربیات آنها استفاده کنم.",
            "رویکرد من شامل چند گام هستش. در گام اول سعی می کنم مقالات جدید در زمینه کاری خودم را مطالعه کنم یکی از این منابع هاروارد ریویو هستش. در گام بعدی پادکستها و ویودیوهای آموزشی را نگاه می کنم و یا در سایتهای معتبر دوره هایی را ثبت نام می کنم. یکی از موثرترین روشها شرکت در کلاسهای آموزشی هستش. که آخرین کلاسی که شرکت کرد تحلیل داده در نرم افزار پاوربی آی بود.",
            "برای به‌روز نگه داشتن مهارت‌ها و دانشم، روش‌های مختلفی را دنبال می‌کنم. مطالعه مقالات معتبر مانند هاروارد بیزینس ریویو، استفاده از پادکست‌ها و ویدیوهای آموزشی در پلتفرم‌هایی مانند YouTube و TED Talks، و شرکت در دوره‌های آنلاین سایت‌هایی مانند Coursera و Udemy بخشی از این فرآیند است. همچنین، در کلاس‌های حضوری یا آنلاین مانند دوره تحلیل داده با Power BI شرکت می‌کنم و آموخته‌هایم را در پروژه‌های واقعی تمرین و اجرا می‌کنم. شبکه‌سازی با متخصصان حوزه کاری‌ام، پیگیری روندها و فناوری‌های جدید از طریق وبلاگ‌ها و خبرنامه‌ها، و شرکت در رویدادها و سمینارهای تخصصی نیز به من کمک می‌کند تا همیشه به‌روز بمانم. علاوه بر این، از شبکه‌های اجتماعی حرفه‌ای مانند LinkedIn برای تعامل با دیگران و یادگیری از تجربیاتشان استفاده می‌کنم. در نهایت، همیشه به دنبال فرصت‌های جدید برای یادگیری و رشد هستم تا بتوانم با چالش‌های جدید روبرو شوم."
        ]

        # Limit the number of questions if specified
        if num_questions is not None and num_questions <= len(self.questions):
            self.questions = self.questions[:num_questions]
            self.answers = self.answers[:num_questions]

        # Define terminators
        self.terminators = [
            self.tokenizer.eos_token_id,
            self.tokenizer.convert_tokens_to_ids("<|eot_id|>")
        ]

    def reshape_text(self, text):
        """Reshape Persian/Arabic text for proper display"""
        reshaped_text = arabic_reshaper.reshape(text)
        return get_display(reshaped_text)

    def analyze_llm_response(self, response):
        """Analyze LLM response with comprehensive scoring"""
        criteria = {
            'completeness': {
                'keywords': [
                    'جزئیات', 'توضیح', 'مثال', 'کامل', 'راهکار', 
                    'استراتژی', 'مرحله', 'گام', 'روش'
                ],
                'weight': 1.0,
                'max_points': 100
            },
            'relevance': {
                'keywords': [
                    'مرتبط', 'هدف', 'موضوع', 'دقیق', 
                    'هدفمند', 'کاربردی', 'ارتباط'
                ],
                'weight': 0.95,
                'max_points': 100
            },
            'specificity': {
                'keywords': [
                    'مشخص', 'خاص', 'واضح', 'روشن', 
                    'دقیق', 'عملیاتی', 'مستقیم'
                ],
                'weight': 0.90,
                'max_points': 100
            },
            'structure': {
                'keywords': [
                    'ساختار', 'ترتیب', 'مراحل', 'منطقی', 
                    'سازمان‌یافته', 'گام‌به‌گام', 'روند'
                ],
                'weight': 0.85,
                'max_points': 100
            }
        }

        score = 0
        detailed_scores = {}

        # Advanced scoring mechanism
        for category, details in criteria.items():
            category_score = 0
            matched_keywords = []
            
            for keyword in details['keywords']:
                if keyword in response.lower():
                    category_score += 5
                    matched_keywords.append(keyword)
            
            normalized_score = min(category_score, details['max_points'])
            weighted_score = normalized_score * details['weight']
            
            score += weighted_score
            detailed_scores[category] = {
                'raw_score': normalized_score,
                'weighted_score': weighted_score,
                'matched_keywords': matched_keywords
            }

        # Advanced length and complexity bonus
        word_count = len(response.split())
        complexity_bonus = min(word_count / 50 * 20, 20)
        score += complexity_bonus

        # Contextual depth bonus
        context_keywords = [
            'تجربه', 'مثال عملی', 'راهکار', 'استراتژی', 
            'نتیجه', 'چالش', 'درس آموخته'
        ]
        context_bonus = sum(7 for keyword in context_keywords if keyword in response.lower())
        score += min(context_bonus, 15)

        # Final score normalization
        final_score = min(round(score), 100)

        return final_score

    def get_llm_response(self, question):
        """Generate LLM response for a given question"""
        messages = [
            {"role": "system", "content": "شما یک دستیار هوش مصنوعی هستید که به سؤالات مهارت‌های ارتباطی پاسخ می‌دهد."},
            {"role": "user", "content": question}
        ]
        
        input_ids = self.tokenizer.apply_chat_template(
            messages,
            add_generation_prompt=True,
            return_tensors="pt"
        ).to(self.model.device)
        
        outputs = self.model.generate(
            input_ids,
            max_new_tokens=512,
            eos_token_id=self.terminators,
            do_sample=True,
            temperature=0.3,
            top_p=0.70,
        )
        
        response = outputs[-1][input_ids.shape[-1]:]
        return self.tokenizer.decode(response, skip_special_tokens=True)

    def generate_random_responses(self):
        """Generate random responses for all questions"""
        responses = {}
        for i, question in enumerate(self.questions):
            responses[f'q{i+1}'] = self.answers[i]  # Use predefined answers
        return responses

    def analyze_responses(self, responses):
        """Analyze all responses and generate scores"""
        scores = {}
        for q_num, response in responses.items():
            scores[q_num] = self.analyze_llm_response(response)
        return scores

    def create_visualization(self, scores, avg_score):
        """Create visualization of communication skills"""
        plt.figure(figsize=(12, 8))
        
        # Prepare data
        questions = [self.reshape_text(q) for q in self.questions]
        
        # Create bar chart
        bars = plt.bar(questions, list(scores.values()))
        
        # Color coding
        colors = ['#ff9999' if x < 60 else '#99ff99' if x >= 90 else '#ffff99' 
                  for x in scores.values()]
        
        for bar, color in zip(bars, colors):
            bar.set_color(color)
            height = bar.get_height()
            plt.text(bar.get_x() + bar.get_width()/2., height,
                    f'{int(height)}',
                    ha='center', va='bottom')
        
        plt.axhline(y=avg_score, color='r', linestyle='--', label='میانگین نمره')
        plt.text(len(scores) - 1, avg_score + 2, f'میانگین: {avg_score:.2f}', color='r')

        plt.title(self.reshape_text('تحلیل مهارت‌های ارتباطی'))
        plt.ylabel(self.reshape_text('نمره'))
        plt.ylim(0, 100)
        
        # Rotate x-axis labels for better readability
        plt.xticks(rotation=45, ha='right')
        plt.legend()
        
        # Create output directory
        output_dir = r"C:\Py code\outputs"
        os.makedirs(output_dir, exist_ok=True)
        
        # Save the plot
        current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(output_dir, f'communication_skills_ver3_{current_time}.png')
        plt.savefig(filename, bbox_inches='tight', dpi=300)
        plt.close()
        
        return filename

    def write_detailed_report(self, responses, scores):
        """Write a detailed report of the analysis with comprehensive feedback"""
        output_dir = r"C:\Py code\outputs"
        os.makedirs(output_dir, exist_ok=True)
        
        current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(output_dir, f'communication_skills_report_{current_time}.txt')
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write("تحلیل جامع مهارت‌های ارتباطی\n")
            f.write("=" * 50 + "\n\n")
            f.write(f"تاریخ و زمان تحلیل: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            avg_score = sum(scores.values()) / len(scores)
            f.write(f"نمره کل: {avg_score:.2f}/100\n")
            f.write("=" * 50 + "\n\n")
            
            for i, (q_num, response) in enumerate(responses.items(), 1):
                score = scores[q_num]
                f.write(f"سؤال {i}:\n")
                f.write(f"{self.questions[i-1]}\n\n")
                f.write("پاسخ:\n")
                f.write(f"{response}\n\n")
                f.write("تحلیل:\n")
                f.write(f"نمره: {score}/100\n")
                
                # Comprehensive feedback based on score
                if score >= 60:
                    feedback = """
                    عالی - پاسخ بسیار قوی
                    • پوشش کامل موضوع
                    • جزئیات دقیق و کاربردی
                    • ساختار منطقی و روشن
                    • نشان‌دهنده مهارت ارتباطی بالا
                    """
                elif score >= 40:
                    feedback = """
                    خوب - پاسخ مناسب با پتانسیل بهبود
                    • پوشش خوب موضوع
                    • نیاز به جزئیات بیشتر
                    • ساختار نسبتاً منظم
                    • فرصت برای افزایش عمق پاسخ
                    """
                elif score >= 25:
                    feedback = """
                    متوسط - نیاز به تمرکز بیشتر
                    • پوشش اولیه موضوع
                    • کمبود جزئیات تخصصی
                    • نیاز به بهبود ساختار
                    • توصیه به مطالعه بیشتر
                    """
                else:
                    feedback = """
                    نیاز به بهبود اساسی
                    • پوشش محدود موضوع
                    • فقدان جزئیات کلیدی
                    • ساختار نامنظم
                    • توصیه به آموزش مهارت‌های ارتباطی
                    """
                
                f.write(f"بازخورد تفصیلی:\n{feedback}\n")
                f.write("-" * 50 + "\n\n")
        
        return filename

    def run_analysis(self):
        """Main method to run the entire analysis process"""
        # Generate random responses
        responses = self.generate_random_responses()
        
        # Analyze responses
        scores = self.analyze_responses(responses)
        
        # Calculate average score
        avg_score = sum(scores.values()) / len(scores)
        
        # Create visualization
        chart_filename = self.create_visualization(scores, avg_score)
        
        # Write detailed report
        report_filename = self.write_detailed_report(responses, scores)
        
        # Print results
        print("\nتحلیل مهارت‌های ارتباطی:")
        for q_num, score in scores.items():
            print(f"سؤال {q_num[-1]}: نمره {score}/100")
        
        print(f"\nنمودار در مسیر زیر ذخیره شد: {chart_filename}")
        print(f"گزارش تفصیلی در مسیر زیر ذخیره شد: {report_filename}")
        
        return responses, scores

def main():
    # Specify the number of questions to analyze (optional)
    num_questions = 5  # Change this value to analyze a different number of questions
    analyzer = CommunicationSkillsAnalyzer(num_questions=num_questions)
    
    # Run the analysis
    responses, scores = analyzer.run_analysis()

if __name__ == "__main__":
    main()