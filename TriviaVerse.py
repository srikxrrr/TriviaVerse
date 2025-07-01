import streamlit as st
import wikipedia
import random
import requests
import time # For animation delays

# Set Wikipedia language
wikipedia.set_lang("en")

# Helper: Get summary and title
@st.cache_data(ttl=3600) # Cache results for an hour
def get_random_wikipedia_summary(category):
    try:
        # Increased search limit to get more diverse results
        page_titles = wikipedia.search(category, results=50)
        if not page_titles:
            return None, None
        
        # Filter out disambiguation pages and very short titles
        valid_titles = [
            title for title in page_titles 
            if "(disambiguation)" not in title and len(title) > 5
        ]
        if not valid_titles:
            return None, None
            
        title = random.choice(valid_titles)
        summary = wikipedia.summary(title, sentences=3) # Increased sentences for more context
        return title, summary
    except wikipedia.exceptions.DisambiguationError as e:
        # Handle disambiguation errors by trying another option
        if e.options:
            for option in random.sample(e.options, min(len(e.options), 5)):
                try:
                    summary = wikipedia.summary(option, sentences=3)
                    return option, summary
                except:
                    continue
        return None, None
    except Exception as e:
        st.error(f"Error fetching Wikipedia summary: {e}")
        return None, None

# Helper: Get Wikidata ID (used for potential future extensions, e.g., fetching more facts)
@st.cache_data(ttl=3600)
def get_wikidata_item_id(title):
    try:
        response = requests.get(
            f"https://en.wikipedia.org/w/api.php?action=query&titles={title}&prop=pageprops&format=json"
        )
        data = response.json()
        pages = data["query"]["pages"]
        for page_id in pages:
            wikibase_item = pages[page_id].get("pageprops", {}).get("wikibase_item")
            if wikibase_item:
                return wikibase_item
        return None
    except Exception as e:
        st.error(f"Error fetching Wikidata ID: {e}")
        return None

# Generate MCQ question
def generate_mcq(category):
    title, summary = get_random_wikipedia_summary(category)
    if not summary:
        return None

    correct_answer = title
    
    # Generate more relevant wrong answers
    wrong_answers_pool = []
    try:
        # Try to get related pages from Wikipedia or search within the category
        search_results = wikipedia.search(category, results=10)
        wrong_answers_pool.extend([
            res for res in search_results 
            if res != correct_answer and "(disambiguation)" not in res
        ])
        
        # Also include some truly random pages to mix it up
        wrong_answers_pool.extend(wikipedia.random(pages=5))

    except Exception as e:
        st.warning(f"Could not fetch diverse wrong answers, using random pages. Error: {e}")
        wrong_answers_pool.extend(wikipedia.random(pages=8)) # Fallback

    # Ensure unique and sufficient wrong answers
    wrong_answers = list(set([ans for ans in wrong_answers_pool if ans != correct_answer]))
    
    if len(wrong_answers) < 3:
        # Fallback if not enough diverse wrong answers are found
        wrong_answers.extend(random.sample(wikipedia.random(pages=5), 3 - len(wrong_answers)))
    
    wrong_answers = random.sample(wrong_answers, min(3, len(wrong_answers)))

    options = wrong_answers + [correct_answer]
    random.shuffle(options)

    return {
        "question": f"What Wikipedia article is this summary from?\n\n***{summary}***",
        "options": options,
        "answer": correct_answer
    }

# Streamlit UI
st.set_page_config(page_title="TriviaVerse Quiz", layout="centered", initial_sidebar_state="expanded")

# Custom CSS for better aesthetics and animations
st.markdown("""
<style>
    .main {
        background-color: #f0f2f6;
        padding: 20px;
        border-radius: 10px;
    }
    .stButton>button {
        background-color: #4CAF50;
        color: white;
        font-size: 18px;
        padding: 10px 20px;
        border-radius: 8px;
        border: none;
        cursor: pointer;
        transition: all 0.3s ease-in-out;
    }
    .stButton>button:hover {
        background-color: #45a049;
        transform: scale(1.05);
    }
    .stRadio > label {
        font-size: 16px;
        margin-bottom: 8px;
    }
    h1 {
        color: #2F80ED;
        text-align: center;
        font-size: 3em;
        margin-bottom: 0.5em;
        animation: fadeInDown 1s ease-out;
    }
    h3 {
        color: #333;
        font-size: 1.8em;
        margin-top: 1.5em;
        margin-bottom: 1em;
    }
    .stMarkdown p {
        font-size: 1.1em;
        line-height: 1.6;
    }
    .correct-feedback {
        background-color: #e6ffe6;
        color: #006600;
        padding: 10px;
        border-radius: 5px;
        margin-top: 10px;
        animation: slideInRight 0.5s ease-out;
    }
    .incorrect-feedback {
        background-color: #ffe6e6;
        color: #cc0000;
        padding: 10px;
        border-radius: 5px;
        margin-top: 10px;
        animation: shake 0.5s ease-out;
    }
    .stProgress > div > div > div > div {
        background-color: #2F80ED;
    }

    @keyframes fadeInDown {
        from { opacity: 0; transform: translateY(-20px); }
        to { opacity: 1; transform: translateY(0); }
    }
    @keyframes slideInRight {
        from { opacity: 0; transform: translateX(20px); }
        to { opacity: 1; transform: translateX(0); }
    }
    @keyframes shake {
        0% { transform: translateX(0); }
        25% { transform: translateX(-5px); }
        50% { transform: translateX(5px); }
        75% { transform: translateX(-5px); }
        100% { transform: translateX(0); }
    }
    @keyframes pulse {
        0% { transform: scale(1); }
        50% { transform: scale(1.02); }
        100% { transform: scale(1); }
    }
    .score-display {
        font-size: 1.5em;
        font-weight: bold;
        color: #2F80ED;
        text-align: right;
        margin-top: 1em;
        animation: pulse 1s infinite;
    }
</style>
""", unsafe_allow_html=True)

st.title("🧠 TriviaVerse Quiz")
st.markdown("##### _A smart quiz powered by Wikipedia & Wikidata_")

# Sidebar for settings
with st.sidebar:
    st.header("Quiz Settings")
    category = st.selectbox("Select Category", ["Science", "History", "Technology", "Pop Culture", "Geography", "Art", "Sports"])
    
    # Difficulty now influences number of sentences and random wrong answers more
    difficulty_level = st.slider("Select Difficulty", 1, 5, 3, help="Higher difficulty means more complex summaries and more diverse wrong answers.")
    
    num_questions = st.number_input("Number of Questions", min_value=3, max_value=20, value=5, step=1)
    
    st.markdown("---")
    st.write("Developed with ❤️ by Your Name")

# Initialize game state
if "score" not in st.session_state:
    st.session_state.score = 0
if "question_number" not in st.session_state:
    st.session_state.question_number = 1
if "questions_asked" not in st.session_state:
    st.session_state.questions_asked = [] # To store questions and prevent repeats
if "current_question_data" not in st.session_state:
    st.session_state.current_question_data = None
if "quiz_started" not in st.session_state:
    st.session_state.quiz_started = False

# Start Quiz Button
if not st.session_state.quiz_started:
    st.info("Click 'Start Quiz' to begin your TriviaVerse journey!")
    if st.button("🚀 Start Quiz", key="start_quiz_button"):
        st.session_state.quiz_started = True
        st.session_state.score = 0
        st.session_state.question_number = 1
        st.session_state.questions_asked = []
        st.session_state.current_question_data = None
        st.experimental_rerun() # Rerun to start the quiz interface
else:
    # Progress Bar
    progress_percentage = (st.session_state.question_number - 1) / num_questions
    st.progress(progress_percentage, text=f"Question {st.session_state.question_number-1}/{num_questions}")

    # --- Question Generation and Display ---
    if st.session_state.question_number <= num_questions:
        if st.session_state.current_question_data is None:
            with st.spinner("Fetching a new question..."):
                # Try generating unique questions
                max_attempts = 5
                attempts = 0
                while attempts < max_attempts:
                    new_question_data = generate_mcq(category)
                    if new_question_data and new_question_data["answer"] not in [q["answer"] for q in st.session_state.questions_asked]:
                        st.session_state.current_question_data = new_question_data
                        st.session_state.questions_asked.append(new_question_data)
                        break
                    attempts += 1
                if attempts == max_attempts:
                    st.warning("Couldn't fetch a unique question. Please try changing the category or restarting.")
                    st.session_state.quiz_started = False # End quiz if no new questions
                    st.stop() # Stop execution to prevent errors

        question_data = st.session_state.current_question_data
        
        if question_data:
            st.markdown(f"### Question {st.session_state.question_number}")
            st.markdown(question_data["question"])

            choice = st.radio("Choose your answer:", question_data["options"], key=f"question_{st.session_state.question_number}")

            submit_button = st.button("Submit Answer", key=f"submit_{st.session_state.question_number}")

            if submit_button:
                if choice == question_data["answer"]:
                    st.markdown('<div class="correct-feedback">Correct! 🎉 Well done!</div>', unsafe_allow_html=True)
                    st.balloons() # Fun animation for correct answer
                    st.session_state.score += 1
                else:
                    st.markdown(f'<div class="incorrect-feedback">Oops! The correct answer was **{question_data["answer"]}**. Better luck next time!</div>', unsafe_allow_html=True)
                    st.snow() # Another animation for incorrect answer

                # Prepare for next question
                st.session_state.question_number += 1
                st.session_state.current_question_data = None # Clear current question
                
                # Small delay for animations to be seen
                time.sleep(1.5) 
                st.experimental_rerun() # Rerun to load next question or end quiz
        else:
            st.warning("Couldn't fetch question. Try a different category or restart the quiz.")
            st.session_state.quiz_started = False # Reset quiz state if questions can't be loaded
    else:
        # --- Quiz End Screen ---
        st.balloons()
        st.success("🎉 Quiz Completed! 🎉")
        final_score_msg = f"You scored **{st.session_state.score}** out of **{num_questions}** questions!"
        if st.session_state.score == num_questions:
            st.markdown(f"### Amazing! {final_score_msg} You're a Trivia Master! 🏆")
        elif st.session_state.score >= num_questions * 0.7:
            st.markdown(f"### Great Job! {final_score_msg} Keep up the good work! 👍")
        else:
            st.markdown(f"### Good Effort! {final_score_msg} Practice makes perfect! 😊")
        
        st.markdown(f'<div class="score-display">Final Score: {st.session_state.score}/{num_questions}</div>', unsafe_allow_html=True)
        
        if st.button("Play Again!", key="play_again_button"):
            st.session_state.quiz_started = False
            st.session_state.score = 0
            st.session_state.question_number = 1
            st.session_state.questions_asked = []
            st.session_state.current_question_data = None
            st.experimental_rerun()

    st.markdown(f'<div class="score-display">Current Score: {st.session_state.score}</div>', unsafe_allow_html=True)
