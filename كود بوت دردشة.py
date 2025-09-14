"""
Advanced Johan - Telegram Smart Bot (Complete, corrected)
Requirements:
    pip install python-telegram-bot==20.7 openai
Usage:
    - ضع توكن التليجرام وOpenAI في قسم CONFIG
    - شغل: python advanced_johan_bot.py
"""

import asyncio
import json
import random
import sqlite3
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import re
from collections import defaultdict

import openai
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ChatAction
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
)

# ---------------- CONFIG ----------------
TELEGRAM_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"
OPENAI_API_KEY = "YOUR_OPENAI_API_KEY"
ADMIN_IDS: List[int] = [123456789]  # غيريه أو افرغه

# Special users configuration (username without @ and some display names)
SPECIAL_USERNAMES = ["brimiro", "eva", "bjorn"]
SPECIAL_DISPLAY_NAMES = ["عصماء", "إيفا", "بيورن", "إيفا براون"]

# ---------------- Logging ----------------
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)


# ---------------- Advanced Johan Bot ----------------
class AdvancedJohanBot:
    def __init__(self, telegram_token: str, openai_api_key: str, admin_ids: Optional[List[int]] = None):
        self.telegram_token = telegram_token
        openai.api_key = openai_api_key
        self.admin_ids = admin_ids or []

        # Active games and interactions
        self.active_games: Dict[int, dict] = {}
        self.pending_questions = {}
        self.conversation_context = defaultdict(list)

        # Personalities (time-based)
        self.personalities = {
            "morning": {"name": "جوهان الصباحي", "traits": "نشيط، متفائل", "style": "متحمس", "greeting": "صباح الخير! ☀️"},
            "afternoon": {"name": "جوهان العادي", "traits": "ودود، مرح", "style": "طبيعي", "greeting": "أهلاً! كيف الحال؟ 😊"},
            "evening": {"name": "جوهان المسائي", "traits": "مرح، مريح", "style": "أطول بالردود", "greeting": "مساء الخير! 🌅"},
            "night": {"name": "جوهان الليلي", "traits": "هادئ، متأمل", "style": "هادئ", "greeting": "أهلاً.. شوي تعبان لكن حاضر 🌙"},
            "sleepy": {"name": "جوهان النعسان", "traits": "متعب، بطيء", "style": "قصير ومباشر", "greeting": "هممم.. أهلاً 😴"}
        }

        # emotion patterns, jokes, games etc. (kept mostly like الأصل)
        self.emotion_patterns = {
            "سعيد_جداً": ["رائع", "ممتاز", "واو", "🤩", "❤️", "احبك"],
            "سعيد": ["حلو", "جميل", "مبسوط", "كويس", "😊", "👍"],
            "حزين_جداً": ["مكتئب", "انتحار", "تعبت", "😭", "💔"],
            "حزين": ["حزين", "زعلان", "تعبت", "😢"],
            "غاضب": ["منرفز", "مزعوج", "غاضب", "😡"],
            "خائف": ["خايف", "قلقان", "😰"],
            "متحمس": ["متحمس", "متشوق", "🤩", "🎉"],
            "ممل": ["ملل", "زهق", "فاضي"],
            "محتار": ["محتار", "ما أدري", "🤔"],
            "امتنان": ["شكراً", "تسلم", "يعطيك العافية", "🙏"]
        }

        self.jokes_database = {
            "برمجة": ["مبرمج قال... (نكتة)"],
            "عامة": ["واحد دخل مطعم... (نكتة)"],
            "تقنية": ["واي فاي راح للطبيب النفسي... (نكتة)"]
        }

        self.games = {
            "حزر_الرقم": {"min_val": 1, "max_val": 100, "max_attempts": 7},
            "كلمة_وكلمة": {"word_chains": ["بحر", "سمك", "ماء", "مطر"]},
            "لغز": {}
        }

        self.riddles = [
            {"question": "أطير بلا جناح، وأبكي بلا عيون، فمن أنا؟", "answer": ["سحابة", "غيمة"], "hint": "في السماء"},
            {"question": "له رأس ولا عقل له، وله عين ولا يرى، فمن هو؟", "answer": ["إبرة", "دبوس"], "hint": "تستخدم في الخياطة"}
        ]

        # Dialect patterns & bad words
        self.dialect_patterns = {
            "خليجي": ["شلونك", "هلا", "ياخي", "الحين"],
            "مصري": ["ايه", "حاضر", "كده", "يلا"],
            "شامي": ["شو", "ليش", "هلأ"],
            "مغاربي": ["واش", "بزاف", "فين"],
            "عراقي": ["شنو", "وين", "هاي"],
            "سعودي": ["وش", "ليه", "تبي"]
        }

        self.bad_words = [
            "غبي", "أحمق", "تافه", "حقير", "وسخ", "قذر", "حمار", "احا",
            "stupid", "idiot", "dumb", "shit", "fuck", "asshole", "damn"
        ]

        # DB init
        self.conn = sqlite3.connect("johan_advanced.db", check_same_thread=False)
        self.setup_advanced_database()

    # ---------------- Database setup ----------------
    def setup_advanced_database(self) -> None:
        cur = self.conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                messages_count INTEGER DEFAULT 0,
                dialect TEXT DEFAULT 'محايد',
                personality_type TEXT DEFAULT 'unknown',
                mood_happy INTEGER DEFAULT 0,
                mood_angry INTEGER DEFAULT 0,
                friendship_level INTEGER DEFAULT 3,
                energy_level INTEGER DEFAULT 5,
                trust_level INTEGER DEFAULT 3,
                favorite_time_period TEXT DEFAULT 'مساء',
                interests TEXT DEFAULT '[]',
                last_interaction TEXT,
                first_met TEXT,
                learned_words TEXT DEFAULT '[]',
                conversation_history TEXT DEFAULT '[]',
                achievements TEXT DEFAULT '[]',
                games_played INTEGER DEFAULT 0,
                total_jokes_told INTEGER DEFAULT 0,
                favorite_joke_category TEXT DEFAULT 'عامة',
                last_emotion_detected TEXT DEFAULT 'محايد',
                response_time_avg REAL DEFAULT 2.0,
                preferred_conversation_style TEXT DEFAULT 'متوسط'
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS emotion_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                detected_emotion TEXT,
                confidence REAL,
                message_sample TEXT,
                timestamp TEXT,
                johan_response TEXT
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS game_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                game_type TEXT,
                started_at TEXT,
                ended_at TEXT,
                result TEXT,
                score INTEGER DEFAULT 0
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS contextual_memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                memory_type TEXT,
                content TEXT,
                importance_level INTEGER DEFAULT 1,
                created_at TEXT,
                last_recalled TEXT,
                recall_count INTEGER DEFAULT 0,
                associated_emotions TEXT DEFAULT '[]',
                tags TEXT DEFAULT '[]'
            )
        """)
        self.conn.commit()

    # ---------------- Helpers ----------------
    def get_current_personality(self) -> Dict:
        hour = datetime.now().hour
        if 5 <= hour < 12:
            return self.personalities["morning"]
        elif 12 <= hour < 17:
            return self.personalities["afternoon"]
        elif 17 <= hour < 22:
            return self.personalities["evening"]
        elif 22 <= hour < 24:
            return self.personalities["night"]
        else:
            return self.personalities["sleepy"]

    def normalize_text(self, text: str) -> str:
        return (text or "").lower().strip()

    def detect_bad_words(self, text: str) -> bool:
        t = self.normalize_text(text)
        return any(w in t for w in self.bad_words)

    def detect_user_emotion(self, text: str) -> Tuple[str, float]:
        t = self.normalize_text(text)
        scores = {}
        for emo, patterns in self.emotion_patterns.items():
            score = 0
            for p in patterns:
                if p in t:
                    weight = 2 if any(ch in p for ch in "😊😂😢😔😠😡🤩❤️💔") else 1
                    score += weight
            if score:
                scores[emo] = score
        if not scores:
            return "محايد", 0.5
        strongest = max(scores, key=scores.get)
        confidence = min(scores[strongest] / 3.0, 1.0)
        return strongest, confidence

    def analyze_personality_type(self, profile: Dict) -> str:
        history = profile.get("conversation_history", [])
        if len(history) < 5:
            return "unknown"
        patterns = defaultdict(int)
        for conv in history[-10:]:
            msg = conv.get("message", "").lower()
            if any(w in msg for w in ["أصدقاء", "مجموعة", "طلعة"]):
                patterns["social"] += 1
            if any(w in msg for w in ["وحيد", "لحالي", "هادئ"]):
                patterns["introvert"] += 1
            if any(w in msg for w in ["ليش", "كيف", "فكرة", "أحلل", "منطق"]):
                patterns["analytical"] += 1
            if any(w in msg for w in ["شعور", "حاسس", "قلب", "مشاعر"]):
                patterns["emotional"] += 1
            if len(msg) > 50:
                patterns["talkative"] += 1
            if any(w in msg for w in ["نكتة", "مضحك", "ضحك"]):
                patterns["humorous"] += 1
        traits = []
        traits.append("اجتماعي" if patterns["social"] > patterns["introvert"] else "هادئ")
        traits.append("تحليلي" if patterns["analytical"] > patterns["emotional"] else "عاطفي")
        if patterns["humorous"] > 2:
            traits.append("مرح")
        if patterns["talkative"] > 3:
            traits.append("ثرثار")
        return "_".join(traits) if traits else "متوازن"

    def get_contextual_conversation_starter(self, profile: Dict) -> str:
        hour = datetime.now().hour
        if 6 <= hour < 12:
            starters = ["كيف نومك امبارح؟", "إيش خططك اليوم؟", "شربت قهوة؟"]
        elif 17 <= hour < 22:
            starters = ["كيف كان يومك؟", "تعبت اليوم؟", "إيش أحسن شي صار اليوم؟"]
        else:
            starters = ["حكيلي عن شي جديد تعلمته", "وش رأيك نلعب لعبة؟"]
        if profile.get("friendship_level", 3) >= 7:
            starters += ["قولي سر صغير عنك 😏", "إيش الشي اللي محتار فيه؟"]
        return random.choice(starters)

    def create_contextual_memory(self, user_id: int, content: str, memory_type: str, importance: int = 1):
        words = content.lower().split()
        tags = [w for w in words if len(w) > 3][:5]
        self.conn.execute("""
            INSERT INTO contextual_memories (user_id, memory_type, content, importance_level, created_at, tags)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (user_id, memory_type, content, importance, datetime.now().isoformat(), json.dumps(tags)))
        self.conn.commit()

    def get_relevant_memories(self, user_id: int, current_message: str, limit: int = 3) -> List[Dict]:
        msg_words = set(self.normalize_text(current_message).split())
        cur = self.conn.execute("""
            SELECT content, memory_type, importance_level, tags, created_at
            FROM contextual_memories WHERE user_id = ?
            ORDER BY importance_level DESC, created_at DESC LIMIT 50
        """, (user_id,))
        mems = []
        for row in cur.fetchall():
            tags = json.loads(row[3])
            relevance = len(msg_words.intersection(set(tags)))
            if relevance > 0 or row[2] >= 3:
                mems.append({"content": row[0], "type": row[1], "importance": row[2], "created_at": row[4], "relevance": relevance})
        mems.sort(key=lambda x: (x["relevance"], x["importance"]), reverse=True)
        return mems[:limit]

    # ---------------- Special requests & bad language ----------------
    def handle_special_requests(self, message: str, profile: Dict) -> Optional[str]:
        m = self.normalize_text(message)
        if any(k in m for k in ["نكتة", "اضحكني", "مزح", "كوميديا", "joke"]):
            cat = profile.get("favorite_joke_category", "عامة")
            jokes = self.jokes_database.get(cat, self.jokes_database["عامة"])
            profile["total_jokes_told"] = profile.get("total_jokes_told", 0) + 1
            return random.choice(jokes)
        if any(k in m for k in ["كم الساعة", "الساعة", "time"]):
            return f"الساعة الحين {datetime.now().strftime('%H:%M')} 🕐"
        if any(k in m for k in ["لعبة", "العب", "نلعب", "game"]):
            return self.suggest_game()
        if any(k in m for k in ["طقس", "جو", "weather"]):
            return random.choice(["ما أقدر أشوف الطقس بس ان شاء الله جو حلو! ☀️", "شوف تطبيق الطقس 🌤️"])
        if any(k in m for k in ["ساعدني", "محتاج مساعدة", "مشكلة", "help"]):
            return "أكيد بساعدك! قولي المشكلة بالتفصيل وأشوف كيف أقدر أساعد 🤝"
        return None

    def handle_bad_language(self, profile: Dict, message: str) -> str:
        self.update_emotions_and_friendship(profile, "angry", 2)
        self.update_emotions_and_friendship(profile, "happy", -1)
        if profile.get("mood_angry", 0) >= 4:
            return random.choice(["خلاص! مو راضي أكلمك لين تتأدب.", "*يتجاهلك*", "بهدل حتى تتعلم الأدب."])
        elif profile.get("mood_angry", 0) >= 2:
            return random.choice(["احترم نفسك شوي! ما نتكلم بهالأسلوب 😤", "ايش هالكلام؟ هدي أعصابك", "لو تعيدها بتنسى اسمي"])
        else:
            return random.choice(["يا أخي، نتكلم بأدب أحسن 😊", "خلنا نتكلم بطريقة حلوة", "ما نحتاج نشتم، قدرنا نتفاهم"])

    # ---------------- Emotions & importance ----------------
    def update_emotions_and_friendship(self, profile: Dict, emotion: str, delta: int) -> None:
        if emotion == "happy":
            profile["mood_happy"] = max(-5, min(5, profile.get("mood_happy", 0) + delta))
        elif emotion == "angry":
            profile["mood_angry"] = max(-5, min(5, profile.get("mood_angry", 0) + delta))
        if profile.get("mood_angry", 0) >= 3:
            profile["friendship_level"] = max(0, profile.get("friendship_level", 3) - 1)
        if profile.get("mood_happy", 0) >= 2:
            profile["friendship_level"] = min(10, profile.get("friendship_level", 3) + 1)

    def calculate_message_importance(self, message: str, profile: Dict) -> int:
        importance = 1
        m = self.normalize_text(message)
        high_keywords = ["أحب", "أكره", "مشكلة", "سعيد", "حزين", "عمل", "دراسة", "عائلة"]
        importance += sum(2 for w in high_keywords if w in m)
        personal_keywords = ["اسمي", "عمري", "شغلي", "أهلي", "صديقي", "حبيبي"]
        importance += sum(3 for w in personal_keywords if w in m)
        if len(message) > 100: importance += 1
        if len(message) > 200: importance += 1
        if any(q in m for q in ["ليش", "كيف", "متى", "وين", "مين", "إيش"]): importance += 1
        return min(importance, 5)

    # ---------------- Response generation (OpenAI) ----------------
    async def generate_enhanced_response(self, message: str, profile: Dict, group_context: str = "") -> str:
        # special commands
        sp = self.handle_special_requests(message, profile)
        if sp:
            return sp
        if self.detect_bad_words(message):
            return self.handle_bad_language(profile, message)

        user_emotion, confidence = self.detect_user_emotion(message)
        profile["last_emotion_detected"] = user_emotion
        # log emotion
        self.conn.execute("""
            INSERT INTO emotion_history (user_id, detected_emotion, confidence, message_sample, timestamp)
            VALUES (?, ?, ?, ?, ?)
        """, (profile["user_id"], user_emotion, confidence, message[:200], datetime.now().isoformat()))
        self.conn.commit()

        current_persona = self.get_current_personality()
        relevant_memories = self.get_relevant_memories(profile["user_id"], message)

        personality_analysis = self.analyze_personality_type(profile)
        conversation_starter = (self.get_contextual_conversation_starter(profile)
                                if random.random() < 0.25 else "")

        memories_text = ""
        if relevant_memories:
            memories_text = "ذكريات مهمة:\n" + "\n".join(f"- {m['content'][:80]}..." for m in relevant_memories)

        system_prompt = f"""
أنت {current_persona['name']} - {current_persona['traits']}
شخصيتك الحالية: {current_persona['style']}

عن المستخدم:
- الاسم: {profile.get('first_name', 'صديق')}
- نوع الشخصية: {personality_analysis}
- مستوى الصداقة: {profile.get('friendship_level', 3)}/10
- اللهجة: {profile.get('dialect', 'محايد')}
- آخر مشاعر مكتشفة: {user_emotion} (ثقة: {confidence:.2f})

{memories_text}

قواعد:
1) تفاعل مع مشاعر المستخدم بذكاء.
2) استخدم لهجته إذا كانت واضحة.
3) اسأل سؤالًا أو اضف تعليقًا ذكيًا.
4) لو المستخدم مميز (إيفا/بيورن) كن ألطف لكن بدون كرنج.
{f"فكر في طرح هذا السؤال: {conversation_starter}" if conversation_starter else ""}
الآن رد على: "{message}"
"""

        try:
            response = await asyncio.to_thread(
                openai.ChatCompletion.create,
                model="gpt-4",
                messages=[{"role": "system", "content": system_prompt},
                          {"role": "user", "content": message}],
                max_tokens=300,
                temperature=0.85
            )
            reply = response["choices"][0]["message"]["content"].strip()
            # update post interaction
            self.update_emotions_and_friendship(profile, "happy", 1)
            if profile.get("mood_angry", 0) > 0:
                self.update_emotions_and_friendship(profile, "angry", -1)
            importance = self.calculate_message_importance(message, profile)
            if importance >= 2:
                self.create_contextual_memory(profile["user_id"],
                                             f"المستخدم قال: {message[:150]} | جوهان رد: {reply[:150]}",
                                             "conversation", importance)
            # log response for latest emotion_history row
            self.conn.execute("""
                UPDATE emotion_history SET johan_response = ?
                WHERE user_id = ? AND timestamp = (
                    SELECT MAX(timestamp) FROM emotion_history WHERE user_id = ?
                )
            """, (reply[:300], profile["user_id"], profile["user_id"]))
            self.conn.commit()
            return reply
        except Exception as e:
            logger.exception("OpenAI error")
            persona = self.get_current_personality()
            return random.choice([
                f"عذراً، {persona['name']} فيه مشكلة تقنية 😅",
                "ثانية، عقلي واجد أمور لازم أفكر فيها 🤔",
                "ما فهمت تمام، أعدلي الكلام لو سمحت؟"
            ])

    # ---------------- Games / Game helpers ----------------
    def suggest_game(self) -> str:
        games_list = ["🔢 حزر الرقم - أفكر في رقم من 1-100", "🔤 كلمة وكلمة - أقول كلمة وإنت قول كلمة لها علاقة", "🧩 لغز - ألغاز ذكية"]
        return "وش رأيك نلعب؟ اختر:\n" + "\n".join(games_list) + "\n\nاكتب اسم اللعبة أو الرقم!"

    async def start_number_guessing_game(self, update: Update, profile: Dict):
        user_id = update.effective_user.id
        number = random.randint(1, 100)
        self.active_games[user_id] = {"type": "حزر_الرقم", "number": number, "attempts": 0, "max_attempts": 7, "started_at": datetime.now()}
        keyboard = [
            [InlineKeyboardButton("1-25", callback_data="range_1-25"), InlineKeyboardButton("26-50", callback_data="range_26-50")],
            [InlineKeyboardButton("51-75", callback_data="range_51-75"), InlineKeyboardButton("76-100", callback_data="range_76-100")],
            [InlineKeyboardButton("إلغاء اللعبة ❌", callback_data="cancel_game")]
        ]
        await update.message.reply_text(f"🎮 حزر الرقم! فكرت برقم من 1-100. عندك {self.active_games[user_id]['max_attempts']} محاولات.\nاختر نطاقًا أو اكتب رقمًا:", reply_markup=InlineKeyboardMarkup(keyboard))

    async def handle_game_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        if user_id not in self.active_games:
            await query.edit_message_text("انتهت اللعبة أو لم تبدأ بعد!")
            return
        data = query.data
        if data == "cancel_game":
            del self.active_games[user_id]
            await query.edit_message_text("تم إلغاء اللعبة! 👋")
            return
        if data.startswith("range_"):
            rng = data.split("_")[1]
            await query.edit_message_text(f"اخترت النطاق {rng}. الآن اكتب رقم محدد من هذا النطاق!")

    async def process_number_guess(self, update: Update, guess: int, profile: Dict) -> str:
        user_id = update.effective_user.id
        game = self.active_games.get(user_id)
        if not game:
            return "ما في لعبة شغالة عندك."
        game["attempts"] += 1
        target = game["number"]
        if guess == target:
            duration = (datetime.now() - game["started_at"]).total_seconds() / 60
            score = max(100 - (game["attempts"] * 10), 10)
            self.conn.execute("INSERT INTO game_sessions (user_id, game_type, started_at, ended_at, result, score) VALUES (?, ?, ?, ?, ?, ?)",
                              (user_id, "حزر_الرقم", game["started_at"].isoformat(), datetime.now().isoformat(), "فوز", score))
            self.conn.commit()
            profile["games_played"] = profile.get("games_played", 0) + 1
            del self.active_games[user_id]
            return f"🎉 برافو! الرقم كان {target}. محاولات: {game['attempts']}. نقاط: {score} ⭐"
        if game["attempts"] >= game["max_attempts"]:
            del self.active_games[user_id]
            return f"💥 انتهت المحاولات! الرقم كان {target}. نلعب مرة ثانية؟"
        remaining = game["max_attempts"] - game["attempts"]
        hint = "📈 أكبر" if guess < target else "📉 أصغر"
        return f"{hint} من {guess}! باقي {remaining} محاولات."

    async def start_word_association_game(self, update: Update, profile: Dict):
        user_id = update.effective_user.id
        starter = random.choice(self.games["كلمة_وكلمة"]["word_chains"])
        self.active_games[user_id] = {"type": "كلمة_وكلمة", "current_word": starter, "chain": [starter], "started_at": datetime.now()}
        await update.message.reply_text(f"🔤 لعبة كلمة وكلمة! الكلمة الأولى: {starter}\nقول كلمة لها علاقة بها.")

    async def start_riddle_game(self, update: Update, profile: Dict):
        user_id = update.effective_user.id
        riddle = random.choice(self.riddles)
        self.active_games[user_id] = {"type": "لغز", "riddle": riddle, "attempts": 0, "started_at": datetime.now()}
        keyboard = [[InlineKeyboardButton("تلميح 💡", callback_data="riddle_hint")], [InlineKeyboardButton("استسلم 😅", callback_data="riddle_give_up")]]
        await update.message.reply_text(f"🧩 لغز:\n{riddle['question']}", reply_markup=InlineKeyboardMarkup(keyboard))

    async def process_word_association(self, update: Update, word: str, profile: Dict) -> str:
        user_id = update.effective_user.id
        game = self.active_games.get(user_id)
        if not game:
            return "ما في لعبة شغالة."
        word = word.strip().lower()
        game["chain"].append(word)
        game["current_word"] = word
        if len(game["chain"]) >= 10:
            chain = " → ".join(game["chain"])
            del self.active_games[user_id]
            return f"🎉 حلو! السلسلة: {chain}\nنلعب مرة ثانية؟"
        bot_word = self.get_associated_word(word)
        game["chain"].append(bot_word)
        game["current_word"] = bot_word
        return f"تمام '{word}'\nأنا أقول: {bot_word}\nإيش كلمة لها علاقة بـ '{bot_word}'؟"

    def get_associated_word(self, word: str) -> str:
        associations = {
            "بحر": ["سمك", "موج", "شاطئ"],
            "سمك": ["ماء", "صيد"],
            "شمس": ["نور", "ضوء"],
            "ليل": ["قمر", "نجوم"],
            "كتاب": ["قراءة", "مكتبة"]
        }
        return random.choice(associations.get(word, ["جميل", "حلو", "مفيد"]))

    async def process_riddle_answer(self, update: Update, answer: str, profile: Dict) -> str:
        user_id = update.effective_user.id
        game = self.active_games.get(user_id)
        if not game:
            return "ما في لغز شغال."
        riddle = game["riddle"]
        ans = answer.strip().lower()
        correct_answers = [a.lower() for a in riddle["answer"]]
        if any(c in ans for c in correct_answers):
            del self.active_games[user_id]
            profile["games_played"] = profile.get("games_played", 0) + 1
            return f"🎉 صح! الجواب: {riddle['answer'][0]}\nتبي لغز ثاني؟"
        game["attempts"] += 1
        if game["attempts"] >= 3:
            del self.active_games[user_id]
            return f"💭 الجواب كان: {riddle['answer'][0]}\nخلاص، نلعب مرة ثانية؟"
        return f"❌ مو صحيح! باقي {3 - game['attempts']} محاولات."

    # ---------------- DB helpers ----------------
    def get_user_profile(self, user_id: int) -> Optional[Dict]:
        cur = self.conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        row = cur.fetchone()
        if not row:
            return None
        return {
            "user_id": row[0], "username": row[1], "first_name": row[2],
            "messages_count": row[3], "dialect": row[4], "personality_type": row[5],
            "mood_happy": row[6], "mood_angry": row[7], "friendship_level": row[8],
            "energy_level": row[9], "trust_level": row[10], "favorite_time_period": row[11],
            "interests": json.loads(row[12]), "last_interaction": row[13],
            "first_met": row[14], "learned_words": json.loads(row[15]),
            "conversation_history": json.loads(row[16]), "achievements": json.loads(row[17]),
            "games_played": row[18], "total_jokes_told": row[19],
            "favorite_joke_category": row[20], "last_emotion_detected": row[21],
            "response_time_avg": row[22], "preferred_conversation_style": row[23]
        }

    def save_user_profile(self, profile: Dict) -> None:
        defaults = {
            "username": None, "first_name": None, "messages_count": 0,
            "dialect": "محايد", "personality_type": "unknown", "mood_happy": 0,
            "mood_angry": 0, "friendship_level": 3, "energy_level": 5,
            "trust_level": 3, "favorite_time_period": "مساء", "interests": [],
            "last_interaction": datetime.now().isoformat(), "first_met": datetime.now().isoformat(),
            "learned_words": [], "conversation_history": [], "achievements": [], "games_played": 0,
            "total_jokes_told": 0, "favorite_joke_category": "عامة", "last_emotion_detected": "محايد",
            "response_time_avg": 2.0, "preferred_conversation_style": "متوسط"
        }
        for k, v in defaults.items():
            profile.setdefault(k, v)
        self.conn.execute("""
            INSERT OR REPLACE INTO users VALUES 
            (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            profile["user_id"], profile["username"], profile["first_name"],
            profile["messages_count"], profile["dialect"], profile["personality_type"],
            profile["mood_happy"], profile["mood_angry"], profile["friendship_level"],
            profile["energy_level"], profile["trust_level"], profile["favorite_time_period"],
            json.dumps(profile["interests"]), profile["last_interaction"],
            profile["first_met"], json.dumps(profile["learned_words"]),
            json.dumps(profile["conversation_history"]), json.dumps(profile["achievements"]),
            profile["games_played"], profile["total_jokes_told"],
            profile["favorite_joke_category"], profile["last_emotion_detected"],
            profile["response_time_avg"], profile["preferred_conversation_style"]
        ))
        self.conn.commit()

    # ---------------- Main message logic ----------------
    async def handle_message_logic(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        try:
            if not update.message or not update.message.text:
                return
            user = update.effective_user
            user_id = user.id
            username = (user.username or "").lower() if user.username else None
            first_name = user.first_name or "مجهول"
            text = update.message.text.strip()
            chat_id = update.effective_chat.id

            profile = self.get_user_profile(user_id)
            if not profile:
                profile = {"user_id": user_id, "username": username, "first_name": first_name, "messages_count": 0, "first_met": datetime.now().isoformat()}

            profile["messages_count"] = profile.get("messages_count", 0) + 1
            profile["last_interaction"] = datetime.now().isoformat()

            # learn
            self.learn_from_message(profile, text)

            # handle games interaction
            if user_id in self.active_games:
                game_resp = await self.handle_active_game(update, profile, text)
                if game_resp:
                    self.save_user_profile(profile)
                    await update.message.reply_text(game_resp)
                    return

            # ignore if angry
            if profile.get("mood_angry", 0) >= 4:
                await update.message.reply_text(random.choice(["...", "*صامت*", "مو راضي أكلمك الآن"]))
                self.save_user_profile(profile)
                return

            # typing
            await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
            await asyncio.sleep(random.uniform(1.0, 3.0))

            reply = await self.generate_enhanced_response(text, profile)

            # subtle special user touch
            if self.is_special_user(username, first_name) and random.random() < 0.25:
                touch = random.choice(["عيوني", "حبيبي", "عزيزي"])
                reply = f"{touch} {reply}"

            self.save_user_profile(profile)
            await update.message.reply_text(reply)

        except Exception:
            logger.exception("Error in handle_message_logic")
            await update.message.reply_text("عذراً، حدث خطأ تقني 😅")

    # hook helper to process active games
    async def handle_active_game(self, update: Update, profile: Dict, text: str) -> Optional[str]:
        user_id = update.effective_user.id
        game = self.active_games.get(user_id)
        if not game:
            return None
        if game["type"] == "حزر_الرقم":
            try:
                guess = int(text)
                return await self.process_number_guess(update, guess, profile)
            except ValueError:
                return "اكتب رقم صحيح من فضلك!"
        if game["type"] == "كلمة_وكلمة":
            return await self.process_word_association(update, text, profile)
        if game["type"] == "لغز":
            return await self.process_riddle_answer(update, text, profile)
        return None


# ---------------- Commands (outside class) ----------------

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    first_name = user.first_name or "صديق"
    current_persona = bot.get_current_personality()
    greeting = current_persona["greeting"]
    welcome_text = f"{greeting}\nأنا جوهان، البوت الذكي 🤖\nكلمني عن أي شي!"
    await update.message.reply_text(welcome_text)

async def mood_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    profile = bot.get_user_profile(user_id)
    if not profile:
        await update.message.reply_text("ما نتعرف بعد! كلمني شوي عشان أعرفك 😅")
        return
    current_persona = bot.get_current_personality()
    mood_text = (
        f"📊 حالة العلاقة مع {profile.get('first_name', 'صديق')}:\n\n"
        f"🤖 شخصية: {current_persona['name']}\n"
        f"😊 السعادة: {profile.get('mood_happy',0)}/5\n"
        f"😠 الغضب: {profile.get('mood_angry',0)}/5\n"
        f"🤝 مستوى الصداقة: {profile.get('friendship_level',3)}/10\n"
        f"💬 رسائلك: {profile.get('messages_count',0)}\n"
        f"🗣 لهجتك: {profile.get('dialect','محايد')}"
    )
    await update.message.reply_text(mood_text)

async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    profile = bot.get_user_profile(user_id)
    if not profile:
        await update.message.reply_text("ما عندي ملف لك بعد.")
        return
    profile["mood_happy"] = 0
    profile["mood_angry"] = 0
    profile["friendship_level"] = 3
    bot.save_user_profile(profile)
    await update.message.reply_text(random.choice(["طيب.. صفحة جديدة 😊", "ماشي، ننسى ونبدأ من جديد ❤️"]))

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if user_id not in bot.admin_ids:
        await update.message.reply_text("هذا الأمر للأدمن فقط.")
        return
    cur = bot.conn.execute("SELECT COUNT(*) FROM users")
    users_count = cur.fetchone()[0]
    cur = bot.conn.execute("SELECT SUM(messages_count) FROM users")
    total_msgs = cur.fetchone()[0] or 0
    await update.message.reply_text(f"👥 مستخدمين: {users_count}\n💬 إجمالي الرسائل: {total_msgs}")

# ---------------- Run ----------------
if __name__ == "__main__":
    if TELEGRAM_TOKEN == "YOUR_TELEGRAM_BOT_TOKEN" or OPENAI_API_KEY == "YOUR_OPENAI_API_KEY":
        print("⚠️ ضع التوكنات في الكود قبل التشغيل (TELEGRAM_TOKEN, OPENAI_API_KEY)")
        raise SystemExit(1)

    bot = AdvancedJohanBot(TELEGRAM_TOKEN, OPENAI_API_KEY, admin_ids=ADMIN_IDS)

    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("mood", mood_command))
    app.add_handler(CommandHandler("reset", reset_command))
    app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(CallbackQueryHandler(bot.handle_game_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, bot.handle_message_logic))

    print("🚀 Johan (Advanced) يعمل الآن...")
    app.run_polling(drop_pending_updates=True)
