from langchain_ollama import ChatOllama
import re
import unicodedata
import os

# os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"
from datetime import datetime

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph, Frame
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_JUSTIFY
from loguru import logger


class CVGenerator:
    def __init__(self, llm: ChatOllama):
        self.llm = llm

    def generate_clean_response(self, prompt: str):
        """Generate clean text response without code/markdown/test artifacts."""
        system_warning = (
            "INSTRUCTIONS: Write ONLY the answer in clear, professional English prose. "
            "DO NOT include any Python code, lists, tests, docstrings, or technical instructions of ANY kind. "
            "No headers, no comments, only pure CV text."
        )
        try:
            messages = [
                (
                    "system",
                    system_warning,
                ),
                ("human", f":\n\n{prompt.strip()}"),
            ]
            ai_msg = self.llm.invoke(messages)
            return self.aggressive_clean(ai_msg.content)
        except Exception as e:
            logger.error(f"Generation error: {e}")
            return ""

    def aggressive_clean(self, text):
        """Remove code, docstrings, tests, and random artifacts."""
        text = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
        text = re.sub(r'"""(.*?)"""', "", text, flags=re.DOTALL)
        text = re.sub(r"'''(.*?)'''", "", text, flags=re.DOTALL)
        text = re.sub(r"def\s+.*?\):.*?(?=\n\S|\Z)", "", text, flags=re.DOTALL)
        text = re.sub(r"@\w+\.\w+$.*?$", "", text)
        text = re.sub(r"^[ \t]*#.*$", "", text, flags=re.MULTILINE)
        text = re.sub(r"import\s+[^\n]*", "", text)
        text = re.sub(r"(from\s+\w+\s+import\s+[^\n]*)", "", text)
        text = re.sub(r"\bassert\b.*", "", text)
        text = re.sub(r"parser\.add_argument.*", "", text)
        text = re.sub(r'if __name__ ?== ?["\']__main__["\']:', "", text)
        text = re.sub(r"unittest\..*", "", text)
        text = re.sub(r"test_.*", "", text)
        text = re.sub(r"[$$\{].*?[$$\}]", "", text)
        text = unicodedata.normalize("NFKD", text)
        text = re.sub(r"[^\x20-\x7E\n]", "", text)
        replacements = {
            "\u2013": "-",
            "\u2014": "--",
            "\u2018": "'",
            "\u2019": "'",
            "\u201c": '"',
            "\u201d": '"',
        }
        for ch, repl in replacements.items():
            text = text.replace(ch, repl)
        clean = []
        for l in text.splitlines():
            s = l.strip()
            if not s or any(
                x in s
                for x in ["import ", "def ", "main(", "__name__", "argparse", "assert"]
            ):
                continue
            if s.startswith("-") or s.startswith("*"):
                clean.append(s)
            elif len(s.split()) > 3 and not s.startswith("["):
                clean.append(s)
        return "\n".join(clean).strip()

    def get_user_input(self):
        """Collect comprehensive user inputs including contact details."""
        print("\n=== CV Personalization ===")
        print("Please provide the following details:\n")

        questions = [
            ("full_name", "1. Your full name: "),
            ("target_role", "2. Desired job title/role: "),
            ("years_exp", "3. Years of experience: "),
            ("current_position", "4. Current/most recent job title: "),
            ("current_company", "5. Current/most recent company: "),
            ("key_skills", "6. Top 5 skills (comma separated): "),
            (
                "education",
                "7. Highest degree (e.g. 'MSc Computer Science - University X (2020)'): ",
            ),
            ("certifications", "8. Certifications (comma separated): "),
            ("achievement", "9. Your proudest professional achievement: "),
            ("languages", "10. Languages you speak (comma separated): "),
            ("email", "11. Your professional email: "),
            ("phone", "12. Your phone number (with country code): "),
            ("linkedin", "13. Your LinkedIn profile URL (or username): "),
            ("address", "14. Your city and country (optional): "),
            ("portfolio", "15. Portfolio/GitHub URL (optional): "),
        ]

        responses = {}
        for key, question in questions:
            responses[key] = input(question).strip()
        return responses

    def generate_cv_content(self, user_data):
        """Generate complete CV content using user inputs."""
        templates = {
            "job_title": (
                f"Write ONLY a short professional job title suitable for a {user_data['target_role']} "
                f"with {user_data['years_exp']} years of experience."
            ),
            "summary": (
                f"Write a professional summary for {user_data['full_name']} as a {user_data['target_role']} with "
                f"{user_data['years_exp']} years experience at {user_data['current_company']}. "
                f"Highlight top skills: {user_data['key_skills']}. "
                f"Also mention the achievement: {user_data.get('achievement', '')}. "
                f"Limit to 3-4 sentences. NO code or instruction, just prose."
            ),
            "experience": (
                f"For the CV section 'Professional Experience', write a 4-5 bullet point list describing the main "
                f"responsibilities and achievements of {user_data['full_name']} as a {user_data['current_position']} "
                f"at {user_data['current_company']}. Include use of these skills: {user_data['key_skills']}. "
                f"Begin each point with a strong action verb."
            ),
            "education": (
                f"Write the Education section for {user_data['full_name']}, include: "
                f"{user_data.get('education', '')}. Then list certifications: {user_data.get('certifications', '')}."
            ),
            "skills": (
                f"List up to 5 professional skills as a single well-formatted, comma-separated line, "
                f"using only these: {user_data['key_skills']}."
            ),
            "languages": (
                f"List the languages {user_data.get('full_name')} speaks as a comma-separated line: "
                f"{user_data.get('languages', '')}."
            ),
        }

        cv = {"name": user_data["full_name"]}
        for section, prompt in templates.items():
            logger.debug(f"Generating {section}...")
            cv[section] = self.generate_clean_response(prompt)

        # Generate contact info from user input
        cv["contact"] = self._generate_contact_info(user_data)
        return cv

    def _generate_contact_info(self, user_data):
        """Format contact information from user input."""
        contact_lines = []
        if user_data.get("email"):
            contact_lines.append(f"Email: {user_data['email']}")
        if user_data.get("phone"):
            contact_lines.append(f"Phone: {user_data['phone']}")
        if user_data.get("linkedin"):
            linkedin = user_data["linkedin"]
            if not linkedin.startswith("http"):
                linkedin = f"linkedin.com/in/{linkedin}"
            contact_lines.append(f"LinkedIn: {linkedin}")
        if user_data.get("address"):
            contact_lines.append(f"Location: {user_data['address']}")
        if user_data.get("portfolio"):
            portfolio = user_data["portfolio"]
            if not portfolio.startswith("http"):
                portfolio = f"github.com/{portfolio}"
            contact_lines.append(f"Portfolio: {portfolio}")
        return "\n".join(contact_lines)

    def create_pdf_cv(self, cv_content, output_path: str = None):
        """Create a professional PDF CV with wrapped text in bordered boxes and no duplicated skills."""

        if output_path is None:
            output_path = f"{cv_content['name'].replace(' ', '_')}_CV.pdf"
        c = canvas.Canvas(output_path, pagesize=letter)
        width, height = letter

        # Colors and styling
        sidebar_bg = colors.HexColor("#23374d")
        sidebar_border_color = colors.HexColor("#ffffff")
        accent_color = colors.HexColor("#2a4b72")
        text_color = colors.HexColor("#ffffff")
        main_text_color = colors.HexColor("#222222")

        sidebar_width = 2.2 * inch
        margin = 14

        # Draw sidebar background
        c.setFillColor(sidebar_bg)
        c.rect(0, 0, sidebar_width, height, fill=1, stroke=0)

        # Sidebar header: Name and job title
        c.setFillColor(text_color)
        c.setFont("Helvetica-Bold", 20)
        c.drawCentredString(sidebar_width / 2, height - 1.1 * inch, cv_content["name"])
        c.setFont("Helvetica", 13)
        c.drawCentredString(
            sidebar_width / 2, height - 1.5 * inch, cv_content.get("job_title", "")
        )

        # Helper to draw bordered box with title and wrapped text Paragraphs
        def draw_sidebar_section(title, top_y, lines, max_height=None):
            """Draw a bordered box with a title, containing wrapped text lines."""
            box_x = margin
            box_y = top_y
            box_width = sidebar_width - 2 * margin

            styles = getSampleStyleSheet()
            title_style = ParagraphStyle(
                "SidebarTitle",
                parent=styles["Heading4"],
                fontName="Helvetica-Bold",
                fontSize=12,
                textColor=text_color,
                spaceAfter=6,
                alignment=TA_JUSTIFY,
            )
            text_style = ParagraphStyle(
                "SidebarText",
                parent=styles["Normal"],
                fontName="Helvetica",
                fontSize=9,
                textColor=text_color,
                leading=12,
                alignment=TA_JUSTIFY,
                spaceAfter=4,
            )

            story = []
            story.append(Paragraph(title, title_style))
            for line in lines:
                story.append(Paragraph(line, text_style))

            frame_height = max_height or (len(lines) + 1) * 14 + 10
            frame_y = box_y - frame_height - 4  # y from bottom-left of frame

            # Draw border rectangle
            c.setStrokeColor(sidebar_border_color)
            c.setLineWidth(1)
            c.rect(box_x - 4, frame_y - 4, box_width + 8, frame_height + 8, fill=0)

            f = Frame(box_x, frame_y, box_width, frame_height, showBoundary=0)
            f.addFromList(story, c)

            return frame_y - 12  # next y position below this box

        # Prepare contact lines
        contact_lines = [
            line.strip()
            for line in cv_content.get("contact", "").split("\n")
            if line.strip()
        ]
        y_pos = height - 1.8 * inch
        y_pos = draw_sidebar_section("Contact", y_pos, contact_lines)

        # Prepare unique skills list
        skill_set = set()
        skills_raw = cv_content.get("skills", "")
        for skill in skills_raw.split(","):
            skill_clean = skill.strip()
            if skill_clean:
                skill_set.add(skill_clean)
        skills_lines = [f"• {s}" for s in sorted(skill_set)]
        y_pos = draw_sidebar_section("Skills", y_pos, skills_lines)

        # Languages
        languages_raw = cv_content.get("languages", "").strip()
        languages_lines = []
        if languages_raw:
            for lang in languages_raw.split(","):
                lang_clean = lang.strip()
                if lang_clean:
                    languages_lines.append(f"• {lang_clean.capitalize()}")
            y_pos = draw_sidebar_section("Languages", y_pos, languages_lines)

        # Main content area with styled sections and wrapped text
        frame_x = sidebar_width + 0.5 * inch
        frame_y = 0.7 * inch
        frame_w = width - sidebar_width - 0.7 * inch
        frame_h = height - 1.25 * inch

        styles = getSampleStyleSheet()
        style_section = ParagraphStyle(
            "SectionHeader",
            parent=styles["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=16,
            textColor=accent_color,
            spaceAfter=12,
            spaceBefore=12,
            underlineWidth=1,
            underlineColor=accent_color,
            underlineOffset=-4,
        )
        style_paragraph = ParagraphStyle(
            "BodyText",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=11,
            leading=15,
            textColor=main_text_color,
            alignment=TA_JUSTIFY,
            spaceAfter=12,
        )
        style_bullet = ParagraphStyle(
            "Bullet",
            parent=style_paragraph,
            bulletFontName="Helvetica",
            bulletFontSize=12,
            leftIndent=16,
            bulletIndent=6,
            spaceAfter=6,
        )

        story = []

        # Summary
        if cv_content.get("summary"):
            story.append(Paragraph("Summary", style_section))
            story.append(Paragraph(cv_content["summary"], style_paragraph))

        # Experience with bullets
        if cv_content.get("experience"):
            story.append(Paragraph("Experience", style_section))
            for line in cv_content["experience"].split("\n"):
                exp_line = line.strip("-* ").strip()
                if exp_line:
                    story.append(Paragraph(exp_line, style_bullet, bulletText="•"))

        # Education
        if cv_content.get("education"):
            story.append(Paragraph("Education", style_section))
            for line in cv_content["education"].split("\n"):
                line_strip = line.strip()
                if line_strip:
                    story.append(Paragraph(line_strip, style_paragraph))

        frame = Frame(frame_x, frame_y, frame_w, frame_h, showBoundary=1)
        frame.addFromList(story, c)

        # Footer
        c.setFont("Helvetica", 8)
        c.setFillColor(colors.gray)
        c.drawRightString(
            width - 0.5 * inch,
            0.5 * inch,
            f"Generated: {datetime.now().strftime('%Y-%m-%d')}",
        )

        c.save()
        logger.debug(f"\nProfessional CV saved as: {output_path}")
        return output_path


def main():
    logger.debug("=== AI-Powered CV Generator ===")

    # Initialize with your model path
    generator = CVGenerator()
    # generator = CVGenerator(r"D:\dsmodel\models--deepseek-ai--DeepSeek-V2\snapshots\4461458f186c35188585855f28f77af5661ad489")
    # Get user input
    user_data = generator.get_user_input()

    # Generate CV content
    logger.debug("\nGenerating your professional CV...")
    cv_content = generator.generate_cv_content(user_data)

    # Create PDF
    generator.create_pdf_cv(cv_content)

    # Preview content
    logger.debug("\n=== Generated CV Content ===")
    for section, content in cv_content.items():
        logger.debug(f"\n{section.upper()}:\n{content}")


if __name__ == "__main__":
    main()
