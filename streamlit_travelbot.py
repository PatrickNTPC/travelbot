# streamlit run streamlit_travelbot.py
# 3天2夜嘉義遊

import os
import streamlit as st
from google import genai
from google.genai import types

import logging
import sys

# ----------------------------------------------------
# 1. 配置頁面和標題
# ----------------------------------------------------
st.set_page_config(page_title="🤖 智能旅遊規劃師 (Gemini API)", layout="wide")
st.title("🗺️ 您的專屬旅遊規劃機器人")

# 由於底層 SDK 可能繞過 Python Loggers，我們將不再依賴 logging 模組
# 僅確保核心配置在最上方

# ----------------------------------------------------
# 2. 核心配置
# ----------------------------------------------------

# 系統指令 (System Instruction)
SYSTEM_INSTRUCTION_TEXT = (
    "你是一位頂級的旅遊規劃師，專精於亞洲文化深度旅行。你的任務是根據用戶的需求，提供包含「景點」、「美食」和「交通」的詳細建議。"
    "回答風格必須是熱情、專業且富有個人見解的。請確保每一次的回覆都像一篇精美的小文章，並以條列式重點結尾。"
)

MODEL_NAME = "gemini-2.5-flash"  # 使用穩定且高效的 flash 模型
TEMPERATURE_VALUE = 0.6
MAX_TOKENS = 65535

# ----------------------------------------------------
# 3. 獲取 API 金鑰 (安全且互動式)
# ----------------------------------------------------
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    GEMINI_API_KEY = st.sidebar.text_input(
        "請輸入您的 GEMINI_API_KEY", 
        type="password", 
        help="金鑰不會被儲存。您可以在 Google AI Studio 獲取。"
    )

if not GEMINI_API_KEY:
    st.info("請先在左側邊欄輸入您的 API 金鑰以繼續。")
    st.stop()


# ----------------------------------------------------
# 4. 初始化 Gemini 客戶端和配置 (重要修正)
# ----------------------------------------------------

# 定義工具 (Google Search)
tools = [
    types.Tool(googleSearch=types.GoogleSearch()),
]

# 定義生成內容的配置
config = types.GenerateContentConfig(
    temperature=TEMPERATURE_VALUE,
    max_output_tokens=MAX_TOKENS,
    tools=tools,
    system_instruction=SYSTEM_INSTRUCTION_TEXT,
)

# 僅初始化 client，並移除 Chat 物件，避免調試輸出
if "client" not in st.session_state:
    st.session_state.messages = []
    
    try:
        # 僅初始化 client
        st.session_state.client = genai.Client(api_key=GEMINI_API_KEY)
        
    except Exception as e:
        st.error(f"初始化 Gemini 失敗：{e}")
        st.info("請檢查您的 API 金鑰和網路連線。")
        st.stop()


# ----------------------------------------------------
# 5. 顯示聊天記錄
# ----------------------------------------------------
# 顯示歷史訊息
for message in st.session_state.messages:
    # 'role' 是 'user' 或 'model'
    role = "user" if message["role"] == "user" else "assistant"
    with st.chat_message(role):
        st.markdown(message["content"])

# ----------------------------------------------------
# 6. 處理用戶輸入和 API 呼叫 (手動迭代並過濾)
# ----------------------------------------------------
if prompt := st.chat_input("請輸入您的旅遊規劃需求..."):
    
    # 儲存並顯示用戶輸入
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 呼叫 Gemini API
    with st.chat_message("assistant"):
        with st.spinner("旅遊規劃師正在努力思考中..."):
            
            # 修正：將 Streamlit 訊息歷史轉換為 API 內容列表
            api_contents = []
            for msg in st.session_state.messages:
                # API 內容需要 'role' ('user' 或 'model') 和 'parts'
                # 注意：Streamlit 的 role 'assistant' 必須轉換為 API 的 'model'
                role = "user" if msg["role"] == "user" else "model"
                api_contents.append(
                    types.Content(
                        role=role,
                        # 修正: 使用 types.Part(text=...) 確保版本兼容性
                        parts=[types.Part(text=msg["content"])]
                    )
                )

            # 修正：使用 generate_content_stream 進行串流呼叫
            response_generator = st.session_state.client.models.generate_content_stream(
                model=MODEL_NAME,
                contents=api_contents, # 傳遞完整的聊天歷史
                config=config          # 傳遞配置 (包含系統指令和工具)
            )

            # 💡 最終修正：手動迭代生成器，只擷取並輸出 .text 內容
            full_response = ""
            message_placeholder = st.empty() 

            # 迭代生成器，只處理帶有文本內容的塊
            for chunk in response_generator:
                # 使用 try-except 確保遇到非標準的調試物件時不會崩潰
                try:
                    # 只有 Content 塊才會有 .text 屬性
                    if hasattr(chunk, 'text'):
                        text_to_print = chunk.text
                        
                        if text_to_print:
                            full_response += text_to_print
                            # 實時更新佔位符並添加游標
                            message_placeholder.markdown(full_response + "▌")
                except Exception:
                    # 忽略所有無法正確解析為文本的物件（例如 sdk_http_response 相關的調試物件）
                    continue 
            
            # 移除閃爍游標，顯示最終完整回覆
            message_placeholder.markdown(full_response)
            
    # 將助理的回覆添加到聊天記錄中
    st.session_state.messages.append({"role": "model", "content": full_response})