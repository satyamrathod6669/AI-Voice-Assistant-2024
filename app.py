import streamlit as st
from google import genai

# 1. Page Configuration
st.set_page_config(page_title="AI Voice Assistant 2024", page_icon="🎙️")
st.title("🎙️ AI Assistant - 2024 Batch")

# 2. Securely get API Key from Streamlit Secrets
API_KEY = st.secrets["GEMINI_API_KEY"]
client = genai.Client(api_key=API_KEY)

# 3. Initialize Chat History
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Hello Satyam! I'm your AI assistant. How can I help with your project today?"}
    ]

# 4. Display Chat History
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 5. Handle User Input
if prompt := st.chat_input("Type your message here..."):
    # Display user message
    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    # 6. Generate AI Response
    with st.chat_message("assistant"):
        try:
            # Use the most stable 2026 model string
            response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt
            )
            
            # Extract and display the text
            if response.text:
                full_response = response.text
                st.markdown(full_response)
                # Save to history
                st.session_state.messages.append({"role": "assistant", "content": full_response})
            else:
                st.error("The model returned an empty response.")
                
        except Exception as e:
            st.error(f"Technical Error: {e}")
            st.info("Check your 'Manage App > Logs' for more details.")

# 7. Sidebar with Project Info
with st.sidebar:
    st.header("Project Details")
    st.write("Role: AI Engineer (2024 Batch)")
    if st.button("🗑️ Clear Chat"):
        st.session_state.messages = []
        st.rerun()
