import streamlit as st
import pandas as pd
import PyPDF2
from docx import Document
import re
import time
import jieba
from rank_bm25 import BM25Okapi
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer
from zhipuai import ZhipuAI
import warnings
warnings.filterwarnings('ignore')

# ==================== 页面配置 ====================
st.set_page_config(page_title="简历匹配系统 - 多策略对比", layout="wide")
st.title("📄 简历匹配系统 · 多策略对比")
st.markdown("上传简历，选择匹配策略，系统将返回匹配度最高的岗位（按分数排序）")

# ==================== 读取并清洗数据 ====================
@st.cache_data
def load_and_clean_data():
    df = pd.read_csv('liepin_auto_all.csv', encoding='utf-8-sig')
    df = df.dropna(how='all')
    df['text_for_match'] = df.apply(
        lambda row: f"{row['职位']} {row['公司']} {row['薪资']} {row['地点']} {row['经验/学历']}",
        axis=1
    )
    return df

# ==================== 简历文本提取 ====================
def extract_text_from_pdf(file):
    reader = PyPDF2.PdfReader(file)
    text = ""
    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            text += page_text
    return text

def extract_text_from_docx(file):
    doc = Document(file)
    text = "\n".join([para.text for para in doc.paragraphs])
    return text

# ==================== 中文分词辅助函数 ====================
STOPWORDS = set(['的', '了', '和', '与', '或', '一个', '一些', '这个', '那个', '这些', '那些', '是', '在', '有', '我', '你', '他', '她', '它', '我们', '你们', '他们', '她们', '它们', '将', '就', '都', '也', '还', '要', '会', '可以', '能', '去', '来', '对', '从', '到', '这', '那', '等', '并', '且', '但', '而', '如', '其', '部分', '一些', '很多', '非常', '比较', '特别'])

def tokenize(text):
    words = jieba.cut(text)
    return [w for w in words if w.strip() and w not in STOPWORDS]

# ==================== 策略1：BM25 ====================
def match_bm25(resume_text, df, top_k=20):
    tokenized_jobs = [tokenize(text) for text in df['text_for_match'].tolist()]
    bm25 = BM25Okapi(tokenized_jobs)
    tokenized_resume = tokenize(resume_text)
    scores = bm25.get_scores(tokenized_resume)
    top_indices = scores.argsort()[-top_k:][::-1]
    results = df.iloc[top_indices].copy()
    results['匹配分数'] = scores[top_indices]
    return results

# ==================== 策略2：TF-IDF + 余弦相似度 ====================
def match_tfidf(resume_text, df, top_k=20):
    all_texts = df['text_for_match'].tolist() + [resume_text]
    vectorizer = TfidfVectorizer(tokenizer=tokenize, token_pattern=None, lowercase=False)
    tfidf_matrix = vectorizer.fit_transform(all_texts)
    resume_vec = tfidf_matrix[-1]
    job_vecs = tfidf_matrix[:-1]
    similarities = cosine_similarity(resume_vec, job_vecs).flatten()
    top_indices = similarities.argsort()[-top_k:][::-1]
    results = df.iloc[top_indices].copy()
    results['匹配分数'] = similarities[top_indices]
    return results

# ==================== 策略3：SBERT（BM25初筛 + 语义精排） ====================
@st.cache_resource
def load_sbert_model():
    return SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')

def match_sbert(resume_text, df, top_k=20, bm25_initial=50):
    # 1. BM25 初筛
    tokenized_jobs = [tokenize(text) for text in df['text_for_match'].tolist()]
    bm25 = BM25Okapi(tokenized_jobs)
    tokenized_resume = tokenize(resume_text)
    bm25_scores = bm25.get_scores(tokenized_resume)
    bm25_top_indices = bm25_scores.argsort()[-bm25_initial:][::-1]
    candidate_df = df.iloc[bm25_top_indices].copy()
    
    # 2. SBERT 精排
    model = load_sbert_model()
    job_texts = candidate_df['text_for_match'].tolist()
    job_embeddings = model.encode(job_texts, convert_to_tensor=True)
    resume_embedding = model.encode([resume_text], convert_to_tensor=True)
    similarities = cosine_similarity(resume_embedding.cpu(), job_embeddings.cpu()).flatten()
    candidate_df['匹配分数'] = similarities
    candidate_df = candidate_df.sort_values('匹配分数', ascending=False).head(top_k)
    return candidate_df

# ==================== 策略4：智谱大模型（BM25初筛 + LLM精排） ====================
ZHIPU_API_KEY = ""  # 需要输入API_KEY
client = ZhipuAI(api_key=ZHIPU_API_KEY)

def match_llm(resume_text, df, top_k=20, bm25_initial=50):
    # 1. BM25 初筛
    tokenized_jobs = [tokenize(text) for text in df['text_for_match'].tolist()]
    bm25 = BM25Okapi(tokenized_jobs)
    tokenized_resume = tokenize(resume_text)
    bm25_scores = bm25.get_scores(tokenized_resume)
    bm25_top_indices = bm25_scores.argsort()[-bm25_initial:][::-1]
    candidate_df = df.iloc[bm25_top_indices].copy()
    
    # 2. 大模型精排
    llm_scores = []
    for _, row in candidate_df.iterrows():
        job_text = row['text_for_match']
        prompt = f"""
你是一个招聘匹配专家。请根据简历内容判断候选人与岗位的匹配程度，只输出一个0-100之间的整数分数，不要输出其他任何内容。

简历：
{resume_text[:1500]}

岗位描述：
{job_text}

请输出匹配分数（0-100）：
"""
        try:
            response = client.chat.completions.create(
                model="glm-4-flash",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
            )
            score_text = response.choices[0].message.content.strip()
            nums = re.findall(r'\d+', score_text)
            score = int(nums[0]) if nums else 50
        except Exception:
            score = 0
        llm_scores.append(score)
        time.sleep(0.3)  # 控制 API 调用频率
    candidate_df['匹配分数'] = llm_scores
    candidate_df = candidate_df.sort_values('匹配分数', ascending=False).head(top_k)
    return candidate_df

# ==================== 主界面 ====================
def main():
    df = load_and_clean_data()
    st.sidebar.header("⚙️ 匹配策略选择")
    strategy = st.sidebar.selectbox(
        "选择匹配算法",
        ["BM25", "TF-IDF + 余弦相似度", "SBERT (语义向量)", "智谱大模型 (GLM-4-Flash)"]
    )
    top_k = st.sidebar.slider("返回岗位数量", min_value=5, max_value=50, value=20, step=5)
    
    uploaded_file = st.file_uploader("📄 上传简历 (PDF 或 Word)", type=["pdf", "docx"])
    
    if uploaded_file is not None:
        if uploaded_file.name.endswith('.pdf'):
            resume_text = extract_text_from_pdf(uploaded_file)
        else:
            resume_text = extract_text_from_docx(uploaded_file)
        
        if not resume_text.strip():
            st.error("无法提取简历文本，请确保文件为文字版（非扫描图片）")
            return
        
        st.success(f"✅ 简历解析成功，共 {len(resume_text)} 字符")
        
        with st.spinner(f"正在使用 {strategy} 进行匹配..."):
            if strategy == "BM25":
                result_df = match_bm25(resume_text, df, top_k)
            elif strategy == "TF-IDF + 余弦相似度":
                result_df = match_tfidf(resume_text, df, top_k)
            elif strategy == "SBERT (语义向量)":
                result_df = match_sbert(resume_text, df, top_k)
            else:
                result_df = match_llm(resume_text, df, top_k)
        
        # 分数归一化展示
        if strategy in ["BM25", "TF-IDF + 余弦相似度", "SBERT (语义向量)"]:
            min_score = result_df['匹配分数'].min()
            max_score = result_df['匹配分数'].max()
            if max_score > min_score:
                result_df['展示分数'] = (result_df['匹配分数'] - min_score) / (max_score - min_score) * 100
            else:
                result_df['展示分数'] = 50
        else:
            result_df['展示分数'] = result_df['匹配分数']
        
        result_df = result_df.sort_values('展示分数', ascending=False)
        st.subheader(f"🏆 匹配结果（{strategy}，按分数降序）")
        
        for _, row in result_df.iterrows():
            with st.expander(f"【{int(row['展示分数'])}分】{row['职位']} - {row['公司']}"):
                st.write(f"**公司**：{row['公司']}")
                st.write(f"**薪资**：{row['薪资'] if pd.notna(row['薪资']) else '面议'}")
                st.write(f"**地点**：{row['地点'] if pd.notna(row['地点']) else '未提供'}")
                st.write(f"**经验/学历**：{row['经验/学历'] if pd.notna(row['经验/学历']) else '未提供'}")
                st.write(f"**原始匹配值**：{row['匹配分数']:.4f}")
        
        csv = result_df[['职位', '公司', '薪资', '地点', '经验/学历', '匹配分数']].to_csv(index=False).encode('utf-8-sig')
        st.download_button("📥 下载匹配结果 CSV", csv, "match_results.csv", "text/csv")

if __name__ == "__main__":
    main()