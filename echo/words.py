"""Function and question words: never boosted for Prisma, and ignored when matching memories."""

STOPWORDS = {
    # Devanagari function words
    "में", "है", "हैं", "हो", "गया", "गई", "गए", "की", "का", "के", "को", "से", "पर", "और", "ये", "वो", "तो",
    "भी", "ही", "कि", "मैं", "मुझे", "मेरा", "मेरी", "मेरे", "कल", "आज", "रखो", "रखना", "करना", "करो", "बाकी",
    "नहीं", "था", "थी", "थे", "रहा", "रही", "लिए", "बहुत", "अब", "फिर", "यह", "इसे", "उसे", "हम", "आप",
    "हाँ", "हां", "याद", "दिलाना",
    # Latin Hinglish function words
    "mein", "hai", "hain", "ho", "gaya", "gayi", "gaye", "ki", "ka", "ke", "ko", "se", "par", "aur", "ye", "wo",
    "to", "bhi", "hi", "mujhe", "mera", "meri", "mere", "kal", "aaj", "rakho", "rakhna", "karna", "karo",
    "baaki", "nahi", "tha", "thi", "the", "raha", "rahi", "liye", "bahut", "ab", "phir", "yeh", "isse", "hum",
    "aap", "and", "for", "with", "that", "this", "have", "will", "haan",
    # question words
    "क्या", "कब", "कौन", "कौनसा", "कौनसी", "कितना", "कितने", "कहाँ", "कैसे", "क्यों", "बचा", "बची", "बचे", "कुछ",
    "बताओ", "बता", "kya", "kab", "kaun", "kaunsa", "kaunsi", "kitna", "kitne", "kahan", "kaise", "kyun", "what",
    "when", "which", "how", "status", "bacha", "kuch", "batao", "bata",
}
