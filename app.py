#Import các thư viện cần thiết
from flask import Flask, render_template, request, send_file,url_for
import os
import docx
import pandas as pd
import joblib
import underthesea
import re
import PyPDF2

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
# Đảm bảo tồn tại các thư mục tải lên và xử lý
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Load model và các nhãn
vector, MultiNB, encoder = joblib.load('Model/model_final.joblib')

def model(sentence):
    #Tiền xử lý dữ liệu
    sentence = preprocess(sentence)
    #Kiểm tra xem câu có rỗng không
    if not sentence.strip():
        return "Tài liệu không có nội dung để xử lý hoặc chỉ chứa nội dung noise."
    #Chuyển câu thành vector
    vector_sentence = vector.transform([sentence])
    #Dự đoán
    final_sentence = MultiNB.predict(vector_sentence)[0]
    #Chuyển nhãn về dạng text
    final_sentence = encoder.inverse_transform([final_sentence])[0]
    return final_sentence

#Load stopword
stopwords = []
with open('Model/vietnamese-stopwords.txt', "r", encoding="utf-8") as file:
    lines = file.readlines()
    #Duyệt từng dòng trong file
for line in lines:
    word = line.strip()  # Loại bỏ khoảng trắng đầu/cuối
    stopwords.append(word)
#Hàm tiền xử lý nội dung
def preprocess(text):
    #Xử lý noise
    # Chuyển về chữ thường
    text = text.lower()
    # Loại bỏ các email
    text = re.sub(r'\b\w+@\w+\.\w+\b', '', text)
    # Loại bỏ các link
    text = re.sub(r'http\S+|www\.\S+', '', text)
    # Xóa các ký tự đặc biệt
    text = re.sub(r'[^\w\s]', '', text)
    # Xóa các chữ số
    text = re.sub(r'\d+', '', text)
    # Loại bỏ các ký tự xuống dòng (newlines)
    text = re.sub(r'\n|\r', ' ', text)
     
    #Tách từ
    tokens = underthesea.word_tokenize(text)
    #Loại bỏ stopword
    final_tokens = [token for token in tokens if token not in stopwords]
    final_text = ' '.join(final_tokens)
    return final_text

#Hàm xử lý file txt
def process_txt(file_path):
    # Load file txt và lấy nội dung
    text = open(file_path,'r',encoding='utf-8').read()
    #Dự đoán
    result = model(text)
    return result

#Hàm xử lý file docx
def process_docx(file_path):
    # Load file Docx và lấy nội dung
    doc = docx.Document(file_path)
    full_text = []
    #Duyệt qua từng trang lấy nội dung
    for paragraph in doc.paragraphs:
        full_text.append(paragraph.text)
    #Gộp lại 
    text = ''.join(full_text)
    #Dự đoán
    result = model(text)
    return result

#Hám xử lý file pdf
def process_pdf(file_path):
    with open(file_path, "rb") as pdf:
        #Đọc file pdf
        pdf_reader = PyPDF2.PdfReader(pdf)
        page = []
        #Duyệt qua từng trang lấy nội dung
        for i in range(len(pdf_reader.pages)):
            #Đọc nội dung trang
            noidung = pdf_reader.pages[i]
            #Chỉ lấy text thêm vào list
            page.append(noidung.extract_text())
    text = ''.join(page)
    #Dự đoán
    result = model(text)
    return result

#Hàm xử lý file excel
def process_excel(file_path):
    # Load file Excel và lấy nội dung
    df = pd.read_excel(file_path)
    
    # Nếu không tìm thấy cột 'content' trong file Excel in lỗi
    if 'content' not in df.columns:
        return "Vui lòng sửa dụng file có cột 'content' chứa nội dung cần phân loại"

    # Xử lí từng hàng excel
    X = df['content'].apply(preprocess)
    df['label'] = X.apply(model)
    
    # Lưu kết quả ra file excel mới
    processed_file_path = os.path.join(app.config['UPLOAD_FOLDER'], 'ketqua.xlsx')
    df.to_excel(processed_file_path, index=False)
    return "Phân loại thành công"

#Hàm chính
@app.route('/', methods=['GET', 'POST'])
def index():
    result =  None
    if request.method == 'POST':
        if 'file' in request.files and request.files['file'].filename != '':
            #Khai báo các định dạng file hợp lệ
            duoi_ok = ('.txt','.docx','.doc','.xlsx','.pdf')
            #Lấy file từ request
            file = request.files['file']
            #Lấy path của file đấy
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
            #Kiểm tra đuôi nếu hợp lệ thì mới lưu
            if file.filename.lower().endswith(duoi_ok):
                file.save(file_path)
            else:
                return render_template('index.html', result="Vui lòng nhập 1 trong các định dạng sau: pdf/docx/txt/xlsx")
            #Phân luồng các tài liệu
            if file.filename.lower().endswith('.txt'):
                result = process_txt(file_path)
            elif file.filename.lower().endswith('.docx'):
                result = process_docx(file_path)
            elif file.filename.lower().endswith('.doc'):
                result = "Vui lòng dùng file định dang .docx"
            elif file.filename.lower().endswith('.pdf'):
                result = process_pdf(file_path)
            elif file.filename.lower().endswith('.xlsx'):
                result = process_excel(file_path)
            #Xóa file sau khi xử lý
            os.remove(file_path)
        else:
            text_content = request.form['text_content']
            if text_content.strip() == '':
                result = "Vui lòng nhập nội dung hoặc chọn file"
            else:
                result = model(text_content) 
    return render_template('index.html', result=result)
#Xử lý download file
@app.route('/download/<ten>')
def download(ten):
    return send_file(f'uploads/{ten}', as_attachment=True)
if __name__ == '__main__':
    app.run(debug=True)
