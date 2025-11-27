import json
import os
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("OPENROUTER_API_KEY")

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

API_URL = "https://openrouter.ai/api/v1/chat/completions"

print("[DEBUG] OpenRouter KEY:", API_KEY[:10], "..." if API_KEY else "❌ 没加载成功")

def generate_questions_with_ai(content):
    prompt = f"""
你是一名教育AI，请根据以下资料生成5道选择题，每题含4个选项，并标出正确答案：

资料内容：
{content[:1000]}

请按照以下格式输出：
题目：
A.
B.
C.
D.
正确答案：
    """

    payload = {
        "model": "mistralai/mixtral-8x7b-instruct",  # 免费、效果强
        "messages": [
            {"role": "user", "content": prompt}
        ]
    }

    response = requests.post(API_URL, headers=headers, json=payload)

    if response.status_code == 200:
        return response.json()['choices'][0]['message']['content']
    else:
        return f"❌ OpenRouter 调用失败：{response.status_code} - {response.text}"

def evaluate_student_answers(questions, answers):
    scores = []
    comments = []
    recommendations = []

    for q, a in zip(questions, answers):
        prompt = f"""
You are an AI tutor. Evaluate the student's answer to the following question.

Question: {q}
Answer: {a}

Please give:
1. A score from 0 to 10
2. A short feedback comment (1~2 sentences)
3. One recommended question or topic for improvement

Respond in JSON format like:
{{"score": 7, "comment": "Good effort but lacks detail.", "recommendation": "Review examples related to this concept."}}
"""

        payload = {
            "model": "mistralai/mixtral-8x7b-instruct",
            "messages": [
                {"role": "user", "content": prompt}
            ]
        }

        response = requests.post(API_URL, headers=headers, json=payload)
        print("[DEBUG] Response status:", response.status_code)

        if response.status_code == 200:
            try:
                result_text = response.json()["choices"][0]["message"]["content"]
                result_json = json.loads(result_text.strip())
                scores.append(result_json.get("score", 0))
                comments.append(result_json.get("comment", "无"))
                recommendations.append(result_json.get("recommendation", "无"))
            except Exception as e:
                scores.append(0)
                comments.append("AI 解析失败")
                recommendations.append("请手动复习本题")
        else:
            scores.append(0)
            comments.append("❌ AI 请求失败")
            recommendations.append("❌ 无推荐")

    return {
        "scores": scores,
        "comments": comments,
        "recommendations": recommendations
    }

def chat_about_material(content, question):
    """
    基于学生上传资料内容和提问生成 AI 回复
    """
    prompt = f"""
你是一个智能学习助手。以下是学生上传的学习资料内容（不一定完整）：
----------------
{content[:1500]}
----------------

学生的问题是：
{question}

请你基于以上资料内容，尽量简洁清晰地回答问题。如果资料中没有明确内容，也请说明。
"""

    payload = {
        "model": "mistralai/mixtral-8x7b-instruct",
        "messages": [
            {"role": "user", "content": prompt}
        ]
    }

    response = requests.post(API_URL, headers=headers, json=payload)
    print("[DEBUG] Chat response status:", response.status_code)

    if response.status_code == 200:
        return response.json()["choices"][0]["message"]["content"]
    else:
        return f"❌ AI 问答失败：{response.status_code}"

def recommend_learning_path(student_records):
    """
    根据学生答题记录，调用 AI 生成学习路径
    """
    formatted_records = ""
    for r in student_records:
        formatted_records += f"""
题目：{r.question}
学生答案：{r.student_answer}
得分：{r.score}
AI 点评：{r.comment}
推荐建议：{r.recommendation}
---
"""

    prompt = f"""
你是一个学习教练，根据以下学生的答题记录，请制定一个个性化学习路径，包含3~5个步骤。
每一步要包括：
- 推荐学习内容或知识点
- 原因说明
- 推荐学习方式（如看视频、练习题、复习资料）

答题记录如下：
{formatted_records}

请用简洁中文回答，结构清晰。
"""

    payload = {
        "model": "mistralai/mixtral-8x7b-instruct",
        "messages": [{"role": "user", "content": prompt}]
    }

    response = requests.post(API_URL, headers=headers, json=payload)
    if response.status_code == 200:
        return response.json()["choices"][0]["message"]["content"]
    else:
        return f"❌ AI 生成失败：{response.status_code}"
def generate_summary_sheet(content):
    """
    用 AI 生成一页纸总结，包括概念、定义、要点、公式等
    """
    prompt = f"""
你是一名教育AI助教，请根据以下学习资料内容，提炼成一页纸总结，内容包括但不限于：

1. 核心知识点
2. 重要定义
3. 常用公式
4. 出现频率高的关键词或术语
5. 一个典型例题及其解法（如有）

资料内容如下：
------------------
{content[:2000]}
------------------

请用简洁中文，结构清晰分段输出，不要超出一页。
"""

    payload = {
        "model": "mistralai/mixtral-8x7b-instruct",
        "messages": [{"role": "user", "content": prompt}]
    }

    response = requests.post(API_URL, headers=headers, json=payload)
    if response.status_code == 200:
        return response.json()["choices"][0]["message"]["content"]
    else:
        return f"❌ AI 总结失败：{response.status_code}"
# def classify_knowledge_tag(question, student_answer=""):
#     """
#     用 AI 判断题目的知识点归属，例如：数学、英语语法、计算机基础等
#     """
#     prompt = f"""
# 请根据以下题目内容，判断该题主要属于哪类知识点领域（如：数学、英语语法、编程基础、历史常识、阅读理解等）。只返回类别名称即可：
#
# 题目：{question}
# 学生答案：{student_answer}
# """
#
#     payload = {
#         "model": "mistralai/mixtral-8x7b-instruct",
#         "messages": [{"role": "user", "content": prompt}]
#     }
#
#     response = requests.post(API_URL, headers=headers, json=payload)
#     if response.status_code == 200:
#         return response.json()["choices"][0]["message"]["content"].strip().replace("：", "").split()[0]
#     else:
#         return "未知"


def generate_teacher_feedback_summary(records):
    formatted = ""
    for r in records[:20]:
        formatted += f"""
题目：{r.question}
学生答案：{r.student_answer}
得分：{r.score}
点评：{r.comment}
建议：{r.recommendation}
---
"""

    prompt = f"""
你是一位教学分析AI，请根据以下学生答题记录，总结：

1. 学生整体表现如何
2. 哪些题目是共性弱项
3. 给教师的教学建议

记录如下：
{formatted}

请用中文输出一段清晰简洁的教学报告。
"""

    payload = {
        "model": "mistralai/mixtral-8x7b-instruct",
        "messages": [{"role": "user", "content": prompt}]
    }

    response = requests.post(API_URL, headers=headers, json=payload)
    if response.status_code == 200:
        return response.json()["choices"][0]["message"]["content"]
    else:
        return "❌ AI 生成失败"
