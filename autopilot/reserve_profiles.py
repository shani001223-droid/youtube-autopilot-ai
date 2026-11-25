"""Finite, original outage-only stories for the two new profiles.
Never reuse a successful topic. Exhaustion fails closed rather than recycling content.
"""
from .research import filter_novel
from .scriptgen import normalize_script, validate_script
from .llm import GeminiUnavailable

HINDI = [
    ("बारहवीं खिड़की", "एक बंद हवेली की ग्यारह खिड़कियों के बीच अचानक बारहवीं खिड़की दिखती है।",
     ["रात को मैं पुरानी हवेली की तस्वीर ले रहा था। उसमें सिर्फ ग्यारह खिड़कियाँ थीं।",
      "अगली तस्वीर में बारहवीं खिड़की चमक रही थी। मैंने सिर उठाया, लेकिन दीवार बिल्कुल खाली थी।",
      "कैमरा फिर उठाया तो नई खिड़की के भीतर मेरा कमरा दिखा। मेज पर वही कैमरा रखा था।",
      "मैं घर भागा। वहाँ दीवार पर एक पुरानी तस्वीर टंगी थी, जिसमें मैं हवेली के बाहर खड़ा था।",
      "तस्वीर में मेरे पीछे बारहवीं खिड़की धीरे धीरे खुल रही थी। कमरे में ठंडी हवा आने लगी।"],
     ["old mansion dusk","glowing mansion window","camera view dark wall","framed photograph desk","window curtain night"],
     "अब मेरे कमरे में ग्यारह खिड़कियाँ हैं।", "तस्वीर लेने से पहले खिड़कियाँ गिन लेना।"),
    ("खाली चाबी", "एक किराएदार को ऐसी चाबी मिलती है जिसकी कोई ताली नहीं है।",
     ["मुझे पुराने मकान की सीढ़ियों पर एक पीतल की चाबी मिली। उस पर मेरा नाम खुदा था।",
      "मैंने उसे मेज पर रख दिया। आधी रात को बंद दरवाजे के पीछे से चाबी घूमने की आवाज आई।",
      "दरवाजे में ताला ही नहीं था। फिर भी लकड़ी पर एक गोल निशान धीरे धीरे उभरने लगा।",
      "अंदर से मेरे बचपन की घड़ी बजने लगी। वह घड़ी बरसों पहले खो चुकी थी।",
      "सुबह चाबी गायब थी। उसकी जगह एक पर्ची रखी थी, जिस पर लिखा था कि कमरा अब खाली है।"],
     ["brass key staircase","key on wooden desk","old locked door mark","antique clock shadows","paper note morning light"],
     "लेकिन मैं अब भी अंदर था।", "कभी अनजान चाबी घर मत लाना।"),
    ("बारिश का नक्शा", "एक नक्शे पर बारिश ऐसी सड़क दिखाती है जो शहर में मौजूद नहीं है।",
     ["एक रात बारिश में मेरा पुराना शहर का नक्शा भीग गया। नीली स्याही अपने आप बहने लगी।",
      "नक्शे पर नई सड़क बनी, जिसका नाम मेरी गली जैसा था। वह मेरे घर तक पहुँचती थी।",
      "मैं बाहर निकला। सड़क के कोने पर एक नया बोर्ड था, जो सुबह तक वहाँ नहीं था।",
      "नक्शे में मेरा घर धीरे धीरे मिट रहा था। असली घर की खिड़कियाँ भी अंधेरी होने लगीं।",
      "मैंने नक्शा मोड़ा और बारिश रुक गई। लेकिन दूर उस सड़क पर अभी भी पानी बह रहा था।"],
     ["wet paper street map","blue ink map closeup","rainy street sign","dark house exterior","empty flooded alley"],
     "वह सड़क मेरे घर का रास्ता याद रखती है।", "अगली बारिश में अपना नक्शा देखना।"),
]
LONG_TITLE = "The Town That Returned Lost Minutes"
LONG_PREMISE = "A railway signal keeper discovers that a disused station can return minutes people have lost, but the town must choose what to remember."
LONG_SCENES = [
("The first envelope arrived on a Tuesday morning, when I was opening the signal office at the edge of Bellweather. There was nothing unusual about the faded paper except the return address. It named a station that had been demolished thirty years earlier.", "old signal office dawn"),
("Inside was a single railway ticket, made from thick grey card. Its destination read Eleven Minutes. Beneath that, in tiny print, was my name and a departure time matching the morning when my father had taught me how to repair a clock.", "grey ticket wooden desk"),
("I remembered that morning clearly, or thought I did. A kettle had boiled, rain had struck the kitchen glass, and my father had placed the clock between us. Then the memory simply stopped. I had never considered those missing minutes important.", "antique clock rainy kitchen"),
("Bellweather was a small town where almost every street ended at the railway. The old platforms had vanished under a car park, but people still called the place North Station. I took the ticket there after work, expecting to find nothing.", "empty station car park dusk"),
("A narrow brass line crossed the asphalt between two painted parking spaces. As I approached it, the evening sounds became muffled. The ticket warmed in my pocket, and a distant bell sounded from somewhere beneath the ground, just once.", "brass line wet asphalt"),
("A stairway appeared where there had been a concrete wall. Beyond it, a platform waited under green lamps. Everything looked newly painted and strangely clean. The station clock showed no hour hand, only a minute hand that did not move.", "green lamps underground platform"),
("The ticket machine stood beside a bench. A brass notice explained the rules in plain language. One ticket could return one lost memory. The traveler must remain on the platform until the clock stopped, and the ticket could never be used again.", "brass notice ticket machine"),
("I placed my ticket into the slot. The lights flickered. Suddenly I could smell the tea from our old kitchen, and I heard my father explaining why a clock sometimes needed to be left alone. He was speaking to me, but I could not see him.", "warm kitchen memory clock"),
("When the memory ended, I found myself on the platform again. Eleven minutes had passed on the wall clock. Only a second had passed on my wristwatch. I left the station feeling oddly grateful, as though something ordinary had finally been returned to me.", "station wristwatch closeup"),
("The next morning, a woman at the bakery asked why I was smiling. Before I could answer, she showed me an envelope identical to mine. The destination was Seven Minutes. She had received it beneath her door shortly after midnight.", "bakery counter grey envelope"),
("Within a week, half the town had tickets. The missing station opened every evening, and people returned with stories about forgotten conversations, lost afternoons, and the last words of friends they had not seen in years. Nobody seemed frightened at first.", "old station evening entrance"),
("Then I noticed that the signal office ledger had changed. A page describing a routine repair now contained an empty strip between two entries. It was exactly eleven minutes long. The time had not merely been recovered. It had been removed from somewhere else.", "railway ledger blank strip"),
("I compared the bakery woman's ticket with the dates in my ledger. The seven minutes she remembered corresponded to seven minutes missing from a shopkeeper's recollection. Neither event had anything to do with the other. The station was transferring time.", "tickets beside open ledger"),
("I started collecting accounts from anyone willing to talk. The pattern grew clearer. For each memory restored, a different person lost a small piece of their own life. The exchange always seemed harmless until I asked what would happen if someone kept returning.", "notebook pinned paper records"),
("The station had no answer for me. The notice remained unchanged, and the ticket machine continued accepting envelopes. But above the platform I discovered a second clock, hidden behind the green lamp. Its minute hand was advancing every time someone entered.", "hidden clock green lamp"),
("I spent the following evening watching the machine rather than using it. Each ticket caused one tiny drawer to open inside the clock. Through the glass I could see dozens of folded slips, each bearing a name and a date. It was an archive.", "clock drawers folded slips"),
("Near the bottom was a drawer labeled Bellweather. It contained no individual names, only a date from thirty years ago. That was the year the original station closed. I realized that the station itself had been waiting for someone to return its lost minutes.", "drawer label old archive"),
("I looked up the closure in the municipal records. On the final day, residents had agreed to preserve the station clock in the town hall. The photograph showed a celebration, but the minutes of the meeting were incomplete. Eleven minutes of the meeting were missing.", "municipal archive newspaper"),
("The archive contained a photograph of my father holding a ticket machine. He had worked at North Station before becoming a clock repairer. In the margin he had written a warning: a clock can lend time, but no clock can create it.", "faded photograph ticket machine"),
("That night I returned to the platform carrying a blank card. I wrote the town's name on it instead of my own. The machine accepted it, and every green lamp went dark. For the first time, the platform clock began moving backward.", "blank card dark platform"),
("The missing meeting came back to me as if I had attended it. The people had not voted to demolish the station. They had voted to close the clock forever, because its promises had become too tempting. Someone had forgotten to remove the machine.", "empty council chamber records"),
("When the lamps returned, the archive drawers stood open. Every borrowed minute had a corresponding slip. A new notice appeared on the machine. The town could restore the original distribution of memories, but everyone would lose the memories they had recently recovered.", "open drawers new notice"),
("I rang the station bell until the residents gathered outside. I explained what we had discovered, and nobody spoke for a long time. Then the baker placed her envelope on the brass line. One by one, the others did the same, including me.", "station bell envelope pile"),
("At sunrise, the stairway vanished. The municipal clock began striking again after decades of silence. I returned to the signal office and found the missing strip in my ledger filled in. My father's eleven minutes had faded, but his warning remained written on the photograph.", "municipal clock sunrise"),
("Years later, I still pass the car park on my way home. Sometimes a brass line appears in the rain. I do not cross it. I have learned that forgetting can be a kind of kindness, and remembering everything can be a dangerous bargain.", "rainy empty car park night"),
]
def _make(title, premise, scenes, queries, ending, loop, hindi=False):
    if hindi:
        hooks = [premise, "क्या होगा अगर एक मामूली चीज अचानक आपकी पूरी दुनिया बदल दे?", "उस रात मुझे लगा सब सामान्य है, लेकिन मैं गलत था।"]
        titles = [title, title + " की रहस्यमयी कहानी", title + " का राज"]
        thumb = ["फिर क्या हुआ", "आखिरी राज", "मत देखना"]
        tags = ["हिंदी डरावनी कहानी", "hindi horror", "रहस्य"]
    else:
        hooks = ["What if the minutes you lost could be returned, but someone else had to lose them?", "The station that vanished thirty years ago began sending people tickets.", "I recovered a memory and discovered that time was being stolen."]
        titles = [title, "The Lost Minutes of Bellweather", "The Station That Borrowed Time"]
        thumb = ["TIME WAS BORROWED", "DON'T USE IT", "MISSING MINUTES"]
        tags = ["original horror story", "supernatural mystery", "cinematic horror"]
    return normalize_script({"logline": premise, "title_ideas":titles, "thumbnail_text":thumb,
        "hooks":hooks, "scenes":[{"narration":n,"visual_query":q,"mood":"dread"} for n,q in zip(scenes,queries)],
        "closing_line":ending,"loop_line":loop,"tags":tags,"content_notes":{"fiction":True,"gore_level":"none"}})

def reserve_profile(settings, recent, rng):
    profile = settings.get("profile")
    if profile == "hindi_shorts":
        entries = HINDI
        hindi = True
    elif profile == "english_long":
        entries = [(LONG_TITLE,LONG_PREMISE,[n for n,q in LONG_SCENES],[q for n,q in LONG_SCENES],
                    "Last week, another envelope appeared on my desk.", "This time, the destination read Tomorrow.")]
        hindi = False
    else:
        raise GeminiUnavailable("No reserve for this profile")
    options = []
    for title,premise,scenes,queries,ending,loop in entries:
        topic = {"topic":title,"premise":premise,"angle":"original outage reserve","why_now":"provider outage; no live trend claim"}
        if not filter_novel([topic],recent): continue
        script = _make(title,premise,scenes,queries,ending,loop,hindi)
        if not validate_script(script,settings): options.append((topic,script))
    if not options:
        raise GeminiUnavailable("Original channel reserve exhausted or unsuitable; wait for provider recovery")
    return rng.choice(options)
