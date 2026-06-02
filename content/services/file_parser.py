import pdfplumber
from docx import Document


def extract_text(file):
    name = file.name.lower()
    if name.endswith('.pdf'):
        return extract_pdf(file)
    elif name.endswith('.docx'):
        return extract_docx(file)
    elif name.endswith('.txt'):
        return extract_txt(file)
    else:
        raise ValueError(f"지원하지 않는 파일 형식입니다: {name}")


def extract_pdf(file):
    text = []
    with pdfplumber.open(file) as pdf:
        for page in pdf.pages:
            content = page.extract_text()
            if content:
                text.append(content)
    return '\n\n'.join(text)


def extract_docx(file):
    doc = Document(file)
    return '\n\n'.join([p.text for p in doc.paragraphs if p.text.strip()])


def extract_txt(file):
    return file.read().decode('utf-8', errors='ignore')