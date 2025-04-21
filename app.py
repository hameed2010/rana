import json
import logging
import os
import time
import datetime
import calendar
import subprocess
import sys

from keep_alive import keep_alive
keep_alive()
from typing import Dict, List, Set, Tuple, Any

from telegram.ext import (
    Updater, CommandHandler, CallbackQueryHandler, 
    ConversationHandler, MessageHandler, Filters, CallbackContext
)
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Get token from environment variables
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '8052506477:AAE6YccFnn6-5PyU314H1gi6lmXiKeJlN7c')

# Admin chat ID - replace with the actual admin's chat ID
ADMIN_CHAT_ID = int(os.getenv('ADMIN_CHAT_ID', '821681748'))

# Conversation states
ASKING_QUESTIONS, FINISHED, START_CONFIRMATION, ADMIN_PANEL, EDIT_DESCRIPTION, VIEW_HISTORY, VIEW_MAJOR_INFO = range(7)

# Data file
DATA_FILE = "bot_data.json"

# التخصصات الأساسية مع نقاطها الافتراضية
majors = {
    # تخصصات الحاسوب والتقنية
    "تكنولوجيا معلومات": 0, "نظم معلومات": 0, "علوم الحاسوب": 0, "أمن سيبراني": 0, "جرافكس": 0,
    
    # تخصصات الهندسة
    "هندسة مدنية": 0, "هندسة كهربائية": 0, "هندسة ميكانيكية": 0, "هندسة معمارية": 0, "ميكاترونكس": 0, "هندسة طبية وحيوية": 0,
    
    # تخصصات الصحة
    "طب وجراحة": 0, "مختبرات": 0, "تمريض": 0, "تخدير": 0, "تغذية علاجية": 0, "الاشعة": 0, "علاج طبيعي": 0,
    "طب اسنان": 0, "فني اسنان": 0, "صيدلة": 0,
    
    # تخصصات الأعمال
    "تجارة واقتصاد": 0,
    
    # تخصصات الإنسانيات والاجتماع
    "علم النفس": 0, "ترجمة": 0,
    
    # تخصصات التربية
    "تربية قرآن": 0, "تربية اسلامية": 0, "تربية رياضيات": 0, "تربية عربي": 0, "تربية علوم": 0,
    "تربية اجتماعيات": 0, "تربية فيزياء": 0, "تربية كيمياء": 0, "تربية احياء": 0, "تربية انجليزي": 0
}

# قائمة الأسئلة مع الخيارات والنقاط لكل تخصص (30 سؤال)
questions = [
    # أسئلة عن التخصصات الهندسية (7 أسئلة)
    ("أي فرع من الهندسة يثير اهتمامك أكثر؟",
     ["هندسة الكمبيوتر والشبكات", "الهندسة الإنشائية والمباني", "هندسة الطاقة والكهرباء", "هندسة الآلات والمعدات"],
     [{"تكنولوجيا معلومات": 3, "نظم معلومات": 3, "أمن سيبراني": 2}, {"هندسة مدنية": 3, "هندسة معمارية": 3}, {"هندسة كهربائية": 3, "هندسة طبية وحيوية": 2}, {"هندسة ميكانيكية": 3, "ميكاترونكس": 3}]),
    
    ("عند التفكير في مشروع هندسي، ما الذي يجذبك أكثر؟",
     ["تصميم بنية تحتية أو مباني", "تطوير أنظمة وبرامج حاسوبية", "تصميم آلات وأجهزة", "حل مشكلات بيئية أو طبية"],
     [{"هندسة مدنية": 3, "هندسة معمارية": 3}, {"تكنولوجيا معلومات": 3, "نظم معلومات": 3, "علوم الحاسوب": 2}, {"هندسة ميكانيكية": 3, "ميكاترونكس": 3}, {"هندسة طبية وحيوية": 3}]),
    
    ("ما هو النشاط الذي تستمتع به أكثر؟",
     ["بناء النماذج والأشكال ثلاثية الأبعاد", "تحليل البيانات وحل المسائل الرياضية", "تفكيك الأجهزة وإعادة تركيبها", "التصميم والرسم الهندسي"],
     [{"هندسة مدنية": 3, "هندسة معمارية": 2}, {"نظم معلومات": 3, "تكنولوجيا معلومات": 2}, {"هندسة ميكانيكية": 3, "ميكاترونكس": 3}, {"هندسة معمارية": 3, "جرافكس": 2}]),
    
    ("كيف تتعامل مع مشكلة تقنية في جهازك؟",
     ["أفتح الجهاز وأعالج المشكلة بنفسي", "أبحث عن الحل عبر الإنترنت", "أستعين بخبير", "أشتري جهازاً جديداً"],
     [{"هندسة كهربائية": 3, "ميكاترونكس": 3}, {"تكنولوجيا معلومات": 3, "أمن سيبراني": 3, "نظم معلومات": 2}, {"هندسة طبية وحيوية": 2}, {"تجارة واقتصاد": 2}]),
    
    ("ما هو المكان المفضل للعمل بالنسبة لك؟",
     ["في موقع إنشائي أو ميداني", "في مكتب هندسي أو استشاري", "في مختبر أو معمل", "في شركة تقنية أو برمجة"],
     [{"هندسة مدنية": 3}, {"هندسة معمارية": 3}, {"هندسة ميكانيكية": 3, "هندسة طبية وحيوية": 3}, {"تكنولوجيا معلومات": 3, "نظم معلومات": 3, "علوم الحاسوب": 3}]),
    

    
    ("ما هو المشروع الذي تحلم بإنجازه؟",
     ["تصميم وبناء مبنى أو جسر متميز", "تطوير نظام حاسوبي أو تطبيق ذكي", "اختراع جهاز أو آلة مبتكرة", "المساهمة في تطوير تقنيات طبية"],
     [{"هندسة مدنية": 3, "هندسة معمارية": 3}, {"تكنولوجيا معلومات": 3, "نظم معلومات": 3, "أمن سيبراني": 3, "علوم الحاسوب": 3}, {"هندسة ميكانيكية": 3, "ميكاترونكس": 3}, {"هندسة طبية وحيوية": 3}]),

    # أسئلة عن تخصصات العلوم الصحية (7 أسئلة)
    ("أي مجال في الرعاية الصحية يثير اهتمامك أكثر؟",
     ["تشخيص وعلاج المرضى مباشرة", "إجراء التحاليل والفحوصات المخبرية", "تقديم الرعاية التمريضية", "المساعدة في العمليات الجراحية"],
     [{"طب وجراحة": 3, "طب اسنان": 3}, {"مختبرات": 3, "الاشعة": 2}, {"تمريض": 3, "تغذية علاجية": 2}, {"تخدير": 3, "علاج طبيعي": 2}]),
    
    ("ما النشاط الذي تستمتع به أكثر؟",
     ["التفاعل والتواصل مع المرضى", "التعامل مع الأجهزة والتقنيات الطبية", "تحليل العينات والبيانات", "تحضير وتركيب الأدوية"],
     [{"طب وجراحة": 3, "تمريض": 3}, {"الاشعة": 3, "تخدير": 3}, {"مختبرات": 3}, {"صيدلة": 3, "فني اسنان": 2}]),
    
    ("ما هي المادة الدراسية التي تفضلها أكثر؟",
     ["التشريح وعلم وظائف الأعضاء", "الكيمياء الحيوية", "علم الأحياء الدقيقة", "الفيزياء الطبية"],
     [{"طب وجراحة": 3, "طب اسنان": 3}, {"صيدلة": 3, "تغذية علاجية": 3}, {"مختبرات": 3}, {"الاشعة": 3, "تخدير": 2}]),
    
    ("كيف تتعامل مع المواقف الطارئة أو الضغط النفسي؟",
     ["أبقى هادئاً وأتخذ قرارات سريعة", "أتبع البروتوكولات والإجراءات المعتمدة بدقة", "أطلب المساعدة والتوجيه عند الحاجة", "أشعر بالتوتر ويصعب علي التركيز"],
     [{"طب وجراحة": 3, "تخدير": 3}, {"تمريض": 3, "مختبرات": 2}, {"صيدلة": 2, "فني اسنان": 2}, {}]),
    
    ("ما الذي يجذبك أكثر في المجال الصحي؟",
     ["إنقاذ حياة الناس وعلاجهم", "اكتشاف طرق تشخيصية جديدة", "تقديم الرعاية والدعم للمرضى", "تطوير وتركيب الأدوية"],
     [{"طب وجراحة": 3, "طب اسنان": 3}, {"مختبرات": 3, "الاشعة": 3}, {"تمريض": 3, "علاج طبيعي": 3}, {"صيدلة": 3}]),
    

    
    ("ما هو التحدي الصحي الذي تهتم به أكثر؟",
     ["مكافحة الأمراض المزمنة", "تطوير طرق التشخيص المبكر", "تحسين جودة حياة المرضى", "تطوير أدوية وعلاجات جديدة"],
     [{"طب وجراحة": 3}, {"الاشعة": 3, "مختبرات": 3}, {"تمريض": 3, "علاج طبيعي": 3, "تغذية علاجية": 3}, {"صيدلة": 3}]),

    # أسئلة عن تخصصات الكمبيوتر والتقنية (7 أسئلة)
    ("أي مجال في تقنية المعلومات تفضل العمل به؟",
     ["تطوير البرمجيات والتطبيقات", "إدارة الشبكات وقواعد البيانات", "أمن المعلومات وحماية البيانات", "تصميم الجرافيك والواجهات"],
     [{"علوم الحاسوب": 3, "تكنولوجيا معلومات": 2}, {"نظم معلومات": 3, "تكنولوجيا معلومات": 2}, {"أمن سيبراني": 3}, {"جرافكس": 3}]),
    
    ("ما هي المهارة التي تستمتع بتطويرها أكثر؟",
     ["كتابة الأكواد البرمجية", "تحليل البيانات والمعلومات", "اختبار واكتشاف الثغرات الأمنية", "التصميم الرقمي والإبداعي"],
     [{"علوم الحاسوب": 3, "تكنولوجيا معلومات": 2}, {"نظم معلومات": 3}, {"أمن سيبراني": 3}, {"جرافكس": 3}]),
    
    ("ما هو المشروع التقني الذي تحلم بإنجازه؟",
     ["تطوير برمجية أو تطبيق مبتكر", "تصميم نظام معلومات متكامل", "إنشاء نظام حماية متطور", "تصميم موقع أو واجهة مستخدم مميزة"],
     [{"علوم الحاسوب": 3, "تكنولوجيا معلومات": 3}, {"نظم معلومات": 3}, {"أمن سيبراني": 3}, {"جرافكس": 3}]),
    
    ("ما هو دورك المفضل في فريق تقني؟",
     ["مطور ومبرمج", "محلل نظم ومدير مشروع", "خبير أمن معلومات", "مصمم ومبدع بصري"],
     [{"علوم الحاسوب": 3, "تكنولوجيا معلومات": 2}, {"نظم معلومات": 3}, {"أمن سيبراني": 3}, {"جرافكس": 3}]),
    

    
    ("ما هو مجال التقنية الذي ترى أنه أكثر أهمية للمستقبل؟",
     ["تطوير البرمجيات والذكاء الاصطناعي", "أنظمة المعلومات والبيانات الضخمة", "الأمن السيبراني", "التصميم الرقمي والواقع الافتراضي"],
     [{"علوم الحاسوب": 3, "تكنولوجيا معلومات": 2}, {"نظم معلومات": 3}, {"أمن سيبراني": 3}, {"جرافكس": 3}]),
    
    ("كيف ترى تأثير التكنولوجيا على المجتمع؟",
     ["أداة لتطوير البرمجيات والمنتجات", "وسيلة لتحسين إدارة المعلومات", "تحدٍ أمني يحتاج للحماية", "وسيلة للإبداع والتعبير الفني"],
     [{"علوم الحاسوب": 3, "تكنولوجيا معلومات": 2}, {"نظم معلومات": 3}, {"أمن سيبراني": 3}, {"جرافكس": 3}]),

    # أسئلة عن التخصصات الاقتصادية والتجارية (4 أسئلة)
    ("ما المجال الذي يثير اهتمامك في عالم الأعمال؟",
     ["التجارة والاقتصاد", "إدارة الأعمال والمشاريع", "التسويق والمبيعات", "المحاسبة والتمويل"],
     [{"تجارة واقتصاد": 3}, {"تجارة واقتصاد": 2}, {"تجارة واقتصاد": 2}, {"تجارة واقتصاد": 2}]),
    
    ("كيف ترى نفسك في عالم المال والأعمال؟",
     ["محلل اقتصادي ومستشار", "مدير أعمال ناجح", "مسوق ومروج للمنتجات", "خبير مالي ومحاسب"],
     [{"تجارة واقتصاد": 3}, {"تجارة واقتصاد": 2}, {"تجارة واقتصاد": 2}, {"تجارة واقتصاد": 2}]),
    
    ("ما هو هدفك من دراسة التجارة والاقتصاد؟",
     ["فهم النظم الاقتصادية والأسواق العالمية", "إدارة شركة أو مشروع خاص", "تطوير استراتيجيات تسويقية", "إدارة الشؤون المالية والمحاسبية"],
     [{"تجارة واقتصاد": 3}, {"تجارة واقتصاد": 2}, {"تجارة واقتصاد": 2}, {"تجارة واقتصاد": 2}]),
    
    ("ما رأيك في الاستثمار والأسواق المالية؟",
     ["موضوع مهم لفهم الاقتصاد العالمي", "وسيلة لنمو وتطوير الأعمال", "فرصة لتحقيق أرباح وعوائد", "مجال يحتاج للدراسة والتخصص"],
     [{"تجارة واقتصاد": 3}, {"تجارة واقتصاد": 2}, {"تجارة واقتصاد": 2}, {"تجارة واقتصاد": 2}]),

    # أسئلة عن تخصصات العلوم الإنسانية (4 أسئلة)
    ("ما المجال الإنساني الذي يجذبك أكثر؟",
     ["علم النفس وفهم السلوك البشري", "الترجمة واللغات", "علم الاجتماع والثقافات", "الفلسفة والمنطق"],
     [{"علم النفس": 3}, {"ترجمة": 3}, {"علم النفس": 2, "ترجمة": 2}, {"ترجمة": 2, "علم النفس": 2}]),
    
    ("ما نوع الكتب التي تميل لقراءتها؟",
     ["كتب علم النفس والتنمية البشرية", "كتب اللغات والأدب المترجم", "كتب اجتماعية وثقافية", "كتب فلسفية وفكرية"],
     [{"علم النفس": 3}, {"ترجمة": 3}, {"ترجمة": 2, "علم النفس": 2}, {"علم النفس": 2}]),
    
    ("كيف تفضل مساعدة الآخرين؟",
     ["فهم مشاكلهم النفسية وتقديم الاستشارة", "مساعدتهم في التواصل وفهم لغات أخرى", "تحليل الظواهر الاجتماعية وتأثيراتها", "مناقشة القضايا الفكرية والفلسفية"],
     [{"علم النفس": 3}, {"ترجمة": 3}, {"علم النفس": 2}, {"ترجمة": 2}]),
    
    ("ما المهارة التي تهتم بتطويرها أكثر؟",
     ["التحليل النفسي والإرشاد", "إتقان اللغات والترجمة", "دراسة المجتمعات وفهمها", "التفكير النقدي والمنطقي"],
     [{"علم النفس": 3}, {"ترجمة": 3}, {"علم النفس": 2}, {"ترجمة": 2}]),

    # أسئلة عن تخصصات التربية/التعليم (4 أسئلة)
    ("أي مجال في التربية والتعليم تفضله؟",
     ["تدريس العلوم الدينية (القرآن والتربية الإسلامية)", "تدريس الرياضيات والعلوم", "تدريس اللغات (عربي/انجليزي)", "تدريس المواد الاجتماعية"],
     [{"تربية قرآن": 3, "تربية اسلامية": 3}, {"تربية رياضيات": 3, "تربية فيزياء": 3, "تربية كيمياء": 3, "تربية احياء": 3, "تربية علوم": 3}, {"تربية عربي": 3, "تربية انجليزي": 3}, {"تربية اجتماعيات": 3}]),
    

    
    ("ما هو أسلوب التدريس المفضل لديك؟",
     ["التدريس التقليدي والشرح المباشر", "استخدام التجارب والأنشطة العملية", "اعتماد التكنولوجيا والوسائل التعليمية", "التعلم التعاوني والنقاش"],
     [{"تربية قرآن": 3, "تربية اسلامية": 2}, {"تربية فيزياء": 3, "تربية كيمياء": 3, "تربية احياء": 3, "تربية علوم": 3}, {"تربية انجليزي": 3, "تربية رياضيات": 2}, {"تربية اجتماعيات": 3, "تربية عربي": 2}]),
    
    ("ما المادة التي كنت تتفوق فيها في المدرسة؟",
     ["التربية الإسلامية والقرآن", "الرياضيات والعلوم", "اللغات (عربي/انجليزي)", "الاجتماعيات والتاريخ"],
     [{"تربية قرآن": 3, "تربية اسلامية": 3}, {"تربية رياضيات": 3, "تربية فيزياء": 3, "تربية كيمياء": 3, "تربية احياء": 3, "تربية علوم": 3}, {"تربية عربي": 3, "تربية انجليزي": 3}, {"تربية اجتماعيات": 3}]),
    

    
    ("ما هو هدفك من التدريس؟",
     ["تعزيز القيم الدينية والأخلاقية", "تنمية التفكير العلمي والرياضي", "تطوير مهارات اللغة والتواصل", "فهم القضايا الاجتماعية والتاريخية"],
     [{"تربية قرآن": 3, "تربية اسلامية": 3}, {"تربية رياضيات": 3, "تربية فيزياء": 3, "تربية كيمياء": 3, "تربية احياء": 3, "تربية علوم": 3}, {"تربية عربي": 3, "تربية انجليزي": 3}, {"تربية اجتماعيات": 3}]),
]

# متغيرات عالمية
message_ids: Dict[int, List[int]] = {}  # تخزين معرفات الرسائل لكل مستخدم
current_question_index: Dict[int, int] = {}  # مؤشر السؤال الحالي لكل مستخدم
user_scores: Dict[int, Dict[str, int]] = {}  # نقاط المستخدم لكل تخصص
users: Set[int] = set()  # مجموعة لتتبع المستخدمين الفريدين


def load_data() -> Dict[str, Any]:
    """تحميل البيانات من ملف JSON"""
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        # إنشاء بيانات افتراضية إذا لم يكن الملف موجوداً
        default_data = {
            "description": "مرحبًا بك في اختبار تحديد التخصص! 🧐\nاختر إجاباتك باستخدام الأزرار أدناه.\n"
                           "هذا الاختبار سيساعدك على اكتشاف التخصص الدراسي المناسب لشخصيتك وميولك. 🎓✨"
        }
        save_data(default_data)
        return default_data


def save_data(data: Dict[str, Any]) -> None:
    """حفظ البيانات إلى ملف JSON"""
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


# دالة لتحديث الإحصائيات
def update_statistics(stat_type: str, data: Dict[str, Any] = None) -> None:
    """تحديث إحصائيات البوت
    
    الأنواع المدعومة:
    - new_user: تسجيل مستخدم جديد
    - complete_quiz: اكتمال اختبار
    - abandon_quiz: إلغاء اختبار
    - restart_quiz: إعادة تشغيل اختبار
    - question_answer: الإجابة على سؤال (data: {"question_index": int, "choice": int})
    - major_result: نتيجة التخصص (data: {"major": str})
    """
    # تحميل البيانات
    bot_data = load_data()
    current_date = time.strftime("%Y-%m-%d")
    
    # التأكد من وجود قسم الإحصائيات
    if "statistics" not in bot_data:
        bot_data["statistics"] = {
            "total_users": 0,
            "completed_quizzes": 0,
            "abandoned_quizzes": 0,
            "restart_count": 0,
            "major_results": {},
            "question_stats": {},
            "daily_usage": {},
            "user_data": {}
        }
    
    stats = bot_data["statistics"]
    
    # تحديث الإحصائيات اليومية
    if current_date not in stats["daily_usage"]:
        stats["daily_usage"][current_date] = {
            "new_users": 0,
            "completed_quizzes": 0,
            "abandoned_quizzes": 0,
            "restart_count": 0
        }
    
    # تحديث الإحصائيات حسب النوع
    if stat_type == "new_user":
        stats["total_users"] += 1
        stats["daily_usage"][current_date]["new_users"] += 1
    
    elif stat_type == "complete_quiz":
        stats["completed_quizzes"] += 1
        stats["daily_usage"][current_date]["completed_quizzes"] += 1
    
    elif stat_type == "abandon_quiz":
        stats["abandoned_quizzes"] += 1
        stats["daily_usage"][current_date]["abandoned_quizzes"] += 1
    
    elif stat_type == "restart_quiz":
        stats["restart_count"] += 1
        stats["daily_usage"][current_date]["restart_count"] += 1
    
    elif stat_type == "question_answer" and data:
        q_index = str(data.get("question_index", "0"))
        choice = str(data.get("choice", "0"))
        
        # تهيئة إحصائيات السؤال إذا لم تكن موجودة
        if "question_stats" not in stats:
            stats["question_stats"] = {}
            
        if q_index not in stats["question_stats"]:
            stats["question_stats"][q_index] = {}
        
        if choice not in stats["question_stats"][q_index]:
            stats["question_stats"][q_index][choice] = 0
        
        stats["question_stats"][q_index][choice] += 1
    
    elif stat_type == "major_result" and data:
        major = data.get("major", "")
        
        if major:
            if "major_results" not in stats:
                stats["major_results"] = {}
                
            if major not in stats["major_results"]:
                stats["major_results"][major] = 0
            
            stats["major_results"][major] += 1
    
    # تحديث بيانات المستخدم إذا تم توفير معرف المستخدم
    if data and "user_id" in data:
        user_id = str(data["user_id"])
        
        if "user_data" not in stats:
            stats["user_data"] = {}
            
        if user_id not in stats["user_data"]:
            stats["user_data"][user_id] = {
                "quiz_count": 0,
                "completed_quizzes": 0,
                "abandoned_quizzes": 0,
                "last_active": current_date,
                "results": []
            }
        
        # تحديث تاريخ النشاط الأخير
        stats["user_data"][user_id]["last_active"] = current_date
        
        # تحديث عداد الاختبارات حسب النوع
        if stat_type == "complete_quiz":
            stats["user_data"][user_id]["completed_quizzes"] += 1
            stats["user_data"][user_id]["quiz_count"] += 1
            
            # تسجيل نتيجة الاختبار إذا تم توفيرها
            if "result" in data:
                stats["user_data"][user_id]["results"].append({
                    "date": current_date,
                    "major": data["result"],
                    "score": data.get("score", 0)
                })
        
        elif stat_type == "abandon_quiz":
            stats["user_data"][user_id]["abandoned_quizzes"] += 1
    
    # حفظ البيانات المحدثة
    save_data(bot_data)

# تحميل البيانات عند بدء التشغيل
bot_data = load_data()


def start(update: Update, context: CallbackContext) -> int:
    """بدء المحادثة مع المستخدم"""
    user_id = update.effective_user.id
    
    # تحديد ما إذا كان الاستدعاء من message أو callback query
    from_callback = update.callback_query is not None
    
    # تحقق ما إذا كان المستخدم جديدًا
    is_new_user = user_id not in users
    users.add(user_id)  # إضافة المستخدم إلى قائمة المستخدمين
    
    # تحديث إحصائيات المستخدمين الجدد
    if is_new_user:
        update_statistics("new_user", {"user_id": user_id})

    # مسح الرسائل السابقة إن وجدت
    if not from_callback:
        # إذا كان الاستدعاء من رسالة
        cleaning_msg = update.message.reply_text("⏳ جاري مسح المحادثات السابقة...")
    else:
        # إذا كان الاستدعاء من callback query
        cleaning_msg = context.bot.send_message(chat_id=user_id, text="⏳ جاري مسح المحادثات السابقة...")

    if user_id in message_ids:
        for msg_id in message_ids[user_id]:
            try:
                context.bot.delete_message(chat_id=user_id, message_id=msg_id)
            except Exception as e:
                logger.error(f"Error deleting message: {e}")
        message_ids[user_id] = []

    time.sleep(1)
    try:
        context.bot.delete_message(chat_id=user_id, message_id=cleaning_msg.message_id)
    except Exception as e:
        logger.error(f"Error deleting cleaning message: {e}")

    # إعداد بيانات المستخدم
    current_question_index[user_id] = 0
    user_scores[user_id] = {major: 0 for major in majors}
    
    if user_id not in message_ids:
        message_ids[user_id] = []

    # إرسال رسالة الترحيب مع تنسيق جذاب وإبداعي
    welcome_text = "╭━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╮\n"
    welcome_text += "┃   🎓 *دليلك نحو مستقبلك الأكاديمي*   🎓   ┃\n"
    welcome_text += "╰━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╯\n\n"
    welcome_text += "✨✨ *أهلاً بك في اختبار تحديد التخصص الجامعي* ✨✨\n\n"
    welcome_text += "┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓\n"
    welcome_text += f"┃ {bot_data['description']} ┃\n"
    welcome_text += "┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛\n\n"
    
    welcome_text += "🌟 *رحلتك تبدأ هنا* 🌟\n\n"
    
    welcome_text += "📚 *مع هذا الاختبار ستتمكن من:*\n"
    welcome_text += "┌───────────────────────────────────┐\n"
    welcome_text += "│ ✅ اكتشاف التخصص المناسب لشخصيتك │\n"
    welcome_text += "│ ✅ معرفة مجالات تميزك الدراسية     │\n"
    welcome_text += "│ ✅ الاطلاع على سجل اختباراتك        │\n"
    welcome_text += "│ ✅ مقارنة نتائجك بمحاولات سابقة    │\n"
    welcome_text += "└───────────────────────────────────┘\n\n"
    
    welcome_text += "🔍 *تعليمات الاختبار:*\n"
    welcome_text += "╔════════════════════════════════════╗\n"
    welcome_text += "║ • ستجيب على 30 سؤال متنوع         ║\n"
    welcome_text += "║ • كل إجابة ترسم ملامح مستقبلك     ║\n"
    welcome_text += "║ • أجب بصدق للحصول على أدق النتائج ║\n"
    welcome_text += "║ • ستحصل على توصيات تناسب شخصيتك  ║\n"
    welcome_text += "╚════════════════════════════════════╝\n"
    
    # إرسال الرسالة بالطريقة المناسبة
    if not from_callback:
        welcome_msg = update.message.reply_text(
            welcome_text,
            parse_mode="Markdown"
        )
    else:
        welcome_msg = context.bot.send_message(
            chat_id=user_id,
            text=welcome_text,
            parse_mode="Markdown"
        )
    message_ids[user_id].append(welcome_msg.message_id)

    # سؤال المستخدم عن رغبته في البدء بتصميم جذاب
    keyboard = [
        [
            InlineKeyboardButton("✅ نعم، أنا جاهز!", callback_data="yes")
        ],
        [
            InlineKeyboardButton("ℹ️ مشاهدة التخصصات المتاحة", callback_data="info")
        ],
        [
            InlineKeyboardButton("⏱️ في وقت لاحق", callback_data="no")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # رسالة محفزة للبدء مع تنسيق جميل
    start_prompt = "┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓\n"
    start_prompt += "┃   🚀 *جاهز لاكتشاف مستقبلك؟*  🚀   ┃\n"
    start_prompt += "┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛\n\n"
    start_prompt += "👋 *مرحباً بك في رحلة اكتشاف ذاتك الأكاديمية!*\n\n"
    start_prompt += "💫 هذا الاختبار صُمم خصيصاً لمساعدتك في تحديد مسارك الدراسي الأمثل الذي يتوافق مع شخصيتك وميولك واهتماماتك.\n\n"
    start_prompt += "⏱️ مدة الاختبار: 5-10 دقائق فقط\n"
    start_prompt += "✨ النتيجة: تحديد أفضل 3 تخصصات تناسبك\n\n"
    start_prompt += "👇 *اختر من الخيارات أدناه:*"
    
    # إرسال رسالة التأكيد بالطريقة المناسبة
    if not from_callback:
        confirm_msg = update.message.reply_text(
            start_prompt,
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
    else:
        confirm_msg = context.bot.send_message(
            chat_id=user_id,
            text=start_prompt,
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
    message_ids[user_id].append(confirm_msg.message_id)
    return START_CONFIRMATION


def handle_confirmation(update: Update, context: CallbackContext) -> int:
    """معالجة اختيار المستخدم للبدء أو التأجيل"""
    query = update.callback_query
    try:
        query.answer()
    except Exception as e:
        logger.warning(f"لم نتمكن من الرد على استدعاء الزر: {e}")
        # نستمر في تنفيذ الوظيفة حتى لو فشل الرد على الاستدعاء
    
    user_id = query.from_user.id

    if query.data == "yes":
        # حذف رسالة التأكيد
        try:
            context.bot.delete_message(chat_id=user_id, message_id=query.message.message_id)
        except Exception as e:
            logger.error(f"Error deleting message: {e}")
        
        # إرسال رسالة بدء الاختبار
        start_msg = context.bot.send_message(
            chat_id=user_id,
            text="🚀 رائع! لنبدأ الاختبار الآن. اختر إجاباتك باستخدام الأزرار أدناه."
        )
        message_ids[user_id].append(start_msg.message_id)
        return ask_next_question(update, context)
    elif query.data == "info":
        # عرض معلومات عن الاختبار وإظهار كل التخصصات المتاحة
        return show_all_majors(update, context)
    elif query.data == "back_to_welcome":
        # العودة إلى رسالة الترحيب الرئيسية (بعد عرض قائمة التخصصات)
        # حذف الرسالة الحالية
        try:
            context.bot.delete_message(chat_id=user_id, message_id=query.message.message_id)
        except Exception as e:
            logger.error(f"Error deleting message: {e}")
        
        # إعادة إرسال رسالة الترحيب مع أزرار الاختيار
        return start(update, context)
    else:
        # حذف رسالة التأكيد
        try:
            context.bot.delete_message(chat_id=user_id, message_id=query.message.message_id)
        except Exception as e:
            logger.error(f"Error deleting message: {e}")
        
        # إرسال رسالة وداع
        goodbye_msg = context.bot.send_message(
            chat_id=user_id,
            text="🌟 لا مشكلة، خذ وقتك! سأكون هنا في انتظارك لنبدأ مغامرة اكتشاف شغفك متى ما كنت جاهزًا. إلى اللقاء! 😊"
        )
        message_ids[user_id].append(goodbye_msg.message_id)
        return ConversationHandler.END


def show_all_majors(update: Update, context: CallbackContext) -> int:
    """عرض جميع التخصصات المتاحة في البوت"""
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    
    # تنظيم التخصصات في مجموعات
    major_categories = {
        "💻 تخصصات الحاسوب والتقنية": [],
        "🔧 تخصصات الهندسة": [],
        "🔬 تخصصات العلوم": [],
        "🏥 تخصصات الصحة": [],
        "📚 تخصصات الإنسانيات والاجتماع": [],
        "💼 تخصصات الأعمال والقانون": [],
        "🎨 تخصصات الفنون والتصميم": [],
        "🌱 تخصصات الزراعة والبيئة": []
    }
    
    # تصنيف التخصصات حسب الأقسام
    for major in majors.keys():
        if major in ["هندسة البرمجيات", "علوم الحاسب", "الذكاء الاصطناعي", "تقنية معلومات", "أمن سيبراني", "تطوير الألعاب",
                   "علم البيانات", "هندسة الشبكات", "الحوسبة السحابية", "التجارة الإلكترونية"]:
            major_categories["💻 تخصصات الحاسوب والتقنية"].append(major)
        
        elif major in ["الهندسة المعمارية", "الهندسة الميكانيكية", "الهندسة المدنية", "الهندسة الكهربائية", "ميكاترونكس",
                     "الهندسة النووية", "هندسة الطيران", "هندسة الفضاء", "الهندسة الطبية", "الهندسة الكيميائية"]:
            major_categories["🔧 تخصصات الهندسة"].append(major)
        
        elif major in ["الرياضيات", "الفيزياء", "الأحياء", "الكيمياء", "علم البيئة",
                      "العلوم البحرية", "الجيولوجيا", "الأرصاد الجوية", "الفلك", "علم الأعصاب"]:
            major_categories["🔬 تخصصات العلوم"].append(major)
        
        elif major in ["طب بشري", "طب أسنان", "صيدلة", "تمريض", "مختبرات", "طب بيطري",
                      "الطب النفسي", "العلاج الطبيعي", "التغذية", "الصحة العامة", "الطب البديل"]:
            major_categories["🏥 تخصصات الصحة"].append(major)
        
        elif major in ["علم النفس", "الفلسفة", "التربية", "علم الاجتماع", "الأدب والفنون", "الترجمة",
                      "علم الإنسان", "علم الآثار", "الاتصال الجماهيري", "العلوم السياسية", "العلاقات الدولية"]:
            major_categories["📚 تخصصات الإنسانيات والاجتماع"].append(major)
        
        elif major in ["إدارة الأعمال", "الاقتصاد", "التسويق", "حقوق", "تجارة واقتصاد", "محاسبة",
                      "إدارة سلاسل الإمداد", "الموارد البشرية", "إدارة الضيافة", "ريادة الأعمال", "التمويل والبنوك"]:
            major_categories["💼 تخصصات الأعمال والقانون"].append(major)
        
        elif major in ["الجرافكس", "التصميم الداخلي", "الفنون الجميلة", "التصميم الصناعي", "العمارة الداخلية",
                      "تصميم الأزياء", "السينما والإخراج", "الموسيقى", "المسرح", "التصوير الفوتوغرافي"]:
            major_categories["🎨 تخصصات الفنون والتصميم"].append(major)
        
        elif major in ["الزراعة", "الطب البيطري", "الغابات", "تنسيق الحدائق", "علم المياه",
                      "الاستدامة البيئية", "هندسة البيئة"]:
            major_categories["🌱 تخصصات الزراعة والبيئة"].append(major)
    
    # بناء رسالة مع جميع التخصصات
    message_text = "🎓 *قائمة التخصصات المتاحة في الاختبار* 🎓\n\n"
    message_text += "اختبار شامل من 30 سؤال لمساعدتك في اكتشاف التخصص المناسب لك\n"
    message_text += "━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    
    # استخدام نفس صيغة التخصصات الموجودة في ملف bot_data.json
    message_text += "📚 *التخصصات المتاحة في الاختبار:*\n\n"
    
    message_text += "✅ *تخصصات الحاسوب والتقنية:*\n"
    message_text += "تكنولوجيا معلومات - نظم معلومات - علوم الحاسوب - أمن سيبراني - جرافكس\n\n"
    
    message_text += "✅ *تخصصات الهندسة:*\n"
    message_text += "هندسة مدنية - هندسة كهربائية - هندسة ميكانيكية - هندسة معمارية - ميكاترونكس - هندسة طبية وحيوية\n\n"
    
    message_text += "✅ *تخصصات الصحة:*\n"
    message_text += "طب وجراحة - مختبرات - تمريض - تخدير - تغذية علاجية - الاشعة - علاج طبيعي - طب اسنان - فني اسنان - صيدلة\n\n"
    
    message_text += "✅ *تخصصات الأعمال:*\n"
    message_text += "تجارة واقتصاد\n\n"
    
    message_text += "✅ *تخصصات الإنسانيات:*\n"
    message_text += "علم النفس - ترجمة\n\n"
    
    message_text += "✅ *تخصصات كلية التربية:*\n"
    message_text += "تربية قرآن - تربية اسلامية - تربية رياضيات - تربية عربي - تربية علوم - تربية اجتماعيات - تربية فيزياء - تربية كيمياء - تربية احياء - تربية انجليزي\n"
    
    # إضافة معلومات عن كيفية الحصول على معلومات تفصيلية عن التخصصات
    message_text += "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    message_text += "📌 *للحصول على معلومات تفصيلية عن أي تخصص*:\n"
    message_text += "قم بإجراء الاختبار وعند ظهور النتائج اضغط على زر 'معلومات أكثر عن التخصص' 🔍\n\n"
    
    # إضافة أزرار التنقل
    keyboard = [
        [
            InlineKeyboardButton("🚀 بدء الاختبار", callback_data="yes"),
            InlineKeyboardButton("🔙 العودة", callback_data="back_to_welcome")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # حذف الرسالة السابقة إن وجدت
    if hasattr(context, 'all_majors_message_id'):
        try:
            context.bot.delete_message(chat_id=chat_id, message_id=context.all_majors_message_id)
        except Exception as e:
            logger.error(f"Error deleting message: {e}")
    
    # إرسال رسالة بجميع التخصصات
    msg = context.bot.send_message(
        chat_id=chat_id,
        text=message_text,
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )
    
    # تخزين معرف الرسالة للاستخدام لاحقاً
    if user_id in message_ids:
        message_ids[user_id].append(msg.message_id)
    else:
        message_ids[user_id] = [msg.message_id]
    context.all_majors_message_id = msg.message_id
    
    return START_CONFIRMATION


def ask_next_question(update: Update, context: CallbackContext) -> int:
    """عرض السؤال التالي للمستخدم"""
    user_id = update.effective_chat.id
    index = current_question_index[user_id]

    # التحقق من وجود أسئلة أخرى
    if index < len(questions):
        question, options, _ = questions[index]
        
        # إنشاء أزرار الإجابات مع رموز تعبيرية
        keyboard = []
        choice_icons = ["🅰️", "🅱️", "©️", "🅿️", "🔹", "🔸", "🔺", "🔻"]  # رموز للخيارات
        for i, option in enumerate(options):
            icon = choice_icons[i] if i < len(choice_icons) else "⚪"
            keyboard.append([InlineKeyboardButton(f"{icon} {option}", callback_data=f"{index}:{i}")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # تقدم الاختبار
        progress = int((index / len(questions)) * 10)
        progress_bar = "🟦" * progress + "⬜" * (10 - progress)
        
        # إضافة رقم السؤال الحالي والعدد الإجمالي مع تنسيق جذاب
        question_text = f"❓ *السؤال {index + 1} من {len(questions)}* ❓\n"
        question_text += f"{progress_bar} ({int((index/len(questions))*100)}%)\n\n"
        question_text += f"🔍 {question}\n\n"
        question_text += "👇 اختر الإجابة المناسبة لك:"
        
        # إرسال السؤال مع تنسيق ماركداون
        question_msg = context.bot.send_message(
            chat_id=user_id, 
            text=question_text,
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
        message_ids[user_id].append(question_msg.message_id)
        return ASKING_QUESTIONS
    else:
        # انتهت الأسئلة، الانتقال إلى النتائج
        return finish(update, context)


def handle_button(update: Update, context: CallbackContext) -> int:
    """معالجة الإجابة على السؤال"""
    query = update.callback_query
    try:
        query.answer()
    except Exception as e:
        logger.warning(f"لم نتمكن من الرد على استدعاء الزر: {e}")
        # نستمر في تنفيذ الوظيفة حتى لو فشل الرد على الاستدعاء
    
    user_id = query.from_user.id
    query_data = query.data
    
    # التحقق من أن هذه استجابة لسؤال وليست لإجراء آخر
    if ":" not in query_data:
        # هذه ليست استجابة لسؤال، بل ربما إجراء مثل "restart" أو "my_history" 
        # يجب أن يُعالج بواسطة وظيفة أخرى
        logger.info(f"زر إجراء: {query_data}")
        return FINISHED
    
    # التحقق من صيغة البيانات قبل المعالجة
    try:
        # استخراج رقم السؤال ورقم الإجابة
        index, choice = map(int, query_data.split(":"))
        
        if index == current_question_index[user_id]:
            # إضافة النقاط بناء على الإجابة
            scores = questions[index][2][choice]
            for major, points in scores.items():
                user_scores[user_id][major] += points
        
        # تحديث إحصائيات إجابة السؤال
        update_statistics("question_answer", {
            "user_id": user_id,
            "question_index": index,
            "choice": choice
        })
        
        # الانتقال للسؤال التالي
        current_question_index[user_id] += 1
        
        # حذف رسالة السؤال الحالي
        try:
            context.bot.delete_message(chat_id=user_id, message_id=query.message.message_id)
        except Exception as e:
            logger.error(f"Error deleting message: {e}")
        
        # عرض السؤال التالي
        return ask_next_question(update, context)
    except ValueError as ve:
        # خطأ في تنسيق البيانات
        logger.error(f"خطأ في تنسيق بيانات الزر: {query_data}, الخطأ: {ve}")
        return FINISHED
    except Exception as e:
        logger.error(f"حدثت مشكلة أثناء معالجة الإجابة: {query_data}, الخطأ: {e}")
        return ASKING_QUESTIONS


def finish(update: Update, context: CallbackContext) -> int:
    """إظهار نتائج الاختبار"""
    user_id = update.effective_chat.id
    
    # الحصول على أفضل 3 تخصصات
    sorted_majors = sorted(user_scores[user_id].items(), key=lambda x: x[1], reverse=True)
    top_three = sorted_majors[:3]
    
    # حفظ تاريخ النتائج مع الوقت
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # حفظ كل نتائج التخصصات بتنسيق أفضل
    all_results = {}
    for major, score in sorted_majors:
        all_results[major] = score
    
    # تحديث إحصائيات إكمال الاختبار مع نتائج مفصلة
    update_statistics("complete_quiz", {
        "user_id": user_id,
        "result": top_three[0][0],
        "score": top_three[0][1],
        "date": now,
        "all_results": all_results
    })
    
    # تحديث إحصائيات نتيجة التخصص
    update_statistics("major_result", {
        "user_id": user_id,
        "major": top_three[0][0]
    })
    
    # إضافة رموز مميزة للتخصصات (تحسين تغطية أكثر شمولاً)
    major_icons = {
        # تخصصات الحاسوب والتقنية
        "هندسة البرمجيات": "💻",
        "علوم الحاسب": "💻",
        "الذكاء الاصطناعي": "🤖",
        "تقنية معلومات": "💾",
        "أمن سيبراني": "🔒",
        "تطوير الألعاب": "🎮",
        "الجرافكس": "🎨",
        "علم البيانات": "📊",
        "هندسة الشبكات": "🌐",
        "الحوسبة السحابية": "☁️",
        
        # تخصصات الهندسة
        "الهندسة المعمارية": "🏛️",
        "الهندسة الميكانيكية": "⚙️",
        "الهندسة المدنية": "🏗️",
        "الهندسة الكهربائية": "⚡",
        "ميكاترونكس": "🤖",
        "الهندسة النووية": "☢️",
        "هندسة الطيران": "✈️",
        "هندسة الفضاء": "🚀",
        "الهندسة الطبية": "🩺",
        "الهندسة الكيميائية": "⚗️",
        
        # تخصصات العلوم
        "الرياضيات": "🔢",
        "الفيزياء": "⚛️",
        "الأحياء": "🧬",
        "الكيمياء": "🧪",
        "علم البيئة": "🌳",
        "العلوم البحرية": "🌊",
        "الجيولوجيا": "🪨",
        "الأرصاد الجوية": "🌤️",
        "الفلك": "🔭",
        "علم الأعصاب": "🧠",
        
        # تخصصات الصحة
        "طب بشري": "👨‍⚕️",
        "طب أسنان": "🦷",
        "صيدلة": "💊",
        "تمريض": "🩹",
        "مختبرات": "🧪",
        "طب بيطري": "🐾",
        "الطب النفسي": "🧠",
        "العلاج الطبيعي": "🤸",
        "التغذية": "🥗",
        "الصحة العامة": "🏥",
        
        # تخصصات الإنسانيات والاجتماع
        "علم النفس": "🧠",
        "الفلسفة": "💭",
        "التربية": "👨‍🏫",
        "علم الاجتماع": "👥",
        "الأدب والفنون": "📚",
        "الترجمة": "🔄",
        "علم الإنسان": "🧍",
        "علم الآثار": "🏺",
        "الاتصال الجماهيري": "📡",
        "العلوم السياسية": "🏛️",
        "العلاقات الدولية": "🌍",
        
        # تخصصات الأعمال والقانون
        "إدارة الأعمال": "💼",
        "الاقتصاد": "📈",
        "التسويق": "📢",
        "حقوق": "⚖️",
        "تجارة واقتصاد": "📊",
        "محاسبة": "🧮",
        "إدارة سلاسل الإمداد": "🚚",
        "الموارد البشرية": "👥",
        "إدارة الضيافة": "🏨",
        "ريادة الأعمال": "🚀",
        "التمويل والبنوك": "💰",
        
        # تخصصات الفنون والتصميم
        "التصميم الداخلي": "🏠",
        "الفنون الجميلة": "🖼️",
        "التصميم الصناعي": "🏭",
        "العمارة الداخلية": "🪑",
        "تصميم الأزياء": "👗",
        "السينما والإخراج": "🎬",
        "الموسيقى": "🎵",
        "المسرح": "🎭",
        "التصوير الفوتوغرافي": "📷",
        
        # تخصصات الزراعة والبيئة
        "الزراعة": "🌱",
        "الغابات": "🌲",
        "تنسيق الحدائق": "🌷",
        "علم المياه": "💧",
        "الاستدامة البيئية": "♻️",
        "هندسة البيئة": "🌍"
    }
    
    # تحديد الرموز لكل تخصص
    top_icons = []
    for major, _ in top_three:
        # استخدام الرمز المناسب أو رمز افتراضي
        icon = major_icons.get(major, "🎓")
        top_icons.append(icon)
    
    # بناء رسالة النتائج بشكل جذاب
    result_text = "✨ *تهانينا!* ✨\n"
    result_text += "┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓\n"
    result_text += "║   🏆 *نتائج اختبار التخصص الدراسي* 🏆   ║\n"
    result_text += "┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛\n\n"
    
    # إضافة الترتيب الأول مع تأثيرات خاصة
    result_text += f"*🥇 التخصص الأنسب لك:* {top_icons[0]} *{top_three[0][0]}*\n"
    result_text += f"     ┗━ التوافق: {top_three[0][1]} نقطة ⭐\n\n"
    
    # إضافة باقي التخصصات بتصميم جذاب
    medal_icons = ["🥈", "🥉"]
    result_text += "*✅ خيارات أخرى مناسبة لك:*\n"
    
    for i, ((major, score), icon) in enumerate(zip(top_three[1:], top_icons[1:]), 1):
        medal = medal_icons[i-1] if i <= len(medal_icons) else "🔹"
        result_text += f"{medal} *{major}* {icon}\n"
        result_text += f"     ┗━ التوافق: {score} نقطة\n"
    
    # إضافة ملاحظات ختامية وتشجيع
    result_text += "\n✨ *ملاحظة:* هذه النتائج تعتمد على إجاباتك في الاختبار، وهي تقدم توجيهًا عامًا فقط.\n"
    result_text += "\n🌟 *نتمنى لك التوفيق في اختيار مسارك الدراسي المناسب!* 🌟"
    
    # حفظ النتائج في تاريخ المستخدم
    data = load_data()
    stats = data.get("statistics", {})
    user_data = stats.setdefault("user_data", {}).setdefault(str(user_id), {})
    results = user_data.setdefault("results", [])
    
    # إضافة نتيجة جديدة
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    results.append({
        "date": timestamp,
        "top_major": top_three[0][0],
        "score": top_three[0][1],
        "all_results": {major: score for major, score in sorted_majors}
    })
    
    # حفظ البيانات
    save_data(data)
    
    # إرسال النتائج مع تنسيق النص
    result_msg = context.bot.send_message(
        chat_id=user_id,
        text=result_text,
        parse_mode="Markdown"
    )
    message_ids[user_id].append(result_msg.message_id)
    
    # تحسين أزرار الإجراءات التالية
    keyboard = [
        [InlineKeyboardButton("🔄 إعادة الاختبار", callback_data="restart")],
        [InlineKeyboardButton("📊 عرض اختباراتي السابقة", callback_data="my_history")],
        [InlineKeyboardButton("🔍 معلومات أكثر عن التخصص", callback_data="more_info")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    restart_msg = context.bot.send_message(
        chat_id=user_id,
        text="*🤔 ماذا تريد أن تفعل الآن؟*",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )
    message_ids[user_id].append(restart_msg.message_id)
    
    return FINISHED


def restart_quiz(update: Update, context: CallbackContext) -> int:
    """إعادة تشغيل الاختبار"""
    query = update.callback_query
    try:
        query.answer()
    except Exception as e:
        logger.warning(f"لم نتمكن من الرد على استدعاء زر إعادة التشغيل: {e}")
        # نستمر في تنفيذ الوظيفة حتى لو فشل الرد على الاستدعاء
    
    # تسجيل إعادة تشغيل الاختبار في الإحصائيات
    user_id = query.from_user.id
    update_statistics("restart_quiz", {"user_id": user_id})
    
    # حذف الرسائل السابقة وبدء اختبار جديد
    chat_id = query.message.chat_id
    context.bot.send_message(
        chat_id=chat_id,
        text="🔄 جاري إعادة تشغيل الاختبار..."
    )
    
    # إعادة تهيئة بيانات المستخدم
    if user_id in user_scores:
        # إعادة تعيين النقاط
        user_scores[user_id] = majors.copy()
    if user_id in current_question_index:
        # إعادة تعيين مؤشر السؤال
        current_question_index[user_id] = 0
    
    # استدعاء دالة start من خلال إرسال رسالة جديدة
    context.bot.send_message(
        chat_id=chat_id,
        text="🎬 مرحباً بك مجدداً في اختبار اكتشاف التخصص المناسب!"
    )
    
    # بدء اختبار جديد
    return ask_next_question(update, context)


def cancel(update: Update, context: CallbackContext) -> int:
    """إلغاء الاختبار"""
    user_id = update.effective_user.id
    
    # تسجيل إلغاء الاختبار في الإحصائيات
    update_statistics("abandon_quiz", {"user_id": user_id})
    
    cancel_msg = update.message.reply_text("❌ تم إلغاء الاختبار. يمكنك البدء من جديد بإرسال /start")
    
    if user_id in message_ids:
        message_ids[user_id].append(cancel_msg.message_id)
    
    return ConversationHandler.END


# وظائف لوحة الإشراف للمدير
def admin_panel(update: Update, context: CallbackContext) -> int:
    """عرض لوحة تحكم المدير"""
    user_id = update.effective_user.id
    
    # التحقق من أن المستخدم هو المدير
    if user_id != ADMIN_CHAT_ID:
        update.message.reply_text("⛔ عذرًا، هذا الأمر مخصص للمشرف فقط!")
        return ConversationHandler.END

    # عرض خيارات لوحة التحكم
    keyboard = [
        [InlineKeyboardButton("📊 لوحة الإحصائيات", callback_data="user_stats")],
        [InlineKeyboardButton("📈 إحصائيات التخصصات", callback_data="major_stats")],
        [InlineKeyboardButton("📅 الإحصائيات اليومية", callback_data="daily_stats")],
        [InlineKeyboardButton("📝 عرض الوصف الحالي", callback_data="show_desc")],
        [InlineKeyboardButton("✏️ تعديل وصف الترحيب", callback_data="edit_desc")],
        [InlineKeyboardButton("❌ خروج", callback_data="exit")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # تحميل البيانات المحدثة
    data = load_data()
    stats = data.get("statistics", {})
    
    # إعداد نص ملخص للإحصائيات
    stats_summary = f"إجمالي المستخدمين: {stats.get('total_users', 0)} | "
    stats_summary += f"اختبارات مكتملة: {stats.get('completed_quizzes', 0)}"
    
    update.message.reply_text(
        f"👨‍💼 مرحبًا بك في لوحة الإشراف!\n\n{stats_summary}\n\nاختر خيارًا من القائمة أدناه:",
        reply_markup=reply_markup
    )
    
    return ADMIN_PANEL


def handle_admin_choice(update: Update, context: CallbackContext) -> int:
    """معالجة اختيارات المدير من لوحة التحكم"""
    query = update.callback_query
    query.answer()
    
    # تحميل البيانات المحدثة
    data = load_data()
    stats = data.get("statistics", {})
    
    if query.data == "user_stats":
        # تجهيز أزرار المعلومات الإضافية
        keyboard = [
            [InlineKeyboardButton("📈 إحصائيات التخصصات", callback_data="major_stats")],
            [InlineKeyboardButton("📊 إحصائيات الأسئلة", callback_data="question_stats")],
            [InlineKeyboardButton("📅 الإحصائيات اليومية", callback_data="daily_stats")],
            [InlineKeyboardButton("👤 بيانات المستخدمين", callback_data="user_data")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="back_to_admin")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # عرض إحصائيات المستخدمين الأساسية
        stats_text = "📊 إحصائيات المستخدمين:\n\n"
        stats_text += f"👥 العدد الكلي للمستخدمين: {stats.get('total_users', 0)}\n"
        stats_text += f"✅ عدد الاختبارات المكتملة: {stats.get('completed_quizzes', 0)}\n"
        stats_text += f"❌ عدد الاختبارات الملغاة: {stats.get('abandoned_quizzes', 0)}\n"
        stats_text += f"🔄 عدد مرات إعادة الاختبار: {stats.get('restart_count', 0)}\n\n"
        stats_text += "اختر من القائمة أدناه لعرض المزيد من التفاصيل:"
        
        query.edit_message_text(
            text=stats_text,
            reply_markup=reply_markup
        )
        
        return ADMIN_PANEL
        
    elif query.data == "major_stats":
        # عرض إحصائيات التخصصات
        major_results = stats.get("major_results", {})
        
        if not major_results:
            stats_text = "🎓 لا توجد بيانات عن نتائج التخصصات بعد"
        else:
            # ترتيب التخصصات حسب الشعبية
            sorted_majors = sorted(major_results.items(), key=lambda x: x[1], reverse=True)
            
            stats_text = "🎓 إحصائيات التخصصات:\n\n"
            for major, count in sorted_majors:
                stats_text += f"- {major}: {count} مستخدم\n"
        
        query.edit_message_text(
            text=stats_text,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع للإحصائيات", callback_data="user_stats")]])
        )
        
        return ADMIN_PANEL
        
    elif query.data == "question_stats":
        # عرض إحصائيات الأسئلة
        question_stats = stats.get("question_stats", {})
        
        if not question_stats:
            stats_text = "❓ لا توجد بيانات عن إجابات الأسئلة بعد"
        else:
            stats_text = "❓ إحصائيات الأسئلة:\n\n"
            
            for q_index, choices in sorted(question_stats.items(), key=lambda x: int(x[0])):
                q_index_int = int(q_index)
                if q_index_int < len(questions):
                    question_text = questions[q_index_int][0]
                    stats_text += f"السؤال {int(q_index) + 1}: {question_text}\n"
                    
                    # عدد الإجابات الكلي لهذا السؤال
                    total_answers = sum(choices.values())
                    
                    # عرض كل خيار ونسبته
                    for choice_idx, count in sorted(choices.items(), key=lambda x: int(x[0])):
                        choice_idx_int = int(choice_idx)
                        if choice_idx_int < len(questions[q_index_int][1]):
                            choice_text = questions[q_index_int][1][choice_idx_int]
                            percentage = (int(count) / total_answers) * 100 if total_answers > 0 else 0
                            stats_text += f"  - {choice_text}: {count} ({percentage:.1f}%)\n"
                    
                    stats_text += "\n"
        
        query.edit_message_text(
            text=stats_text,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع للإحصائيات", callback_data="user_stats")]])
        )
        
        return ADMIN_PANEL
        
    elif query.data == "daily_stats":
        # عرض الإحصائيات اليومية
        daily_usage = stats.get("daily_usage", {})
        
        if not daily_usage:
            stats_text = "📅 لا توجد بيانات عن الاستخدام اليومي بعد"
        else:
            # ترتيب الأيام تنازليًا (الأحدث أولاً)
            sorted_days = sorted(daily_usage.items(), reverse=True)
            
            stats_text = "📅 الإحصائيات اليومية:\n\n"
            for day, day_stats in sorted_days:
                stats_text += f"📆 {day}:\n"
                stats_text += f"  - مستخدمون جدد: {day_stats.get('new_users', 0)}\n"
                stats_text += f"  - اختبارات مكتملة: {day_stats.get('completed_quizzes', 0)}\n"
                stats_text += f"  - اختبارات ملغاة: {day_stats.get('abandoned_quizzes', 0)}\n"
                stats_text += f"  - إعادة تشغيل: {day_stats.get('restart_count', 0)}\n\n"
        
        query.edit_message_text(
            text=stats_text,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع للإحصائيات", callback_data="user_stats")]])
        )
        
        return ADMIN_PANEL
        
    elif query.data == "user_data":
        # عرض بيانات المستخدمين
        user_data = stats.get("user_data", {})
        
        if not user_data:
            stats_text = "👤 لا توجد بيانات مفصلة عن المستخدمين بعد"
        else:
            # عرض ملخص لبيانات المستخدمين
            stats_text = "👤 بيانات المستخدمين:\n\n"
            stats_text += f"عدد المستخدمين المسجلين: {len(user_data)}\n\n"
            
            # المستخدمين الأكثر نشاطًا (حسب عدد الاختبارات المكتملة)
            active_users = sorted(user_data.items(), key=lambda x: x[1].get('completed_quizzes', 0), reverse=True)[:5]
            
            if active_users:
                stats_text += "أكثر المستخدمين نشاطًا:\n"
                for user_id, data in active_users:
                    stats_text += f"- المستخدم {user_id}: {data.get('completed_quizzes', 0)} اختبار مكتمل\n"
            
            # آخر المستخدمين نشاطًا
            stats_text += "\nآخر المستخدمين نشاطًا:\n"
            recent_users = sorted(user_data.items(), key=lambda x: x[1].get('last_active', ''), reverse=True)[:5]
            
            for user_id, data in recent_users:
                stats_text += f"- المستخدم {user_id}: آخر نشاط {data.get('last_active', '')}\n"
        
        query.edit_message_text(
            text=stats_text,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع للإحصائيات", callback_data="user_stats")]])
        )
        
        return ADMIN_PANEL
    
    elif query.data == "show_desc":
        # عرض الوصف الحالي
        query.edit_message_text(
            text=f"📝 الوصف الحالي:\n\n{bot_data['description']}",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="back_to_admin")]])
        )
        
        return ADMIN_PANEL
    
    elif query.data == "edit_desc":
        # تعديل وصف الترحيب
        query.edit_message_text("✏️ أرسل الوصف الجديد:")
        return EDIT_DESCRIPTION
    
    elif query.data == "back_to_admin":
        # العودة للوحة الإشراف
        return admin_panel_callback(update, context)
    
    elif query.data == "exit":
        # الخروج من لوحة الإشراف
        query.edit_message_text("👋 تم الخروج من لوحة الإشراف.")
        return ConversationHandler.END
    
    return ADMIN_PANEL


def admin_panel_callback(update: Update, context: CallbackContext) -> int:
    """إعادة عرض لوحة تحكم المدير"""
    query = update.callback_query
    
    # عرض خيارات لوحة التحكم
    keyboard = [
        [InlineKeyboardButton("📊 لوحة الإحصائيات", callback_data="user_stats")],
        [InlineKeyboardButton("📈 إحصائيات التخصصات", callback_data="major_stats")],
        [InlineKeyboardButton("📅 الإحصائيات اليومية", callback_data="daily_stats")],
        [InlineKeyboardButton("📝 عرض الوصف الحالي", callback_data="show_desc")],
        [InlineKeyboardButton("✏️ تعديل وصف الترحيب", callback_data="edit_desc")],
        [InlineKeyboardButton("❌ خروج", callback_data="exit")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # تحميل البيانات المحدثة
    data = load_data()
    stats = data.get("statistics", {})
    
    # إعداد نص ملخص للإحصائيات
    stats_summary = f"إجمالي المستخدمين: {stats.get('total_users', 0)} | "
    stats_summary += f"اختبارات مكتملة: {stats.get('completed_quizzes', 0)}"
    
    query.edit_message_text(
        f"👨‍💼 مرحبًا بك في لوحة الإشراف!\n\n{stats_summary}\n\nاختر خيارًا من القائمة أدناه:",
        reply_markup=reply_markup
    )
    
    return ADMIN_PANEL


def edit_description(update: Update, context: CallbackContext) -> int:
    """تعديل وصف الترحيب"""
    user_id = update.effective_user.id
    
    # التحقق من أن المستخدم هو المدير
    if user_id != ADMIN_CHAT_ID:
        return ConversationHandler.END

    # تحديث الوصف
    new_desc = update.message.text
    bot_data["description"] = new_desc
    save_data(bot_data)
    
    # إرسال تأكيد التحديث
    update.message.reply_text("✅ تم تحديث وصف الترحيب بنجاح!")
    
    # العودة للوحة الإشراف
    return admin_panel(update, context)


def show_history(update: Update, context: CallbackContext) -> int:
    """عرض تاريخ اختبارات المستخدم"""
    query = update.callback_query
    query.answer()
    
    user_id = query.from_user.id
    chat_id = query.message.chat_id
    
    # تحميل بيانات المستخدم
    data = load_data()
    stats = data.get("statistics", {})
    user_data = stats.get("user_data", {}).get(str(user_id), {})
    
    # الحصول على تاريخ نتائج الاختبارات
    results_history = user_data.get("results", [])
    
    if not results_history:
        # لا يوجد تاريخ اختبارات سابقة
        no_history_text = "┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓\n"
        no_history_text += "┃  📜 *سجل الاختبارات السابقة*  📜  ┃\n"
        no_history_text += "┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛\n\n"
        no_history_text += "⚠️ *لا توجد اختبارات سابقة!* ⚠️\n\n"
        no_history_text += "┌───────────────────────────────┐\n"
        no_history_text += "│ 🔍 يبدو أن هذا أول اختبار      │\n"
        no_history_text += "│    تقوم به، أو أنك لم تكمل     │\n"
        no_history_text += "│    أي اختبارات سابقة.         │\n"
        no_history_text += "└───────────────────────────────┘\n\n"
        no_history_text += "✨ *نصيحة مفيدة:* ✨\n"
        no_history_text += "👉 عند إكمال الاختبارات، ستظهر نتائجك \n"
        no_history_text += "   السابقة هنا لتتمكن من مقارنتها \n"
        no_history_text += "   ومتابعة تطور ميولك المهنية والدراسية!"
        
        keyboard = [
            [InlineKeyboardButton("🔄 إجراء اختبار جديد", callback_data="restart")],
            [InlineKeyboardButton("🏠 العودة للقائمة الرئيسية", callback_data="back_to_results")]
        ]
        
        context.bot.send_message(
            chat_id=chat_id,
            text=no_history_text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return FINISHED
    
    # عرض تاريخ الاختبارات
    loading_animation = "⏳ *جاري تحميل سجل اختباراتك* ⏳\n"
    loading_animation += "┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓\n"
    loading_animation += "┃      🔄 يرجى الانتظار...      ┃\n"
    loading_animation += "┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛"
    
    loading_msg = context.bot.send_message(
        chat_id=chat_id,
        text=loading_animation,
        parse_mode="Markdown"
    )
    
    # حفظ النتائج في سياق المحادثة للاستخدام في التنقل
    context.user_data['results_history'] = results_history
    context.user_data['history_page'] = 0
    
    # حفظ معرف رسالة التحميل ليتم تحديثها لاحقاً
    context.history_message_id = loading_msg.message_id
    
    # عرض صفحة النتائج الأولى (أحدث 5 نتائج)
    return show_history_page(update, context)


def show_history_page(update: Update, context: CallbackContext) -> int:
    """عرض صفحة من تاريخ اختبارات المستخدم"""
    query = update.callback_query
    chat_id = query.message.chat_id
    
    # الحصول على البيانات من سياق المحادثة
    results_history = context.user_data.get('results_history', [])
    current_page = context.user_data.get('history_page', 0)
    
    # عدد النتائج في كل صفحة
    items_per_page = 5
    total_pages = (len(results_history) + items_per_page - 1) // items_per_page
    
    # نطاق النتائج المعروضة
    start_idx = current_page * items_per_page
    end_idx = min(start_idx + items_per_page, len(results_history))
    
    # رموز مميزة للتخصصات
    major_icons = {
        "الهندسة": "🏗️",
        "الطب": "⚕️",
        "العلوم": "🔬",
        "الحاسب الآلي": "💻",
        "الأدب": "📚",
        "الفنون": "🎨",
        "التجارة": "📊",
        "القانون": "⚖️",
        "التربية": "👨‍🏫",
        "الإعلام": "📱",
        "الرياضة": "🏅",
        "الزراعة": "🌱",
        "السياحة": "🏝️",
        "العمارة": "🏛️",
        "الصيدلة": "💊",
        "التصميم": "🎭",
        "علم النفس": "🧠"
    }
    
    # شريط التقدم للصفحات
    page_progress = ""
    for i in range(total_pages):
        if i == current_page:
            page_progress += "🔵"  # الصفحة الحالية
        else:
            page_progress += "⚪"  # الصفحات الأخرى
    
    # عرض عنوان للتاريخ مع تصميم جذاب
    history_text = "┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓\n"
    history_text += "┃  📜 *سجل اختباراتك السابقة* 📜  ┃\n"
    history_text += "┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛\n\n"
    
    # إضافة معلومات الصفحة بإطار جميل
    history_text += "┌─────────────────────────────┐\n"
    history_text += f"│ 📊 *صفحة {current_page + 1} من {total_pages}*  {page_progress} │\n"
    history_text += "└─────────────────────────────┘\n\n"
    
    # عرض النتائج في هذه الصفحة بتنسيق مُحسّن
    current_results = results_history[start_idx:end_idx]
    
    for i, result in enumerate(current_results, start=1):
        # تحديد رمز التخصص
        major = result.get('major', 'غير محدد')
        icon = major_icons.get(major, "🎓")
        
        # إضافة التاريخ والوقت بتنسيق أنيق
        date_str = result.get('date', 'تاريخ غير معروف')
        score = result.get('score', 0)
        
        # إطار جميل لكل نتيجة
        history_text += f"╔══ *نتيجة الاختبار #{i}* ══╗\n"
        history_text += f"║ {icon} *التخصص:* {major}\n"
        history_text += f"║ 📅 *التاريخ:* {date_str}\n"
        history_text += f"║ 🏆 *النتيجة:* {score} نقطة\n"
        history_text += "╚════════════════════════╝\n\n"
    
    # إضافة تلميحات مفيدة
    if total_pages > 1:
        history_text += "✨ *نصائح مفيدة:* ✨\n"
        history_text += "👉 استخدم الأزرار أدناه للتنقل بين صفحات سجل اختباراتك\n"
        history_text += "📊 قارن بين نتائجك السابقة لمتابعة تطور ميولك المهنية\n"
        history_text += "🔍 جرب إعادة الاختبار مرة أخرى للحصول على نتائج أدق"
    
    # إنشاء أزرار التنقل مع رموز تعبيرية
    nav_buttons = []
    
    # أزرار السابق والتالي
    if total_pages > 1:
        nav_row = []
        if current_page > 0:
            nav_row.append(InlineKeyboardButton("◀️ السابق", callback_data="prev_page"))
        
        if current_page < total_pages - 1:
            nav_row.append(InlineKeyboardButton("التالي ▶️", callback_data="next_page"))
        
        if nav_row:
            nav_buttons.append(nav_row)
    
    # أزرار إضافية
    nav_buttons.append([
        InlineKeyboardButton("🔄 إجراء اختبار جديد", callback_data="restart"),
        InlineKeyboardButton("🔙 العودة للنتائج", callback_data="back_to_results")
    ])
    
    reply_markup = InlineKeyboardMarkup(nav_buttons)
    
    # إرسال أو تحديث الرسالة مع تنسيق ماركداون
    if hasattr(context, 'history_message_id'):
        # تحديث الرسالة الموجودة
        try:
            context.bot.edit_message_text(
                text=history_text,
                chat_id=chat_id,
                message_id=context.history_message_id,
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Error updating history message: {e}")
            # في حالة حدوث خطأ أثناء التحديث، إرسال رسالة جديدة
            msg = context.bot.send_message(
                chat_id=chat_id,
                text=history_text,
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
            context.history_message_id = msg.message_id
    else:
        # إرسال رسالة جديدة
        msg = context.bot.send_message(
            chat_id=chat_id,
            text=history_text,
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
        context.history_message_id = msg.message_id
    
    return VIEW_HISTORY


def show_major_info(update: Update, context: CallbackContext) -> int:
    """عرض معلومات تفصيلية عن التخصص"""
    query = update.callback_query
    query.answer()
    
    user_id = query.from_user.id
    chat_id = query.message.chat_id
    
    # الحصول على بيانات نتيجة المستخدم
    data = load_data()
    stats = data.get("statistics", {})
    user_data = stats.get("user_data", {}).get(str(user_id), {})
    results = user_data.get("results", [])
    
    # الحصول على أحدث نتيجة من تاريخ الاختبارات
    if results:
        latest_result = results[-1]
        top_major = latest_result.get("top_major", "")
    else:
        # إذا لم يكن هناك نتائج، عرض قائمة بكل التخصصات
        top_major = list(majors.keys())[0]
    
    # حفظ التخصص الحالي في سياق المحادثة
    context.user_data['current_major'] = top_major
    
    # قائمة التخصصات المتاحة للاستعراض
    context.user_data['available_majors'] = list(majors.keys())
    context.user_data['major_index'] = context.user_data['available_majors'].index(top_major)
    
    # عرض معلومات التخصص
    return show_major_details(update, context)

def show_major_details(update: Update, context: CallbackContext) -> int:
    """عرض معلومات تفصيلية عن التخصص المحدد"""
    query = update.callback_query
    chat_id = query.message.chat_id if query else update.effective_chat.id
    
    # الحصول على التخصص الحالي
    current_major = context.user_data.get('current_major', list(majors.keys())[0])
    
    # تحميل معلومات التخصصات المفصلة من الملف
    bot_data = load_data()
    major_details = bot_data.get("major_details", {})
    
    # معلومات التخصصات (احتياطية في حالة عدم وجود بيانات في ملف البيانات)
    majors_info = {
        "هندسة البرمجيات": {
            "وصف": "تخصص يركز على تطوير وتصميم البرمجيات بشكل منهجي ومهيكل، مع التركيز على جودة وكفاءة أنظمة البرمجيات.",
            "مجالات العمل": ["مطوّر برمجيات", "مهندس برمجيات", "محلل نظم", "مدير مشاريع تقنية"],
            "المهارات المطلوبة": ["البرمجة", "تصميم قواعد البيانات", "تحليل النظم", "إدارة المشاريع"],
            "المواد الدراسية": ["أساسيات البرمجة", "هندسة البرمجيات", "قواعد البيانات", "هياكل البيانات", "أمن المعلومات"],
            "الرمز": "💻"
        },
        "علوم الحاسب": {
            "وصف": "دراسة نظرية وعملية للخوارزميات والبرمجيات والمعلومات، مع التركيز على فهم المفاهيم الأساسية لعلوم الحاسب.",
            "مجالات العمل": ["عالم حاسوب", "محلل خوارزميات", "باحث", "مطور برمجيات"],
            "المهارات المطلوبة": ["التفكير المنطقي", "الرياضيات", "البرمجة", "تصميم الخوارزميات"],
            "المواد الدراسية": ["نظرية الحوسبة", "تصميم البرمجيات", "الذكاء الاصطناعي", "الخوارزميات"],
            "الرمز": "🖥️"
        },
        "الرياضيات": {
            "وصف": "دراسة البنى المجردة والأنماط والعلاقات بين الأرقام والأشكال، وتطبيقاتها النظرية والعملية.",
            "مجالات العمل": ["عالم رياضيات", "محلل إحصائي", "عالم بيانات", "باحث"],
            "المهارات المطلوبة": ["التفكير المنطقي", "التحليل الرياضي", "حل المشكلات", "الدقة"],
            "المواد الدراسية": ["التفاضل والتكامل", "الجبر الخطي", "نظرية الأعداد", "الإحصاء والاحتمالات"],
            "الرمز": "🧮"
        },
        "الهندسة المعمارية": {
            "وصف": "فن وعلم تصميم المباني والمنشآت، مع مراعاة الجوانب الجمالية والوظيفية والبيئية.",
            "مجالات العمل": ["مهندس معماري", "مصمم داخلي", "مخطط مدن", "مصمم مناظر طبيعية"],
            "المهارات المطلوبة": ["التصميم", "الإبداع", "الرسم الهندسي", "استخدام برامج التصميم"],
            "المواد الدراسية": ["تاريخ العمارة", "تصميم معماري", "الرسم الهندسي", "نظريات العمارة"],
            "الرمز": "🏛️"
        },
        "الجرافكس": {
            "وصف": "تخصص يركز على إنشاء وتطوير التصاميم البصرية، بما في ذلك الشعارات والإعلانات والمطبوعات.",
            "مجالات العمل": ["مصمم جرافيك", "مصمم واجهات", "مصمم ويب", "مخرج فني"],
            "المهارات المطلوبة": ["الإبداع", "الفن البصري", "برامج التصميم", "التفكير النقدي"],
            "المواد الدراسية": ["تصميم جرافيك", "التايبوغرافي", "نظرية الألوان", "التسويق البصري"],
            "الرمز": "🎨"
        },
        "الفيزياء": {
            "وصف": "دراسة الطبيعة والمادة والطاقة والقوى، ومحاولة فهم كيفية عمل الكون على المستويات الأساسية.",
            "مجالات العمل": ["عالم فيزياء", "باحث", "مهندس بحث وتطوير", "عالم فلك"],
            "المهارات المطلوبة": ["التحليل الرياضي", "التفكير النقدي", "البحث", "حل المشكلات"],
            "المواد الدراسية": ["الميكانيكا", "الكهرومغناطيسية", "الفيزياء الحديثة", "فيزياء الكم"],
            "الرمز": "⚛️"
        },
        "علم النفس": {
            "وصف": "دراسة العقل البشري والسلوك، مع التركيز على فهم العمليات العقلية والسلوكية.",
            "مجالات العمل": ["معالج نفسي", "مستشار", "باحث", "أخصائي اجتماعي"],
            "المهارات المطلوبة": ["التعاطف", "الاستماع", "التحليل", "المهارات الاجتماعية"],
            "المواد الدراسية": ["علم النفس الإكلينيكي", "علم النفس الاجتماعي", "علم النفس المعرفي"],
            "الرمز": "🧠"
        }
    }
    
    # معلومات عن التخصصات الأخرى المهمة عالمياً
    # تخصصات الحاسوب والتقنية
    majors_info.update({
        "علم البيانات": {
            "وصف": "تخصص متعدد التخصصات يجمع بين الإحصاء وعلوم الحاسوب لتحليل كميات هائلة من البيانات واستخراج رؤى قيمة.",
            "مجالات العمل": ["محلل بيانات", "عالم بيانات", "مهندس بيانات", "أخصائي التعلم الآلي"],
            "المهارات المطلوبة": ["الإحصاء والرياضيات", "البرمجة", "التعلم الآلي", "التفكير التحليلي"],
            "المواد الدراسية": ["خوارزميات البيانات الضخمة", "التعلم الآلي", "الإحصاء التطبيقي", "تحليل البيانات"],
            "الرمز": "📊"
        },
        "أمن سيبراني": {
            "وصف": "تخصص يركز على حماية الأنظمة والشبكات والبرامج من الهجمات الرقمية وتطوير استراتيجيات أمنية للمؤسسات.",
            "مجالات العمل": ["محلل أمن معلومات", "مختبر اختراق", "مدير أمن سيبراني", "مستجيب للحوادث الأمنية"],
            "المهارات المطلوبة": ["معرفة بالشبكات", "فهم الثغرات الأمنية", "البرمجة", "التفكير التحليلي"],
            "المواد الدراسية": ["أمن الشبكات", "التشفير", "استجابة الحوادث", "القانون السيبراني", "تحليل البرمجيات الخبيثة"],
            "الرمز": "🔐"
        },
        "تطوير الألعاب": {
            "وصف": "تخصص يجمع بين البرمجة والفن لتصميم وتطوير ألعاب الفيديو التفاعلية للحواسيب والأجهزة المحمولة ومنصات الألعاب.",
            "مجالات العمل": ["مطور ألعاب", "مصمم ألعاب", "مبرمج محركات ألعاب", "فنان ألعاب ثلاثية الأبعاد"],
            "المهارات المطلوبة": ["البرمجة", "تصميم الجرافيكس", "محركات الألعاب", "الذكاء الاصطناعي"],
            "المواد الدراسية": ["برمجة الألعاب", "الرسوميات ثلاثية الأبعاد", "تصميم المستويات", "الذكاء الاصطناعي للألعاب"],
            "الرمز": "🎮"
        },
        "الحوسبة السحابية": {
            "وصف": "تخصص يركز على تصميم وبناء وإدارة البنية التحتية السحابية والخدمات المستضافة عبر الإنترنت.",
            "مجالات العمل": ["مهندس سحابة", "مهندس DevOps", "مطور تطبيقات سحابية", "مدير بنية تحتية"],
            "المهارات المطلوبة": ["الشبكات", "أنظمة التشغيل", "الأمن السيبراني", "أدوات السحابة"],
            "المواد الدراسية": ["بنية السحابة", "التوزيع والتوازي", "أمن السحابة", "إدارة البيانات"],
            "الرمز": "☁️"
        },
    })
    
    # تخصصات الهندسة
    majors_info.update({
        "الهندسة المدنية": {
            "وصف": "تخصص يركز على تصميم وتنفيذ المشاريع الإنشائية مثل المباني والجسور والطرق والبنية التحتية.",
            "مجالات العمل": ["مهندس مدني", "مهندس إنشائي", "مهندس طرق", "مشرف مشاريع"],
            "المهارات المطلوبة": ["التصميم الهندسي", "الرياضيات", "تحليل الهياكل", "إدارة المشاريع"],
            "المواد الدراسية": ["الميكانيكا الإنشائية", "هندسة الزلازل", "تصميم الخرسانة", "هندسة الأساسات"],
            "الرمز": "🏗️"
        },
        "الهندسة الكهربائية": {
            "وصف": "تخصص يدرس النظم الكهربائية والإلكترونية وتطبيقات الطاقة الكهربائية والاتصالات.",
            "مجالات العمل": ["مهندس كهربائي", "مهندس اتصالات", "مهندس طاقة", "مهندس تحكم"],
            "المهارات المطلوبة": ["تصميم الدوائر", "برمجة الأنظمة المدمجة", "الرياضيات", "حل المشكلات"],
            "المواد الدراسية": ["الدوائر الكهربائية", "الكترونيات القوى", "معالجة الإشارات", "نظم التحكم"],
            "الرمز": "⚡"
        },
        "هندسة الطيران": {
            "وصف": "تخصص يركز على تصميم وتطوير وصيانة الطائرات والمركبات الفضائية ومحركاتها.",
            "مجالات العمل": ["مهندس طيران", "مهندس محركات", "مهندس هياكل", "مهندس أنظمة طيران"],
            "المهارات المطلوبة": ["ديناميكا الهواء", "المواد المتقدمة", "التصميم بمساعدة الحاسوب", "تحليل الأنظمة"],
            "المواد الدراسية": ["ديناميكا الهواء", "ميكانيكا الطيران", "دفع الطائرات", "هياكل الطائرات"],
            "الرمز": "✈️"
        },
        "الهندسة الطبية": {
            "وصف": "تخصص يجمع بين الهندسة والطب لتطوير الأجهزة والمعدات والبرمجيات الطبية وحلول الرعاية الصحية.",
            "مجالات العمل": ["مهندس طبي", "مطور أجهزة طبية", "مهندس أبحاث طبية", "مهندس جودة طبية"],
            "المهارات المطلوبة": ["الإلكترونيات", "معالجة الإشارات", "علم الأحياء", "تصميم الأجهزة"],
            "المواد الدراسية": ["الأجهزة الطبية", "معالجة الصور الطبية", "المستشعرات الحيوية", "التشريح والفسيولوجيا"],
            "الرمز": "🩺"
        },
    })
    
    # تخصصات العلوم والصحة
    majors_info.update({
        "الطب النفسي": {
            "وصف": "تخصص طبي يركز على تشخيص وعلاج ومنع الاضطرابات العقلية والعاطفية والسلوكية.",
            "مجالات العمل": ["طبيب نفسي", "معالج نفسي", "باحث في علوم الدماغ", "استشاري صحة نفسية"],
            "المهارات المطلوبة": ["التشخيص السريري", "التعاطف", "التفكير التحليلي", "مهارات التواصل"],
            "المواد الدراسية": ["علم النفس السريري", "علم الأدوية النفسية", "الطب النفسي للبالغين", "طب نفس الأطفال"],
            "الرمز": "🧠"
        },
        "الصحة العامة": {
            "وصف": "تخصص متعدد التخصصات يركز على حماية وتحسين صحة السكان من خلال التثقيف الصحي والوقاية من الأمراض.",
            "مجالات العمل": ["مسؤول صحة عامة", "محلل سياسات صحية", "باحث وبائيات", "أخصائي تثقيف صحي"],
            "المهارات المطلوبة": ["تحليل البيانات", "مهارات البحث", "التواصل الفعال", "إدارة المشاريع"],
            "المواد الدراسية": ["علم الأوبئة", "السياسات الصحية", "الإحصاء الحيوي", "صحة البيئة", "الوقاية من الأمراض"],
            "الرمز": "🌍"
        },
        "علم الأعصاب": {
            "وصف": "تخصص علمي يدرس الجهاز العصبي والدماغ وكيفية تأثيرهما على السلوك والوظائف المعرفية.",
            "مجالات العمل": ["باحث أعصاب", "عالم أعصاب سريري", "أخصائي تصوير أعصاب", "أخصائي إعادة تأهيل عصبي"],
            "المهارات المطلوبة": ["التفكير التحليلي", "مهارات البحث", "تقنيات المختبر", "تحليل البيانات"],
            "المواد الدراسية": ["تشريح الجهاز العصبي", "فسيولوجيا الأعصاب", "علم النفس العصبي", "علم الأدوية العصبية"],
            "الرمز": "🔬"
        },
        "الفلك": {
            "وصف": "تخصص علمي يدرس الأجرام السماوية والظواهر التي تحدث خارج الغلاف الجوي للأرض.",
            "مجالات العمل": ["عالم فلك", "باحث كونيات", "محلل بيانات فلكية", "مهندس تلسكوبات"],
            "المهارات المطلوبة": ["الفيزياء", "الرياضيات", "تحليل البيانات", "البرمجة"],
            "المواد الدراسية": ["فيزياء فلكية", "الكونيات", "الفلك الرصدي", "فيزياء الفضاء"],
            "الرمز": "🔭"
        },
        "التغذية": {
            "وصف": "تخصص يدرس العلاقة بين الغذاء والصحة وتأثير العناصر الغذائية على وظائف الجسم.",
            "مجالات العمل": ["أخصائي تغذية", "مستشار غذائي", "باحث تغذية", "مخطط وجبات علاجية"],
            "المهارات المطلوبة": ["معرفة بالكيمياء الحيوية", "مهارات التواصل", "التحليل العلمي", "تخطيط الوجبات"],
            "المواد الدراسية": ["كيمياء حيوية للتغذية", "علم التغذية البشرية", "التغذية العلاجية", "تخطيط وجبات"],
            "الرمز": "🥗"
        },
    })
    
    # تخصصات العلوم الإنسانية والاجتماعية
    majors_info.update({
        "العلوم السياسية": {
            "وصف": "تخصص يدرس النظريات والممارسات السياسية وأنظمة الحكم والعلاقات بين المؤسسات السياسية.",
            "مجالات العمل": ["محلل سياسي", "مستشار سياسات", "دبلوماسي", "باحث سياسي"],
            "المهارات المطلوبة": ["التحليل النقدي", "البحث", "الكتابة", "فهم الأنظمة السياسية"],
            "المواد الدراسية": ["النظريات السياسية", "السياسة المقارنة", "العلاقات الدولية", "السياسة العامة"],
            "الرمز": "🏛️"
        },
        "العلاقات الدولية": {
            "وصف": "تخصص يدرس التفاعلات بين الدول والمنظمات الدولية والجهات الفاعلة غير الحكومية.",
            "مجالات العمل": ["دبلوماسي", "محلل شؤون دولية", "مسؤول منظمة دولية", "مستشار سياسي دولي"],
            "المهارات المطلوبة": ["اللغات الأجنبية", "التفاوض", "تحليل السياسات", "فهم الثقافات المختلفة"],
            "المواد الدراسية": ["نظرية العلاقات الدولية", "الاقتصاد السياسي الدولي", "القانون الدولي", "حل النزاعات"],
            "الرمز": "🌐"
        },
        "الاتصال الجماهيري": {
            "وصف": "تخصص يدرس كيفية خلق ونقل المعلومات إلى جماهير واسعة من خلال وسائل الإعلام المختلفة.",
            "مجالات العمل": ["صحفي", "مدير علاقات عامة", "منتج إعلامي", "مدير اتصالات"],
            "المهارات المطلوبة": ["الكتابة والتحرير", "التواصل الفعال", "إنتاج المحتوى", "وسائل التواصل الاجتماعي"],
            "المواد الدراسية": ["نظريات الاتصال", "الصحافة", "الإعلام الرقمي", "العلاقات العامة"],
            "الرمز": "📱"
        },
    })
    
    # تخصصات الأعمال والقانون
    majors_info.update({
        "ريادة الأعمال": {
            "وصف": "تخصص يركز على تطوير المهارات والمعرفة اللازمة لإنشاء وإدارة المشاريع التجارية الجديدة.",
            "مجالات العمل": ["رائد أعمال", "مستشار أعمال ناشئة", "مطور أعمال", "مدير حاضنة أعمال"],
            "المهارات المطلوبة": ["الابتكار", "القيادة", "حل المشكلات", "إدارة المخاطر"],
            "المواد الدراسية": ["نماذج الأعمال", "التمويل الريادي", "التسويق للشركات الناشئة", "الابتكار وتصميم المنتجات"],
            "الرمز": "🚀"
        },
        "التمويل والبنوك": {
            "وصف": "تخصص يدرس إدارة الأموال والاستثمارات والأسواق المالية والعمليات المصرفية.",
            "مجالات العمل": ["محلل مالي", "مصرفي استثماري", "مستشار مالي", "مدير محفظة استثمارية"],
            "المهارات المطلوبة": ["التحليل المالي", "الرياضيات والإحصاء", "فهم الأسواق", "اتخاذ القرارات"],
            "المواد الدراسية": ["الأسواق المالية", "التحليل المالي", "إدارة المخاطر", "التمويل الدولي"],
            "الرمز": "💹"
        },
        "الموارد البشرية": {
            "وصف": "تخصص يركز على إدارة القوى العاملة للمنظمات، بما في ذلك التوظيف والتدريب وتطوير الموظفين.",
            "مجالات العمل": ["مدير موارد بشرية", "أخصائي توظيف", "مستشار تطوير مهني", "مدير تدريب وتطوير"],
            "المهارات المطلوبة": ["التواصل الفعال", "التفاوض", "حل النزاعات", "فهم سلوك الموظفين"],
            "المواد الدراسية": ["إدارة الموارد البشرية", "قانون العمل", "التعويضات والمزايا", "تطوير وتدريب الموظفين"],
            "الرمز": "👥"
        },
    })
    
    # إذا كان التخصص غير موجود في قاعدة البيانات، يتم عرض معلومات عامة
    if current_major not in majors_info:
        majors_info[current_major] = {
            "وصف": "تخصص أكاديمي يتيح الفرصة للطلاب لتطوير المعرفة والمهارات في مجال محدد من الدراسة.",
            "مجالات العمل": ["وظائف متعلقة بالتخصص", "وظائف إدارية", "وظائف في البحث"],
            "المهارات المطلوبة": ["المهارات التقنية", "مهارات التواصل", "مهارات التفكير النقدي"],
            "المواد الدراسية": ["مواد تخصصية", "مواد عامة", "مواد اختيارية"],
            "الرمز": "🎓"
        }
    
    # معلومات التخصص الحالي
    major_data = majors_info[current_major]
    
    # بناء رسالة معلومات التخصص
    info_text = f"*{major_data['الرمز']} معلومات عن تخصص {current_major}*\n"
    info_text += "━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    
    # الوصف
    info_text += "*📝 الوصف:*\n"
    info_text += f"{major_data['وصف']}\n\n"
    
    # مجالات العمل
    info_text += "*💼 مجالات العمل:*\n"
    for field in major_data['مجالات العمل']:
        info_text += f"• {field}\n"
    info_text += "\n"
    
    # المهارات المطلوبة
    info_text += "*🔧 المهارات المطلوبة:*\n"
    for skill in major_data['المهارات المطلوبة']:
        info_text += f"• {skill}\n"
    info_text += "\n"
    
    # المواد الدراسية
    info_text += "*📚 أهم المواد الدراسية:*\n"
    for subject in major_data['المواد الدراسية']:
        info_text += f"• {subject}\n"
    
    # بناء أزرار التنقل
    keyboard = []
    
    # أزرار التنقل بين التخصصات
    nav_row = []
    available_majors = context.user_data.get('available_majors', list(majors.keys()))
    current_index = context.user_data.get('major_index', 0)
    
    if current_index > 0:
        nav_row.append(InlineKeyboardButton("◀️ السابق", callback_data="prev_major"))
    
    if current_index < len(available_majors) - 1:
        nav_row.append(InlineKeyboardButton("التالي ▶️", callback_data="next_major"))
    
    if nav_row:
        keyboard.append(nav_row)
    
    # أزرار إضافية
    keyboard.append([
        InlineKeyboardButton("🔄 إعادة الاختبار", callback_data="restart"),
        InlineKeyboardButton("🔙 العودة للنتائج", callback_data="back_to_results")
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # إرسال أو تحديث الرسالة
    if hasattr(context, 'major_info_message_id'):
        try:
            context.bot.edit_message_text(
                text=info_text,
                chat_id=chat_id,
                message_id=context.major_info_message_id,
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Error updating major info message: {e}")
            msg = context.bot.send_message(
                chat_id=chat_id,
                text=info_text,
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
            context.major_info_message_id = msg.message_id
    else:
        msg = context.bot.send_message(
            chat_id=chat_id,
            text=info_text,
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
        context.major_info_message_id = msg.message_id
    
    return VIEW_MAJOR_INFO

def show_detailed_major_info(update: Update, context: CallbackContext) -> int:
    """عرض معلومات تفصيلية عن التخصص من بيانات التخصصات المفصلة"""
    query = update.callback_query
    query.answer()
    user_id = query.from_user.id
    chat_id = query.message.chat_id
    
    # الحصول على التخصصات من آخر اختبار (أفضل 3 تخصصات)
    data = load_data()
    stats = data.get("statistics", {})
    user_data = stats.get("user_data", {}).get(str(user_id), {})
    results = user_data.get("results", [])
    
    # تخزين قائمة التخصصات المناسبة من نتائج الاختبار
    top_majors = []
    
    if results:
        # آخر نتيجة في التاريخ
        last_result = results[-1]
        all_results = last_result.get("all_results", {})
        
        # ترتيب التخصصات حسب النقاط تنازلياً
        sorted_majors = sorted(all_results.items(), key=lambda x: x[1], reverse=True)
        
        # أخذ أفضل 3 تخصصات على الأقل
        top_majors = [major for major, _ in sorted_majors[:3]]
        
        # إذا كان هناك تخصصات أكثر بنفس النقاط، نضيفها أيضاً
        for major, score in sorted_majors[3:]:
            if score >= sorted_majors[2][1]:
                top_majors.append(major)
            else:
                break
    
    # إذا لم نجد تخصصات، نستخدم القائمة الافتراضية
    if not top_majors:
        top_majors = list(majors.keys())
    
    # حفظ قائمة التخصصات في context
    context.user_data['available_majors'] = top_majors
    
    # تعيين المؤشر إلى التخصص الأول (الأعلى نقاطاً)
    context.user_data['major_index'] = 0
    current_major = top_majors[0]
    context.user_data['current_major'] = current_major
    
    # تحميل معلومات التخصصات المفصلة من الملف
    bot_data = load_data()
    major_details = bot_data.get("major_details", {})
    
    # التحقق مما إذا كان هناك معلومات مفصلة عن التخصص
    if current_major in major_details:
        major_data = major_details[current_major]
        
        # تحضير رسالة جذابة بمعلومات التخصص مع تصميم محسن
        icon = major_data.get("icon", "🎓")
        
        # عنوان جذاب مع إطار مميز
        info_text = f"✨ {icon} *تفاصيل تخصص {current_major}* {icon} ✨\n"
        info_text += "┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓\n"
        info_text += "┃   📚 *دليلك الشامل للتخصص الدراسي*   ┃\n"
        info_text += "┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛\n\n"
        
        # قسم الوصف بتنسيق أفضل
        info_text += "🔷 *نبذة عن التخصص:*\n"
        info_text += f"┌───────────────────────┐\n"
        info_text += f"│ {major_data.get('description', 'غير متوفر')}\n"
        info_text += f"└───────────────────────┘\n\n"
        
        # قسم المقررات الدراسية مع رموز مميزة
        info_text += "📚 *أهم المقررات الدراسية:*\n"
        course_icons = ["📘", "📗", "📕", "📙", "📓", "📔"]
        for i, course in enumerate(major_data.get("courses", ["غير متوفر"])):
            icon_index = i % len(course_icons)
            info_text += f"{course_icons[icon_index]} {course}\n"
        info_text += "\n"
        
        # قسم المهارات بتنسيق جذاب
        info_text += "💪 *المهارات المطلوبة للنجاح:*\n"
        skill_icons = ["🔹", "🔸", "⭐", "✅", "🌟"]
        for i, skill in enumerate(major_data.get("skills", ["غير متوفر"])):
            icon_index = i % len(skill_icons)
            info_text += f"{skill_icons[icon_index]} {skill}\n"
        info_text += "\n"
        
        # قسم مجالات العمل بتصميم مميز
        info_text += "🔍 *فرص العمل ومجالات التوظيف:*\n"
        for path in major_data.get("career_paths", ["غير متوفر"]):
            info_text += f"🚀 {path}\n"
        info_text += "\n"
        
        # تم إزالة قسم الجامعات بناءً على طلب المستخدم
        
        # قسم معلومات إضافية بإطار خاص
        info_text += "💡 *معلومات إضافية مهمة:*\n"
        info_text += f"┌─────────────────────┐\n"
        info_text += f"│ {major_data.get('info', 'لا توجد معلومات إضافية متاحة.')}\n"
        info_text += f"└─────────────────────┘\n\n"
        
        # ملاحظة ختامية
        info_text += "✨ *هل تريد معلومات عن تخصص آخر؟* ✨\n"
        info_text += "👇 *استخدم الأزرار أدناه للتنقل* 👇"
        
        # أزرار التنقل محسنة
        keyboard = [
            [
                InlineKeyboardButton("⬅️ التخصص السابق", callback_data="prev_major"),
                InlineKeyboardButton("التخصص التالي ➡️", callback_data="next_major")
            ],
            [InlineKeyboardButton("🔙 العودة للنتائج", callback_data="back_to_results")],
            [InlineKeyboardButton("🔄 إعادة الاختبار", callback_data="restart")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # تحديث رسالة المعلومات
        try:
            query.edit_message_text(
                text=info_text,
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Error updating message: {e}")
            context.bot.send_message(
                chat_id=chat_id,
                text=info_text,
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
        
        return VIEW_MAJOR_INFO
    else:
        # إذا لم تتوفر معلومات مفصلة، استخدم دالة عرض معلومات التخصص الأساسية
        return show_major_details(update, context)

def handle_major_info_navigation(update: Update, context: CallbackContext) -> int:
    """معالجة التنقل بين معلومات التخصصات"""
    query = update.callback_query
    query.answer()
    
    available_majors = context.user_data.get('available_majors', list(majors.keys()))
    current_index = context.user_data.get('major_index', 0)
    
    if query.data == "prev_major":
        # الانتقال للتخصص السابق
        new_index = max(0, current_index - 1)
        context.user_data['major_index'] = new_index
        context.user_data['current_major'] = available_majors[new_index]
        
        # الرجوع إلى صفحة المعلومات التفصيلية
        # نستخدم show_detailed_major_info إذا كان التخصص في قائمة major_details
        bot_data = load_data()
        major_details = bot_data.get("major_details", {})
        
        if context.user_data['current_major'] in major_details:
            # تغيير الرسالة الحالية بدلاً من إرسال رسالة جديدة
            # نستخدم show_major_details دائمًا لعرض البيانات
            return show_major_details(update, context)
        else:
            return show_major_details(update, context)
    
    elif query.data == "next_major":
        # الانتقال للتخصص التالي
        new_index = min(len(available_majors) - 1, current_index + 1)
        context.user_data['major_index'] = new_index
        context.user_data['current_major'] = available_majors[new_index]
        
        # الرجوع إلى صفحة المعلومات التفصيلية
        # نستخدم show_detailed_major_info إذا كان التخصص في قائمة major_details
        bot_data = load_data()
        major_details = bot_data.get("major_details", {})
        
        if context.user_data['current_major'] in major_details:
            # تغيير الرسالة الحالية بدلاً من إرسال رسالة جديدة
            # نستخدم show_major_details دائمًا لعرض البيانات
            return show_major_details(update, context)
        else:
            return show_major_details(update, context)
    
    elif query.data == "back_to_results":
        # العودة لشاشة النتائج وإعادة عرضها
        return finish(update, context)
    
    elif query.data == "restart":
        # إعادة تشغيل الاختبار
        return restart_quiz(update, context)
    
    # التعامل مع الحالات الأخرى
    return VIEW_MAJOR_INFO

def handle_history_navigation(update: Update, context: CallbackContext) -> int:
    """معالجة التنقل في تاريخ الاختبارات"""
    query = update.callback_query
    query.answer()
    
    if query.data == "prev_page":
        # الانتقال للصفحة السابقة
        context.user_data['history_page'] = max(0, context.user_data.get('history_page', 0) - 1)
        return show_history_page(update, context)
    
    elif query.data == "next_page":
        # الانتقال للصفحة التالية
        results_history = context.user_data.get('results_history', [])
        items_per_page = 5
        total_pages = (len(results_history) + items_per_page - 1) // items_per_page
        
        context.user_data['history_page'] = min(
            total_pages - 1,
            context.user_data.get('history_page', 0) + 1
        )
        return show_history_page(update, context)
    
    elif query.data == "back_to_results":
        # العودة لشاشة النتائج وإعادة عرضها
        return finish(update, context)
    
    elif query.data == "restart":
        # إعادة تشغيل الاختبار
        return restart_quiz(update, context)
    
    # التعامل مع الحالات الأخرى
    return VIEW_HISTORY


def error_handler(update, context):
    """معالج الأخطاء الشائعة في البوت"""
    try:
        if update.callback_query:
            # تجاهل الأخطاء المتعلقة بالاستدعاءات القديمة
            if "Query is too old" in str(context.error):
                logger.warning("تم تجاهل استدعاء قديم")
                return
    except:
        pass
    
    # تسجيل الخطأ
    logger.error(f"خطأ بسبب التحديث {update}: {context.error}")

def main() -> None:
    """تشغيل البوت"""
    # تهيئة نظام التسجيل
    logger.info("بدء تشغيل البوت...")
    
    # عدد محاولات إعادة الاتصال
    max_retries = 10
    retry_count = 0
    retry_delay = 5  # ثوانٍ
    
    while retry_count < max_retries:
        try:
            # إنشاء المحدث
            updater = Updater(TELEGRAM_BOT_TOKEN, request_kwargs={'read_timeout': 30, 'connect_timeout': 30})
            dispatcher = updater.dispatcher
            
            # إضافة معالج الأخطاء
            dispatcher.add_error_handler(error_handler)
    
            # تعريف محادثة المستخدم العادي
            conv_handler = ConversationHandler(
                entry_points=[CommandHandler('start', start)],
                states={
                    START_CONFIRMATION: [CallbackQueryHandler(handle_confirmation)],
                    ASKING_QUESTIONS: [CallbackQueryHandler(handle_button)],
                    FINISHED: [
                        CallbackQueryHandler(restart_quiz, pattern='^restart$'),
                        CallbackQueryHandler(show_history, pattern='^my_history$'),
                        CallbackQueryHandler(show_detailed_major_info, pattern='^more_info$')
                    ],
                    VIEW_HISTORY: [CallbackQueryHandler(handle_history_navigation)],
                    VIEW_MAJOR_INFO: [CallbackQueryHandler(handle_major_info_navigation)]
                },
                fallbacks=[CommandHandler('cancel', cancel)],
                allow_reentry=True
            )
    
            # تعريف محادثة المدير
            admin_handler = ConversationHandler(
                entry_points=[CommandHandler('admin', admin_panel)],
                states={
                    ADMIN_PANEL: [CallbackQueryHandler(handle_admin_choice)],
                    EDIT_DESCRIPTION: [MessageHandler(Filters.text & ~Filters.command, edit_description)]
                },
                fallbacks=[CommandHandler('cancel', cancel)]
            )
    
            # إضافة المحادثات للتطبيق
            dispatcher.add_handler(conv_handler)
            dispatcher.add_handler(admin_handler)
    
            # إضافة رسالة بدء تشغيل
            logger.info("بدء الاستماع للرسائل...")
            
            # بدء البوت بنظام الاستطلاع مع تجاهل الرسائل القديمة
            updater.start_polling(drop_pending_updates=True, timeout=30)
            
            # تنفيذ البوت حتى الضغط على Ctrl-C أو استلام إشارة للتوقف
            updater.idle()
            break  # الخروج من الحلقة إذا تم التوقف بشكل طبيعي
            
        except Exception as e:
            logger.error(f"حدث خطأ أثناء تشغيل البوت: {e}")
            retry_count += 1
            
            if retry_count < max_retries:
                logger.info(f"محاولة إعادة الاتصال بعد {retry_delay} ثوانٍ... (المحاولة {retry_count} من {max_retries})")
                time.sleep(retry_delay)
                # زيادة وقت الانتظار تدريجياً
                retry_delay = min(retry_delay * 2, 60)  # زيادة حتى دقيقة واحدة كحد أقصى
            else:
                logger.error(f"فشلت جميع محاولات إعادة الاتصال. توقف البوت بعد {max_retries} محاولات.")
                raise


if __name__ == '__main__':
    main()
